"""Manage CONSENSUS operator profiles from a console menu.

Run tools\\launchers\\manage_users.cmd, or CONSENSUS.exe --users.
The first profile switches the PIN lock on; removing the last one switches it off.
Once profiles exist, an owner must sign in here before anything can be changed.
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import identity
from core.identity import windows_hello
from core.identity.store import IdentityError, PIN_MIN_LENGTH


def _new_pin(ask_pin: Callable[[str], str], say: Callable[[str], None]) -> str | None:
    first = ask_pin(f"New PIN (at least {PIN_MIN_LENGTH} characters, not shown while typing): ")
    if first != ask_pin("Repeat the PIN: "):
        say("The two PINs differ. Nothing was changed.")
        return None
    return first


def _owner_signs_in(ask: Callable[[str], str], ask_pin: Callable[[str], str], say: Callable[[str], None]) -> bool:
    owners = [operator for operator in identity.list_operators() if operator.role == "owner"]
    if not owners:
        say("No owner profile exists; the operator file needs repair.")
        return False
    name = owners[0].name if len(owners) == 1 else ask("Owner name: ").strip()
    if not any(owner.name.casefold() == name.casefold() for owner in owners):
        say("That is not an owner profile.")
        return False
    check = identity.verify_pin(name, ask_pin(f"PIN of owner {name}: "))
    if not check.ok:
        say(check.message)
    return check.ok


def run_menu(
    ask: Callable[[str], str] = input,
    ask_pin: Callable[[str], str] = getpass.getpass,
    say: Callable[[str], None] = print,
    hello_available: Callable[[], bool] = windows_hello.hello_available,
) -> int:
    try:
        operators = identity.list_operators()
    except IdentityError as exc:
        say(str(exc))
        return 1
    say("CONSENSUS OPERATOR PROFILES")
    if not operators:
        say("The PIN lock is OFF: no profiles exist. The first profile becomes the owner and switches it on.")
    elif not _owner_signs_in(ask, ask_pin, say):
        return 1

    while True:
        operators = identity.list_operators()
        say("")
        for operator in operators:
            hello = ", Windows Hello on" if operator.windows_hello else ""
            say(f"  {operator.name} ({operator.role}{hello})")
        if not operators:
            say("  (no profiles; the PIN lock is off)")
        say("")
        say("1 Add profile   2 Change a PIN   3 Windows Hello on/off   4 Remove profile   0 Finish")
        try:
            choice = ask("Choose: ").strip()
            if choice in {"0", ""}:
                return 0
            if choice == "1":
                name = ask("Name: ")
                role = "owner" if operators and ask("Owner rights? (y/N): ").strip().lower() == "y" else "operator"
                pin = _new_pin(ask_pin, say)
                if pin is not None:
                    created = identity.add_operator(name, pin, role)
                    say(f"Profile {created.name} created ({created.role}).")
            elif choice == "2":
                name = ask("Whose PIN: ")
                pin = _new_pin(ask_pin, say)
                if pin is not None:
                    identity.change_pin(name, pin)
                    say("PIN changed.")
            elif choice == "3":
                name = ask("Profile: ")
                operator = identity.find_operator(name)
                if operator is None:
                    say(f"No profile named {name}.")
                elif operator.windows_hello:
                    identity.set_windows_hello(name, False)
                    say("Windows Hello switched off for this profile.")
                elif not hello_available():
                    say("Windows Hello is not set up on this PC (Windows Settings > Accounts > Sign-in options).")
                else:
                    identity.set_windows_hello(name, True)
                    say("Windows Hello switched on. It confirms whoever is signed in to Windows on this PC,")
                    say("so switch it on only for the person who owns that Windows account.")
            elif choice == "4":
                name = ask("Remove which profile: ")
                if ask(f"Type the name again to remove {name.strip()}: ").strip().casefold() == name.strip().casefold():
                    identity.remove_operator(name)
                    say("Profile removed.")
                else:
                    say("Names differ. Nothing was removed.")
            else:
                say("Choose 0 to 4.")
        except IdentityError as exc:
            say(str(exc))
        except (EOFError, KeyboardInterrupt):
            say("")
            return 0


def main() -> int:
    return run_menu()


if __name__ == "__main__":
    raise SystemExit(main())
