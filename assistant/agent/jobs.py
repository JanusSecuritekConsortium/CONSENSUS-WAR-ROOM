"""Bounded durable background work; restart never replays an uncertain action."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from threading import Event, RLock
from uuid import uuid4
from .loop import audit


class BackgroundTasks:
    def __init__(self, runtime, path, max_workers=2):
        if not runtime.config.enabled or not runtime.config.background_enabled:
            raise ValueError('Agent background execution is disabled')
        if not 1 <= max_workers <= 4:
            raise ValueError('Invalid background worker count')
        self.runtime = runtime
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._closed = False
        self._futures = {}
        self._cancellations = {}
        self._owner = (self.path.with_suffix('.lock')).open('a+b')
        try:
            if __import__('os').name == 'nt':
                import msvcrt
                if self._owner.tell() == 0:
                    self._owner.write(b'0')
                    self._owner.flush()
                self._owner.seek(0)
                msvcrt.locking(self._owner.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._owner.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._owner.close()
            raise RuntimeError('Another background owner is active') from None
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='aurelius-agent')
        with self._db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, request_key TEXT UNIQUE NOT NULL, status TEXT NOT NULL, prompt TEXT NOT NULL, result TEXT, created_at TEXT NOT NULL)')
            db.execute("UPDATE jobs SET status='interrupted' WHERE status IN ('queued','running','waiting_approval')")

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def submit(self, request_key, prompt):
        if not isinstance(request_key, str) or not 1 <= len(request_key) <= 200 or not isinstance(prompt, str):
            raise ValueError('Invalid background request')
        if len(prompt) > self.runtime.config.context_chars // 2:
            raise ValueError('Background input exceeds budget')
        with self._lock:
            if self._closed:
                raise RuntimeError('Background tasks closed')
            with self._db() as db:
                row = db.execute('SELECT id,prompt FROM jobs WHERE request_key=?', (request_key,)).fetchone()
                if row:
                    if row[1] != prompt:
                        raise ValueError('Request key already belongs to a different task')
                    return row[0]
                count = db.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','running','waiting_approval')").fetchone()[0]
                if count >= 32:
                    raise RuntimeError('Background queue full')
                job_id = uuid4().hex
                db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?)',
                    (job_id, request_key, 'queued', prompt, None, datetime.now(timezone.utc).isoformat()))
            self._cancellations[job_id] = Event()
            self._futures[job_id] = self._pool.submit(self._execute, job_id, prompt)
            return job_id

    def _execute(self, job_id, prompt=None, run_id=None):
        with self._lock:
            with self._db() as db:
                state = db.execute('SELECT status FROM jobs WHERE id=?', (job_id,)).fetchone()[0]
                if state == 'cancelled':
                    return
                db.execute("UPDATE jobs SET status='running' WHERE id=?", (job_id,))
        try:
            result = (self.runtime.resume(run_id) if run_id else self.runtime.run(
                prompt, cancel_event=self._cancellations[job_id])).as_dict()
        except Exception as error:
            result = {'status': 'degraded', 'reason': type(error).__name__}
        with self._lock:
            with self._db() as db:
                state = db.execute('SELECT status FROM jobs WHERE id=?', (job_id,)).fetchone()[0]
                # Cancellation during a callback is cooperative; preserve its actual outcome.
                status = result['status'] if state != 'cancel_requested' else 'cancelled'
                db.execute('UPDATE jobs SET status=?,result=? WHERE id=?',
                    (status, json.dumps(result, ensure_ascii=False), job_id))
            self._futures.pop(job_id, None)
            if status != 'waiting_approval':
                self._cancellations.pop(job_id, None)
        audit('background_result', job_id=job_id, status=status)

    def status(self, job_id):
        with self._db() as db:
            row = db.execute('SELECT status,result,created_at FROM jobs WHERE id=?', (job_id,)).fetchone()
        if row is None:
            raise ValueError('Unknown background job')
        return {'job_id': job_id, 'status': row[0], 'result': json.loads(row[1]) if row[1] else None, 'created_at': row[2]}

    def resume(self, job_id):
        """Host grants exact pending approval to runtime.policy.approvals first."""
        with self._lock:
            if self._closed:
                raise RuntimeError('Background tasks closed')
            current = self.status(job_id)
            if current['status'] != 'waiting_approval':
                raise ValueError('Job is not waiting for approval')
            with self._db() as db:
                db.execute("UPDATE jobs SET status='queued' WHERE id=?", (job_id,))
            self._futures[job_id] = self._pool.submit(self._execute, job_id, None, current['result']['run_id'])

    def cancel(self, job_id):
        with self._lock:
            current = self.status(job_id)
            if current['status'] not in {'queued', 'running', 'waiting_approval'}:
                return False
            future = self._futures.get(job_id)
            stopped = future.cancel() if future else True
            event = self._cancellations.get(job_id)
            if event:
                event.set()
            run_id = (current['result'] or {}).get('run_id')
            if run_id:
                self.runtime.cancel(run_id)
            with self._db() as db:
                db.execute('UPDATE jobs SET status=? WHERE id=?',
                    ('cancelled' if stopped else 'cancel_requested', job_id))
            return True

    def close(self):
        with self._lock:
            self._closed = True
            for event in self._cancellations.values():
                event.set()
        self._pool.shutdown(wait=True, cancel_futures=True)
        self._owner.close()


def register_legacy_schedule(schedule_module, morning, evening):
    """Called by the existing bot owner only. Creates no independent daemon."""
    schedule_module.every().day.at('08:00').do(morning)
    schedule_module.every().day.at('18:00').do(evening)
