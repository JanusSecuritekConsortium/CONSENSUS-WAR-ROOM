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


__all__ = ["hide_boot_console"]
