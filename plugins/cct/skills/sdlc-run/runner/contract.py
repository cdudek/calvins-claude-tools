"""Contract, approval digest, receipts and the `sdlc check` verdict (design 3.2, 3.4).

A receipt is written only by verify.py, from the exit status and output of the process it ran. It binds the run,
the contract item, the repo head it ran on, the approved-bundle digest, the digest of the pinned inputs, the exit
code and the collected-test count. `check` recomputes every one of those; a pass for another head, another
contract or another set of pinned files is stale. Receipts are unsigned: the plugin hook that keeps agents out of the runs folder is the barrier.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import store
from store import SdlcError

READY, FAIL, BLOCKED, PENDING = 0, 1, 2, 3
# The owner's decision lives only in the memory of the process that ran the gate: `discover.gate` grants it after Plannotator
# returned "approved" and consumes it in the same process. No file stands in for it, so no other process can forge one.
_GRANTS: dict[tuple[str, str], str] = {}
NAMES = {READY: "READY", FAIL: "FAIL", BLOCKED: "BLOCKED", PENDING: "PENDING"}
CHECK_FIELDS = ("id", "repo", "milestone", "runner", "expect")


def git(repo: str | Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    if r.returncode:
        raise SdlcError(f"git {' '.join(args)} failed in {repo}: {r.stderr.strip()}")
    return r.stdout.strip()


def wt_path(repo_path: str, rid: str, name: str) -> Path:
    """Worktrees live at <repo>/.worktrees/<name>, kept out of the tracked tree through .git/info/exclude."""
    common = Path(git(repo_path, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    ex = common / "info" / "exclude"
    ex.parent.mkdir(parents=True, exist_ok=True)
    if ".worktrees/" not in (ex.read_text() if ex.exists() else "").splitlines():
        with open(ex, "a") as f:
            f.write(".worktrees/\n")
    return Path(repo_path) / ".worktrees" / f"sdlc-{rid}-{name}"


# Exact shapes only: {ref} is the one placeholder. npm packs with scripts off; no source-building python packer.
PACK_ALLOWED = (("git", "ls-tree", "-r", "{ref}"), ("git", "archive", "--format=tar", "{ref}"), ("git", "rev-parse", "{ref}"),
                ("npm", "pack", "--ignore-scripts"))


def safe_relpath(p) -> bool:
    return (isinstance(p, str) and p != "" and "\\" not in p and not p.startswith(("/", "~")) and ".." not in p.split("/")
            and "." not in p.split("/")[:1] and "" not in p.split("/"))


# A workspace package name: optional @scope/, no leading dot or dash, so it can never read as an option or a path.
PKG_NAME = re.compile(r"^(@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*$")
VENDORED = "vendored-tarball"


def workspace_pack(name: str) -> list[str]:
    return ["npm", "pack", "--ignore-scripts", "--workspace", name]


def argv_allowed(argv) -> bool:
    if not isinstance(argv, list):
        return False
    ws = len(argv) == 5 and isinstance(argv[4], str) and PKG_NAME.fullmatch(argv[4]) is not None and argv == workspace_pack(argv[4])
    return tuple(argv) in PACK_ALLOWED or ws  # shortcut: npm only; pnpm and yarn packs are not run, 4.1 has no source-building packer


def pkg_names(e: dict) -> list[str]:
    """Package names of an edge: plain names, or {"name": ..., "dir": ...} objects (dir is informational)."""
    return [x if isinstance(x, str) else x.get("name") for x in e.get("packages") or []]


def edge_packs(e: dict) -> dict[str | None, list[str]]:
    """The pack argv per package of an edge; a plain single-artifact edge is {None: argv}."""
    return {n: workspace_pack(n) for n in pkg_names(e)} if e.get("packages") else {None: e["pack"]}


def vendored(e: dict) -> bool:
    """A consumer that gets the producer's tarballs vendored and pinned structurally in its package.json."""
    return e.get("release", {}).get("kind") == VENDORED or e.get("pin", {}).get("kind") in (VENDORED, "package-json")


def pin_dir(e: dict) -> str:
    return (e["pin"].get("dir") or e["pin"].get("vendor_dir") or "").rstrip("/")


def pin_manifest(e: dict) -> str:
    return e["pin"].get("manifest") or e["pin"].get("file") or "package.json"


def pinned_map(c: dict) -> dict[str, list[str]]:
    """pinned_inputs as {repo: [paths]}; the list form [{"repo", "path", ...}] is accepted too."""
    v = c.get("pinned_inputs") or {}
    if isinstance(v, list):
        out: dict[str, list[str]] = {}
        for x in v:
            out.setdefault(x["repo"], []).append(x["path"])
        return out
    return v


def validate_pinned_inputs(c: dict) -> None:
    v = c.get("pinned_inputs")
    if v is None:
        return
    items = [(x.get("repo") if isinstance(x, dict) else None, x.get("path") if isinstance(x, dict) else None) for x in v] if isinstance(v, list) \
        else [(r, p) for r, ps in v.items() for p in (ps if isinstance(ps, list) else [None])] if isinstance(v, dict) else [(None, None)]
    for repo, rel in items:
        if not (isinstance(repo, str) and repo and safe_relpath(rel)):
            raise SdlcError("pinned_inputs must be {repo: [paths]} or [{repo, path}] with relative paths inside the repo")


BAD_PLACEHOLDER = re.compile(r"\{producer_sha:(?![A-Za-z0-9._-]+\})")


def validate_placeholders(c: dict) -> None:
    """{base}, {head} and {producer_sha:<repo>} are the only substitutions; a producer_sha must name a repo the contract knows."""
    repos = {k["repo"] for k in c.get("checks", [])} | {e["producer"] for e in c.get("edges", [])} | {e["consumer"] for e in c.get("edges", [])}
    for k in c.get("checks", []):
        for a in [*runner_of(k), *(k["expect"].get("control") or [])]:
            if not isinstance(a, str):
                continue
            if BAD_PLACEHOLDER.search(a):
                raise SdlcError(f"check {k['id']}: malformed {{producer_sha:<repo>}} placeholder")
            for m in re.finditer(r"\{producer_sha:([A-Za-z0-9._-]+)\}", a):
                if m[1] not in repos:
                    raise SdlcError(f"check {k['id']}: {{producer_sha:{m[1]}}} names a repo the contract does not know")


READY_URL = re.compile(r"^http://(127\.0\.0\.1|localhost)(:(\d{2,5}|\{port\}))?(/[A-Za-z0-9._~/%?&=-]*)?$")
BOARD_KEYS = {"spec", "expected_rows", "build", "start", "ready_url", "ready_timeout", "surface_allow"}


def runner_of(chk: dict) -> list[str]:
    """The argv a check runs. A `"kind": "board"` row names no runner path: the runner's own board.py runs the pinned spec."""
    if chk.get("kind") == "board":
        b = chk["board"]
        argv = [sys.executable, str(Path(__file__).with_name("board.py")), "check", b["spec"], "--expected-rows", str(b["expected_rows"])]
        if b.get("surface_allow"):  # from the approved row, never from the spec: the spec cannot widen what a surface may be given
            argv += ["--surface-allow", json.dumps(b["surface_allow"], sort_keys=True)]
        return argv
    return chk["runner"]


def validate_board_row(chk: dict) -> None:
    """`{"kind": "board", "board": {"spec", "expected_rows", "start"?, "ready_url"?, "ready_timeout"?}, "pins": {<spec>: sha256}, ...}`:
    the spec is a pinned input, the row count is the approved one, and `start` (an argv the contract approved) brings the web app up
    for the check and is stopped afterwards."""
    b, who = chk.get("board"), f"check {chk['id']}"
    if not isinstance(b, dict) or set(b) - BOARD_KEYS:
        raise SdlcError(f"{who}: board must be an object with only {sorted(BOARD_KEYS)}")
    if not safe_relpath(b.get("spec")) or b["spec"] not in chk.get("pins", {}):
        raise SdlcError(f"{who}: board.spec must be a relative path listed in pins, so a modified copy is refused")
    n = b.get("expected_rows")
    if not (isinstance(n, int) and not isinstance(n, bool) and n > 0):
        raise SdlcError(f"{who}: board.expected_rows must be a whole number above 0")
    if b.get("surface_allow") is not None:
        import board
        try:
            board.validate_allow(b["surface_allow"], f"{who}: board.surface_allow")
        except ValueError as e:
            raise SdlcError(str(e)) from None
    build = b.get("build")
    if build is not None and not (isinstance(build, list) and build and all(isinstance(a, str) for a in build)):
        raise SdlcError(f"{who}: board.build is an argv list")
    start, url, wait = b.get("start"), b.get("ready_url"), b.get("ready_timeout", 120)
    if start is not None and not (isinstance(start, list) and start and all(isinstance(a, str) for a in start) and isinstance(url, str)):
        raise SdlcError(f"{who}: board.start is an argv list and needs board.ready_url")
    if url is not None and not (isinstance(url, str) and READY_URL.match(url)):
        raise SdlcError(f"{who}: board.ready_url must be an http://127.0.0.1 or http://localhost URL")
    if not (isinstance(wait, int) and not isinstance(wait, bool) and 1 <= wait <= 600):
        raise SdlcError(f"{who}: board.ready_timeout is whole seconds from 1 to 600")


def validate_board_checks(c: dict) -> None:
    """A board check's spec is a pinned input and its row count comes from the approved row, never from the spec file."""
    for k in c.get("checks", []):
        r = k.get("runner") or []
        for i, a in enumerate(r):
            if isinstance(a, str) and a.rsplit("/", 1)[-1] == "board.py" and r[i + 1:i + 2] == ["check"]:
                spec = r[i + 2] if len(r) > i + 2 else None
                if spec not in k.get("pins", {}):
                    raise SdlcError(f"check {k['id']}: the board spec {spec} must be listed in pins, so a modified copy is refused")
                n = r[r.index("--expected-rows") + 1] if "--expected-rows" in r and len(r) > r.index("--expected-rows") + 1 else None
                if not (isinstance(n, str) and n.isdigit() and int(n) > 0):
                    raise SdlcError(f"check {k['id']}: a board check needs --expected-rows N (N > 0) in its approved runner")


def validate_edges(c: dict) -> None:
    for e in c.get("edges", []):
        for k in ("producer", "consumer"):
            if k not in e:
                raise SdlcError(f"edge lacks {k}")
        pk = e.get("packages")
        if pk is not None:
            names = pkg_names(e) if isinstance(pk, list) else []
            if not (names and len(set(names)) == len(names) and all(isinstance(n, str) and PKG_NAME.fullmatch(n) for n in names)
                    and all(isinstance(x, str) or (isinstance(x, dict) and ("dir" not in x or safe_relpath(str(x["dir"]).rstrip("/")))) for x in pk)):
                raise SdlcError(f"edge {e['producer']}: packages must be a non-empty list of distinct workspace package names")
            if "pack" in e and not argv_allowed(e["pack"]):
                raise SdlcError(f"edge {e['producer']}: pack command is not on the allowlist {[' '.join(a) for a in PACK_ALLOWED]}")
        elif "pack" not in e:
            raise SdlcError("edge lacks pack or packages")
        elif not argv_allowed(e["pack"]):
            raise SdlcError(f"edge {e['producer']}: pack command is not on the allowlist {[' '.join(a) for a in PACK_ALLOWED]}")
        rel = e.get("release", {})
        pin = e.get("pin", {})
        if vendored(e):
            if rel.get("kind") != VENDORED:  # a pin kind alone would let a consumer reach READY with no pack, publish or pin
                raise SdlcError(f"edge {e['producer']}: a vendored pin needs release.kind \"{VENDORED}\"")
            man = pin_manifest(e)
            if not pk:
                raise SdlcError(f"edge {e['producer']}: {VENDORED} needs packages")
            if not safe_relpath(pin_dir(e)) or not safe_relpath(man) or not man.endswith("package.json") \
                    or ("lockfile" in pin and not safe_relpath(pin["lockfile"])) or pin.get("section", "dependencies") not in SECTIONS:
                raise SdlcError(f"edge {e['producer']}: pin.dir and pin.manifest must be relative paths inside the repo (no .. or absolute path)")
            if rel.get("kind", "none") not in ("none", VENDORED) and "fetch" in rel and not argv_allowed(rel["fetch"]):
                raise SdlcError(f"edge {e['producer']}: fetch command is not on the allowlist")
        elif rel.get("kind", "none") != "none":
            if not argv_allowed(rel.get("fetch")):
                raise SdlcError(f"edge {e['producer']}: fetch command is not on the allowlist")
            if not safe_relpath(pin.get("file")) or not isinstance(pin.get("line"), str):
                raise SdlcError(f"edge {e['producer']}: pin.file must be a relative path inside the repo (no .. or absolute path)")


SECTIONS = ("dependencies", "devDependencies", "optionalDependencies")


MAX_BUILDERS = 10  # the default is 8; the contract may raise it to this


def validate_contract(c: dict) -> None:
    validate_edges(c)
    validate_pinned_inputs(c)
    b = c.get("limits", {}).get("builders", 8)
    if not (isinstance(b, int) and not isinstance(b, bool) and 1 <= b <= MAX_BUILDERS):
        raise SdlcError(f"limits.builders must be a whole number from 1 to {MAX_BUILDERS} (default 8)")
    ids = set()
    for chk in c.get("checks", []):
        for f in CHECK_FIELDS:
            if f not in chk and not (f == "runner" and chk.get("kind") == "board"):
                raise SdlcError(f"contract check {chk.get('id', '?')} lacks {f}")
        if not (isinstance(chk["id"], str) and CHECK_ID.match(chk["id"]) and ".." not in chk["id"]):
            raise SdlcError(f"check id {chk['id']!r} must be letters, digits and . _ : / - (up to 80), starting with a letter or digit, no ..")
        if chk["id"] in ids:
            raise SdlcError(f"duplicate contract check {chk['id']}")
        ids.add(chk["id"])
        if chk.get("kind") == "board":
            validate_board_row(chk)
        elif not isinstance(chk.get("runner"), list) or not chk["runner"]:
            raise SdlcError(f"check {chk['id']}: runner must be an argv list")
        if chk["expect"].get("kind") not in ("pass", "fails_on_base", "negative_control"):
            raise SdlcError(f"check {chk['id']}: expect.kind must be pass, fails_on_base or negative_control")
    validate_placeholders(c)
    validate_board_checks(c)
    validate_bases(c)
    validate_spec(c)


# ---- the spec the checks must cover (4.2) -------------------------------------------------------------------------------
CHECK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,79}$")
SPEC_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$")


def validate_spec(c: dict) -> None:
    """`spec`: [{"id", "text", "source"?}] is part of the contract and so of the approved bundle digest. A check's `covers` names spec ids
    (unknown ids are an error). Every spec item needs a covering check or a named waiver `spec_waivers: [{"id", "reason"}]`.
    A contract with no `spec` key has none of this."""
    spec, waivers = c.get("spec"), c.get("spec_waivers", [])
    known: set[str] = set()
    if spec is not None:
        if not isinstance(spec, list) or not spec:
            raise SdlcError("spec must be a non-empty list of {id, text, source}")
        for it in spec:
            if not (isinstance(it, dict) and isinstance(it.get("id"), str) and SPEC_ID.match(it["id"]) and isinstance(it.get("text"), str)
                    and it["text"].strip() and set(it) <= {"id", "text", "source"} and isinstance(it.get("source", ""), str)):
                raise SdlcError(f"spec item {it.get('id', it) if isinstance(it, dict) else it!r} needs an id, a text and optionally a source")
            if it["id"] in known:
                raise SdlcError(f"duplicate spec id {it['id']}")
            known.add(it["id"])
    for chk in c.get("checks", []):
        cov = chk.get("covers", [])
        if not isinstance(cov, list) or not all(isinstance(i, str) for i in cov):
            raise SdlcError(f"check {chk['id']}: covers must be a list of spec ids")
        if unknown := [i for i in cov if i not in known]:
            raise SdlcError(f"check {chk['id']} covers unknown spec id {', '.join(unknown)}")
    if spec is None:
        if waivers:
            raise SdlcError("spec_waivers need a spec")
        return
    waived: set[str] = set()
    for w in waivers if isinstance(waivers, list) else [None]:
        if not (isinstance(w, dict) and w.get("id") in known and isinstance(w.get("reason"), str) and w["reason"].strip() and set(w) <= {"id", "reason"}):
            raise SdlcError(f"a spec waiver needs the id of a spec item and a reason: {w!r}")
        waived.add(w["id"])
    covered = {i for chk in c.get("checks", []) for i in chk.get("covers", [])}
    if missing := [i for i in sorted(known) if i not in covered and i not in waived]:
        raise SdlcError(f"spec items with no covering check and no named waiver: {', '.join(missing)}")


def spec_rows(c: dict) -> list[dict]:
    """Per spec item: its text, covering checks, their tasks and the waiver, uncovered and waived items first."""
    waivers = {w["id"]: w["reason"] for w in c.get("spec_waivers", [])}
    out = []
    for it in c.get("spec") or []:
        cov = [k for k in c.get("checks", []) if it["id"] in k.get("covers", [])]
        out.append({"id": it["id"], "text": it["text"], "source": it.get("source", ""), "checks": [k["id"] for k in cov],
                    "tasks": sorted({k["task"] for k in cov if k.get("task")}), "waiver": waivers.get(it["id"])})
    return sorted(out, key=lambda r: (bool(r["checks"]) and not r["waiver"], r["waiver"] is None, r["id"]))


def spec_status(rid: str, sealed: bool) -> list[dict]:
    """PASS, FAIL, WAIVED or PENDING per spec item, rolled up from the receipts of its covering checks. PASS needs every covering check to
    have passed on the current head with a receipt of this bundle, and the final gate to have sealed those heads (`sealed`)."""
    c = store.read_json(store.run_dir(rid) / "contract.json")
    meta = store.load_meta(rid)
    out = []
    for r in spec_rows(c):
        if not r["checks"]:
            out.append({**r, "status": "WAIVED"})
            continue
        states = []
        for k in (k for k in c["checks"] if k["id"] in r["checks"]):
            rec = read_receipt(rid, k)
            b = rec["body"] if rec else None
            try:
                fresh = b and b["bundle"] == bundle_digest(rid) and b["pins"] == pins_digest(k) and b["sha"] == current_head(meta, k["repo"])
            except SdlcError:
                fresh = False
            states.append("PENDING" if not fresh else ("PASS" if b["verdict"] == "PASS" else "FAIL"))
        status = "FAIL" if "FAIL" in states else "PENDING" if "PENDING" in states or not sealed else "PASS"
        out.append({**r, "status": status})
    return out


def spec_report(rid: str, sealed: bool) -> list[str]:
    return [f"SPEC {r['id']} {r['status']}: {', '.join(r['checks']) or ('waived: ' + r['waiver'])}" for r in spec_status(rid, sealed)]


# ---- an approved base per repo (4.2) -----------------------------------------------------------------------------------
BASE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,99}$")


def validate_bases(c: dict) -> None:
    """`repos.<repo>.base` is a branch to build on instead of the default branch; `base_sha` is what the runner resolved it to."""
    repos = c.get("repos")
    if repos is None:
        return
    if not isinstance(repos, dict):
        raise SdlcError("contract repos must map a repo name to {base}")
    for name, r in repos.items():
        ref, sha = (r.get("base"), r.get("base_sha")) if isinstance(r, dict) and set(r) <= {"base", "base_sha"} else (0, 0)
        if ref == 0 or not (ref is None or (isinstance(ref, str) and BASE_REF.match(ref) and ".." not in ref and "//" not in ref
                                            and not ref.endswith(("/", ".lock")))):
            raise SdlcError(f"repos.{name}: base must be a branch name (letters, digits, . _ - /)")
        if sha is not None and not (ref and isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{40}", sha)):
            raise SdlcError(f"repos.{name}: base_sha must be a full SHA of its base")


def resolve_base(repo: dict, ref: str) -> str:
    """The full SHA of `ref`, fetched from origin when the repo has one."""
    p = repo["path"]
    if repo.get("remote"):
        r = subprocess.run(["git", "fetch", "-q", "origin", f"+refs/heads/{ref}:refs/remotes/origin/{ref}"], cwd=p, capture_output=True, text=True)
        if r.returncode:
            raise SdlcError(f"BLOCKED env cannot fetch origin/{ref}: {r.stderr.strip()[:120]}")
        return git(p, "rev-parse", "--verify", f"refs/remotes/origin/{ref}^{{commit}}")
    return git(p, "rev-parse", "--verify", f"refs/heads/{ref}^{{commit}}")


def base_ahead(repo: dict, sha: str) -> int:
    d = repo["default_branch"]
    return int(git(repo["path"], "rev-list", "--count", f"{'refs/remotes/origin/' if repo.get('remote') else 'refs/heads/'}{d}..{sha}"))


def base_problem(rid: str) -> str:
    """Empty when every approved base ref still is the SHA the owner approved; otherwise which ref moved. The run never follows a ref."""
    meta = store.load_meta(rid)
    for name, r in (store.read_json(store.run_dir(rid) / "contract.json").get("repos") or {}).items():
        if not r.get("base"):
            continue
        if not r.get("base_sha") or name not in meta["repos"]:
            return f"base {r['base']} of {name} was never resolved (run `sdlc draft`)"
        try:
            now = resolve_base(meta["repos"][name], r["base"])
        except SdlcError as e:
            return str(e)
        if now != r["base_sha"]:
            return f"base ref {r['base']} of {name} moved from {r['base_sha'][:9]} to {now[:9]}; the run does not follow it (start a new run to build on the new tip)"
    return ""


def bundle_digest(rid: str) -> str:
    """Digest of what the owner approved: plan, contract, task graph and every pinned input file."""
    d = store.run_dir(rid)
    parts = {n: store.sha256((d / n).read_bytes()) for n in ("plan.md", "contract.json", "tasks.json") if (d / n).exists()}
    for sub in ("inputs", "deps"):  # pinned specs and fixtures; the approved manifest and lockfile contents
        root = d / sub
        for p in sorted(root.rglob("*")) if root.exists() else []:
            if p.is_file():
                parts[f"{sub}/" + p.relative_to(root).as_posix()] = store.sha256(p.read_bytes())
    return store.sha256(store.canon(parts))


def coverage(rid: str) -> list[str]:
    """What the contract leaves unproven: a milestone with no check, a task with neither a check nor a named waiver."""
    d = store.run_dir(rid)
    checks = store.read_json(d / "contract.json").get("checks", [])
    out = [] if checks else ["the contract has no checks"]
    for m in store.read_json(d / "tasks.json").get("milestones", []):
        if not any(k.get("milestone") == m["id"] or k.get("task") in {t["id"] for t in m.get("tasks", [])}
                   or (k.get("due") == "each" and k["repo"] == m["repo"]) for k in checks):  # the full gate runs at every close
            out.append(f"milestone {m['id']} has no contract check")
        for t in m.get("tasks", []):
            if not (any(k.get("task") == t["id"] for k in checks) or str(t.get("waiver", "")).strip()):
                out.append(f"task {t['id']} has no check and no named waiver")
    return out


def grant(purpose: str, rid: str) -> None:
    """Called by the gate in its own process after the owner approved this exact bundle (not by anything else)."""
    _GRANTS[(purpose, rid)] = bundle_digest(rid)


def granted(purpose: str, rid: str) -> bool:
    """One use: the grant is for the bundle as it stood when the owner decided."""
    digest = _GRANTS.pop((purpose, rid), None)
    return digest is not None and digest == bundle_digest(rid)


def approve(rid: str, by: str) -> dict:
    """Record the owner's one approval of the frozen bundle, only in the process whose gate the owner approved."""
    d = store.run_dir(rid)
    if (d / "approval.json").exists():
        raise SdlcError("this run is already approved; re-approving would reset its deadline and caps")
    c = store.read_json(d / "contract.json")
    validate_contract(c)
    if problems := coverage(rid):
        raise SdlcError("not approvable: " + "; ".join(problems))
    if problem := base_problem(rid):
        raise SdlcError("not approvable: " + problem)
    cap = c.get("limits", {}).get("max_dispatches")
    if not isinstance(cap, int) or cap < 1:
        raise SdlcError("not approvable: limits.max_dispatches must be set (a finite dispatch cap)")
    for repo, rels in pinned_map(c).items():  # exact bytes, hashed in the bundle through inputs/
        for rel in rels:
            if not safe_relpath(rel) or not (d / "inputs" / repo / rel).is_file():
                raise SdlcError(f"not approvable: pinned_inputs {repo}:{rel} needs a relative path and an --input {repo}:{rel}=<file>")
    digest = bundle_digest(rid)
    if not granted("approve", rid):
        raise SdlcError("not approvable: the approval gate has not approved this exact bundle (run `sdlc gate <id> --by <name>`)")
    hours = c.get("limits", {}).get("deadline_hours", 24)
    rec = {"digest": digest, "by": by, "at": store.iso(), "deadline": store.now() + hours * 3600}
    store.write_json(d / "approval.json", rec)
    meta = store.load_meta(rid)
    meta["local_only_ok"] = c.get("local_only_ok", [])  # approved local-only repos: the CI reader honours exactly these
    store.save_meta(rid, meta)
    store.set_status(rid, "approved", f"by {by}")
    return rec


def approved_digest_ok(rid: str) -> tuple[bool, str]:
    p = store.run_dir(rid) / "approval.json"
    if not p.exists():
        return False, "not approved"
    rec = store.read_json(p)
    return (rec["digest"] == bundle_digest(rid)), "approved bundle changed after approval"


def pins_digest(chk: dict) -> str:
    return store.sha256(store.canon(chk.get("pins", {})))


def receipt_path(rid: str, check_id: str, repo: str) -> Path:
    return store.run_dir(rid) / "receipts" / f"{repo}--{check_id.replace('/', '_')}.json"


def write_receipt(rid: str, chk: dict, *, sha: str, verdict: str, exit_code: int | None, tests: int | None,
                  base: dict | None, reason: str = "", deps: dict | None = None) -> dict:
    body = {
        "run": rid, "check": chk["id"], "repo": chk["repo"], "sha": sha, "verdict": verdict,
        "bundle": bundle_digest(rid), "pins": pins_digest(chk), "exit": exit_code, "tests": tests,
        "base": base, "reason": reason, "deps": deps or {}, "at": store.iso(),
    }
    rec = {"body": body}
    store.write_json(receipt_path(rid, chk["id"], chk["repo"]), rec)
    return rec


def read_receipt(rid: str, chk: dict) -> dict | None:
    p = receipt_path(rid, chk["id"], chk["repo"])
    return store.read_json(p) if p.exists() else None


def current_head(meta: dict, repo: str) -> str:
    r = meta["repos"][repo]
    return git(r["path"], "rev-parse", r["branch"])


def evaluate(rid: str, due: str | None = None, skip_ci: bool = False, repo: str | None = None) -> tuple[int, str, list[dict]]:
    """Recompute the verdict from records only. Read-only: never builds, reruns, pushes or edits."""
    meta = store.load_meta(rid)
    notes: list[dict] = []

    def out(code: int, first: str):
        return code, first, notes

    if store.is_stopped(rid):
        return out(BLOCKED, "STOPPED by the owner")
    ok, why = approved_digest_ok(rid)
    if not ok:
        return out(BLOCKED, f"integrity: {why}")
    contract = store.read_json(store.run_dir(rid) / "contract.json")
    if problems := coverage(rid):
        return out(BLOCKED, "contract: " + problems[0])
    heads = {}
    for name in meta["repos"]:
        try:
            heads[name] = current_head(meta, name)
        except SdlcError as e:
            return out(BLOCKED, f"integrity: {e}")
    cp = store.load_cp(rid)
    if cp.get("blocked"):
        return out(BLOCKED, cp["blocked"])
    fail = blocked = pending = None
    ran = 0
    for chk in contract["checks"]:
        if repo and chk["repo"] != repo:
            continue
        if due and chk.get("milestone") not in (due, None) and chk.get("due") != "final":
            continue
        rec = read_receipt(rid, chk)
        key = f"{chk['repo']}:{chk['id']}"
        if rec is None:
            pending = pending or f"{key} has no receipt"
            continue
        b = rec["body"]
        if b["bundle"] != bundle_digest(rid) or b["pins"] != pins_digest(chk) or b["run"] != rid:
            pending = pending or f"{key} receipt is for another contract"
            continue
        if b["sha"] != heads[chk["repo"]]:
            pending = pending or f"{key} passed on {b['sha'][:9]}, head is {heads[chk['repo']][:9]}"
            continue
        stale = _stale_deps(meta, b.get("deps", {}))
        if stale:
            pending = pending or f"{key} {stale}"
            continue
        if b["verdict"] == "FAIL":
            fail = fail or f"{key} failed: {b['reason']}"
        elif b["verdict"] == "BLOCKED":
            blocked = blocked or f"{key} blocked: {b['reason']}"
        elif b["verdict"] != "PASS":
            blocked = blocked or f"{key} has an unknown verdict"
        notes.append({"check": key, "verdict": b["verdict"], "sha": b["sha"]})
        ran += 1
    if not ran and not (fail or blocked or pending):
        return out(BLOCKED, "no contract check produced a result: an empty result set proves nothing")
    if fail:
        return out(FAIL, fail)
    if blocked:
        return out(BLOCKED, blocked)
    if pending:
        return out(PENDING, pending)
    if due is None and repo is None and (why := final_problem(rid, meta)):  # the full completion test re-checked the receipts
        return out(PENDING, why)
    if contract.get("edges"):
        import release
        code, first = release.gate(rid, meta, consumer=repo)
        if code != READY:
            return out(code, first)
    if meta.get("prs") and not skip_ci:  # once a PR exists its current checks count
        import ci
        code, first = ci.gate(rid, meta, heads)
        if code != READY:
            return out(code, first)
    return out(READY, "all required proof is present; the next action is the owner's merge")


def _final_state(rid: str, meta: dict) -> dict:
    d = store.run_dir(rid)
    heads = {n: current_head(meta, n) for n in meta["repos"]}
    receipts = {}
    for chk in store.read_json(d / "contract.json")["checks"]:
        p = receipt_path(rid, chk["id"], chk["repo"])
        receipts[p.name] = store.sha256(p.read_bytes()) if p.exists() else ""
    pins = {p.stem: store.sha256(p.read_bytes()) for p in sorted((d / "pins").glob("*.json"))}  # what the runner pinned in consumers
    return {"bundle": bundle_digest(rid), "heads": heads, "receipts": receipts, "pins": pins}


def seal_final(rid: str) -> None:
    """Written by the final gate right after it re-ran every contract check on the frozen heads."""
    store.write_json(store.run_dir(rid) / "final.json", _final_state(rid, store.load_meta(rid)))


def final_problem(rid: str, meta: dict) -> str:
    """READY needs the final gate to have re-run the checks on these heads: a receipt written, replaced or edited after it
    (or without it) is not proof."""
    p = store.run_dir(rid) / "final.json"
    if not p.exists():
        return "the final gate has not re-run the checks on the final heads (run `sdlc final`)"
    if store.read_json(p) != _final_state(rid, meta):
        return "a receipt, head or the bundle changed after the final gate ran (run `sdlc final` again)"
    return ""


def status_line(rid: str, code: int, first: str) -> str:
    meta = store.load_meta(rid)
    heads = []
    for r in meta["repos"]:
        try:
            heads.append(f"{r}@{current_head(meta, r)[:9]}")
        except SdlcError:
            heads.append(f"{r}@?")
    return f"{NAMES[code]} run={rid} heads={','.join(heads)} first={first}"


def _stale_deps(meta: dict, deps: dict) -> str:
    """A producer that moved after the consumer's receipt invalidates it (design 3.6)."""
    for producer, sha in deps.items():
        if producer in meta["repos"] and current_head(meta, producer) != sha:
            return f"proved against {producer}@{sha[:9]}, which changed"
    return ""
