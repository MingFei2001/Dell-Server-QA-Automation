# Decision log

[Back to the README](../README.md#documentation)

Decisions are grouped by topic. The date is when the decision was made. The earlier row-by-row log is in git history (the commit "Drop the legacy jobs table after its one-time copy" and earlier).

## Platform and stack

| Date | Decision | Why |
|---|---|---|
| 2026-11-18 | Ubuntu Server 26.04 LTS in a VM on a hypervisor (Proxmox). Docker Compose. Any hypervisor works (2026-11-24). | Newer, longer support. Portable if the server moves. The hypervisor does not change the design. |
| 2026-11-18 | Python 3.14 with a pinned image. FastHTML. | 3.15.2 is the newest on Docker Hub and 3.14 is safer. One Python file to read and update. |
| 2026-11-18 | VM approved at 4 cores, 8 GB RAM, 128 GB. Minimum is 4 GB RAM (2026-11-24). | Approved for the project. Measured use is under 1 GB ([Software stack and design](architecture.md#software-stack-and-design)). |
| 2026-11-24 | No AI agent at run time. The app calls the Redfish API directly. | No token cost, works offline on the lab network, credentials and logs stay local ([Software stack and design](architecture.md#software-stack-and-design)). |

## Access and security

| Date | Decision | Why |
|---|---|---|
| 2026-11-18 | No web login | Lab network, internal people only |
| 2026-11-18 | Dell default credentials in `.env` and the docs. `.env` is committed (2026-11-20). | Customer defaults, not secret. They help troubleshooting. |
| 2026-11-24 | Optional per-server login typed in the Add box, kept in memory only. The dashboard says "default login" and never names `.env`. | One iDRAC had a different password. Passwords never reach disk. Users do not need to know how the default is set. |
| 2026-11-24 | File browser is a separate copyparty container: read-only, no login, one `Files` link. `state.db` and `.sesskey` are unmapped. | Gives access to files of removed servers without changing the app. Read-only keeps the evidence safe. |

## Collection rules

| Date | Decision | Why |
|---|---|---|
| 2026-11-18 | Serial number means the Dell Service Tag (Redfish `SKU`). Folders are named by serial, not hostname. | Same number as the box label |
| 2026-11-18 | TSR contents `HWData` and `TTYLogs`. The TSR is streamed to disk with a 30 minute timeout (2026-11-20). | The default choice. The TSR can be large and slow. Tune in the pilot. |
| 2026-11-23 | The EULA counts as accepted when `Interface` in the status response is not null. A TSR job is finished when the poll response `Location` header contains `sacollect.zip`. | Taken from Dell's `SupportAssistCollectionLocalREDFISH.py`. The second rule replaces waiting for `JobState` `Completed`. |
| 2026-11-23 | Target iDRAC firmware 7.00.00 and above | Local export works on 7.20.60.50 and fails on 3.21.26.22. Older firmware is a later discussion ([Open item 10](status.md#open-items)). |

## Naming and layout

| Date | Decision | Why |
|---|---|---|
| 2026-11-18 | Three buttons: pre-integration, post-integration, general. Dashboard columns Pre, Post and General, with links `TSR .zip` and `LC .xml` and the full file name as a tooltip (2026-11-23). | Matches the workflow. The stage and type are already in the file name. |
| 2026-11-23 | File names are `<serial>-<stage>-<timestamp>`, with `.zip` for the TSR and `.xml` for the Lifecycle log. General has no stage part. Folders are flat: `data/<serial>/<stage>/`. | The user's naming convention. The extension shows the type. |

## Dashboard behaviour

| Date | Decision | Why |
|---|---|---|
| 2026-11-20 | Three-state status light, checked by a background thread, not on page load (2026-11-23). | Ping can answer before the iDRAC web service is ready. Page load stays fast with many servers. |
| 2026-11-23 | Job status is stored per server and stage. A restart marks unfinished jobs as failed. A short error shows on the row and the full error goes to the log (2026-11-20). | A job cannot survive a restart. Short errors are easier to read. |
| 2026-11-23 | Rows refresh only when they change: the app answers 204 when nothing changed. | A full table redraw every few seconds lost clicks and was slow with many servers. |
| 2026-11-23 | Add shows a message for each outcome, only accepts an IP that answers ping, and clears the input on success. Remove asks for confirmation, is blocked while a job runs, and keeps the files. The model is read from the same Redfish call as the serial number. | The user could not tell why an Add did nothing, and dead entries are avoided. The app never deletes evidence. One call, no extra load. |
| 2026-11-24 | The documentation (the README and `docs/`) is shown at `/docs`, as rendered copies of the files in the image. | Users find the maintenance steps without leaving the app, offline. One source of truth. |

## Build and runtime

| Date | Decision | Why |
|---|---|---|
| 2026-11-20 | htmx is bundled, with no CDN, framework, web fonts or extra scripts (plain inline CSS, 2026-11-24). `serve(reload=False)`. | FastHTML's default page loads files from a public CDN and lab PCs may have no internet. The default reload would start the worker threads twice. |
| 2026-11-20 | Worker pool of 4, one job per server. Downloads use a file ID. | One worker would run servers one after another. No user-typed paths, so no path traversal. |
| 2026-11-20 | `iputils-ping` in the image. `TZ=Asia/Singapore`. | The slim image has no ping. File times match local time. |
| 2026-11-23 | The container runs as UID 1000. FastHTML's session key is stored in `/data/.sesskey`. `.dockerignore` and `data/.gitkeep` exist. | `/app` is not writable by the non-root user, and the first start crashed on `.sesskey`. Without `.dockerignore` the build sends `data/` to Docker. Without `.gitkeep` Docker creates `data/` owned by root. |
| 2026-11-23 | The test VM runs the app with `sudo docker`, with no `docker` group. | Avoids root-equivalent group membership |
| 2026-11-24 | The old `jobs` table is dropped after its one-time copy into `job_status`. | A restart brought back status rows deleted by Remove. A backup of `state.db` is taken before the rebuild. |

## Repository and process

| Date | Decision | Why |
|---|---|---|
| 2026-11-20 | Git on branch `main`. `.gitignore` excludes `data/*` (keeps `data/.gitkeep`), `__pycache__/` and `*.pyc`. `.gitattributes` forces LF line endings. | Keeps evidence out of the repository. Windows Git can break scripts on Linux. |
| 2026-11-20 | `README.md` keeps its uppercase name. | Standard name. Other files are lowercase-hyphenated, except `Dockerfile` and `compose.yaml`, which follow tool conventions. |
| 2026-11-25 | The README is a short introduction. The details are in `docs/`, one topic per file. The pages are written as present-tense instructions. Progress and test history are in `docs/status.md` and `CHANGELOG.md`. | A new reader gets the overview on the GitHub page and opens only the page needed. Progress reports mixed in made the pages harder to follow. |
| 2026-11-24 | Two decks in `docs/slides/`: a short demo deck and a reference deck for onboarding. | The demo stays high level. The reference deck is a refresher for the next person. |

## Scope and not built

| Date | Decision | Why |
|---|---|---|
| 2026-11-18 | Burn-in is not automated. | Evidence is the power graph screenshot from the iDRAC web interface. |
| 2026-11-18 | Nightly rsync is planned, not enabled. | No NAS yet |
| 2026-11-25 | No data handling rules for the collected files. Take care only when publishing code. | The files stay on the lab network and carry no risk (owner). |
| 2026-11-25 | VM snapshots are manual, or a Proxmox schedule if set up. Not a requirement. | The container can be rebuilt from the repository (owner). |
| 2026-11-25 | The dashboard shows iDRAC version and firmware in one column, read from `/redfish/v1/Managers/iDRAC.Embedded.1`. The version name comes from the generation in the Manager `Model`. | Shows at a glance which servers can use the Redfish collection. Read-only. |
| 2026-11-25 | The project is described as generic log collection for Dell servers, not for one client project. A design overview is kept in git as `docs/design/design-overview.md`. The original proposal files stay local. | The proposal names the client. The stage names Pre, Post and General stay, so existing files and names do not change. |
| 2026-11-23 | Test on real iDRACs instead of a mock. Not built for now: bulk add, checkbox batch collect, a warning for post before pre. | Two real machines were available. Decided with the user: a person should check that each server was added and answers ping. The reward does not justify the effort yet. |
