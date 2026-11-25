import hashlib, ipaddress, os, re, socket, sqlite3, subprocess, threading, time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import markdown
import requests
import urllib3
from fasthtml.common import *

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

USER = os.getenv("IDRAC_USER", "root")
PASSWORD = os.getenv("IDRAC_PASS", "calvin")
PORT = int(os.getenv("PORT", "5001"))
FILES_PORT = int(os.getenv("FILES_PORT", "3923"))  # port of the copyparty file browser
DATA = Path(os.getenv("DATA_DIR", "/data"))
MAX_PARALLEL = int(os.getenv("MAX_PARALLEL", "4"))
TSR_TIMEOUT = int(os.getenv("TSR_TIMEOUT_MIN", "30")) * 60
POLL = int(os.getenv("POLL_SECONDS", "5"))
LIGHT_SECONDS = int(os.getenv("LIGHT_SECONDS", "10"))
STAGES = {"pre-integration": "Pre", "post-integration": "Post", "general": "General"}
LC = "/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellLCService"

if hasattr(time, "tzset"):
    time.tzset()
DATA.mkdir(parents=True, exist_ok=True)
pool = ThreadPoolExecutor(max_workers=MAX_PARALLEL)
busy, busy_lock = set(), threading.Lock()
LIGHT = {}  # ip -> green / amber / red, refreshed by light_loop
CREDS = {}  # ip -> (user, password) typed in the Add box. Memory only: never written to disk or logs.


# ---------- database ----------
@contextmanager
def db():
    con = sqlite3.connect(DATA / "state.db", timeout=30)
    con.row_factory = sqlite3.Row
    try:
        with con:
            yield con
    finally:
        con.close()


with db() as con:
    con.executescript("""
    CREATE TABLE IF NOT EXISTS devices(ip TEXT PRIMARY KEY, serial TEXT NOT NULL, added TEXT);
    CREATE TABLE IF NOT EXISTS files(id INTEGER PRIMARY KEY, serial TEXT, stage TEXT,
        kind TEXT, path TEXT, size INTEGER, sha256 TEXT, created TEXT);
    CREATE TABLE IF NOT EXISTS job_status(ip TEXT, stage TEXT, status TEXT, started TEXT, updated TEXT,
        PRIMARY KEY(ip, stage));
    """)
    cols = [r["name"] for r in con.execute("PRAGMA table_info(devices)")]
    if "model" not in cols:
        con.execute("ALTER TABLE devices ADD COLUMN model TEXT")
    if "own_login" not in cols:  # flag only: the password itself is never stored
        con.execute("ALTER TABLE devices ADD COLUMN own_login INTEGER DEFAULT 0")
    # carry over the last status per server from the old single-status table, once, then drop it.
    # Keeping it would bring back deleted status rows at every restart.
    if con.execute("SELECT 1 FROM sqlite_master WHERE name='jobs'").fetchone():
        con.execute("INSERT OR IGNORE INTO job_status SELECT ip, stage, status, updated, updated FROM jobs")
        con.execute("DROP TABLE jobs")
    # a job cannot survive a restart: do not leave it showing as running
    con.execute("UPDATE job_status SET status='Failed: interrupted by app restart' "
                "WHERE status LIKE 'Running%' OR status='Queued'")


def set_status(ip, stage, status, start=False):
    now = datetime.now().isoformat(timespec="seconds")
    with db() as con:
        if start:
            con.execute("INSERT OR REPLACE INTO job_status VALUES(?,?,?,?,?)", (ip, stage, status, now, now))
        else:
            con.execute("UPDATE job_status SET status=?, updated=? WHERE ip=? AND stage=?",
                        (status, now, ip, stage))


def is_active(r):
    return bool(r) and (r["status"].startswith("Running") or r["status"] == "Queued")


# ---------- network ----------
def ping(ip):
    flags = ["-n", "1", "-w", "2000"] if os.name == "nt" else ["-c", "1", "-W", "2"]
    r = subprocess.run(["ping", *flags, ip], capture_output=True)
    return r.returncode == 0


def port_open(ip, port=443):
    try:
        with socket.create_connection((ip, port), timeout=2):
            return True
    except OSError:
        return False


def light(ip):
    if not ping(ip):
        return "red"
    return "green" if port_open(ip) else "amber"


def rf(ip, method, path, creds=None, **kw):
    kw.setdefault("timeout", 60)
    return requests.request(method, f"https://{ip}{path}",
                            auth=creds or CREDS.get(ip) or (USER, PASSWORD), verify=False, **kw)


def identity(ip, creds=None):
    """Service Tag (SKU) and server model from one Redfish call."""
    r = rf(ip, "GET", "/redfish/v1/Systems/System.Embedded.1", creds=creds)
    r.raise_for_status()
    j = r.json()
    return j["SKU"], j.get("Model") or ""


model_tried = {}  # ip -> time of the last attempt, so a bad password is not retried in a loop


def fill_models():
    with db() as con:
        todo = [r["ip"] for r in con.execute(
            "SELECT ip, own_login FROM devices WHERE model IS NULL OR model=''") if not r["own_login"] or r["ip"] in CREDS]
    for ip in todo:
        if LIGHT.get(ip) != "green" or time.time() - model_tried.get(ip, 0) < 600:
            continue
        model_tried[ip] = time.time()
        try:
            model = identity(ip)[1] or "-"
            with db() as con:
                con.execute("UPDATE devices SET model=? WHERE ip=?", (model, ip))
        except Exception as e:
            print(f"[{ip}] model lookup failed: {e!r}", flush=True)


def light_loop():
    with ThreadPoolExecutor(max_workers=16) as ex:
        while True:
            try:
                ips = device_ips()
                for ip, state in zip(ips, ex.map(light, ips)):
                    LIGHT[ip] = state
                fill_models()
            except Exception as e:
                print(f"light loop error: {e!r}", flush=True)
            time.sleep(LIGHT_SECONDS)


# ---------- collection ----------
def stream_to(ip, address, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256()
    with rf(ip, "GET", address, stream=True, timeout=(10, 120)) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
                h.update(chunk)
    (dest.parent / f"{dest.name}.sha256").write_text(f"{h.hexdigest()}  {dest.name}\n")
    return dest.stat().st_size, h.hexdigest()


def record(serial, stage, kind, path, size, digest):
    with db() as con:
        con.execute("INSERT INTO files(serial,stage,kind,path,size,sha256,created) VALUES(?,?,?,?,?,?,?)",
                    (serial, stage, kind, str(path), size, digest,
                     datetime.now().isoformat(timespec="seconds")))


def wait_job(ip, address, timeout):
    # Follows Dell's SupportAssistCollectionLocalREDFISH.py (iDRAC9 loop): the job is
    # finished when the response Location header points at sacollect.zip.
    end = time.time() + timeout
    while time.time() < end:
        r = rf(ip, "GET", address)
        if r.status_code in (200, 202) and "sacollect.zip" in r.headers.get("Location", "").lower():
            return r
        r.raise_for_status()
        try:
            data = r.json()
        except ValueError:
            data = {}
        if data.get("JobState") in ("CompletedWithErrors", "Failed"):
            raise RuntimeError(f"job {data['JobState']}: {str(data.get('Message', ''))[:40]}")
        time.sleep(POLL)
    raise RuntimeError("timeout")


def ensure_eula(ip):
    r = rf(ip, "POST", f"{LC}/Actions/DellLCService.SupportAssistGetEULAStatus", json={})
    r.raise_for_status()
    # Dell's script treats a non-null "Interface" in the status response as EULA accepted.
    if r.json().get("Interface") is None:
        rf(ip, "POST", f"{LC}/Actions/DellLCService.SupportAssistAcceptEULA", json={}).raise_for_status()


def stem(serial, stage, stamp):
    # <serial>-pre-integration-<stamp>, <serial>-post-integration-<stamp>, <serial>-<stamp> for general
    return f"{serial}-{stamp}" if stage == "general" else f"{serial}-{stage}-{stamp}"


def collect_tsr(ip, serial, stage, stamp):
    if "SupportAssistCollection" not in rf(ip, "GET", LC).text:
        raise RuntimeError("action not supported")
    ensure_eula(ip)
    r = rf(ip, "POST", f"{LC}/Actions/DellLCService.SupportAssistCollection",
           json={"ShareType": "Local", "DataSelectorArrayIn": ["HWData", "TTYLogs"]})
    if r.status_code != 202:
        raise RuntimeError(f"TSR start HTTP {r.status_code}")
    done = wait_job(ip, r.headers["Location"], TSR_TIMEOUT)
    dest = DATA / serial / stage / f"{stem(serial, stage, stamp)}.zip"
    record(serial, stage, "tsr", dest, *stream_to(ip, done.headers["Location"], dest))


def collect_lc(ip, serial, stage, stamp):
    r = rf(ip, "POST", f"{LC}/Actions/DellLCService.ExportLCLog", json={"ShareType": "Local"})
    if r.status_code not in (201, 202):
        raise RuntimeError(f"LC log start HTTP {r.status_code}")
    dest = DATA / serial / stage / f"{stem(serial, stage, stamp)}.xml"
    record(serial, stage, "lifecycle", dest, *stream_to(ip, r.headers["Location"], dest))


def run_job(ip, serial, stage):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        set_status(ip, stage, "Running TSR")
        collect_tsr(ip, serial, stage, stamp)
        set_status(ip, stage, "Running Lifecycle log")
        collect_lc(ip, serial, stage, stamp)
        set_status(ip, stage, "Done")
    except Exception as e:
        print(f"[{ip}] {stage} failed: {e!r}", flush=True)
        if isinstance(e, requests.HTTPError) and e.response is not None and e.response.status_code == 401:
            set_status(ip, stage, "Failed: login rejected (401)")
        else:
            set_status(ip, stage, f"Failed: {str(e)[:60]}")
    finally:
        with busy_lock:
            busy.discard(ip)


# ---------- web ----------
TITLE = "Dell Server Log Collection Automation Server"
CSS = """
:root{--bg:#f4f6f8;--card:#fff;--line:#e3e7ec;--text:#1f2933;--muted:#6b7785;--accent:#0b6bcb;--ok:#1a7f37;--bad:#c62828}
*{box-sizing:border-box}
body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--text);margin:0;padding:1.5rem}
.wrap{max-width:1150px;margin:0 auto}
header{display:flex;align-items:baseline;justify-content:space-between;gap:1rem;margin-bottom:1rem;flex-wrap:wrap}
h1{font-size:1.35rem;font-weight:650;margin:0}
nav a{color:var(--accent);text-decoration:none;font-size:.9rem;margin-left:1.1rem}
nav a:hover,td a:hover{text-decoration:underline}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px}
.add{padding:.8rem 1rem;margin-bottom:1rem}
.add form{display:flex;gap:.5rem;flex-wrap:wrap}
input{font:inherit;font-size:.9rem;padding:.4rem .6rem;border:1px solid #c5ccd4;border-radius:6px;background:#fff}
input:focus{outline:2px solid #9cc4ee;border-color:var(--accent)}
button{font:inherit;font-size:.85rem;padding:.3rem .8rem;border:1px solid #c5ccd4;border-radius:6px;background:#fff;color:var(--text);cursor:pointer}
button:hover{background:#eef2f6}
button:disabled{opacity:.5;cursor:default}
button.primary{background:var(--accent);border-color:var(--accent);color:#fff}
button.primary:hover{background:#0958a8}
td button{color:var(--accent);border-color:#9cc4ee}
td button:hover{background:#eaf3fc}
td button.danger{color:var(--bad);border-color:#c5ccd4}
td button.danger:hover{background:#fdeeee}
.hint{font-size:.8rem;color:var(--muted);margin:.5rem 0 0}
#msg{min-height:1.2rem;margin:.6rem 0 0;font-size:.9rem}
#msg.ok{color:var(--ok)}#msg.err{color:var(--bad)}
.tablecard{overflow-x:auto}
table{border-collapse:collapse;width:100%}
th{font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);text-align:left;font-weight:600;background:#f9fafb;padding:.6rem .8rem;border-bottom:1px solid var(--line)}
td{padding:.65rem .8rem;border-bottom:1px solid var(--line);vertical-align:top;font-size:.9rem}
tr:last-child td{border-bottom:0}
tbody tr:hover{background:#fafbfc}
.dot{display:inline-block;width:.75rem;height:.75rem;border-radius:50%;margin-top:.25rem}
.green{background:#2fa84f}.red{background:#d83a3a}.amber{background:#e8a317}.grey{background:#aab2bb}
.st{font-size:.8rem;color:var(--muted);margin:.25rem 0}
.st.ok{color:var(--ok)}.st.fail{color:var(--bad)}
td a{display:inline-block;font-size:.8rem;color:var(--accent);text-decoration:none;margin-right:.6rem}
.ip{font-weight:600}
"""
app, rt = fast_app(
    pico=False, default_hdrs=False, live=False, key_fname=str(DATA / ".sesskey"),
    hdrs=(Script(src="/static/htmx.min.js"),
          Style(CSS)),
)


def device_ips():
    with db() as con:
        ips = [r["ip"] for r in con.execute("SELECT ip FROM devices")]
    return sorted(ips, key=ipaddress.ip_address)


def ips_ver(ips):
    return hashlib.md5(",".join(ips).encode()).hexdigest()[:10]


def rid(ip):
    return "row-" + ip.replace(".", "-")


def snapshot(ip):
    with db() as con:
        d = con.execute("SELECT * FROM devices WHERE ip=?", (ip,)).fetchone()
        if not d:
            return None
        st = {r["stage"]: r for r in con.execute("SELECT * FROM job_status WHERE ip=?", (ip,))}
        files = con.execute("SELECT * FROM files WHERE serial=? ORDER BY id DESC", (d["serial"],)).fetchall()
    latest = {}
    for f in files:
        latest.setdefault((f["stage"], f["kind"]), f)  # newest first
    return d, st, latest


def status_text(r):
    if not r:
        return "-"
    if is_active(r):
        try:
            secs = int((datetime.now() - datetime.fromisoformat(r["started"])).total_seconds())
        except (TypeError, ValueError):
            secs = 0
        return f"{r['status']} ({secs // 60}m{secs % 60:02d}s)"
    return f"{r['status']} ({(r['updated'] or '')[11:16]})"


def stage_status(st, latest, stage):
    """Job status for a stage. With files but no status record (data from before status tracking), show Done."""
    r = st.get(stage)
    if r is None:
        f = latest.get((stage, "tsr")) or latest.get((stage, "lifecycle"))
        if f:
            return {"status": "Done", "started": None, "updated": f["created"]}
    return r


def login_state(d):
    """None: uses .env. 'own login': password held in memory. 'login needed': own login lost after a restart."""
    if not d["own_login"]:
        return None
    return "own login" if d["ip"] in CREDS else "login needed"


def row_ver(ip, snap):
    d, st, latest = snap
    key = (d["serial"], d["model"], LIGHT.get(ip), login_state(d), [status_text(stage_status(st, latest, s)) for s in STAGES],
           sorted((k, f["id"]) for k, f in latest.items()))
    return hashlib.md5(repr(key).encode()).hexdigest()[:10]


def row(ip):
    snap = snapshot(ip)
    if not snap:
        return ""
    d, st, latest = snap
    off = {"disabled": True} if any(is_active(r) for r in st.values()) else {}
    cells = []
    for stage in STAGES:
        r = stage_status(st, latest, stage)
        links = [Div(A(label, href=f"/download/{f['id']}", title=Path(f["path"]).name))
                 for kind, label in (("tsr", "TSR .zip"), ("lifecycle", "LC .xml"))
                 if (f := latest.get((stage, kind)))]
        failed = r is not None and r["status"].startswith("Failed")
        cells.append(Td(Button("Collect", title=f"Collect {stage}", hx_post=f"/collect/{ip}/{stage}",
                               hx_target=f"#{rid(ip)}", hx_swap="outerHTML", **off),
                        Div(status_text(r), cls="st fail" if failed else "st ok" if r and r["status"] == "Done" else "st"),
                        *links))
    ls = login_state(d)
    ip_cell = Td(Span(ip, cls="ip"), Div(ls, cls="st fail" if ls == "login needed" else "st",
                         title="Login typed in the Add box, kept in memory only" if ls == "own login"
                         else "Enter user and password for this IP in the Add box") if ls else "")
    return Tr(Td(Span(cls=f"dot {LIGHT.get(ip, 'grey')}")), ip_cell, Td(d["serial"]), Td(d["model"] or ""),
              *cells,
              Td(Button("Remove", cls="danger", title=f"Remove {ip} from the list", hx_post=f"/remove/{ip}",
                        hx_target="#devices", hx_swap="outerHTML",
                        hx_confirm=f"Remove {ip} from the list? Collected files stay on disk.", **off)),
              id=rid(ip), hx_get=f"/row/{ip}?v={row_ver(ip, snap)}", hx_trigger="every 3s", hx_swap="outerHTML")


def table():
    ips = device_ips()
    head = Tr(Th(""), Th("iDRAC IP"), Th("Serial number"), Th("Model"),
              Th("Pre", title="Pre-integration"), Th("Post", title="Post-integration"),
              Th("General"), Th(""))
    return Div(Table(Thead(head), Tbody(*[row(ip) for ip in ips])),
               id="devices", cls="card tablecard", hx_get=f"/table?v={ips_ver(ips)}", hx_trigger="every 10s", hx_swap="outerHTML")


def msg(text, ok=True):
    return Div(text, id="msg", cls="ok" if ok else "err", hx_swap_oob="true")


APP_DIR = Path(__file__).parent
DOC_NAME = re.compile(r"[a-z][a-z-]*")


def doc_path(name):
    """Map a page name to its Markdown file in the image. Only plain lowercase names are served."""
    if not name:
        return APP_DIR / "README.md"
    if name == "changelog":
        return APP_DIR / "CHANGELOG.md"
    if DOC_NAME.fullmatch(name):
        return APP_DIR / "docs" / f"{name}.md"
    return None


def doc_link(m):
    """Point a relative link to a Markdown file at its page under /docs."""
    stem = m.group(1).rsplit("/", 1)[-1]
    page = {"README": "/docs", "CHANGELOG": "/docs/changelog"}.get(stem, f"/docs/{stem}")
    return f'href="{page}{m.group(2) or ""}"'


def doc_html(text):
    html = markdown.markdown(text, extensions=["tables", "fenced_code", "toc"])
    html = re.sub(r'<p>\s*<img [^>]*src="docs/[^"]*"[^>]*>\s*</p>', "", html)  # screenshots are not in the image
    return re.sub(r'href="([^"#:]+)\.md(#[^"]*)?"', doc_link, html)


def docs_page(name):
    path = doc_path(name)
    try:
        text = path.read_text(encoding="utf-8") if path else None
    except OSError:
        text = None
    if text is None:
        return Response("Not found", status_code=404)
    return (Title("Documentation"),
            Style(".docs{padding:1rem 1.5rem;max-width:60rem;line-height:1.5}.docs table{margin:1rem 0}"
                  ".docs pre{background:#f4f4f4;padding:.7rem;overflow-x:auto}"
                  ".docs code{background:#f4f4f4;padding:0 .2rem}.docs pre code{padding:0}"),
            Div(Header(H1(TITLE), Nav(A("Documentation home", href="/docs"), A("Back to dashboard", href="/"))),
                Div(NotStr(doc_html(text)), cls="card docs"), cls="wrap"))


@rt("/docs")
def get():
    """The README, rendered from the copy inside the image."""
    return docs_page("")


@rt("/docs/{name}")
def get(name: str):
    """One documentation page: docs/<name>.md, or CHANGELOG.md for `changelog`."""
    return docs_page(name)


@rt("/")
def get(request: Request):
    # The file browser runs in its own container on FILES_PORT, on the same host as this page.
    files_url = f"http://{request.url.hostname}:{FILES_PORT}/"
    return (Title(TITLE),
            Div(Header(H1(TITLE),
                       Nav(A("Documentation", href="/docs", target="_blank", rel="noopener"),
                           A("Files", href=files_url, target="_blank", rel="noopener"))),
                Div(Form(Input(name="ip", placeholder="iDRAC IP", required=True, autocomplete="off", size="16"),
                         Input(name="user", placeholder="user (optional)", autocomplete="off", size="14"),
                         Input(name="password", type="password", placeholder="password (optional)",
                               autocomplete="new-password", size="18"),
                         Button("Add", cls="primary"), hx_post="/add", hx_target="#devices", hx_swap="outerHTML",
                         **{"hx-on:clear-add": "this.reset()"}),
                    P("Leave user and password empty to use the default login. To use another login for one server, "
                      "type it here. It is kept in memory only and forgotten when the app restarts.", cls="hint"),
                    Div(id="msg"), cls="card add"),
                table(), cls="wrap"))


@rt("/table")
def get(v: str = ""):
    if ips_ver(device_ips()) == v:
        return Response(status_code=204)
    return table()


@rt("/row/{ip}")
def get(ip: str, v: str = ""):
    snap = snapshot(ip)
    if not snap:
        return ""  # removed: swaps the row out
    if row_ver(ip, snap) == v:
        return Response(status_code=204)  # unchanged: no swap
    return row(ip)


@rt("/add")
def post(ip: str, user: str = "", password: str = ""):
    raw = ip.strip()
    try:
        ip = str(ipaddress.IPv4Address(raw))
    except ValueError:
        return table(), msg(f"Not a valid IPv4 address: {raw[:40]}", False)
    user = user.strip()
    if bool(user) != bool(password):
        return table(), msg("Enter both user and password, or leave both empty to use the default login.", False)
    creds = (user, password) if user else None
    listed = ip in device_ips()
    if listed and not creds:
        return table(), msg(f"{ip} is already in the list. To set a login for it, fill user and password.", False)
    if not ping(ip):
        return table(), msg(f"{ip}: no ping reply. Not {'changed' if listed else 'added'}.", False)
    try:
        serial, model = identity(ip, creds)
    except requests.HTTPError as e:
        code = e.response.status_code
        if code == 401:
            why = "login rejected (401), check the user and password typed" if creds \
                else "login rejected (401), the default login does not work here. Type a user and password for this server"
        else:
            why = f"Redfish returned HTTP {code}"
        return table(), msg(f"{ip}: {why}. Not {'changed' if listed else 'added'}.", False)
    except Exception as e:
        print(f"[{ip}] add failed: {e!r}", flush=True)
        return table(), msg(f"{ip}: cannot read the iDRAC ({type(e).__name__}). "
                            f"Not {'changed' if listed else 'added'}.", False)
    if listed:
        with db() as con:
            d = con.execute("SELECT serial FROM devices WHERE ip=?", (ip,)).fetchone()
            if d and d["serial"] != serial:
                return table(), msg(f"{ip}: serial is {serial}, the list has {d['serial']}. Login not set.", False)
            con.execute("UPDATE devices SET own_login=1, model=COALESCE(NULLIF(model,''), ?) WHERE ip=?",
                        (model, ip))
        CREDS[ip] = creds
        return table(), msg(f"Login set for {ip}. Kept in memory until the app restarts."), \
            HtmxResponseHeaders(trigger="clear-add")
    with db() as con:
        con.execute("INSERT INTO devices(ip, serial, added, model, own_login) VALUES(?,?,?,?,?)",
                    (ip, serial, datetime.now().isoformat(timespec="seconds"), model, 1 if creds else 0))
    if creds:
        CREDS[ip] = creds
    LIGHT[ip] = "green"
    return table(), msg(f"Added {ip}: {serial} {model}".strip() + (" (own login)" if creds else "")), \
        HtmxResponseHeaders(trigger="clear-add")


@rt("/collect/{ip}/{stage}")
def post(ip: str, stage: str):
    if stage not in STAGES:
        return row(ip)
    with busy_lock:
        with db() as con:
            d = con.execute("SELECT * FROM devices WHERE ip=?", (ip,)).fetchone()
        if not d:
            return row(ip)
        if d["own_login"] and ip not in CREDS:
            return row(ip), msg(f"{ip} needs its login again: type user and password in the Add box "
                                f"with this IP.", False)
        if ip in busy:
            return row(ip), msg(f"{ip} already has a job running", False)
        busy.add(ip)
    set_status(ip, stage, "Queued", start=True)
    pool.submit(run_job, ip, d["serial"], stage)
    return row(ip)


@rt("/remove/{ip}")
def post(ip: str):
    with busy_lock:
        if ip in busy:
            return table(), msg(f"{ip} has a job running. Remove it after the job ends.", False)
        with db() as con:
            n = con.execute("DELETE FROM devices WHERE ip=?", (ip,)).rowcount
            con.execute("DELETE FROM job_status WHERE ip=?", (ip,))
    LIGHT.pop(ip, None)
    CREDS.pop(ip, None)
    if n:
        return table(), msg(f"Removed {ip}. Collected files stay on disk.")
    return table(), msg(f"{ip} was not in the list", False)


@rt("/download/{file_id}")
def get(file_id: int):
    with db() as con:
        f = con.execute("SELECT * FROM files WHERE id=?", (file_id,)).fetchone()
    if not f or not Path(f["path"]).is_file():
        return Response("Not found", status_code=404)
    return FileResponse(f["path"], filename=Path(f["path"]).name)


threading.Thread(target=light_loop, daemon=True).start()
serve(port=PORT, reload=False)
