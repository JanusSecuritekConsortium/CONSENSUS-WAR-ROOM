# DIRECTORATE

DIRECTORATE is the Flet desktop's tribunal dispatch desk. Its continuous paper
roll uses fixed-width type, perforated edges, ruled separators and stamped
outcomes inside the existing theme's frame. It adds no
theme key or dependency. The visual reference is the terminal/teletype character
of [Third Bloc](https://store.steampowered.com/app/5155860/Third_Bloc/); no game
resources or text are included.

## Using it

Launch through the existing source launcher or `main.py --gui`. Normal desktop
startup opens the war room and checks configuration, interface, provider, local
memory and runtime capabilities in the background. Ctrl+P DIRECTORATE in the
footer (or Open DIRECTORATE in the command palette) opens the decision register.
Diagnostics → System Checks opens the observed availability checks and preferences.
Invalid configuration opens recovery automatically. JANUS is a theme and has no
startup component row. Pending, running, available, degraded
and failed checks remain distinct. READY requires all checks to finish with
available status. Provider availability means health and model inventory, not
proof of successful generation. Mock mode is explicitly degraded/simulation.

Retry rechecks in a worker; Close permits offline inspection when the
configuration and interface are usable. A corrupt configuration remains intact
and can be corrected locally before retrying. Interface construction failures
fall back to a simple error/retry screen. Prior failed checks remain in the
bounded diagnostics record after successful retries. Normal executable launch
retains the original themed BIOS animation and console handoff before the desktop.
Safe mode and invalid-configuration recovery bypass animation.

The compact panel at the start of LIVE LOGS starts folded on each launch.
Click + DIRECTORATE to unfold and read the latest complete dispatch in its
scrolling paper area; click - DIRECTORATE to fold it again. OPEN shows the full
dispatch desk. Routine startup checks, model
turns and health polling do not appear in this preview or in the paper roll.
Preferences are
stored atomically in the existing local runtime directory in
`directorate_preferences.json`; operator/provider configuration is not rewritten.
Reduced motion freezes ambient cursor/pulse changes and skips synthesis typing
and confidence interpolation. The initialization progress indicator becomes
static. New dispatches reveal whole lines over at most three seconds; reduced
motion shows the full report immediately. Clipboard and export always use the
complete report. The mounted roll retains its reading position during updates.

The session register retains the latest 20 immutable decision snapshots with
monotonically numbered dispatches; it starts fresh with each desktop process.
Existing durable decision storage is unchanged and remains reachable through
HISTORY. A previous dispatch remains available while another query is running.
Each report includes the proposal, individual final votes and actual models,
the ruling and public structured claims, changed-vote explanations, final dissent,
earlier objections, conditions, review requirements, risks and retrieved sources.
Conditions are recorded output, not automatically scheduled follow-up actions.
Only substantive operational notices (model substitutions, assessment/processing
failures, session-save failures and report export outcomes) accompany decisions;
their independent buffer is bounded to 80 so health polling cannot displace them.

COPY LATEST DISPATCH and EXPORT LATEST DISPATCH act on the frozen report, even
when a new proposal has cleared the live result panel. A local archive receipt is
shown only after the file write succeeds. Missing public claims remain explicitly
unavailable; unstructured model reasoning and raw responses are excluded.

CABLE VIEW switches the result panel to a selectable report. STANDARD restores
the existing result presentation. COPY CABLE uses the existing Flet clipboard
API; EXPORT CABLE writes UTF-8 text into the existing local export directory.
REPORT_ARCHIVED is emitted only after a successful file write. Failed exports
retain the report and permit retry. The view preference survives theme changes.

The report includes the actual result/session/date/query, models used (including
earlier substitutions), retrieved references, public final evaluation, explicit
dissent, conditions and limitations. Missing fields are indicated as unavailable.
Sources come from the host's GhostNotes, RSS and normalized feed retrieval, and
local prior-decision identifiers. Model-generated evidence is not misrepresented
as retrieved material. Earlier dissent is distinguished from unresolved final
dissent. Raw responses and private reasoning are excluded. The existing tribunal
score aggregates model self-reports; the cable does not present it as a calibrated
probability or fabricate a confidence percentage.

## Actual integration boundaries

- Msty: the existing health/inventory and model execution adapter.
- AURELIUS: the existing local runtime's capability report. Constructed adapters
  do not prove successful audio, network or agent execution.
- Memory: existing local decision history, context retrieval and session writes.
  No independent MNEMOSYNE service or remote archival receipt is invented.
- JANUS: an existing theme adapter; no independent JANUS service is integrated.

The activity buffer is presentation-independent, protected by a lock and bounded
to 80 immutable events. Events include local time with timezone, component, type,
state, brief operational summary and a proposal/session identifier when relevant.
Desktop producers use the existing worker callbacks; rendering uses the existing
render lock. Events do not expose provider contexts, endpoints, raw exceptions or
model responses. Only explicit result branches create consensus events. Model
failures have ASSESSMENT_FAILED status; explicit peer challenges/rejections create
DISSENT_FILED. No contradiction is inferred from task completion.

DIRECTORATE text colors fall back to the theme text token when a status token
does not meet 4.5:1 contrast against the surface. Text wraps and scrolls; labels
supplement colors. Narrow logical viewports retain usable panel widths with
horizontal body scrolling. The existing header/footer stay in place, and
status/history regions scroll internally. Background polling stops
on disconnect and live updates retain the mounted proposal editor.

## Files

| File | Responsibility |
| --- | --- |
| `core/directorate.py` | Bounded events, observed readiness, provider states, preferences |
| `ui/directorate.py` | Common teletype, activity and cable controls with theme adapters |
| `ui/flet_app.py` | Worker startup/retry, callbacks, clipboard/export, movement and resize integration |
| `ui/components/log_panel.py` | Mounts the shared compact activity panel |
| `ui/components/proposal_panel.py` | Full-height writing area, pinned submission actions and watch option |
| `ui/components/monolith_panel.py` | Border pulse, semantic verdict colours and timed return to theme |
| `ui/deliberation.py` | Allowlisted public assessments, peer objections and revisions |
| `tests/test_directorate_interaction.py` | Long drafts, feedback timing/contrast, live viewer and mounted controls |
| `core/export/cable.py` | Reference provenance, report rendering and local export |
| `tools/boot.py`, `core/cli.py` | Canonical launcher compatibility and normal GUI boot routing |
| `tests/test_directorate.py` | Availability/failure/retry, threads, reports, controls, movement and contrast |
| `tests/test_gui_layout_contract.py` | Locates decision rows by their semantic label |
| `README.md`, `docs/DIRECTORATE.md` | Usage and validation boundaries |

## Initial validation — 2026-10-06

- Focused integration run: 80 tests passed, including existing launcher, GUI,
  deliberation, visual geometry and GhostNotes checks.
- Final focused revision: 30 tests passed, including 25 DIRECTORATE cases and
  five existing refresh/boot checks. Runs overlap; these are not 110 unique tests.
- Nine changed Python files compile; Git whitespace checks pass.
- A hidden native Flet probe mounted the actual startup and checked the configured
  provider health/inventory successfully. It delivered boot/activity/cable control
  trees for all seven themes and a reduced-motion scene. Cable scenes used an
  explicit simulation fixture. A Flet executor warning occurred during probe
  shutdown after scene delivery; this does not constitute a pixel-level review.
- The live Windows screenshot attempt failed with `OSError: screen grab failed`.
  No generated image is presented as a screenshot. Pixel layout, physical Windows
  DPI scaling, keyboard interaction and assistive-technology review remain manual
  verification tasks. Logical geometry, contrast and narrow-window scrolling were
  tested; actual 125%/150% Windows desktop captures were not verified.
- Provider-offline and retry cases used deterministic faults. No real model
  generation, voice output or remote memory/archive service was tested.

Existing uncommitted work was preserved. The initial implementation performed no
source push, merge, dependency installation, service restart or executable rebuild.
Running source processes must reload changed modules; older executable bundles
need rebuilding. GitHub progress publication was rejected by automatic approval
review; the local implementation and validation remain available for review.

## Desktop follow-up — 2026-10-06

The proposal panel starts at its original compact height, with the verdict visible
underneath. Focusing the input to write expands it through the centre column;
leaving the input or submitting restores the compact view. An existing draft alone
does not expand the panel. Resizing updates the mounted regions and preserves the
input, draft and selection. Submission actions remain outside the scrolling text
field. Both sizes constrain the input to the space left after their controls, so
long text cannot push Submit below the panel. The former manual size buttons have
been removed. DIRECTORATE system-status redesign is deferred to a later stage.

Monolith borders gently pulse during actual model execution. Queued roles wait
without a thinking pulse. Completed assessments and the final arbiter verdict
receive 12 seconds of semantic border feedback before returning to the theme:
red for denial/failure, green (cyan in the green military theme) for approval,
and amber or white for abstention, stalemate or escalation. Text status labels
remain after the border returns to idle. Reduced motion keeps static status
colours. Only the borders update on the animation timer; editor focus, card
controls and text remain mounted.

WATCH DELIBERATION optionally opens the live viewer on submission. LIVE
DELIBERATION opens it during or after voting. Assessments appear at the end of
each model turn, across assessment, critique and revision. The view contains the
structured public decision reason, claim, evidence attributed to the model,
assumptions, objections, peer responses, changed-vote explanation, conditions and
review requests. It includes the final arbiter evaluation. It does not expose
provider prompts, retrieved context, raw responses or tagged private reasoning.
Failed validation displays a generic failure instead of raw exception details.
Mock assessments are labelled. Closing the viewer leaves voting running. It
keeps the reading position during live updates and retains at most 12 records
for the current session; new submissions clear the previous view. The watch
preference is saved locally alongside the other DIRECTORATE options.

Follow-up validation: 72 focused interaction, startup, layout and existing GUI
checks passed. The final queue-state and compact-input refinements passed 46
overlapping focused checks; these counts are not additive. Ten implementation
sources compiled and Git whitespace checks passed. A hidden native probe delivered
35 fixture scenes across all seven
themes, including long editor, compact result, live deliberation, verdict feedback
and reduced motion. A Flet executor warning occurred at probe shutdown after all
scene delivery. Pixel screenshots remain unverified. Three existing legacy logo
expectation failures were reproduced separately; their artwork was not changed.

The existing local `dist/CONSENSUS.exe` has now been rebuilt with the current
sources. Its packaged self-test passed, and the archive was checked for the
DIRECTORATE, public deliberation and latest flexible-editor modules. The previous
executable was backed up outside the source repository before an atomic
replacement; the installed file matches the validated build's SHA-256. Reopen
the desktop app to load it. Operator configuration/history and running sessions
were preserved. No dependency installation, source push or merge was performed.

### Editor trigger correction — 2026-10-06

The user clarified that expansion is only for active writing. The default is now
compact, including when a saved draft exists. Focus expands the mounted editor;
blur or submission restores the original proposal/verdict arrangement. Manual
size switches are removed. DIRECTORATE system-status changes remain deferred.
Validation: 68 focused checks passed, both edited UI sources compile, and Git
whitespace checks pass. The hidden native probe delivered 21 idle/editing/blur
transitions across seven themes, retaining the same input control and draft;
pixel screenshots remain unverified. Its known Flet shutdown warning recurred
after scene delivery. The executable was rebuilt, its compact default and focus
callbacks verified inside the archive, and its packaged self-test passed. The
validated build replaced local `dist/CONSENSUS.exe` after backing up the previous
file; installed SHA-256 verified. Running app sessions were preserved.

### Startup access and submission correction — 2026-10-06

Normal launch runs checks in the background. Open the same DIRECTORATE checks
view with the bottom-bar Ctrl+P control, the command palette, or POST in the
activity panel. Configuration recovery still opens automatically when needed.
JANUS remains a selectable theme and is removed from startup components and
readiness requirements. The system-status redesign remains deferred.

Submit stays in place when the editor loses focus to its action row, so the
button does not move during a click. Ctrl+Enter now invokes submission. Inline
feedback acknowledges accepted proposals and explains empty input, configuration
errors, duplicate active submissions, dispatch failures and worker failures.
Optional background checks do not block valid proposals. Dispatch failures
release the submission lock to permit retry.

Validation: 71 focused checks passed, including an actual Submit handler completing
nine mock model assessments. Four edited production sources compile and Git
whitespace checks pass. A hidden native probe delivered 21 control scenes across
seven themes with fixture dispatch; physical mouse clicks, pixel screenshots and
real model generation remain unverified. The known Flet executor warning occurred
after probe delivery. The rebuilt executable passed its packaged self-test and
archive checks for the footer, submission handler and five startup components.
The installed executable was backed up and its SHA-256 verified. Reopen the app
to load the changes. No source push, merge or dependency installation was performed.

### Footer and first outside click — 2026-10-06

Footer commands now have full-height clickable targets. All operator viewers are
positioned and clipped above the footer, including Command and History; transparent
viewer space cannot cover the bar. Export displays its outcome in the proposal
feedback line. Ordinary redraws no longer construct unused disk-backed viewers or
rescan the complete decision log. History and trace views are constructed when
opened.

The editor handles the first outside pointer event and explicitly releases its
focus. It collapses in place, preserving the mounted input and draft. Hover
protection applies to actual proposal action targets rather than the whole row,
so blank space also collapses the editor. Submit remains stable until its click
is delivered; Watch deliberation collapses the editor after changing its setting.

Validation covers 59 distinct selected regression cases across the final runs:
58 passed initially; the remaining case exposed a test Page that did not accept
Flet's `update(control)` API. After correcting that helper, all 13 affected checks
passed (overlapping coverage). Two production sources compile and whitespace
checks pass. A hidden native probe delivered 42 event-dispatch scenes across all
seven themes, covering footer viewer toggles, export feedback and the first
outside event. It waits for each callback and redraw to finish. Physical clicks
and pixel screenshots remain unverified because desktop automation failed to
initialize. Initial Python/Flet test imports also failed; the successful runner
preloaded Flet, disabled automatic garbage collection and optional pytest plugins.
These runner changes do not modify the application runtime.

The rebuilt archive was checked for clickable footer targets, lazy construction
of history/trace viewers and the outside-click handler. Packaged and installed
self-tests passed. The previous executable was backed up before installation;
installed SHA-256 was verified. Close the current app and reopen the rebuilt
`dist/CONSENSUS.exe`. Existing user data and running app sessions were preserved.

### Boot animation restoration — 2026-10-06

The user identified that the executable skipped the original themed boot
animation. The DIRECTORATE integration had left the BIOS renderer callable only
through an explicit hook, so ordinary launches bypassed it. Normal launch again
runs the existing animated theme logo, POST, loading sequence and console handoff
before opening the War Room. DIRECTORATE remains available on demand. Provider
readiness stays pending during the animation and is checked by the desktop worker;
the animation does not perform an extra synchronous provider check. Safe mode
and invalid-configuration recovery continue to bypass the animation.

Validation: 17 focused checks passed, including the default renderer path for
all seven selectable themes, ordering before the GUI, diagnostic modes, executable
entrypoint and configuration recovery. The edited boot source compiles and Git
whitespace checks pass. The animation renderer itself is unchanged.

The executable was rebuilt and its embedded normal-launch path checked for the
restored renderer and console handoff. Packaged and installed self-tests passed;
the previous build was backed up and the installed hash verified. Reopen the
updated local executable to load the restoration.

### Teletype dispatch desk — 2026-10-08

The user approved separating DIRECTORATE from system vitals. Ctrl+P, the footer,
command palette and compact panel now open a continuous paper dispatch desk.
Numbered immutable reports retain proposals, final votes, actual models, public
structured justifications, dissent, conditions, review requirements and attributed
references. Meaningful model substitutions and failures appear as operational
notices. Availability checks and movement preferences are under Diagnostics →
System Checks; automatic configuration recovery and original boot animations remain.

The desktop session retains 20 dispatches and 80 notices; durable decision history
remains separate. A new submission does not erase prior dispatches. Copy/export
uses complete frozen content while the paper reveals whole lines over three
seconds. A separate brief refresh updates only the roll; reduced motion displays
everything immediately. Reader position, mounted editor and submission controls
remain intact.

Validation: 97 focused checks passed, six production sources compile and whitespace
checks pass. A hidden native Flet probe delivered 18 sample-report scenes at
1500×900 and 950×700 across all six selectable themes, including Diagnostics
navigation; no renderer errors were reported. Catalog tests also cover the legacy
NERV alias. Screenshot/physical-pointer review is unverified: the computer-use
kernel could not initialize. No real model generation was required for this UI
change. Rebuilt archive verified for dispatch modules, the short reveal poll and
original boot renderer. Packaged and installed self-tests passed; the previous
executable was backed up and the installed SHA-256 verified. Reopen the executable
to load the changes. Existing sessions and operator data were preserved.

### DIRECTORATE folded by default — 2026-10-08

The user requested that the right-hand DIRECTORATE panel start folded. Each launch
now starts compact, including with an older saved expanded setting. Click
`+ DIRECTORATE` to unfold the complete latest dispatch in a bounded scrolling paper
area, and `- DIRECTORATE` to fold it again. OPEN retains the full dispatch desk.
The open reader remains mounted through ordinary updates to preserve its scroll
position. Fold state is session-only; motion and other preferences still persist.

73 existing affected checks passed. A callback probe verified legacy-preference
handling, unfolding the complete report, keeping the same reader through refresh,
refolding and opening the full desk. Both changed production sources compile;
whitespace checks pass. Rebuilt archive verified for the folded startup assignment
and inline report; packaged and installed self-tests passed. Prior executable
backed up and installed SHA-256 verified. Reopen the app to load this correction.

