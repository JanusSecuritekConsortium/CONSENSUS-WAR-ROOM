"""Host-only, exact-argument, single-use approval grants. Never a model tool."""
import hashlib
import json
from threading import Lock
from time import monotonic
from .contracts import Impact


def fingerprint(run_id, name, arguments):
    raw = json.dumps([run_id, name, arguments], sort_keys=True, ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


class ApprovalStore:
    def __init__(self):
        self._grants = {}
        self._lock = Lock()

    def grant(self, run_id, name, arguments, ttl_seconds=300):
        """Call only from a trusted host after approving the exact displayed action."""
        if not 0 < ttl_seconds <= 300:
            raise ValueError('Invalid approval expiry')
        with self._lock:
            now = monotonic()
            self._grants = {k: expiry for k, expiry in self._grants.items() if expiry > now}
            if len(self._grants) >= 128:
                raise ValueError('Approval capacity exceeded')
            self._grants[fingerprint(run_id, name, arguments)] = now + ttl_seconds

    def consume(self, run_id, name, arguments):
        with self._lock:
            expiry = self._grants.pop(fingerprint(run_id, name, arguments), 0)
            return expiry > monotonic()


class PermissionPolicy:
    def __init__(self, approvals=None, auto_write_tools=frozenset()):
        self.approvals = approvals or ApprovalStore()
        self.auto_write_tools = frozenset(auto_write_tools)

    def allowed(self, run_id, tool, arguments, untrusted_seen):
        if tool.impact == Impact.READ:
            return True
        if self.approvals.consume(run_id, tool.name, arguments):
            return True
        return (tool.impact == Impact.WRITE and tool.name in self.auto_write_tools
                and not untrusted_seen)
