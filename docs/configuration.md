# Configuration

[Back to the README](../README.md#documentation)

Set in `.env`. After a change, run `docker compose up -d --force-recreate` ([Operations](operations.md)).

| Key | Default | Meaning |
|---|---|---|
| `IDRAC_USER` | `root` | iDRAC user |
| `IDRAC_PASS` | `calvin` | iDRAC password |
| `PORT` | `5001` | Dashboard port inside the container |
| `FILES_PORT` | `3923` | Port of the `Files` browser on the host. Optional. The dashboard link uses it. |
| `DATA_DIR` | `/data` | Evidence and database folder |
| `TZ` | `Asia/Singapore` | Time zone for timestamps |
| `MAX_PARALLEL` | `4` | Maximum collections at the same time |
| `TSR_TIMEOUT_MIN` | `30` | Give up on a TSR job after this many minutes |
| `POLL_SECONDS` | `5` | Seconds between job status checks |
| `LIGHT_SECONDS` | `10` | Seconds between status light checks of all servers |

## Syntax

Docker Compose reads `.env`. Its documentation is the reference: <https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/> and <https://docs.docker.com/reference/compose-file/container-spec/>.

- One `KEY=value` per line. A line that starts with `#` is a comment. Spaces around `=` are ignored.
- Quotes are not part of the value.
- An unquoted `$` starts a variable and is replaced: `a$b` becomes `a`. Write `$$` for a literal `$`, or put the value in single quotes.
- A `#` after a space starts a comment: `ab #cd` becomes `ab`. A `#` without a space stays in the value.
- If the password has a space, `$` or `#`, put it in single quotes: `IDRAC_PASS='my pass$1'`.
- `setup.sh` is stricter: it refuses a password with a space, `$`, a quote or a backslash.

## If `.env` is lost

Without `.env`, `docker compose` refuses to start and prints `env file ... not found`. The files in `data/` are not affected.

1. In the project folder, run `docker compose config`. It prints the `env file ... not found` error.
2. Rebuild the file in one of these ways:
    - Copy the template: `cp .env.example .env`, then edit `IDRAC_USER` and `IDRAC_PASS`. The template is in the repository and in the zip.
    - Run `bash setup.sh`. It asks for the user, password and port and writes `.env`. It uses built-in defaults if `.env.example` is missing.
    - Type the file by hand. Only `IDRAC_USER`, `IDRAC_PASS` and `TZ` need values. The other keys have the same defaults inside the app.
3. Run `chmod 600 .env`.
4. Run `docker compose up -d --force-recreate`.
5. Open the dashboard and add one server to confirm that the login works.

Keep a copy of the real `.env` outside the VM, for example in a password manager. The repository holds only the Dell defaults, so a different lab password cannot be recovered from it.
