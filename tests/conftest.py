"""Keep test deliberations out of the owner's decision history and session memory."""
import atexit
import os
import shutil
import tempfile

# Set before any test module imports core.paths, which reads it once.
if not os.environ.get("CONSENSUS_TEST_DECISION_DIR"):
    _folder = tempfile.mkdtemp(prefix="consensus-test-decisions-")
    os.environ["CONSENSUS_TEST_DECISION_DIR"] = _folder
    atexit.register(shutil.rmtree, _folder, ignore_errors=True)
