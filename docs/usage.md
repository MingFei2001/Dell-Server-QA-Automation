# Usage

[Back to the README](../README.md#documentation)

## Using the dashboard

Everything below is done from the dashboard in a browser.

1. Power on the server and wait for the iDRAC to come up.
2. Type the iDRAC IP address and press Add or Enter. The app adds it only if it answers ping and the Redfish login works. A message under the form says what happened: added, invalid address, already in the list, no ping, or login rejected. The row shows the serial number and the model.
3. Before SSD integration, click Collect under Pre.
4. Power down, integrate the SSD, power on.
5. Click Collect under Post.
6. Use Collect under General at any other time.
7. Download files from the `TSR .zip` and `LC .xml` links under each stage. Hover a link to see the full file name. A stage shows the files of its latest run.
8. Remove deletes the row from the list after a confirmation. It is blocked while a job runs. Collected files stay on disk.

Documentation and files:

- The page title is `Dell Server Log Collection Automation Server`. The `Documentation` and `Files` links are on the same row, at the right.
- The `Documentation` link opens `/docs` in a new tab. It shows the README and the pages in `docs/`, read from the copies inside the image. Links between the pages work offline.
- The `Files` link opens the copyparty file browser on port 3923 of the same host. It lists `data/<serial>/<stage>/`, including servers that were removed from the list.
- `Files` is read-only for everyone: browse, download and zip. Upload, delete and rename are refused. `data/` is also mounted read-only in that container.
- `state.db` and `.sesskey` are unmapped in `files.conf` and cannot be fetched. Other files in `data/` are listed, so keep backups outside `data/`.
- Both pages have no login, like the rest of the dashboard. Lab network only.

Own login for one server:

- Fill `user` and `password` next to the IP and press Add. Both are required, or both empty. Empty means the default login, which is set in `.env` ([Configuration](configuration.md)). To change it, see [Operations](operations.md).
- The login is checked with one Redfish call before it is used. A wrong login is not stored.
- The password is kept in app memory only. It is never written to the database, the logs or disk. It is sent in the form body over plain HTTP, like the rest of the dashboard.
- The database keeps only a flag that the server has its own login. The IP cell shows `own login`.
- After an app restart or container recreate the password is gone. The IP cell shows `login needed` and Collect is refused. Type the user and password again with the same IP and press Add. The app reports `Login set` and the serial must match the list.
- Remove forgets the login.
- A server that uses the default login is unaffected.

The page updates by itself. A row is redrawn only when its content changes. The buttons of a server are disabled while a job runs on it.

Status light:

| Colour | Meaning |
|---|---|
| Green | Ping OK and port 443 open |
| Amber | Ping OK, port 443 closed. The iDRAC web service is still starting. |
| Red | No ping |

Status text per server and stage (Pre, Post, General): `Queued`, `Running TSR`, `Running Lifecycle log` with the elapsed time, `Done` or `Failed: <short reason>` with the finish time. The full error is in the app log. A job that was running when the app restarted shows `Failed: interrupted by app restart`.

Running a collection again makes new timestamped files. Earlier files are never overwritten.

## Evidence layout

```
data/
  <serial>/
    pre-integration/    <serial>-pre-integration-<timestamp>.zip   .xml   and a .sha256 file for each
    post-integration/   <serial>-post-integration-<timestamp>.zip  .xml   and a .sha256 file for each
    general/            <serial>-<timestamp>.zip                   .xml   and a .sha256 file for each
  state.db
```

Some early files sit in `tsr/` and `lifecycle/` subfolders inside the stage folder. The database holds the full path of every file, so their download links still work.

- Timestamp format: `YYYYMMDD-HHMMSS`, local time (Asia/Singapore).
- File names start with the serial number. The part after the stage is the timestamp, so a rerun never overwrites an earlier file.
- Pre-integration: `<serial>-pre-integration-<timestamp>`. Post-integration: `<serial>-post-integration-<timestamp>`. General: `<serial>-<timestamp>`.
- The file type is given by the extension: `.zip` for the TSR, `.xml` for the Lifecycle log.
- TSR contents: `HWData` and `TTYLogs` (storage logs).
- Each file has a `.sha256` file next to it. To check a file, run `sha256sum -c <file>.sha256` in that folder.
