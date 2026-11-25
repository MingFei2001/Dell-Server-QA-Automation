# Operations

[Back to the README](../README.md#documentation)

| Task | Command |
|---|---|
| Start or update | `docker compose up -d --build` |
| Stop | `docker compose down` |
| Status | `docker compose ps` |
| Logs | `docker compose logs -f` |
| Disk space | `df -h` and `du -sh data/*` |
| Apply a `.env` change | `docker compose up -d --force-recreate` |

- Change `.env` (iDRAC login, port, limits): edit the file, then run `docker compose up -d --force-recreate`. No rebuild is needed. `docker restart` does not reload `.env`.
- Rebuild (`--build`) only after a change to `main.py`, `README.md`, `CHANGELOG.md`, `docs/*.md`, `static/`, `requirements.txt` or the `Dockerfile`. The `Documentation` link on the dashboard shows the copies inside the image, so a change to a document needs a rebuild to appear there.
- Before a recreate or rebuild: check that no job is running, and copy `data/state.db` to `~/backups/state.db.bak-<reason>`, and `.env` to `~/backups/.env.bak-<reason>` (it holds the password, so keep it private). Keep backups outside `data/`, because the `Files` browser shares `data/`.
- A recreate or rebuild forgets logins typed in the Add box (those servers show `login needed`) and marks running jobs `Failed: interrupted by app restart`. The list, statuses and files are kept.
- Restore the list after a bad change: stop the containers (`docker compose down`), copy the backup over `data/state.db`, start them again.
- Rollback of the `Files` service: restore the previous `compose.yaml` and `main.py`, then run `docker compose up -d --build --remove-orphans`. Evidence and the list are not touched.
- Rollback of a code change: keep a copy of the previous `main.py`, `README.md`, `CHANGELOG.md` and `docs/` in `~/backups/code-before-<reason>/` before each deploy, copy them back and run `docker compose up -d --build`.
- Optional extra rollback layer: a hypervisor snapshot of the VM before a big change. A snapshot also rolls back `data/` (evidence and the list), so do not use it for routine changes. Snapshots are manual and not required, because the container can be rebuilt from the repository.
- Update: copy the new project files to the server, then run `docker compose up -d --build`.
- Rollback: restore the previous project files and run `docker compose up -d --build`.
- Evidence stays in `data/` through rebuilds.
- The 128 GB disk is shared by the OS, Docker and evidence.
- Backup: a nightly rsync to a NAS is planned, not built. Until a NAS exists, copy `data/` by hand at agreed intervals.
