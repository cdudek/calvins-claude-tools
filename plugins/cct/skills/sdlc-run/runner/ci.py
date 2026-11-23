"""Existing CI as proof (design 3.6, "Use existing CI"): read the PR's checks and the base branch's required checks.

Nothing here merges. The only remote writes are `gh pr create` and `gh pr merge --auto`; the first goes through
engine.external so it happens at most once. Every function that shells out takes an injectable `run`
(args, cwd) -> stdout so tests feed recorded JSON.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile

import contract
import engine
import store
from contract import BLOCKED, FAIL, PENDING, READY
from store import SdlcError

BAD = {"FAILURE", "ERROR", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE"}
RANK = {BLOCKED: 0, FAIL: 1, PENDING: 2, READY: 3}  # lower rank is worse


def _run(args: list[str], cwd=None) -> str:
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise SdlcError(f"{' '.join(args[:3])} failed: {(r.stderr + r.stdout).strip()}")
    return r.stdout


RUN = _run  # tests monkeypatch this


def worst(results: list[tuple[int, str]]) -> tuple[int, str]:
    return min(results, key=lambda r: RANK[r[0]], default=(READY, "ok"))


def _norm(c: dict) -> dict:
    """CheckRun (name/status/conclusion) and StatusContext (context/state) into one shape."""
    if "context" in c:
        st = c.get("state", "")
        return {
            "name": c["context"],
            "done": st != "PENDING",
            "result": st,
            "sha": c.get("head_sha"),
        }
    return {
        "name": c.get("name", ""),
        "done": c.get("status") == "COMPLETED",
        "result": c.get("conclusion") or "",
        "sha": c.get("head_sha"),
    }


def _check_one(name: str, checks: list[dict], local_head: str) -> tuple[int, str]:
    mine = [c for c in map(_norm, checks) if c["name"] == name]
    if not mine:
        return PENDING, f"check {name} has not reported"
    c = mine[-1]
    if c["sha"] and c["sha"] != local_head:
        return PENDING, f"check {name} is stale: ran on {c['sha'][:9]}, head is {local_head[:9]}"
    if not c["done"]:
        return PENDING, f"check {name} is still running"
    if c["result"] == "SUCCESS":
        return READY, f"check {name} passed"
    if c["result"] in ("SKIPPED", "NEUTRAL"):
        return PENDING, f"check {name} was skipped ({c['result'].lower()}), which proves nothing"
    if c["result"] in BAD:
        return FAIL, f"check {name} failed ({c['result'].lower()})"
    return PENDING, f"check {name} has no usable result"


def classify(
    pr_head_sha: str,
    local_head: str,
    required: list[str] | None,
    checks: list[dict],
    ci_items: list[dict],
    local_only_ok: bool = False,
) -> tuple[int, str]:
    res: list[tuple[int, str]] = []
    if required is None:
        res.append((BLOCKED, "required-check policy could not be read"))
    elif not required and not local_only_ok:
        res.append(
            (BLOCKED, "no required CI is configured and the plan did not approve local-only proof")
        )
    if pr_head_sha != local_head:
        res.append((PENDING, f"PR head {pr_head_sha[:9]} is stale, local head is {local_head[:9]}"))
        return worst(res)
    names = list(required or []) + [
        i["site"][3:] for i in ci_items if i["site"][3:] not in (required or [])
    ]
    res += [_check_one(n, checks, local_head) for n in names]
    return worst(res)


# ---- IO wrappers ------------------------------------------------------------------------------


def fetch_pr(repo_path: str, number_or_url, run=None) -> dict:
    fields = "headRefOid,statusCheckRollup,mergeStateStatus,autoMergeRequest,baseRefName,url,state"
    return json.loads(
        (run or RUN)(["gh", "pr", "view", str(number_or_url), "--json", fields], repo_path)
    )


def required_checks(repo_path: str, base_branch: str, run=None) -> list[str] | None:
    run = run or RUN
    names: set[str] = set()
    try:
        d = json.loads(
            run(
                [
                    "gh",
                    "api",
                    f"repos/{{owner}}/{{repo}}/branches/{base_branch}/protection/required_status_checks",
                ],
                repo_path,
            )
        )
        names |= set(d.get("contexts") or []) | {c["context"] for c in d.get("checks") or []}
    except SdlcError as e:
        if (
            "not protected" not in str(e).lower()
        ):  # a 404 for an unprotected branch is known absence
            return None
    except (ValueError, KeyError, TypeError):
        return None
    try:
        rules = json.loads(
            run(["gh", "api", f"repos/{{owner}}/{{repo}}/rules/branches/{base_branch}"], repo_path)
        )
        for r in rules:
            if r.get("type") == "required_status_checks":
                names |= {
                    c["context"] for c in r.get("parameters", {}).get("required_status_checks", [])
                }
    except (SdlcError, ValueError, KeyError, TypeError):
        return None
    return sorted(names)


def repo_allows_auto_merge(repo_path: str, run=None) -> bool:
    try:
        return bool(
            json.loads(
                (run or RUN)(["gh", "repo", "view", "--json", "autoMergeAllowed"], repo_path)
            ).get("autoMergeAllowed")
        )
    except (SdlcError, ValueError):
        return False


# ---- the gate contract.evaluate calls ---------------------------------------------------------


def gate(rid: str, meta: dict, heads: dict) -> tuple[int, str]:
    items = store.read_json(store.run_dir(rid) / "contract.json").get("checks", [])
    ok_local = set(meta.get("local_only_ok", []))
    res: list[tuple[int, str]] = []
    for repo, r in meta["repos"].items():
        url = meta.get("prs", {}).get(repo)
        if not url:
            res.append((PENDING, f"no PR for {repo}"))
            continue
        try:
            pr = fetch_pr(r["path"], url)
            if pr.get("state") == "CLOSED":
                res.append((BLOCKED, f"{repo}: PR was closed without merging"))
                continue
            req = required_checks(r["path"], pr["baseRefName"])
        except (SdlcError, ValueError, KeyError) as e:
            res.append((BLOCKED, f"{repo}: cannot read the PR: {e}"))
            continue
        mine = [i for i in items if i["repo"] == repo and str(i.get("site", "")).startswith("ci:")]
        code, first = classify(
            pr["headRefOid"],
            heads[repo],
            req,
            pr.get("statusCheckRollup") or [],
            mine,
            repo in ok_local,
        )
        res.append((code, f"{repo}: {first}"))
    return worst(res)


# ---- PR body and the one remote write ---------------------------------------------------------


def _two_sentences(s: str) -> str:
    return " ".join(re.split(r"(?<=[.!?])\s+", " ".join(s.split()))[:2])


def _scrub(s: str) -> str:
    s = re.sub(r"(/Users/\S*|~/\S*)", "a local path", s)
    return re.sub(r"(?i)\b(opus|sonnet|haiku)\b", "a model", s)


def _section(plan: str, name: str) -> str:
    m = re.search(rf"^##\s+{name}\s*\n(.*?)(?=^#|\Z)", plan, re.S | re.M | re.I)
    return next(
        (ln.strip(" -*") for ln in (m.group(1).splitlines() if m else []) if ln.strip()), ""
    )


def pr_body(rid: str) -> str:
    meta, d = store.load_meta(rid), store.run_dir(rid)
    plan = (d / "plan.md").read_text(encoding="utf-8") if (d / "plan.md").exists() else ""
    cp = store.load_cp(rid)
    outcome = next(
        (ln.strip() for ln in plan.splitlines() if ln.strip() and not ln.startswith("#")),
        meta.get("title", ""),
    )
    merged = [m for m, e in cp["milestones"].items() if e.get("status") == "merged"]
    why = _section(plan, "Why") or meta.get("title", "")
    proof = []
    for c in store.read_json(d / "contract.json").get("checks", []):
        rec = contract.read_receipt(rid, c)
        b = rec["body"] if rec else None
        proof.append(
            f"- **{c['id']}:** "
            + (f"{b['verdict']} on {b['sha'][:9]}" if b else "no receipt yet")
            + f" ({c['repo']})"
        )
    try:
        proof.append("- **Check:** " + contract.status_line(rid, *contract.evaluate(rid)[:2]))
    except SdlcError as e:
        proof.append(f"- **Check:** not readable ({e})")
    undo = ["- **Revert:** Reverting the merge commit restores the previous state."]
    undo += [f"- **Remote write:** {k} ({v['state']})" for k, v in sorted(cp["external"].items())]
    body = "\n".join(
        [
            "## What",
            "",
            f"- **Outcome:** {_two_sentences(outcome)}",
            f"- **Milestones merged:** {', '.join(merged) or 'none yet'}",
            "",
            "## Why",
            "",
            f"- **Reason:** {_two_sentences(why)}",
            "",
            "## Proof",
            "",
            *proof,
            "",
            "## Undo",
            "",
            *undo,
            "",
        ]
    )
    return _scrub(body)


def open_pr(rid: str, repo_name: str, run=None) -> str:
    """Create the PR once. The branch must already be pushed (engine.push); this pushes nothing."""
    run = run or RUN
    meta = store.load_meta(rid)
    r = meta["repos"][repo_name]
    sha = contract.git(r["path"], "rev-parse", r["branch"])
    found: dict = {}

    def do():
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=True) as f:
            f.write(pr_body(rid))
            f.flush()
            out = run(
                [
                    "gh",
                    "pr",
                    "create",
                    "--base",
                    r.get("default_branch", "main"),
                    "--head",
                    r["branch"],
                    "--title",
                    meta.get("title", rid),
                    "--body-file",
                    f.name,
                ],
                r["path"],
            )
        found["url"] = out.strip().splitlines()[-1]

    def done():
        prs = json.loads(
            run(
                ["gh", "pr", "list", "--head", r["branch"], "--state", "open", "--json", "url"],
                r["path"],
            )
        )
        if prs:
            found["url"] = prs[0]["url"]
        return bool(prs)

    state = engine.external(rid, f"pr:{repo_name}", sha, do, done)
    if found.get("url"):
        m = store.load_meta(rid)
        m.setdefault("prs", {})[repo_name] = found["url"]
        store.save_meta(rid, m)
    return state


def arm_auto_merge(rid: str, repo_name: str, run=None) -> bool:
    run = run or RUN
    meta = store.load_meta(rid)
    path, url = meta["repos"][repo_name]["path"], meta.get("prs", {}).get(repo_name)
    if not url:
        raise SdlcError(f"no PR for {repo_name}")
    if not repo_allows_auto_merge(path, run):
        store.log(rid, f"{repo_name}: auto-merge is not allowed here, owner merges")
        return False
    run(["gh", "pr", "merge", url, "--squash", "--auto"], path)
    store.log(rid, f"{repo_name}: auto-merge armed")
    return True
