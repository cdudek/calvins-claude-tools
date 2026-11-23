"""Run records under ~/.sdlc (or $SDLC_HOME). Nothing here is ever committed to a repo.

Layout: runs/<run-id>/{run.json, plan.md, contract.json, tasks.json, checkpoint.json, approval.json,
receipts/, inputs/, evidence/, jobs/, log.md, .key}; active/<run-id> -> ../runs/<run-id> while the run lives.
"""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import re
import time
from datetime import date
from pathlib import Path


class SdlcError(Exception):
    """A refusal with a one-line reason; the CLI prints it and exits 2."""


def home() -> Path:
    return Path(os.environ.get("SDLC_HOME") or Path.home() / ".sdlc")


def runs_dir() -> Path:
    return home() / "runs"


def run_dir(rid: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", rid) or rid in (".", ".."):
        raise SdlcError(f"bad run id: {rid!r}")
    return runs_dir() / rid


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "run"


def make_run_id(start_repo: str, slug: str, today: str | None = None) -> str:
    base = f"{today or date.today().isoformat()}-{slugify(start_repo)}-{slugify(slug)}"
    rid, n = base, 1
    while run_dir(rid).exists():  # a number only on a collision
        n += 1
        rid = f"{base}-{n}"
    return rid


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if default is not None:
            return default
        raise SdlcError(f"missing record: {path.name}") from None
    except json.JSONDecodeError as e:
        raise SdlcError(f"unreadable record {path.name}: {e}") from None


def write_json(path: Path, obj) -> None:
    atomic_write(path, json.dumps(obj, indent=1, sort_keys=True) + "\n")


def canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def sha256(data: bytes | str) -> str:
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def now() -> float:
    return time.time()


def iso(ts: float | None = None) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts if ts is not None else now()))


def log(rid: str, line: str) -> None:
    p = run_dir(rid) / "log.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(f"- {iso()} {line}\n")


# ---- who may write what ---------------------------------------------------------------------------
# Receipts and checkpoints are written only by the runner's own scripts. The barrier is the plugin hook that denies agent
# reads and writes under runs/ (hooks/sdlc-records-guard.py); there is no signature, because a key an agent can read adds
# nothing. A hostile same-user process can still forge a record: the accepted risk for a one-owner setup.

def briefs_dir(rid: str) -> Path:
    """Task briefs live outside runs/ so a builder may read its own brief."""
    return home() / "briefs" / rid


def proc_ident(pid: int) -> str:
    """Start time of a live process, so a recycled PID is never mistaken for our job. Not the command: a child recorded right after the
    fork and read again after its exec has another command, which made `sdlc stop` skip a live job."""
    import subprocess
    r = subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


# ---- records --------------------------------------------------------------------------------------

def init_run(rid: str, meta: dict) -> Path:
    d = run_dir(rid)
    d.mkdir(parents=True, exist_ok=False)
    for sub in ("receipts", "inputs", "evidence", "jobs"):
        (d / sub).mkdir()
    meta = {"id": rid, "status": "planning", "created": iso(), "prs": {}, **meta}
    write_json(d / "run.json", meta)
    write_json(d / "checkpoint.json", new_checkpoint())
    set_active(rid, True)
    log(rid, f"run created ({meta.get('title', '')})")
    return d


def set_active(rid: str, live: bool) -> None:
    link = home() / "active" / rid
    if live:
        link.parent.mkdir(parents=True, exist_ok=True)
        if not link.is_symlink():
            link.symlink_to(Path("..") / "runs" / rid)
    elif link.is_symlink():
        link.unlink()


def load_meta(rid: str) -> dict:
    return read_json(run_dir(rid) / "run.json")


def save_meta(rid: str, meta: dict) -> None:
    write_json(run_dir(rid) / "run.json", meta)


def set_status(rid: str, status: str, reason: str = "") -> None:
    m = load_meta(rid)
    m["status"], m["reason"] = status, reason
    save_meta(rid, m)
    set_active(rid, status not in ("done", "stopped"))  # a finished or stopped run leaves ~/.sdlc/active/
    log(rid, f"status {status} {reason}".strip())


def new_checkpoint() -> dict:
    return {"dispatches": 0, "tasks": {}, "milestones": {}, "external": {}, "retries": {}, "events": []}


@contextlib.contextmanager
def locked(rid: str):
    """Exclusive lock for read-modify-write of the checkpoint; parallel jobs share one run."""
    d = run_dir(rid)
    with open(d / ".lock", "a+") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def load_cp(rid: str) -> dict:
    return read_json(run_dir(rid) / "checkpoint.json")


def update_cp(rid: str, fn) -> dict:
    """Apply fn(checkpoint) under the lock and persist it (fsync + rename) before returning."""
    with locked(rid):
        cp = load_cp(rid)
        fn(cp)
        write_json(run_dir(rid) / "checkpoint.json", cp)
        return cp


def stop_marker(rid: str) -> Path:
    return run_dir(rid) / "STOP"


def is_stopped(rid: str) -> bool:
    return stop_marker(rid).exists()


def resolve_run(arg: str | None = None, cwd: Path | None = None) -> str:
    """A run id, or the one named by the current branch (sdlc/<id>, sdlc-m/<id>/<m>, sdlc-t/<id>/<t>)."""
    if arg:
        run_dir(arg)
        return arg
    import subprocess
    r = subprocess.run(["git", "branch", "--show-current"], cwd=cwd, capture_output=True, text=True)
    b = r.stdout.strip()
    for pre in ("sdlc-m/", "sdlc-t/", "sdlc/"):
        if b.startswith(pre):
            rid = b[len(pre):].split("/")[0] if pre != "sdlc/" else b[len(pre):]
            if (runs_dir() / rid).is_dir():
                return rid
    raise SdlcError("not on an sdlc branch and no run id given")
