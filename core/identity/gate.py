"""The identity check shown in the boot window before CONSENSUS starts."""
from __future__ import annotations

import getpass
from typing import Callable, List, Optional, Tuple

from core import identity
from core.identity import windows_hello
from core.identity.store import IdentityError, Operator

MAX_PIN_ATTEMPTS = 5


def _choose(operators: List[Operator], ask: Callable[[str], str], say: Callable[[str], None]) -> Optional[Operator]:
    if len(operators) == 1:
        say(f"OPERATOR: {operators[0].name}")
        return operators[0]
    for number, operator in enumerate(operators, 1):
        say(f"  {number}. {operator.name}")
    for _ in range(3):
        answer = ask("OPERATOR (number or name): ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(operators):
            return operators[int(answer) - 1]
        for operator in operators:
            if operator.name.casefold() == answer.casefold():
                return operator
        say("Not on the list.")
    return None


def unlock_console(
    *,
    ask: Callable[[str], str] = input,
    ask_pin: Callable[[str], str] = getpass.getpass,
    say: Callable[[str], None] = print,
    hello_available: Callable[[], bool] = windows_hello.hello_available,
    request_hello: Callable[[str], bool] = windows_hello.request_hello,
) -> Tuple[bool, Optional[Operator]]:
    """Ask who is starting CONSENSUS. Returns (allowed, operator).

    With no profiles the lock is off: (True, None). A profile file that cannot be
    read keeps the door shut instead of opening it."""
    try:
        operators = identity.list_operators()
    except IdentityError as exc:
        say(f"IDENTITY CHECK: {exc}")
        say("ACCESS DENIED")
        return False, None
    if not operators:
        identity.sign_in(None)
        return True, None

    say("")
    say("IDENTITY CHECK")
    try:
        operator = _choose(operators, ask, say)
        if operator is None:
            say("ACCESS DENIED")
            return False, None
        if operator.windows_hello and hello_available():
            say("Windows Hello: confirm in the Windows prompt (or cancel it to type the PIN).")
            if request_hello(f"Unlock CONSENSUS as {operator.name}"):
                identity.sign_in(operator)
                say(f"IDENTITY CONFIRMED: {operator.name}")
                return True, operator
            say("Windows Hello did not confirm. PIN required.")
        for _ in range(MAX_PIN_ATTEMPTS):
            check = identity.verify_pin(operator.name, ask_pin("PIN: "))
            if check.ok and check.operator is not None:
                identity.sign_in(check.operator)
                say(f"IDENTITY CONFIRMED: {check.operator.name}")
                return True, check.operator
            say(check.message or "Name or PIN not recognised.")
            if check.wait_seconds:
                break
    except (EOFError, KeyboardInterrupt):
        say("")
    except IdentityError as exc:
        say(f"IDENTITY CHECK: {exc}")
    say("ACCESS DENIED")
    return False, None
