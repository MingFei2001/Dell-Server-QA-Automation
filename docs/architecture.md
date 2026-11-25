# Architecture

[Back to the README](../README.md#documentation)

## Scope and terms

The app collects the TSR and the Lifecycle log from each Dell server through the iDRAC Redfish API. It saves the files by serial number and shows status and downloads on a web dashboard.

In scope:

- Collect TSR and Lifecycle log before the work on a server (Pre), after it (Post), and on demand (General). The work can be any staging step, such as installing a part.
- Save files under the server's serial number.
- Show status and download links on one dashboard.

Out of scope:

- The physical work on the server.
- Burn-in: the 24-hour run, uptime logs and the power graph screenshot. These stay manual.
- Any change to iDRAC, BIOS, firmware, storage or network settings.
- One exception: the SupportAssist EULA is accepted once per iDRAC if it is not accepted yet. The TSR export needs it.

Terms:

- Serial number: the Dell Service Tag, the same number as the box label. The app reads it from the Redfish field `SKU` at `/redfish/v1/Systems/System.Embedded.1`.
- TSR: Tech Support Report (SupportAssist collection). A zip file.
- Lifecycle log: the iDRAC Lifecycle Controller log. An XML file.

## Software stack and design

This section lists what the software is made of and why it is built this way.

### Stack and versions

- Linux VM (Ubuntu Server 26.04) running Docker and Docker Compose.
- Python 3.14 with FastHTML. The pages are written in Python, with no hand-written HTML. The look is plain CSS kept in `main.py`. htmx is bundled for live updates.
- SQLite for the device list, job status and file records.
- `requests` for the Redfish calls.
- copyparty (`copyparty/min`) for retrieving the collected files.
- `markdown` for the `/docs` pages, which show this documentation.

| Item | Version | Note |
|---|---|---|
| Hypervisor | Proxmox | Hosts the Ubuntu VM. Any hypervisor works. |
| Ubuntu Server | 26.04 LTS | VM, minimum 4 GB RAM, 4 cores, 128 GB. Standard support through April 2031. |
| Docker Engine and Compose | From Docker's apt repository | Install per [Quick start](getting-started.md#quick-start) |
| Python image | `python:3.14.10-slim-trixie` | Pinned. Digest `sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f`. |
| python-fasthtml | 0.14.25 | Pinned |
| requests | 2.34.2 | Pinned |
| markdown | 3.11.3 | Pinned. Renders the documentation on the `/docs` pages. |
| copyparty | `copyparty/min:1.20.27` | Pinned. File browser on port 3923. Smallest image: no thumbnails, no indexing. MIT license. |
| htmx | 2.0.7 | Bundled in `static/`. From npm package `htmx.org@2.0.7`. Zero-Clause BSD license. |
| Port | 5001 | FastHTML default |

### Hosting

The software runs in an Ubuntu 26.04 VM on a hypervisor (Proxmox) in the lab. Docker runs inside the VM, with the app and Files containers and the `data/` folder.

- A work laptop only opens the dashboard in a browser.
- The VM reaches the iDRACs of the Dell servers over Redfish and ping.
- Any hypervisor works. The design needs only a Linux VM that can run Docker. The VM and the containers keep the setup portable: copy the project folder (with `data/`) to another VM and run `setup.sh`.
- VM size: minimum 4 GB RAM, 4 cores and 128 GB disk. Ubuntu lists 1.5 GB as the minimum and 3 GB as suggested for a server ([References](architecture.md#references)). Measured use: about 75 MiB for the two containers together and about 0.7 GB for the whole VM.
- Set the VM to start at boot in the hypervisor. The containers restart by themselves (`restart: unless-stopped`).

### Why there is no AI agent at run time

- Cost: a collection is a fixed sequence of HTTP calls ([Redfish calls](redfish-reference.md)). An agent would spend tokens on every run and add nothing.
- Offline use: the app runs on the lab network without internet. An agent depends on an external service and stops working in a network outage.
- Data and credentials: iDRAC logins and collected logs stay on the lab network. Nothing is sent to an outside AI service. The collected data carries no risk, so no data handling rules are set ([Open items](status.md#open-items)).
- An agent was used during development to write and test the code. The finished app contains none.

### Build logic

- Everything is packaged in Docker containers. The result is portable and light: a slim Python image and a small file browser image.
- `docker compose up -d --build` builds and starts it. A rebuild takes about a minute and keeps the data ([Operations](operations.md)).
- These docs are the recipe. With them, and `setup.sh`, a new person can recreate the setup on a fresh VM, and adapt it to another vendor ([Adapting to another vendor](development.md#adapting-to-another-vendor)).

## How it works

One Python process serves the dashboard and runs the collections.

- A pool of `MAX_PARALLEL` workers runs the jobs, with one job per server at a time.
- SQLite (`data/state.db`) holds the device list, job status per server and stage, and file records.
- A background thread checks the status light of every server every `LIGHT_SECONDS`. The page reads the stored result.
- Each row asks the app for changes every 3 seconds. The app answers `204 No Content` when nothing changed, so the row is not redrawn.
- Downloads use a file ID from the database. The app never opens a path typed by a user.
- The TSR is streamed to disk, because it can be large.

The Redfish calls are listed in [Redfish calls](redfish-reference.md).

## References

- Dell iDRAC Redfish scripting (official GitHub): <https://github.com/dell/iDRAC-Redfish-Scripting>
- Dell iDRAC9 3.31.31.31 Redfish API Guide, ExportTechSupportReport: <https://www.dell.com/support/manuals/en-sg/idrac9-lifecycle-controller-v3.3-series/idrac_3.31.31.31_redfishapiguide/supported-action-exporttechsupportreport?guid=guid-c3adac77-7b7c-4bda-af2f-d276c8449f45&lang=en-us>
- Docker Engine on Ubuntu: <https://docs.docker.com/engine/install/ubuntu/>
- Docker Compose, variable interpolation and `.env` syntax: <https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/>
- Docker Compose, `env_file` format: <https://docs.docker.com/reference/compose-file/container-spec/>
- Ubuntu 26.04 LTS release notes: <https://documentation.ubuntu.com/release-notes/26.04/>
- Ubuntu Server system requirements: <https://ubuntu.com/server/docs/reference/installation/system-requirements/index.html>
- Docker Hub, official Python image: <https://hub.docker.com/_/python>
- Python version status: <https://devguide.python.org/versions/>
- FastHTML docs: <https://www.fastht.ml/docs/>
