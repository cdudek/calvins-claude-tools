"""Contract, approval digest, receipts and the `sdlc check` verdict (design 3.2, 3.4).

A receipt is written only by verify.py, from the exit status and output of the process it ran. It binds the run,
the contract item, the repo head it ran on, the approved-bundle digest, the digest of the pinned inputs, the exit
code and the collected-test count. `check` recomputes every one of those; a pass for another head, another
contract or another set of pinned files is stale. Receipts are unsigned: the plugin hook that keeps agents out of the runs folder is the barrier.
"""
from __future__ import annotations

import subprocess
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


def argv_allowed(argv) -> bool:
    return isinstance(argv, list) and tuple(argv) in PACK_ALLOWED


def validate_edges(c: dict) -> None:
    for e in c.get("edges", []):
        for k in ("producer", "consumer", "pack"):
            if k not in e:
                raise SdlcError(f"edge lacks {k}")
        if not argv_allowed(e["pack"]):
            raise SdlcError(f"edge {e['producer']}: pack command is not on the allowlist {[' '.join(a) for a in PACK_ALLOWED]}")
        rel = e.get("release", {})
        if rel.get("kind", "none") != "none":
            if not argv_allowed(rel.get("fetch")):
                raise SdlcError(f"edge {e['producer']}: fetch command is not on the allowlist")
            if not safe_relpath(e.get("pin", {}).get("file")) or not isinstance(e["pin"].get("line"), str):
                raise SdlcError(f"edge {e['producer']}: pin.file must be a relative path inside the repo (no .. or absolute path)")


def validate_contract(c: dict) -> None:
    validate_edges(c)
    ids = set()
    for chk in c.get("checks", []):
        for f in CHECK_FIELDS:
            if f not in chk:
                raise SdlcError(f"contract check {chk.get('id', '?')} lacks {f}")
        if chk["id"] in ids:
            raise SdlcError(f"duplicate contract check {chk['id']}")
        ids.add(chk["id"])
        if not isinstance(chk["runner"], list) or not chk["runner"]:
            raise SdlcError(f"check {chk['id']}: runner must be an argv list")
        if chk["expect"].get("kind") not in ("pass", "fails_on_base", "negative_control"):
            raise SdlcError(f"check {chk['id']}: expect.kind must be pass, fails_on_base or negative_control")


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
    cap = c.get("limits", {}).get("max_dispatches")
    if not isinstance(cap, int) or cap < 1:
        raise SdlcError("not approvable: limits.max_dispatches must be set (a finite dispatch cap)")
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
    return {"bundle": bundle_digest(rid), "heads": heads, "receipts": receipts}


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
