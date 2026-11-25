# Design overview

## Purpose

Staging a Dell server often means collecting the same logs from its iDRAC before and after some work on the server, for example installing a part. Doing this by hand through each iDRAC web page is slow and easy to get wrong. This app collects the logs for several servers at once and keeps them under the server's Service Tag.

The design is not tied to one project. Any team that stages Dell servers and needs the TSR and the Lifecycle log as evidence can use it.

## Requirements

- Collect the TSR and the Lifecycle log from an iDRAC without opening its web page.
- Run several collections in parallel.
- Name and store the files so that a server's evidence is easy to find and a rerun never overwrites an earlier file.
- Prove that a file is unchanged later (a SHA-256 checksum next to each file).
- Show status and downloads on one page that the whole team can open.
- Run on the lab network without internet.
- Stay read-only on the iDRAC. The only change allowed is accepting the SupportAssist EULA once, because the TSR export needs it.

## Design

- **Redfish API:** the app talks to the iDRAC Redfish API with plain HTTPS calls. Dell's own scripts use the same calls. The call list is in [Redfish calls](../redfish-reference.md).
- **Local export:** the TSR and the Lifecycle log are downloaded straight from the iDRAC to the app. No file share is needed, and the check for finished jobs is a plain poll.
- **One Python file:** FastHTML serves the dashboard, htmx refreshes it live, and SQLite keeps the device list, job status and file records. A reader can follow the whole app in one file.
- **Containers:** the app and a read-only file browser (copyparty) run in Docker on one Linux VM. The VM can be rebuilt from the repository, and the evidence lives in one `data/` folder.
- **No AI agent at run time:** a collection is a fixed sequence of calls. An agent would add cost and an outside dependency for no gain.
- **No web login:** the dashboard is for the in-house team on the lab network, and everyone sees the same list and progress.
- **Credentials:** the iDRAC default login comes from `.env`. A server with its own login can be added with a user and password, which are kept in memory only.

## Limits

- Firmware without the `DellLCService` Redfish action, such as iDRAC9 3.21.26.22, cannot be collected. A racadm based method is being considered.
- A TSR takes about 12 to 13 minutes per server, mostly iDRAC time. More servers in parallel are limited by the iDRAC, not by the app.
- The dashboard has no login and trusts the network around it.
- Nothing is verified for hardware from other vendors. [Development](../development.md) lists what would change.

## Possible next steps

- A legacy collection method for older firmware.
- A NAS for backup, and the nightly copy that goes with it.
- Tuning of the parallel limit and the TSR timeout once more servers are on hand.
