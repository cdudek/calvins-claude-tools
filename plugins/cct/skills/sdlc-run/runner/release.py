"""Producer and consumer repos in one run (design 3.6): artifacts with identity, merge order, publication, the consumer pin."""
from __future__ import annotations

import contextlib
import json
import posixpath
import re

import deps
import store
import verify
from contract import PENDING, READY, VENDORED, argv_allowed, edge_packs, git, safe_relpath
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


def _run(rid: str, repo: str, argv: list[str], ref: str, label: str) -> tuple[str | bytes, str | None]:
    """Run an allowlisted pack or fetch command in a detached worktree at `ref`, never in the owner's checkout.
    Returns (the artifact's bytes or the command's output, the tarball's file name for npm)."""
    if not argv_allowed(argv):
        raise SdlcError(f"BLOCKED integrity {label}: command is not on the allowlist")
    r = store.load_meta(rid)["repos"][repo]
    sha = git(r["path"], "rev-parse", ref)
    wt = verify._checkout(rid, repo, r["path"], sha, "pack-" + re.sub(r"[^A-Za-z0-9]+", "-", label))
    try:
        job = verify.run_job(rid, label, [a.replace("{ref}", sha) for a in argv], wt)
        if job.exit != 0:
            raise SdlcError(f"BLOCKED env {label} failed: {job.out.strip()[:200]}")
        if argv[0] == "npm":  # npm prints the tarball's name: the artifact is that file's bytes
            names = [ln.strip() for ln in job.out.splitlines() if ln.strip().endswith(".tgz")]
            tar = wt / names[-1] if names else wt
            if not names or "/" in names[-1] or not tar.resolve().is_relative_to(wt.resolve()) or not tar.is_file():
                raise SdlcError(f"BLOCKED env {label} produced no tarball")
            return tar.read_bytes(), names[-1]
        return job.out, None
    finally:
        verify._drop(r["path"], wt)


def _of(rid: str, producer: str) -> list[dict]:
    return [e for e in edges(rid) if e["producer"] == producer]


def _packs(rid: str, producer: str, fetch: bool) -> dict[str | None, list[str]]:
    """Pack (or fetch) argv per package for a producer: every package any of its edges names, once."""
    out: dict[str | None, list[str]] = {}
    for e in _of(rid, producer):
        out.update(edge_packs(e) if e.get("packages") or not fetch else {None: e.get("release", {}).get("fetch", e["pack"])})
    return out


def _measure(rid: str, producer: str, ref: str, fetch: bool = False) -> tuple[dict, dict[str, tuple[str, bytes]]]:
    """Identity of the producer at `ref`: the source SHA, a digest per package and one combined digest.
    Also the tarball bytes per package, which `pack` keeps and `publish` vendors."""
    path = store.load_meta(rid)["repos"][producer]["path"]
    ident = {"source": git(path, "rev-parse", ref)}
    argvs = _packs(rid, producer, fetch)
    if set(argvs) == {None}:  # one plain artifact, as in 4.0
        out, _ = _run(rid, producer, argvs[None], ref, f"{'fetch' if fetch else 'pack'}-{producer}")
        return {**ident, "digest": store.sha256(out)}, {}
    pk, blobs = {}, {}
    for name, argv in argvs.items():
        data, fname = _run(rid, producer, argv, ref, f"{'fetch' if fetch else 'pack'}-{producer}-{name}")
        pk[name] = {"digest": store.sha256(data), "file": fname}
        blobs[name] = (fname, data)
    return {**ident, "digest": store.sha256(store.canon({n: p["digest"] for n, p in pk.items()})), "packages": pk}, blobs


def identity(rid: str, edge: dict, ref: str) -> dict:
    return _measure(rid, edge["producer"], ref)[0]


def pack(rid: str, producer: str) -> dict:
    """Pack the producer's current head; consumers see it through SDLC_ARTIFACT_<PRODUCER> while they verify."""
    meta = store.load_meta(rid)
    if not _of(rid, producer):
        raise SdlcError(f"{producer} is not the producer of any edge")
    ident, blobs = _measure(rid, producer, meta["repos"][producer]["branch"])
    if blobs:  # keep the tarballs: the consumer's checks may read them, and publish compares what the remote built
        d = store.run_dir(rid) / "artifacts" / producer
        d.mkdir(parents=True, exist_ok=True)
        for fname, data in blobs.values():
            (d / fname).write_bytes(data)
        ident["dir"] = str(d)
    store.update_cp(rid, lambda cp: cp.setdefault("artifacts", {}).__setitem__(producer, ident))
    return ident


def _differs(packed: dict, published: dict, producer: str) -> str:
    if packed["digest"] == published["digest"]:
        return ""
    for n, p in published.get("packages", {}).items():  # name the package that moved
        if packed.get("packages", {}).get(n, {}).get("digest") != p["digest"]:
            return f"BLOCKED integrity published artifact of {producer} (package {n}) differs from the packed one"
    return f"BLOCKED integrity published artifact of {producer} differs from the packed one"


def publish(rid: str, producer: str) -> dict:
    """After the owner merged the producer: fetch what was published, require the packed identity, apply the approved pin
    to every consumer of the producer."""
    meta = store.load_meta(rid)
    if not _of(rid, producer):
        raise SdlcError(f"{producer} is not the producer of any edge")
    packed = store.load_cp(rid).get("artifacts", {}).get(producer)
    if not packed:
        raise SdlcError(f"{producer} was never packed")
    r = meta["repos"][producer]
    git(r["path"], "fetch", "-q", "origin")
    published, blobs = _measure(rid, producer, f"origin/{r['default_branch']}", fetch=True)
    if why := _differs(packed, published, producer):
        raise SdlcError(why)
    from engine import project_wt
    rec: dict = {"digest": published["digest"], "consumers": {}}
    for edge in _of(rid, producer):
        pwt = project_wt(rid, edge["consumer"])
        if edge.get("release", {}).get("kind") == VENDORED:
            files = _pin_vendored(rid, edge, pwt, {n: blobs[n] for n in edge["packages"]})
        else:
            files = _pin_line(edge, pwt, published["digest"])
        rec["consumers"][edge["consumer"]] = {"pin_sha": git(pwt, "rev-parse", "HEAD"), "files": files}
        rec["pin_sha"] = rec["consumers"][edge["consumer"]]["pin_sha"]
    store.update_cp(rid, lambda cp: cp.setdefault("release", {}).__setitem__(producer, rec))
    return rec


def _pin_line(edge: dict, pwt, digest: str) -> dict:
    pin = edge["pin"]
    target = (pwt / pin["file"]).resolve()
    if not safe_relpath(pin["file"]) or not target.is_relative_to(pwt.resolve()):
        raise SdlcError(f"BLOCKED integrity pin file {pin['file']} resolves outside the consumer worktree")
    new = pin["line"].replace("{digest}", digest)
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
    git(pwt, "commit", "-qm", f"sdlc: pin {edge['producer']} {digest[:12]}", "--", pin["file"])
    return {}


SECTIONS = ("dependencies", "devDependencies", "optionalDependencies")
LOCK = ["npm", "install", "--package-lock-only", "--ignore-scripts", "--offline"]


def _pin_vendored(rid: str, edge: dict, pwt, blobs: dict[str, tuple[str, bytes]]) -> dict:
    """Vendor the producer's tarballs into the consumer, point its package.json at them and let npm rewrite the lockfile
    offline with scripts off. The runner then records the resulting bytes as the approved ones. Any failure undoes the worktree."""
    pin, consumer = edge["pin"], edge["consumer"]
    man_rel = pin.get("manifest", "package.json")
    vend = pin["dir"].rstrip("/")
    mdir = posixpath.dirname(man_rel) or "."
    root = pwt.resolve()
    man = (pwt / man_rel).resolve()
    if not (pwt / vend).resolve().is_relative_to(root) or not man.is_relative_to(root) or not man.is_file():
        raise SdlcError(f"BLOCKED integrity pin of {consumer}: {man_rel} or {vend} is missing or outside the consumer worktree")
    text = man.read_text()
    doc = json.loads(text)
    indent = (re.search(r'^([ \t]+)"', text, re.M) or [None, "  "])[1]
    gone: list[str] = []
    for name, (fname, _) in blobs.items():
        seen = [s for s in SECTIONS if name in doc.get(s, {})]
        if not seen:
            raise SdlcError(f"BLOCKED plan {consumer}'s {man_rel} does not depend on {name}, so there is nothing to pin")
        for s in seen:
            old = doc[s][name]
            if old.startswith("file:") and old.endswith(".tgz"):
                gone.append(posixpath.normpath(posixpath.join(mdir, old[5:])))
            doc[s][name] = "file:" + posixpath.relpath(f"{vend}/{fname}", mdir)
    gone = [g for g in dict.fromkeys(gone) if g.startswith(vend + "/") and g not in {f"{vend}/{f}" for f, _ in blobs.values()}]
    try:
        for g in gone:
            (pwt / g).unlink(missing_ok=True)
        (pwt / vend).mkdir(parents=True, exist_ok=True)
        for fname, data in blobs.values():
            (pwt / vend / fname).write_bytes(data)
        man.write_text(json.dumps(doc, indent=indent, ensure_ascii=False) + ("\n" if text.endswith("\n") else ""))
        job = verify.run_job(rid, f"{consumer}-pin", LOCK, pwt / mdir)
        if job.exit != 0:
            raise SdlcError(f"BLOCKED env the lockfile of {consumer} could not be rewritten offline ({job.out.strip()[-200:] or 'exit ' + str(job.exit)})")
    except BaseException:
        git(pwt, "reset", "-q", "--hard")
        git(pwt, "clean", "-fdq", "--", vend)
        for d in (pwt / vend, *(pwt / vend).parents):  # the empty folders this attempt made, up to the worktree
            if d == pwt or not d.is_relative_to(pwt):
                break
            with contextlib.suppress(OSError):
                d.rmdir()
        raise
    lock_rel = posixpath.normpath(posixpath.join(mdir, "package-lock.json"))
    files = {man_rel: store.sha256(man.read_bytes()), lock_rel: store.sha256((pwt / lock_rel).read_bytes()),
             **{f"{vend}/{f}": store.sha256(d) for f, d in blobs.values()}}
    rec = {k: v for k, v in deps.pin_record(rid, consumer).items() if k not in gone}
    pdir = store.run_dir(rid) / "pins"
    pdir.mkdir(exist_ok=True)
    store.write_json(pdir / f"{consumer}.json", {**rec, **files})  # written by the runner: the new approved bytes
    git(pwt, "add", "-A", "--", man_rel, lock_rel, vend)
    git(pwt, "commit", "-qm", f"sdlc: pin {edge['producer']} {store.sha256(store.canon(files))[:12]}", "--", man_rel, lock_rel, vend)
    return files


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
        c = meta["repos"][e["consumer"]]
        if e["release"]["kind"] == VENDORED:  # the consumer's head must hold exactly the bytes the runner pinned
            want = rel.get("consumers", {}).get(e["consumer"], {}).get("files", {})
            if not want or any(store.sha256(deps.blob(c["path"], c["branch"], f)) != d for f, d in want.items()):
                return PENDING, f"{e['consumer']} does not carry the pin for {p}"
            continue
        pinned = git(c["path"], "show", f"{c['branch']}:{e['pin']['file']}")
        if e["pin"]["line"].replace("{digest}", rel["digest"]) not in pinned.splitlines():
            return PENDING, f"{e['consumer']} does not carry the pin for {p}"
    return READY, ""
