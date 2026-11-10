"""Hide the boot console once the War Room window is up.

CONSENSUS.exe plays its boot animation in its own console window, which otherwise stays
behind the desktop window until CONSENSUS closes. The console is hidden, not closed: the
process keeps its output handles, and the window disappears for good when CONSENSUS exits.
A console shared with other programs (CONSENSUS started from a terminal) is left alone.
"""
from __future__ import annotations

import sys
from typing import Any, Optional

SW_HIDE = 0


def _windows_api() -> Optional[Any]:
    if sys.platform != "win32":
        return None
    import ctypes

    return ctypes.windll


def _own_process_ids() -> set[int]:
    """This process plus the PyInstaller starter that launched it (same executable)."""
    import os

    ids = {os.getpid()}
    try:
        import psutil

        me = psutil.Process()
        parent = me.parent()
        if parent is not None and getattr(sys, "frozen", False) and parent.exe() == me.exe():
            ids.add(parent.pid)
    except Exception:
        pass
    return ids


def console_is_ours(kernel32: Any, own_ids: Optional[set[int]] = None) -> bool:
    """True when no other process (a shell or terminal) shares this console."""
    import ctypes

    size = 16
    processes = (ctypes.c_uint32 * size)()
    count = kernel32.GetConsoleProcessList(processes, size)
    if count <= 0 or count > size:
        return False
    own = own_ids if own_ids is not None else _own_process_ids()
    return all(processes[index] in own for index in range(count))


def hide_boot_console(api: Optional[Any] = None, *, owned=console_is_ours) -> bool:
    """Hide this process's console window if CONSENSUS opened it. Returns True when hidden."""
    api = api if api is not None else _windows_api()
    if api is None:
        return False
    try:
        hwnd = api.kernel32.GetConsoleWindow()
        if not hwnd or not owned(api.kernel32):
            return False
        api.user32.ShowWindow(hwnd, SW_HIDE)
        return True
    except Exception:
        return False


def _is_shutdown_noise(context: dict) -> bool:
    error = context.get("exception")
    return isinstance(error, RuntimeError) and "after shutdown" in str(error)


def quiet_shutdown_errors(loop: Any) -> bool:
    """Drop the harmless "cannot schedule new futures after shutdown" traceback printed when the window closes.

    Flet hands one last callback to its thread pool after the pool has stopped. Every other loop error
    is still reported as before. Returns True when the handler was installed.
    """
    if loop is None or not hasattr(loop, "set_exception_handler"):
        return False
    previous = loop.get_exception_handler() if hasattr(loop, "get_exception_handler") else None

    def handler(event_loop, context):
        if _is_shutdown_noise(context):
            return
        if previous is not None:
            previous(event_loop, context)
        else:
            event_loop.default_exception_handler(context)

    try:
        loop.set_exception_handler(handler)
    except Exception:
        return False
    return True


__all__ = ["hide_boot_console", "quiet_shutdown_errors"]
