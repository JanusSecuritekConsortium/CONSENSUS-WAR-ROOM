# Phone access: submit proposals and read verdicts from a phone

The phone page is a small web page served by the CONSENSUS PC. From the phone's
browser you sign in with your operator profile and PIN, write a proposal, and
read the verdict when the tribunal has finished.

The PC must be on, with Msty running, because the models live there. The phone
only shows the page.

## What you need once

1. **Operator profiles.** The phone page uses the same profiles and PINs as the
   lock before boot (docs/OPERATOR_LOCK.md). Without at least one profile the
   page refuses to start. Create them with `tools\launchers\manage_users.cmd`.
2. **Tailscale on the PC and on the phone.** Tailscale is a private network
   between your own devices: the phone can reach the PC from anywhere, and
   nothing is opened to the internet. Install it from tailscale.com on both,
   and sign in to the same Tailscale account on both.

## Opening the page

1. On the PC, run `tools\launchers\start_phone_page.cmd`. It prints an address
   such as `http://100.x.y.z:8891/`.
2. On the phone, with Tailscale switched on, open that address in the browser.
3. Choose your name, type your PIN, sign in.

The page stays available while that window on the PC is open. Closing the
window closes the page and signs every phone out.

## What the page does

- **Submit** a proposal (up to 4,000 characters). It becomes an ordinary
  tribunal deliberation with your name on it. One deliberation runs at a time;
  while one is running, a new proposal is refused with "busy". On local models a
  deliberation can take up to an hour.
- **Recent** lists the proposals submitted from phones, by anyone, with who
  submitted each one, its state, and the verdict, confidence and reason once
  finished. It refreshes every 30 seconds.

The page does not show the War Room, the voters' full arguments, or decisions
made at the desktop.

## Safety

- The page listens only on this PC (`127.0.0.1`) or on the one address you
  give it. It refuses to listen on every network.
- Never forward a router port to it or put it on the public internet. The
  connection is plain web traffic, protected only by Tailscale's encryption, and
  a PIN is short.
- Wrong PINs from the phone count toward the same growing wait as at the PC.
- A sign-in lasts 12 hours. Removing a profile ends its phone access at once.

## Settings

Stored in `.env` or the environment:

- `CONSENSUS_PHONE_HOST`: `tailscale` (pick this PC's Tailscale address), or one
  private address. Default `127.0.0.1` (this PC only, for testing).
- `CONSENSUS_PHONE_PORT`: default `8891`.
