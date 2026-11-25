# Troubleshooting

[Back to the README](../README.md#documentation)

| Symptom | Check | Fix |
|---|---|---|
| `docker compose` says `env file ... not found` | `.env` is missing | Rebuild it as described in [If `.env` is lost](configuration.md#if-env-is-lost). |
| Light is red | Cable, iDRAC IP, route from the server to the bench network | Fix the network. Test with `ping <ip>` on the server. |
| Light is amber | iDRAC web service still starting | Wait and refresh. |
| Add says "Not added" | Ping, then `https://<ip>` in a browser, then the login | Use `root` / `calvin`, or type the server's own user and password. After editing `.env`, recreate the container (`docker compose up -d --force-recreate`). A restart does not reload `.env`. |
| `Failed` with job limit (JCP017) | Dell reports "Maximum job limit reached" | Wait for running iDRAC jobs to finish, then retry. |
| `Failed`: action not supported | `DellLCService` is missing. Seen on firmware 3.21.26.22. Works on 7.20.60.50. | Use newer firmware, or a legacy method ([Open item 10](status.md#open-items-and-unverified)). Record the firmware version. |
| `Failed`: EULA | SupportAssist EULA could not be accepted | Accept it in the iDRAC web interface, then retry. |
| Page loads but buttons do nothing | `static/htmx.min.js` missing | Restore the file and rebuild. |
| Cannot write to `data/` | Folder owner | `sudo chown -R 1000:1000 data` |
| File times are wrong | `TZ` in `.env` | Set `TZ` and run `docker compose up -d --force-recreate`. |
| `Files` link does not open | `docker compose ps`: is `idrac-day0-files` running? Is port 3923 (or `FILES_PORT`) free on the host? | `docker compose logs files`, then `docker compose up -d`. The dashboard is not affected. |
| Light is always red inside the app but ping works on the host | Ping inside the container | Run `docker exec idrac-day0-staging ping -c 1 <ip>`. See [Status and open items](status.md). |
