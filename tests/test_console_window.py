"""The boot console is hidden after the War Room opens, but only when CONSENSUS owns it."""
from types import SimpleNamespace

from ui.console_window import SW_HIDE, hide_boot_console


def _api(hwnd):
    calls = []
    api = SimpleNamespace(kernel32=SimpleNamespace(GetConsoleWindow=lambda: hwnd),
                          user32=SimpleNamespace(ShowWindow=lambda handle, mode: calls.append((handle, mode))))
    return api, calls


def test_own_console_is_hidden():
    api, calls = _api(77)
    assert hide_boot_console(api, owned=lambda kernel32: True)
    assert calls == [(77, SW_HIDE)]


def test_shared_console_and_no_console_are_left_alone():
    api, calls = _api(77)
    assert not hide_boot_console(api, owned=lambda kernel32: False)
    api_none, calls_none = _api(0)
    assert not hide_boot_console(api_none, owned=lambda kernel32: True)
    assert calls == calls_none == []


def test_api_errors_never_break_startup():
    def broken():
        raise OSError("no console")
    api = SimpleNamespace(kernel32=SimpleNamespace(GetConsoleWindow=broken), user32=None)
    assert not hide_boot_console(api)


def test_ownership_counts_the_packaged_starter_as_consensus():
    from ui.console_window import console_is_ours

    def kernel32_with(*pids):
        def fill(buffer, size):
            for index, pid in enumerate(pids):
                buffer[index] = pid
            return len(pids)
        return SimpleNamespace(GetConsoleProcessList=fill)

    assert console_is_ours(kernel32_with(10, 11), own_ids={10, 11})
    assert not console_is_ours(kernel32_with(10, 11, 99), own_ids={10, 11})  # a terminal shares it


def test_only_the_shutdown_noise_is_dropped():
    import asyncio
    from ui.console_window import quiet_shutdown_errors

    loop = asyncio.new_event_loop()
    reported = []
    loop.set_exception_handler(lambda event_loop, context: reported.append(context["message"]))
    try:
        assert quiet_shutdown_errors(loop)
        handler = loop.get_exception_handler()
        handler(loop, {"message": "noise", "exception": RuntimeError("cannot schedule new futures after shutdown")})
        handler(loop, {"message": "real", "exception": ValueError("broken")})
    finally:
        loop.close()
    assert reported == ["real"]
    assert quiet_shutdown_errors(None) is False
