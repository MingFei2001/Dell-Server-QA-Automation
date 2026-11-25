# Development

[Back to the README](../README.md#documentation)

## Project layout

| Path | Purpose |
|---|---|
| `README.md` | Introduction and links to the docs |
| `CHANGELOG.md` | Change log |
| `docs/*.md` | The documentation pages |
| `docs/slides/` | The demo deck, the reference deck and the dashboard screenshot used in them |
| `docs/design/` | Local design notes. Not in git. |
| `main.py` | The whole app: dashboard, collection worker and the documentation pages |
| `static/htmx.min.js` | Bundled htmx, so the page works without internet |
| `Dockerfile` | Image: Python 3.14 slim, plus ping. Copies `main.py`, the Markdown docs and `static/` into the image. |
| `compose.yaml` | Two services: the app (port 5001, `./data` at `/data`) and `files`, the copyparty file browser (port 3923, `./data` at `/w`, read-only) |
| `files.conf` | copyparty settings: read-only for everyone, `state.db` and `.sesskey` unmapped |
| `requirements.txt` | Pinned Python packages |
| `.env` | Settings and the Dell default credentials |
| `.env.example` | Template for `.env`, used by `setup.sh` |
| `setup.sh` | Sets up a fresh Ubuntu VM: Docker, `.env`, build, start ([Quick start](getting-started.md#quick-start)) |
| `.gitignore` | Excludes the contents of `data/` (except `.gitkeep`), `docs/design/`, `dist/` and Python cache files |
| `.dockerignore` | Keeps `data/`, `docs/design/`, `docs/slides/` and git files out of the build context |
| `data/` | Evidence and database. Not in git. |
| `dist/` | Demo package zip. A build output, not in git. |
| `ops/rsync-nightly.sh` | Nightly backup to a NAS. Planned, not built. |
| `mock/` | Fake iDRAC for testing. Planned, not built. |

### Code map

Where things are in `main.py`:

| Area | Functions |
|---|---|
| Status light | `ping`, `port_open`, `light`, `light_loop` |
| Redfish access | `rf`, `identity`, `fill_models` |
| Collection | `wait_job`, `ensure_eula`, `collect_tsr`, `collect_lc`, `run_job`, `stream_to`, `record` |
| Documentation pages | `doc_path`, `doc_html`, `doc_link`, `docs_page` |
| Page and routes | `CSS`, `row`, `table`, and the routes for `/`, `/add`, `/collect`, `/remove`, `/download`, `/docs` and `/docs/{name}` |

## Adapting to another vendor

Redfish is a standard API, but the log collection actions are vendor specific. Nothing below is verified for any other vendor. Check each point against that vendor's official Redfish documentation first.

- Stays the same: the dashboard, the database, the job pool, the file layout and checksums, the status light, Docker, `setup.sh`, and the hosting (a VM on a hypervisor).
- Changes in `main.py`: the identity call and fields in `identity` (Dell uses `SKU` and `Model` at `/redfish/v1/Systems/System.Embedded.1`), `idrac_info` (the version and firmware from `/redfish/v1/Managers/iDRAC.Embedded.1`), the collection calls in `collect_tsr` and `collect_lc` (Dell uses `DellLCService` actions, which are Dell OEM), the job polling in `wait_job`, and the default login in `.env`.
- Changes in the text: the page title, the stage names if the workflow differs, and the pages [iDRAC access](getting-started.md#idrac-access) and [Redfish calls](redfish-reference.md).

## Testing

Test against a real iDRAC on the lab network: add it on the dashboard and press Collect ([Using the dashboard](usage.md#using-the-dashboard)). There is no mock iDRAC. One would need only the calls in [Redfish calls](redfish-reference.md).
