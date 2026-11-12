# Operator lock: profiles and a PIN before boot

CONSENSUS can ask who is starting it before the boot sequence runs. Each person
has a named profile with their own PIN. Proposals and decisions record the name
of whoever was signed in.

The lock is **off until the first profile is created**. With no profiles,
CONSENSUS starts exactly as before.

## Switching it on

1. Run `tools\launchers\manage_users.cmd` (or `CONSENSUS.exe --users`).
2. Choose **1 Add profile**, type a name and a PIN twice. The PIN is not shown
   while typing. The first profile becomes the **owner**.
3. From the next start, the boot window shows `IDENTITY CHECK` and asks for the
   PIN before anything else appears.

Later changes in the same menu (add people, change a PIN, remove a profile,
Windows Hello on or off) need an owner's PIN first.

## What a PIN must look like

4 to 64 characters; letters and symbols are allowed, so a passphrase works. One
character repeated (`1111`) is refused.

## Wrong PINs

Three wrong PINs for a profile start a wait of 5 seconds, which doubles with each
further wrong PIN up to 5 minutes. The wait is stored with the profile, so
closing and reopening CONSENSUS does not clear it. A correct PIN resets it.

## Windows Hello (fingerprint, face or the Windows PIN)

An owner can switch Windows Hello on for a profile. At start, Windows then shows
its own prompt; if it confirms, no CONSENSUS PIN is asked. If it is cancelled or
fails, CONSENSUS asks for the PIN as usual.

Windows Hello confirms **whoever is signed in to Windows on this PC**, not a
particular CONSENSUS profile. Switch it on only for the person who owns that
Windows account. Windows performs the check; CONSENSUS never sees a fingerprint.
On a PC without Windows Hello set up, the PIN is asked.

## Roles

- **owner**: may manage profiles. The last owner cannot be removed while other
  profiles exist.
- **operator**: may use CONSENSUS.

Inside the War Room both roles can currently do the same things. The role is
recorded so that limits can be added later.

## What is recorded

- Each proposal in `reports/proposal_history.jsonl` has `submitted_by`.
- Each decision in the system log has `submitted_by`.
- Both are empty (`null`) while the lock is off.

## What this does and does not protect

Profiles live in `_ARBITER/users.json`, which is not published to GitHub. The
packaged app keeps its own copy next to `CONSENSUS.exe` (`dist\_ARBITER\users.json`),
separate from the one used when CONSENSUS is run from source; the launcher above
manages the packaged app's profiles whenever `dist\CONSENSUS.exe` exists. A PIN
is never stored: the file holds a salted scrypt digest, so reading it does not
reveal the PIN.

This is a **door lock for the application**. It does not encrypt anything:
decision records, logs and settings on the drive stay readable in File Explorer,
and someone with access to the files can delete `_ARBITER/users.json` to switch
the lock off. To protect the data if the drive is lost, encrypt the drive (for
example with BitLocker).

The lock covers the normal start of `CONSENSUS.exe` and `consensus_launcher.py`.
It does not yet cover the developer command line (`python main.py`), the local
API or the guest door, which has its own password.

## Forgotten PIN

Another owner can set a new PIN in the menu. If the only owner forgot theirs,
delete `_ARBITER/users.json` and create the profiles again.
