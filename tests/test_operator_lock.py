"""Operator profiles, the PIN lock before boot, and who-submitted stamps."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core import identity
from core.identity import gate, store, windows_hello
from core.identity.store import IdentityError

PIN = "2468-fixture"  # a test value, not anyone's real PIN


@pytest.fixture
def users(tmp_path: Path, monkeypatch) -> Path:
    path = tmp_path / "users.json"
    monkeypatch.setattr(store, "USERS_PATH", path)
    identity.sign_in(None)
    yield path
    identity.sign_in(None)


def _console(answers: list[str], pins: list[str]):
    said: list[str] = []
    answers, pins = list(answers), list(pins)
    return said, dict(ask=lambda prompt: answers.pop(0), ask_pin=lambda prompt: pins.pop(0), say=said.append,
                      hello_available=lambda: False, request_hello=lambda message: False)


def test_lock_is_off_until_the_first_profile_exists(users: Path) -> None:
    assert not identity.lock_enabled()
    said, console = _console([], [])
    assert gate.unlock_console(**console) == (True, None)
    assert said == [] and identity.current_operator() is None

    first = identity.add_operator("Fixture Owner", PIN)
    assert first.role == "owner"  # the first profile owns the installation
    assert identity.lock_enabled()
    assert identity.add_operator("Second", PIN + "x").role == "operator"


def test_the_pin_is_not_stored_and_each_profile_has_its_own_salt(users: Path) -> None:
    identity.add_operator("One", PIN)
    identity.add_operator("Two", PIN)
    text = users.read_text(encoding="utf-8")
    assert PIN not in text
    one, two = json.loads(text)["users"]
    assert one["salt"] != two["salt"] and one["pin_digest"] != two["pin_digest"]


def test_pin_and_name_rules(users: Path) -> None:
    for bad_pin in ("123", "1111", "x" * 65):
        with pytest.raises(IdentityError):
            identity.add_operator("Owner", bad_pin)
    for bad_name in ("", "   ", "a" * 33, "semi;colon"):
        with pytest.raises(IdentityError):
            identity.add_operator(bad_name, PIN)
    identity.add_operator("Owner", PIN)
    with pytest.raises(IdentityError):
        identity.add_operator("owner", PIN)  # names differ only by case
    assert not users.with_name("users.json.tmp").exists()


def test_verify_pin_and_growing_wait_that_survives_a_restart(users: Path) -> None:
    identity.add_operator("Owner", PIN)
    assert identity.verify_pin("owner", PIN, now=1000).ok
    assert not identity.verify_pin("nobody", PIN, now=1000).ok

    assert identity.verify_pin("Owner", "wrong-1", now=1000).wait_seconds == 0
    assert identity.verify_pin("Owner", "wrong-2", now=1000).wait_seconds == 0
    assert identity.verify_pin("Owner", "wrong-3", now=1000).wait_seconds == 5
    # During the wait even the right PIN is refused; the wait is in the file, not in memory.
    blocked = identity.verify_pin("Owner", PIN, now=1002)
    assert not blocked.ok and blocked.wait_seconds == 3
    assert identity.verify_pin("Owner", "wrong-4", now=1006).wait_seconds == 10
    assert identity.verify_pin("Owner", PIN, now=1017).ok
    assert identity.verify_pin("Owner", "wrong-again", now=1018).wait_seconds == 0  # counter was reset


def test_change_pin_remove_and_last_owner_protection(users: Path) -> None:
    identity.add_operator("Owner", PIN)
    identity.add_operator("Guest", PIN + "g")
    identity.change_pin("Guest", "new-guest-pin")
    assert identity.verify_pin("Guest", "new-guest-pin").ok and not identity.verify_pin("Guest", PIN + "g").ok
    with pytest.raises(IdentityError):
        identity.remove_operator("Owner")  # would leave profiles nobody can manage
    identity.remove_operator("Guest")
    identity.remove_operator("Owner")
    assert not identity.lock_enabled()
    with pytest.raises(IdentityError):
        identity.change_pin("Owner", PIN)


def test_damaged_profile_file_keeps_the_door_shut(users: Path) -> None:
    users.write_text("{not json", encoding="utf-8")
    with pytest.raises(IdentityError):
        identity.lock_enabled()
    said, console = _console([], [])
    assert gate.unlock_console(**console) == (False, None)
    assert said[-1] == "ACCESS DENIED"


def test_gate_accepts_the_right_pin_and_signs_the_operator_in(users: Path) -> None:
    identity.add_operator("Owner", PIN)
    said, console = _console([], ["wrong", PIN])
    allowed, operator = gate.unlock_console(**console)
    assert allowed and operator.name == "Owner"
    assert identity.current_operator_name() == "Owner"
    assert "IDENTITY CONFIRMED: Owner" in said
    assert PIN not in "\n".join(said)


def test_gate_refuses_after_wrong_pins_and_on_cancel(users: Path) -> None:
    identity.add_operator("Owner", PIN)
    said, console = _console([], ["a-wrong", "b-wrong", "c-wrong", PIN])
    assert gate.unlock_console(**console) == (False, None)  # third wrong PIN starts a wait and ends the try
    assert said[-1] == "ACCESS DENIED" and identity.current_operator() is None

    def cancelled(prompt: str) -> str:
        raise KeyboardInterrupt

    users.unlink()
    identity.add_operator("Owner", PIN)
    said, console = _console([], [])
    console["ask_pin"] = cancelled
    assert gate.unlock_console(**console) == (False, None)


def test_gate_lets_you_pick_a_profile_by_number_or_name(users: Path) -> None:
    identity.add_operator("Owner", PIN)
    identity.add_operator("Guest", "guest-pin-1")
    said, console = _console(["9", "guest"], ["guest-pin-1"])
    allowed, operator = gate.unlock_console(**console)
    assert allowed and operator.name == "Guest" and operator.role == "operator"
    said, console = _console(["1"], [PIN])
    assert gate.unlock_console(**console)[1].name == "Owner"
    said, console = _console(["x", "y", "z"], [])
    assert gate.unlock_console(**console) == (False, None)


def test_windows_hello_is_a_shortcut_only_for_profiles_that_enabled_it(users: Path) -> None:
    identity.add_operator("Owner", PIN)
    asked: list[str] = []
    said, console = _console([], [PIN])
    console.update(hello_available=lambda: True, request_hello=lambda message: asked.append(message) or True)
    assert gate.unlock_console(**console)[0] and asked == []  # not enabled: PIN path, no Hello prompt

    identity.set_windows_hello("Owner", True)
    said, console = _console([], [])
    console.update(hello_available=lambda: True, request_hello=lambda message: asked.append(message) or True)
    assert gate.unlock_console(**console)[1].name == "Owner" and len(asked) == 1

    # Hello cancelled or failed: fall back to the PIN.
    said, console = _console([], [PIN])
    console.update(hello_available=lambda: True, request_hello=lambda message: False)
    assert gate.unlock_console(**console)[0]
    # Hello not set up on this PC: straight to the PIN.
    said, console = _console([], [PIN])
    assert gate.unlock_console(**console)[0]


def test_windows_hello_only_trusts_an_explicit_verified_answer() -> None:
    assert windows_hello.request_hello(run=lambda script, timeout, message="": "Verified")
    for answer in ("Canceled", "DeviceNotPresent", "RetriesExhausted", ""):
        assert not windows_hello.request_hello(run=lambda script, timeout, message="", a=answer: a)
    assert windows_hello.hello_available(run=lambda script, timeout, message="": "Available")
    assert not windows_hello.hello_available(run=lambda script, timeout, message="": "DeviceNotPresent")


def test_boot_stops_before_the_animation_when_identity_is_refused(tmp_path: Path, monkeypatch) -> None:
    from tools import boot

    monkeypatch.setattr(boot, "build_dependency_report", lambda: {"missing_required": []})
    monkeypatch.setattr(boot, "print_human_report", lambda report: None)
    config = tmp_path / "genesis_config.json"
    config.write_text(json.dumps({"backend": "mock", "startup_theme": "MILITARY"}), encoding="utf-8")
    shown: list[str] = []
    common = dict(config_path=config, launch_gui=lambda *a, **kw: shown.append("gui"),
                  render_bios=lambda **kw: shown.append("bios"), hide_console=lambda: None)

    assert boot.run_boot(unlock=lambda: (False, None), **common) == 1
    assert shown == []
    assert boot.run_boot(unlock=lambda: (True, None), **common) == 0
    assert shown == ["bios", "gui"]


def test_proposals_and_decisions_record_who_was_signed_in(users: Path, tmp_path: Path, monkeypatch) -> None:
    from core.proposals.store import create_proposal

    history = tmp_path / "proposal_history.jsonl"
    assert create_proposal(title="t", body="lock off", path=history)["submitted_by"] is None

    identity.add_operator("Owner", PIN)
    identity.sign_in(identity.verify_pin("Owner", PIN).operator)
    assert create_proposal(title="t", body="lock on", path=history)["submitted_by"] == "Owner"
    assert create_proposal(title="t", body="named", submitted_by="Phone Guest", path=history)["submitted_by"] == "Phone Guest"
    assert json.loads(history.read_text(encoding="utf-8").splitlines()[1])["submitted_by"] == "Owner"


def test_exe_in_the_project_shares_the_projects_profile_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("CONSENSUS_USERS_FILE", raising=False)
    project = tmp_path / "project"
    (project / "_ARBITER").mkdir(parents=True)
    (project / "dist").mkdir()
    shared = project / "_ARBITER" / "users.json"
    assert store.default_users_path(project / "dist", frozen=True) == shared  # CONSENSUS.exe in dist
    assert store.default_users_path(project, frozen=False) == shared  # run from source
    # An exe copied somewhere else keeps its own file beside it.
    elsewhere = tmp_path / "usb" / "dist"
    elsewhere.mkdir(parents=True)
    assert store.default_users_path(elsewhere, frozen=True) == elsewhere / "_ARBITER" / "users.json"
    monkeypatch.setenv("CONSENSUS_USERS_FILE", str(tmp_path / "override.json"))
    assert store.default_users_path(project / "dist", frozen=True) == tmp_path / "override.json"


def test_user_menu_requires_an_owner_once_profiles_exist(users: Path) -> None:
    from tools.users import run_menu

    said: list[str] = []
    answers = ["1", "Owner", "0"]
    pins = [PIN, PIN]
    assert run_menu(lambda p: answers.pop(0), lambda p: pins.pop(0), said.append, lambda: False) == 0
    assert identity.find_operator("Owner").role == "owner"

    # Wrong owner PIN: nothing can be changed.
    assert run_menu(lambda p: "1", lambda p: "wrong-pin", said.append, lambda: False) == 1
    assert [operator.name for operator in identity.list_operators()] == ["Owner"]

    answers = ["1", "Guest", "n", "3", "Guest", "0"]
    pins = [PIN, "guest-pin-1", "guest-pin-1"]
    assert run_menu(lambda p: answers.pop(0), lambda p: pins.pop(0), said.append, lambda: False) == 0
    assert identity.find_operator("Guest").role == "operator"
    assert not identity.find_operator("Guest").windows_hello  # Hello is not set up on the fixture PC
    assert PIN not in "\n".join(said)
