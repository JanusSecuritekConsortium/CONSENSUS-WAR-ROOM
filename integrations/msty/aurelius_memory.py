"""Bounded shared-memory operations on one native Msty Go Memory Bank pack.

No transcript scraping, network calls, credentials, arbitrary paths or SQL tools.
Each write creates a revision under a SQLite transaction; all other packs remain
untouched. Chat working briefs are intentionally not linked as writable copies.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
from uuid import uuid4

PACK_ID = 'aurelius-shared-persistent-memory'
PACK_TITLE = 'Aurelius — Shared Memory (Telegram + Mobile)'
SECRET = re.compile(r'-----BEGIN .*PRIVATE KEY|\b(?:password|passwd|api[_ -]?key|bot[_ -]?token|access[_ -]?token|secret)\s*[:=]\s*\S+|\b\d{8,12}:[A-Za-z0-9_-]{30,}\b', re.I)


def database_path() -> Path:
    return Path(os.path.expandvars(r'%APPDATA%\Msty Go\msty-go.db'))


def normalize_key(key: str) -> str:
    if not isinstance(key, str):
        raise ValueError('Memory key must be text')
    result = re.sub(r'\s+', '_', key.strip().casefold())
    if not re.fullmatch(r'[\w.-]{1,80}', result):
        raise ValueError('Use a short descriptive memory key without punctuation')
    return result


def validate_value(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 2000:
        raise ValueError('Memory value must be nonempty text of at most 2000 characters')
    if SECRET.search(value) or any(ord(c) < 32 and c not in '\n\t' for c in value):
        raise ValueError('Do not store credentials or control characters in shared memory')
    return value.strip()


def _load(db: sqlite3.Connection) -> tuple[dict, int]:
    row = db.execute('SELECT p.archived,r.state_json,r.revision_number FROM memory_packs p LEFT JOIN memory_pack_revisions r ON r.id=p.current_revision_id AND r.pack_id=p.id WHERE p.id=?', (PACK_ID,)).fetchone()
    if not row or row[0] or row[1] is None:
        raise ValueError('Shared Memory Bank pack is missing or archived; no save was made')
    state = json.loads(row[1])
    if not isinstance(state, dict) or not isinstance(state.get('facts'), list):
        raise ValueError('Shared memory has an unexpected format; no save was made')
    return state, row[2]


def recall(query: str = '', *, db_path: Path | None = None) -> dict:
    if not isinstance(query, str) or len(query) > 200:
        raise ValueError('Recall query must be short text')
    with closing(sqlite3.connect((db_path or database_path()).resolve().as_uri()+'?mode=ro', uri=True, timeout=10)) as db:
        state, revision = _load(db)
    words = re.findall(r'[^\W_]+', query.casefold())
    facts = [fact for fact in state['facts'] if fact.get('status', 'current') == 'current']
    if words:
        facts = [fact for fact in facts if all(word in (str(fact.get('key','')).replace('_',' ')+' '+str(fact.get('value',''))).casefold() for word in words)]
    return {'pack_id': PACK_ID, 'revision': revision, 'found': bool(facts), 'facts': facts[:30], 'truncated': len(facts)>30}


def _index(db: sqlite3.Connection, revision_id: str, state: dict, stamp: str) -> None:
    text = '\n'.join(str(f.get('key',''))+': '+str(f.get('value','')) for f in state['facts'] if f.get('status','current')=='current')
    tags = json.dumps(['aurelius', 'shared', 'telegram', 'mobile'])
    db.execute('INSERT INTO memory_pack_search_docs(pack_id,revision_id,title,summary,tags_json,content_text,updated_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(pack_id) DO UPDATE SET revision_id=excluded.revision_id,title=excluded.title,summary=excluded.summary,tags_json=excluded.tags_json,content_text=excluded.content_text,updated_at=excluded.updated_at', (PACK_ID,revision_id,PACK_TITLE,state['summary'],tags,text,stamp))
    doc_id = db.execute('SELECT id FROM memory_pack_search_docs WHERE pack_id=?', (PACK_ID,)).fetchone()[0]
    db.execute('DELETE FROM memory_pack_fts WHERE rowid=?', (doc_id,))
    db.execute('INSERT INTO memory_pack_fts(rowid,title,summary,tags,content_text) VALUES(?,?,?,?,?)', (doc_id,PACK_TITLE,state['summary'],'aurelius shared telegram mobile',text))


def remember(key: str, value: str, origin: str = 'desktop', *, db_path: Path | None = None) -> dict:
    return _write(key, validate_value(value), origin, False, db_path)


def forget(key: str, origin: str = 'desktop', *, db_path: Path | None = None) -> dict:
    """Explicit-user-request operation; old revisions remain recoverable."""
    return _write(key, None, origin, True, db_path)


def _write(key: str, value: str | None, origin: str, deleting: bool, db_path: Path | None) -> dict:
    key = normalize_key(key)
    if re.search(r'(?:^|[_.-])(?:password|passwd|token|secret|credential|api_key)(?:$|[_.-])', key):
        raise ValueError('Credentials must not be saved as shared memories')
    if origin not in ('telegram', 'mobile', 'desktop'):
        raise ValueError('Origin must be telegram, mobile or desktop')
    path = db_path or database_path()
    if not path.is_file():
        raise ValueError('Msty memory database is unavailable; no save was made')
    stamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
    with closing(sqlite3.connect(path, timeout=10)) as db:
        db.execute('PRAGMA foreign_keys=ON')
        with db:
            db.execute('BEGIN IMMEDIATE')
            state, revision = _load(db)
            facts = state['facts']
            matching = next((f for f in facts if f.get('key')==key), None)
            if deleting and not matching:
                return {'pack_id':PACK_ID,'revision':revision,'forgotten':False,'key':key,'reason':'not found'}
            if not deleting and matching and matching.get('value')==value and matching.get('status','current')=='current':
                return {'pack_id':PACK_ID,'revision':revision,'saved':True,'key':key,'value':value,'unchanged':True}
            if not deleting and not matching and len(facts)>=200:
                raise ValueError('Shared memory is full; review it before adding more facts')
            if deleting:
                state['facts'] = [f for f in facts if f.get('key')!=key]
            else:
                fact = {'id':matching.get('id') if matching else str(uuid4()),'key':key,'value':value,'status':'current','note':'User-confirmed via '+origin+' at '+stamp}
                if matching:
                    facts[facts.index(matching)] = fact
                else:
                    facts.append(fact)
            state['summary'] = 'Shared user-confirmed Aurelius memory for Telegram and mobile. '+ '; '.join(str(f.get('key',''))+': '+str(f.get('value','')) for f in state['facts'])[:3000]
            state['changes_since_last_revision'] = [('Forgot ' if deleting else 'Saved ')+key+' via '+origin]
            revision_id = str(uuid4())
            # MAX protects against another native writer's revision numbering.
            next_revision = db.execute('SELECT COALESCE(MAX(revision_number),0)+1 FROM memory_pack_revisions WHERE pack_id=?', (PACK_ID,)).fetchone()[0]
            db.execute('INSERT INTO memory_pack_revisions(id,pack_id,revision_number,state_json,revision_reason,created_at) VALUES(?,?,?,?,?,?)', (revision_id,PACK_ID,next_revision,json.dumps(state,ensure_ascii=False),('forget:' if deleting else 'remember:')+key,stamp))
            db.execute('UPDATE memory_packs SET current_revision_id=?,updated_at=? WHERE id=?', (revision_id,stamp,PACK_ID))
            _index(db,revision_id,state,stamp)
        # Read-back occurs after commit before reporting success.
        committed, committed_revision = _load(db)
        saved = any(f.get('key')==key and f.get('value')==value for f in committed['facts'])
        if (not deleting and not saved) or (deleting and any(f.get('key')==key for f in committed['facts'])):
            raise ValueError('Memory verification failed; do not claim a successful save')
    return {'pack_id':PACK_ID,'revision':committed_revision,'key':key,('forgotten' if deleting else 'saved'):True, **({} if deleting else {'value':value})}


def main() -> int:
    parser = argparse.ArgumentParser(description='Aurelius shared native Memory Bank helper')
    parser.add_argument('action',choices=('recall','remember','forget'))
    parser.add_argument('--query',default='')
    parser.add_argument('--key')
    parser.add_argument('--value')
    parser.add_argument('--origin',choices=('telegram','mobile','desktop'),default='desktop')
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        if args.action=='recall':
            result = recall(args.query)
        elif args.action=='remember':
            result = remember(args.key,args.value,args.origin)
        else:
            result = forget(args.key,args.origin)
        print(json.dumps(result,ensure_ascii=False))
        return 0
    except (ValueError,sqlite3.Error,OSError) as error:
        print(json.dumps({'saved':False,'error':str(error)},ensure_ascii=False))
        return 1


if __name__=='__main__':
    raise SystemExit(main())
