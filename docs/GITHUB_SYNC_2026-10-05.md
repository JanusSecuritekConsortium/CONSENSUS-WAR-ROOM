# GitHub synchronization — 2026-10-05

The current integration source has been committed and published on
`codex/boot-refresh-fix`, with pull request #9 targeting `main`.
The September audit branch is merged into this branch, preserving its launcher
sources, exclusions and documented historical cleanup.

Included: personal email/calendar workflows, contextual briefings, shared vault
retrieval, Telegram voice input, English briefing defaults with replies matching
the original message language, agent and Odysseus integrations, and the pending
packaging and GUI changes. Personal account addresses were removed from setup
defaults. Existing private local configuration is not changed by this cleanup.

Credentials, runtime databases, audio recordings and private vault contents are
not GitHub artifacts. GitHub stores the implementation, not the installed apps,
local account sessions or machine-specific configuration.

Validation:

- Active-source compilation passed for 555 files.
- Targeted integration suite: 157 passed, plus 12 subtests.
- First Linux CI run: 802 passed, 18 failed, 7 skipped. Follow-up fixes install
  the declared calendar dependencies, use a POSIX publication lock on Linux,
  and restrict the DPAPI test to Windows. Agent route tests are isolated from
  the operator's live Odysseus environment.
- Remaining known failures include older GUI geometry expectations, a test
  requiring a removed archived bot, and a Linux test expecting Windows TTS.
  This PR remains draft; publication does not certify a release or a green main.

Historical audit details remain in `GITHUB_SYNC_AUDIT_2026-09-16.md`.
