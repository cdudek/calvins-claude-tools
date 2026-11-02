"""The verify contract of the SDLC chain: one command, one last line.

    python3 scripts/verify_gate.py approve <id>              # lock the criteria at approval
    python3 scripts/verify_gate.py lint <id>                 # plain-language lint of the docs
    python3 scripts/verify_gate.py feature|milestone <id>    # run sdlc.json checks.<scope>
    # After UX review, also require each visual run:
    # ... --visual-check <omr-ux visual-check.py> --visual-run <run> [--visual-run <run> ...]

Written by `sdlc-run adopt` from the kit; edit the kit, not this copy. stdlib only.

`approve` writes <changesDir>/<id>/lock.json: the hash of facts.md, done.json and
sdlc.json `checks`, taken when the engineer approved the plan. `feature`/`milestone` refuse to
run against criteria that moved since. `milestone` also fails with check=parent-sync while
origin's default branch, or project/<slug> in a project, has commits HEAD lacks: merge them in
locally first. Then it runs the checks in order (cheapest first, the first
failure stops the run), and write <changesDir>/<id>/verify/report.json + report.md.

Stdout is capped. The last line is exactly one of:
    VERIFY PASS <scope> <id> <sha>         exit 0
    VERIFY FAIL <scope> <id> check=<name>  exit 1   -- fix and run again
    VERIFY BLOCKED reason=<code>           exit 3   -- stop and ask the engineer

A repo whose `sdlcVersion` is missing or differs from the kit's gets one `WARN` line first;
it never changes the verdict.

A check may block on its own: when its output ends `VERIFY BLOCKED reason=<code>`, that line is
passed through. The same failure three runs in a row blocks with reason=no-progress, and any
three failed runs of one scope block with reason=attempts (delete verify/state.json to start
over; a PASS resets the count).

A check that passed on this exact tree, command and lock is not run again: verify/cache.json
holds the passes and the report says `ok (cached)`. A failing E2E check (command contains
`playwright` or `test:e2e`) is re-run once with `--last-failed` to say whether its failures
reproduce (real) or not (flaky). The check still counts as failed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

from marks import sessions
from sdlc_version import kit_version, message

REASONS = {
    "not-approved",  # no lock.json: the plan gate has not run
    "protected-path",  # facts.md, done.json or checks changed since approval
    "no-progress",
    "attempts",  # three failed runs of one scope, whatever the failures were
    "flaky",
    "unknown-verdict",
    "needs-baseline",
    "allowlist-request",
    "scope-growth",
    "spec-conflict",
    "env",
    "test-proves-nothing",
}
LOCKED = ("facts.md", "done.json")
TAIL = 60  # stdout lines of a failing check
BREAKER = 3
ATTEMPTS = 3
SENTENCE_WORDS = 25


def sh(*cmd: str) -> str:
    out = subprocess.run(cmd, capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else ""


def root() -> Path:
    return Path(sh("git", "rev-parse", "--show-toplevel") or ".").resolve()


def criteria_hash(change: Path, checks: object) -> dict[str, str]:
    hashes = {
        name: hashlib.sha256((change / name).read_bytes()).hexdigest()
        for name in LOCKED
        if (change / name).exists()
    }
    hashes["checks"] = hashlib.sha256(
        json.dumps(checks, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return hashes


def parent_tips(change: Path, cfg: dict) -> list[tuple[str, str]]:
    """(branch, sha) on origin of every branch a milestone must contain: the default branch,
    and project/<slug> too when the change has a project. A branch origin lacks (no remote,
    offline, project not created yet) is left out."""
    names = [cfg.get("defaultBranch") or "main"]
    try:
        project = json.loads((change / "decisions.json").read_text(encoding="utf-8")).get("project")
    except (OSError, ValueError, AttributeError):
        project = None
    if isinstance(project, dict) and project.get("slug"):
        prefix = (cfg.get("projects") or {}).get("branchPrefix", "project/")
        names.insert(0, f"{prefix}{project['slug']}")
    tips = []
    for name in names:
        sh("git", "fetch", "--quiet", "origin", name)  # offline: the last fetched tip still counts
        tip = sh("git", "rev-parse", "--verify", "--quiet", f"origin/{name}^{{commit}}")
        if tip:
            tips.append((name, tip))
    return tips


def end(line: str, code: int) -> int:
    print(line)
    return code


def approve(change: Path, cfg: dict) -> int:
    lock = {
        "approved_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),  # noqa: UP017 -- runs on macOS python3 3.9
        "sha": sh("git", "rev-parse", "HEAD"),
        "criteria": criteria_hash(change, cfg.get("checks", {})),
    }
    (change / "lock.json").write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    print(f"locked {', '.join(lock['criteria'])} in {change.name}/lock.json -- commit it")
    return 0


def prose(text: str) -> list[str]:
    """Sentences outside frontmatter, code fences, tables, headings and HTML comments."""
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    text = re.sub(r"```.*?```|<!--.*?-->", "", text, flags=re.S)
    lines = [
        re.sub(r"^\s*(?:[-*]|\d+\.)\s+(?:\[[ x]\]\s+)?", "", line)
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith(("|", "#", ">"))
    ]
    return [s for line in lines for s in re.split(r"(?<=[.!?])\s+", line) if s.strip()]


def lint(change: Path) -> int:
    """Plain language: no sentence over SENTENCE_WORDS words, no leftover template prompts."""
    problems = []
    for name in ("intent.md", "facts.md", "plan.md"):
        path = change / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for s in prose(text):
            if len(s.split()) > SENTENCE_WORDS:
                problems.append(f"{name}: {len(s.split())} words: {s[:90]}...")
        if "[NEEDS CLARIFICATION" in text:
            problems.append(f"{name}: an open [NEEDS CLARIFICATION] remains")
    for p in problems[:TAIL]:
        print(p)
    print(f"LINT {'FAIL' if problems else 'PASS'} {change.name} problems={len(problems)}")
    return 1 if problems else 0


def signature(name: str, output: str) -> str:
    tail = "\n".join(output.strip().splitlines()[-20:])
    tail = re.sub(r"\d+(\.\d+)?m?s\b|\b[0-9a-f]{7,40}\b", "#", tail)  # timings and shas drift
    return hashlib.sha256(f"{name}\n{tail}".encode()).hexdigest()[:16]


def cache_key(tree: str, cmd: str, criteria: dict[str, str]) -> str:
    return hashlib.sha256(
        "\n".join([tree, cmd, json.dumps(criteria, sort_keys=True)]).encode()
    ).hexdigest()


def is_e2e(cmd: str) -> bool:
    return "playwright" in cmd or "test:e2e" in cmd


def classify_e2e(cmd: str, repo: Path) -> str:
    """Re-run only the failures of an E2E check: they reproduce (real) or they do not (flaky)."""
    last = repo / "test-results" / ".last-run.json"
    if last.exists() and not json.loads(last.read_text(encoding="utf-8")).get("failedTests"):
        return ""  # nothing recorded as failed: --last-failed would run the whole suite
    again = subprocess.run(
        f"{cmd} --last-failed",
        shell=True,
        cwd=repo,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    return "reproduced (real)" if again.returncode else "did not reproduce (flaky)"


def run(
    scope: str,
    change: Path,
    cfg: dict,
    repo: Path,
    visual_check: str | None = None,
    visual_runs: list[str] | None = None,
) -> int:
    out_dir = change / "verify"
    out_dir.mkdir(exist_ok=True)
    report: dict = {"scope": scope, "id": change.name, "checks": []}
    kit, changelog = kit_version()
    notice = message(cfg.get("sdlcVersion"), kit, changelog)
    if notice:
        print(f"WARN {notice}")  # never blocks; the last line stays the verdict

    def finish(line: str, code: int) -> int:
        report["result"] = line
        report["sha"] = sh("git", "rev-parse", "HEAD")
        (out_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        rows = "\n".join(
            f"| {c['name']} | {c['status']} | {c['seconds']} |" for c in report["checks"]
        )
        failed = next((c for c in report["checks"] if c["status"] != "pass"), None)
        detail = f"\n\n## {failed['name']}\n\n```\n{failed['tail']}\n```\n" if failed else ""
        (out_dir / "report.md").write_text(
            f"# verify {scope} {change.name}\n\n| check | status | s |\n|---|---|---|\n{rows}\n"
            f"{detail}\n`{line}`\n",
            encoding="utf-8",
        )
        if code == 0:
            (out_dir / "state.json").unlink(missing_ok=True)
        return end(line, code)

    lock_path = change / "lock.json"
    if not lock_path.exists():
        print(f"{change.name}/lock.json is missing: run `verify_gate.py approve {change.name}`")
        print("at the plan gate, when the engineer approves.")
        return finish("VERIFY BLOCKED reason=not-approved", 3)
    locked = json.loads(lock_path.read_text(encoding="utf-8"))["criteria"]
    now = criteria_hash(change, cfg.get("checks", {}))
    moved = sorted(k for k in set(locked) | set(now) if locked.get(k) != now.get(k))
    if moved:
        print(f"changed since approval: {', '.join(moved)}. The engineer decides; never re-lock.")
        report["moved"] = moved
        return finish("VERIFY BLOCKED reason=protected-path", 3)

    dirty = [
        line
        for line in sh("git", "status", "--porcelain").splitlines()
        if f"{change.name}/verify/" not in line
    ]
    if dirty:
        print("uncommitted changes: a PASS must name a commit. Commit, then run again.")
        print("\n".join(dirty[:TAIL]))
        return finish(f"VERIFY FAIL {scope} {change.name} check=uncommitted", 1)

    if scope == "milestone":
        behind = [
            name
            for name, tip in parent_tips(change, cfg)
            if subprocess.run(
                ["git", "merge-base", "--is-ancestor", tip, "HEAD"], capture_output=True
            ).returncode
        ]
        if behind:
            print(f"{', '.join('origin/' + b for b in behind)} has commits this milestone lacks.")
            print("Merge in locally, then run the gate again (a commit here, never a PR):")
            print("  git fetch origin && " + " && ".join(f"git merge origin/{b}" for b in behind))
            return finish(f"VERIFY FAIL {scope} {change.name} check=parent-sync", 1)

    checks = cfg.get("checks", {}).get(scope, [])
    if not checks:
        print(f"sdlc.json checks.{scope} is empty: nothing would prove this change.")
        return finish("VERIFY BLOCKED reason=env", 3)

    # Runtime evidence is additional to the locked checks; never weaken or re-lock them.
    # It depends on more than the tree (sessions, visual runs), so it is never cached.
    checks = [c if isinstance(c, dict) else {"run": c} for c in checks]
    if scope == "milestone" and ((change / "marks.json").exists() or sessions(change)):
        checks.append(
            {
                "name": "owner-marks",
                "cache": False,
                "run": shlex.join(
                    [
                        sys.executable,
                        str(Path(__file__).with_name("marks.py")),
                        "check",
                        change.name,
                    ]
                ),
            }
        )
    for number, visual_run in enumerate(visual_runs or [], 1):
        checks.append(
            {
                "name": f"ux-visual-{number}",
                "cache": False,
                "run": shlex.join(
                    [
                        sys.executable,
                        str(visual_check),
                        visual_run,
                        "--repo",
                        str(repo),
                    ]
                ),
            }
        )

    cache_path = out_dir / "cache.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    tree = sh("git", "rev-parse", "HEAD^{tree}")

    for i, check in enumerate(checks, 1):
        name = check.get("name") or f"check-{i}"
        cmd = check["run"].replace("{id}", change.name)
        key = cache_key(tree, cmd, now) if check.get("cache", True) and tree else ""
        if key in cache:
            report["checks"].append(
                {"name": name, "run": cmd, "status": "pass", "exit": 0, "seconds": 0,
                 "tail": "cached", "cached": True}
            )  # fmt: skip
            print(f"ok (cached) {name}: {cmd}")
            continue
        started = time.monotonic()
        proc = subprocess.run(
            cmd, shell=True, cwd=repo, capture_output=True, text=True, stdin=subprocess.DEVNULL
        )
        output = proc.stdout + proc.stderr
        tail = "\n".join(output.strip().splitlines()[-TAIL:])
        status = "pass" if proc.returncode == 0 else "fail"
        report["checks"].append(
            {
                "name": name,
                "run": cmd,
                "status": status,
                "exit": proc.returncode,
                "seconds": round(time.monotonic() - started, 1),
                "tail": tail,
            }
        )
        print(f"{'ok  ' if status == 'pass' else 'FAIL'} {name}: {cmd}")
        if status == "pass":
            if key:
                cache[key] = name
                cache_path.write_text(json.dumps(cache, indent=2) + "\n", encoding="utf-8")
            continue
        print(tail)
        blocked = re.search(r"VERIFY BLOCKED reason=([\w-]+)\s*\Z", output.strip())
        if blocked:
            reason = blocked.group(1) if blocked.group(1) in REASONS else "unknown-verdict"
            return finish(f"VERIFY BLOCKED reason={reason}", 3)
        if is_e2e(cmd):
            verdict = classify_e2e(cmd, repo)
            if verdict:
                print(f"--last-failed re-run: the failures {verdict}")
                report["checks"][-1]["rerun"] = verdict
                report["checks"][-1]["tail"] += f"\n--last-failed re-run: the failures {verdict}"
        state_path = out_dir / "state.json"
        state = json.loads(state_path.read_text()) if state_path.exists() else {}
        sig = signature(name, output)
        count = state.get("count", 0) + 1 if state.get("signature") == sig else 1
        attempts = {**state.get("attempts", {}), scope: state.get("attempts", {}).get(scope, 0) + 1}
        state_path.write_text(
            json.dumps({"signature": sig, "count": count, "attempts": attempts}) + "\n"
        )
        if count >= BREAKER:
            print(f"the same failure {count} runs in a row: the loop is not making progress.")
            return finish("VERIFY BLOCKED reason=no-progress", 3)
        if attempts[scope] >= ATTEMPTS:
            print(
                f"{attempts[scope]} failed {scope} runs of {change.name}: "
                "stop and ask the engineer."
            )
            return finish("VERIFY BLOCKED reason=attempts", 3)
        return finish(f"VERIFY FAIL {scope} {change.name} check={name}", 1)

    return finish(f"VERIFY PASS {scope} {change.name} {sh('git', 'rev-parse', 'HEAD')}", 0)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scope", choices=("approve", "lint", "feature", "milestone"))
    parser.add_argument("id")
    parser.add_argument("--visual-check")
    parser.add_argument("--visual-run", action="append", default=[])
    args = parser.parse_args(argv[1:])
    if bool(args.visual_check) != bool(args.visual_run):
        parser.error("--visual-check and at least one --visual-run must be supplied together")
    if args.visual_run and args.scope not in ("feature", "milestone"):
        parser.error("visual checks apply only to feature and milestone gates")
    repo = root()
    cfg = json.loads((repo / "sdlc.json").read_text(encoding="utf-8"))
    change = repo / cfg.get("changesDir", "changes") / args.id
    if not change.is_dir():
        print(f"no change folder {change.relative_to(repo)}")
        return end("VERIFY BLOCKED reason=env", 3)
    if args.scope == "approve":
        return approve(change, cfg)
    if args.scope == "lint":
        return lint(change)
    return run(args.scope, change, cfg, repo, args.visual_check, args.visual_run)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
