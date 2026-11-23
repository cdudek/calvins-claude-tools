"""Producer and consumer repos in one run (design 3.6): artifacts with identity, merge order, publication, the consumer pin."""
from __future__ import annotations

import store
import verify
from contract import PENDING, READY, argv_allowed, git, safe_relpath
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


def _run(rid: str, repo: str, argv: list[str], ref: str, label: str) -> str | bytes:
    """Run an allowlisted pack or fetch command in a detached worktree at `ref`, never in the owner's checkout."""
    if not argv_allowed(argv):
        raise SdlcError(f"BLOCKED integrity {label}: command is not on the allowlist")
    r = store.load_meta(rid)["repos"][repo]
    sha = git(r["path"], "rev-parse", ref)
    wt = verify._checkout(rid, repo, r["path"], sha, f"pack-{label}")
    try:
        job = verify.run_job(rid, label, [a.replace("{ref}", sha) for a in argv], wt)
        if job.exit != 0:
            raise SdlcError(f"BLOCKED env {label} failed: {job.out.strip()[:200]}")
        if argv[0] == "npm":  # npm prints the tarball's name: the artifact is that file's bytes
            tar = wt / job.out.strip().splitlines()[-1]
            if not tar.resolve().is_relative_to(wt.resolve()) or not tar.is_file():
                raise SdlcError(f"BLOCKED env {label} produced no tarball")
            return tar.read_bytes()
        return job.out
    finally:
        verify._drop(r["path"], wt)


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
    target = (pwt / pin["file"]).resolve()
    if not safe_relpath(pin["file"]) or not target.is_relative_to(pwt.resolve()):
        raise SdlcError(f"BLOCKED integrity pin file {pin['file']} resolves outside the consumer worktree")
    new = pin["line"].replace("{digest}", published)
    prefix = pin["line"].split("{digest}")[0]  # the part that names what is pinned, e.g. "lib="
    lines = target.read_text().splitlines() if target.exists() else []
    hit = [i for i, ln in enumerate(lines) if prefix and ln.startswith(prefix)]
    if hit:
        lines[hit[0]] = new  # replace only the matching pin line
        lines = [ln for i, ln in enumerate(lines) if i not in hit[1:]]
    else:
        lines.append(new)
    target.write_text("\n".join(lines) + "\n")
    git(pwt, "add", "--", pin["file"])  # only the pin file, never the rest of the worktree
    git(pwt, "commit", "-qm", f"sdlc: pin {producer} {published[:12]}", "--", pin["file"])
    rec = {"digest": published, "pin_sha": git(pwt, "rev-parse", "HEAD")}
    store.update_cp(rid, lambda cp: cp.setdefault("release", {}).__setitem__(producer, rec))
    return rec


def gate(rid: str, meta: dict, consumer: str | None = None) -> tuple[int, str]:
    """Read-only: consumers stay PENDING until the producer's release is recorded, matches the packed artifact and is pinned.
    It reads the digests `pack` recorded and compares source SHAs; it never packs or runs a command."""
    cp = store.load_cp(rid)
    for e in edges(rid):
        if e.get("release", {}).get("kind", "none") == "none" or (consumer and e["consumer"] != consumer):
            continue
        p = e["producer"]
        rel, packed = cp.get("release", {}).get(p), cp.get("artifacts", {}).get(p)
        if not rel or not packed:
            return PENDING, f"{e['consumer']} awaits publication of {p}"
        if packed["source"] != git(meta["repos"][p]["path"], "rev-parse", meta["repos"][p]["branch"]):
            return PENDING, f"{p} changed after its release was recorded"
        pinned = git(meta["repos"][e["consumer"]]["path"], "show", f"{meta['repos'][e['consumer']]['branch']}:{e['pin']['file']}")
        if e["pin"]["line"].replace("{digest}", rel["digest"]) not in pinned.splitlines():
            return PENDING, f"{e['consumer']} does not carry the pin for {p}"
    return READY, ""
