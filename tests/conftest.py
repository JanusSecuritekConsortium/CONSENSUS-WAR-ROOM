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

# Aurelius' private store (accounts, interactions, voice relay) must not receive test data either.
if not os.environ.get("AURELIUS_PRIVATE_DIR"):
    _private = tempfile.mkdtemp(prefix="consensus-test-aurelius-private-")
    os.environ["AURELIUS_PRIVATE_DIR"] = _private
    atexit.register(shutil.rmtree, _private, ignore_errors=True)

# Operator profiles and PINs: tests use an empty throwaway file, never the owner's, so the PIN lock is off.
if not os.environ.get("CONSENSUS_USERS_FILE"):
    _users = tempfile.mkdtemp(prefix="consensus-test-users-")
    os.environ["CONSENSUS_USERS_FILE"] = os.path.join(_users, "users.json")
    atexit.register(shutil.rmtree, _users, ignore_errors=True)

# The world map downloads GDELT news events; tests must not reach the network for them.
os.environ.setdefault("BELLATOR_GDELT_EVENTS", "0")

# Online voter models: ignore the owner's .env (keys and model choices) and any shell settings,
# so no test reaches a paid API. Tests that need a route set it themselves.
os.environ["CONSENSUS_ONLINE_ENV_FILE"] = ""
for _name in [name for name in os.environ if name.startswith("CONSENSUS_ONLINE_MODEL_")]:
    del os.environ[_name]


# ---- tests that open real CONSENSUS windows ---------------------------------------------------
# A plain local `pytest` must not put the desktop app on the owner's screen. Tests marked
# `opens_window` start the real Flet app (hidden or not) and run only when
# CONSENSUS_GUI_TESTS=1, which CI sets. Without it, any other test that reaches flet.app()
# fails with a clear error instead of opening a window.
import pytest

GUI_TESTS_ENABLED = os.environ.get("CONSENSUS_GUI_TESTS") == "1"


def pytest_configure(config):
    config.addinivalue_line("markers", "opens_window: starts the real desktop app; needs CONSENSUS_GUI_TESTS=1")


def pytest_collection_modifyitems(config, items):
    if GUI_TESTS_ENABLED:
        return
    skip = pytest.mark.skip(reason="opens a CONSENSUS window; set CONSENSUS_GUI_TESTS=1 to run")
    for item in items:
        if "opens_window" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True, scope="session")
def _no_windows_unless_asked():
    if GUI_TESTS_ENABLED:
        yield
        return
    try:
        import flet
    except ImportError:
        yield
        return

    def refuse(*args, **kwargs):
        raise RuntimeError("This test tried to open a CONSENSUS window; mark it opens_window "
                           "or stub the launcher. Set CONSENSUS_GUI_TESTS=1 to allow it.")

    patcher = pytest.MonkeyPatch()
    patcher.setattr(flet, "app", refuse)
    yield
    patcher.undo()
