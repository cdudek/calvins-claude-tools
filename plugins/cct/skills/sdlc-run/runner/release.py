"""Producer and consumer repos in one run (design 3.6): artifacts with identity, merge order, publication, the consumer pin."""
from __future__ import annotations

import store
import verify
from contract import PENDING, READY, git
from store import SdlcError


def edges(rid: str) -> list[dict]:
    return store.read_json(store.run_dir(rid) / "contract.json").get("edges", [])


def merge_order(rid: str) -> list[str]:
    """Producers before consumers: the final merge sequence."""
    meta = store.load_meta(rid)
    order, left = [], {r: {e["producer"] for e in edges(rid) if e["consumer"] == r} for r in meta["repos"]}
    while left:
        ready = sorted(r for r, d in left.items() if not d - set(order))
        if not ready:
            raise SdlcError("plan error: producer and consumer repos depend on each other")
        order += ready
        left = {r: d for r, d in left.items() if r not in ready}
    return order


def _run(rid: str, repo: str, argv: list[str], ref: str, label: str):
    r = store.load_meta(rid)["repos"][repo]
    job = verify.run_job(rid, label, [a.replace("{ref}", ref) for a in argv], __import__("pathlib").Path(r["path"]))
    if job.exit != 0:
        raise SdlcError(f"BLOCKED env {label} failed: {job.out.strip()[:200]}")
    return job.out


def identity(rid: str, edge: dict, ref: str) -> dict:
    out = _run(rid, edge["producer"], edge["pack"], ref, f"pack-{edge['producer']}")
    return {"source": git(store.load_meta(rid)["repos"][edge["producer"]]["path"], "rev-parse", ref), "digest": store.sha256(out)}


def pack(rid: str, producer: str) -> dict:
    """Pack the producer's current head; consumers see it through SDLC_ARTIFACT_<PRODUCER> while they verify."""
    meta = store.load_meta(rid)
    edge = next(e for e in edges(rid) if e["producer"] == producer)
    ident = identity(rid, edge, meta["repos"][producer]["branch"])
    store.update_cp(rid, lambda cp: cp.setdefault("artifacts", {}).__setitem__(producer, ident))
    return ident


def publish(rid: str, producer: str) -> dict:
    """After the owner merged the producer: fetch what was published, require the packed identity, apply the approved pin."""
    meta = store.load_meta(rid)
    edge = next(e for e in edges(rid) if e["producer"] == producer)
    cp = store.load_cp(rid)
    packed = cp.get("artifacts", {}).get(producer)
    if not packed:
        raise SdlcError(f"{producer} was never packed")
    r = meta["repos"][producer]
    git(r["path"], "fetch", "-q", "origin")
    published = store.sha256(_run(rid, producer, edge["release"]["fetch"], f"origin/{r['default_branch']}", f"fetch-{producer}"))
    if published != packed["digest"]:
        raise SdlcError(f"BLOCKED integrity published artifact of {producer} differs from the packed one")
    from engine import project_wt
    pwt = project_wt(rid, edge["consumer"])
    pin = edge["pin"]
    (pwt / pin["file"]).write_text(pin["line"].replace("{digest}", published) + "\n")
    git(pwt, "add", "-A")
    git(pwt, "commit", "-qm", f"sdlc: pin {producer} {published[:12]}")
    rec = {"digest": published, "pin_sha": git(pwt, "rev-parse", "HEAD")}
    store.update_cp(rid, lambda cp: cp.setdefault("release", {}).__setitem__(producer, rec))
    return rec


def gate(rid: str, meta: dict) -> tuple[int, str]:
    """Consumers stay PENDING until the producer's release is recorded, matches the packed artifact and is pinned."""
    cp = store.load_cp(rid)
    for e in edges(rid):
        if e.get("release", {}).get("kind", "none") == "none":
            continue
        p = e["producer"]
        rel = cp.get("release", {}).get(p)
        if not rel:
            return PENDING, f"{e['consumer']} awaits publication of {p}"
        now = identity(rid, e, meta["repos"][p]["branch"]) if not (store.is_stopped(rid)) else None
        if now and now["digest"] != rel["digest"]:
            return PENDING, f"{p} changed after its release was recorded"
        pinned = git(meta["repos"][e["consumer"]]["path"], "show", f"{meta['repos'][e['consumer']]['branch']}:{e['pin']['file']}")
        if e["pin"]["line"].replace("{digest}", rel["digest"]) not in pinned:
            return PENDING, f"{e['consumer']} does not carry the pin for {p}"
    return READY, ""
