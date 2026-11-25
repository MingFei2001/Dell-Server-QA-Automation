# CLAUDE.md

## Project

Dell Server QA Automation: Day-0 staging automation for Dell servers, used across client projects.

The app collects the TSR and Lifecycle log from Dell iDRACs through the Redfish API and shows them on a FastHTML dashboard.

Owner: Mingfei, Configuration Technician I, WWT AIC Singapore.

## Start here

1. Read `README.md` for the overview and the links to the docs.
2. Read `docs/status.md` for the current stage and the open items, `docs/decisions.md` for the decisions and `docs/redfish-reference.md` for the Redfish call table.
3. Read `docs/design/chat-export-2026-11-20.txt` (local only, not in git) for the full design conversation, only if the docs do not answer the question.
4. Read the technical proposal in `docs/design/` only if neither answers the question.

## Rules for agents

### Rule 1: Approval before changes

- Never delete, modify or create files without explicit written approval from the user in chat. No exceptions.
- Stage every change in the conversation first. Write to the project only after the user confirms.
- This includes README changes.

### Rule 2: Keep it simple

- No filler, agreeing words or decorative language in notes or edits.
- No redundant explanations.

### Rule 3: Markdown first

- Write all documentation in Markdown.
- Headings in order: `#`, `##`, `###`.
- Lists: `- Item` for unordered, `1. Step` for ordered.
- Code: inline with single backticks, blocks with triple backticks.

### Rule 4: Repository style

- File names are lowercase-hyphenated, for example `example-notes.md`.
- Exceptions that follow tool conventions: `README.md`, `CHANGELOG.md`, `CLAUDE.md`, `Dockerfile`, `compose.yaml`.
- Separate sections with blank lines.
- One idea per paragraph.

## Current status

- Stage 2 is done (2026-11-23). The code and Docker files are rebuilt and committed.
- The app was built and run on a test VM and collected a TSR and Lifecycle log from a real iDRAC (firmware 7.20.60.50).
- Next: Stage 3, pilot one real server on the existing VM. Find the firmware on the target servers first.
- Open: a legacy method for firmware without `DellLCService` (3.21.26.22). See `docs/status.md`.

## Known issues

- `.env` in the repository holds the Dell defaults. The test VM has its own `.env` that the user edits. Never copy the local `.env` over it. The dashboard calls it the default login and does not mention `.env`; the maintenance steps are in `docs/operations.md`.
- Local TSR export on the target servers' firmware, the `SKU` match with the box label and EULA acceptance are unverified. See `docs/status.md`.
- The test VM address and user are not stored in the repository (DHCP, may change; they are in the agent memory file `reference-test-vm.md`). It uses key login, passwordless sudo, project in `~/idrac-day0-staging`. The VM runs on a hypervisor (Proxmox) and is also the pilot VM. Write code locally first, then copy to the VM.
- Git is initialised (2026-11-23, branch `main`). Use the installed `git` command (winget, 2.56.1).

## Fixed decisions

Do not change these without asking. The full list is in `docs/decisions.md`.

- Serial number means the Dell Service Tag, Redfish field `SKU`.
- Credentials are the iDRAC defaults `root` / `calvin`, set in `.env`. A server can use its own login typed in the Add box. It is kept in memory only, never stored.
- Image `python:3.14.10-slim-trixie`, python-fasthtml 0.14.25, requests 2.34.2, markdown 3.11.3, copyparty/min 1.20.27 (read-only file browser on port 3923).
- htmx bundled locally, no CDN; `serve(reload=False)`. Reasons are in `docs/decisions.md`.
- No web login. Lab network only.
- The app never changes iDRAC configuration. The only exception is accepting the SupportAssist EULA once.
- Burn-in is out of scope.
- The nightly rsync stays disabled until a NAS exists.

## Working notes

- Docker may not run in the agent's environment. Say so when a build is untested.
- Verify Dell facts against official Dell documentation or the official Dell GitHub only.
- Update the docs after every change: `docs/decisions.md`, `docs/status.md` and `CHANGELOG.md`. Keep `README.md` to the introduction.
