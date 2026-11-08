"""The verify contract of the SDLC chain: one command, one last line.

    python3 scripts/verify_gate.py approve <id>              # lock the criteria at approval
    python3 scripts/verify_gate.py lint <id>                 # plain-language lint of the docs
    python3 scripts/verify_gate.py feature|milestone <id>    # run sdlc.json checks.<scope>
    python3 scripts/verify_gate.py audit [--no-evidence]     # read-only: is every gate enforced?
    # After UX review, also require each visual run:
    # ... --visual-check <ux visual-check.py> --visual-run <run> [--visual-run <run> ...]

Written by `sdlc-run adopt` from the kit; edit the kit, not this copy. stdlib only.

`audit` changes nothing. For every sdlc.json check and every installed hook it reports four
states apart: installed (the checker or script exists), configured (which gate scope, CI job or
hook event invokes it), executed (the newest verify/report.json that ran it) and passed. For a
check run by a CI job it also reports whether that job is a required status on the default
branch (read with `gh api`; `unknown` when gh or the API is unavailable, `local` when no CI job
runs it). Last line `AUDIT PASS|FAIL problems=<n> unknown=<m>`, exit 1 on a problem: a missing
checker, a check that never ran (`--no-evidence` skips that test, for a CI runner without reports), a CI-run check that is not required, a hook file that is not
registered or a registered one that is missing.

`approve` writes <changesDir>/<id>/lock.json: the hash of facts.md, done.json and
sdlc.json `checks`, taken when the engineer approved the plan. `feature`/`milestone` refuse to
run against criteria that moved since. `approve` refuses (APPROVE FAIL) an unchecked
`checklist.md` item, an open CRITICAL in `analyze.md` or `challenge.md`, a plan violation without a justification,
and an intent without a valid Decision4 `class` (Undo, Repair, Migrate, Answer); the class goes
into lock.json. `milestone` blocks on a `not met` or `partly` row in `validation.md`
(validation-not-met), an unchecked item in `findings.md` outside `## Advisory` (findings-open) and
a `## Converge` section without a `Converged:` line (not-converged). `milestone` also fails with check=parent-sync while
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
import os
import re
import shlex
import shutil
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
    "validation-not-met",  # a `not met` or `partly` row in validation.md
    "findings-open",  # an unchecked item in findings.md outside ## Advisory
    "not-converged",  # findings.md ## Converge has no `Converged:` line
}
CLASSES = ("Undo", "Repair", "Migrate", "Answer")  # Decision4 v1, lowest to highest
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
    and project/<slug> too when the change's project has a branch. A project without
    `branch: true` is planning only (3.7.0), but one written before 3.7.0 has no `branch` key
    and keeps its branch. A branch origin lacks (no remote, offline, project not created yet)
    is left out."""
    names = [cfg.get("defaultBranch") or "main"]
    try:
        project = json.loads((change / "decisions.json").read_text(encoding="utf-8")).get("project")
    except (OSError, ValueError, AttributeError):
        project = None
    if isinstance(project, dict) and project.get("slug") and project.get("branch", True):
        prefix = (cfg.get("projects") or {}).get("branchPrefix", "project/")
        names.insert(0, f"{prefix}{project['slug']}")
    tips = []
    for name in names:
        sh("git", "fetch", "--quiet", "origin", name)  # offline: the last fetched tip still counts
        tip = sh("git", "rev-parse", "--verify", "--quiet", f"origin/{name}^{{commit}}")
        if tip:
            tips.append((name, tip))
    return tips


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def table_rows(text: str) -> list[list[str]]:
    """Cells of every markdown table row, separator rows dropped; the header is the first row."""
    return [
        [c.strip() for c in line.strip().strip("|").split("|")]
        for line in text.splitlines()
        if line.lstrip().startswith("|") and not re.fullmatch(r"\s*\|[\s:|-]+\|\s*", line)
    ]


def section(text: str, heading: str) -> str:
    m = re.search(rf"^#{{2,3}} {re.escape(heading)}\s*$(.*?)(?=^#{{1,3}} |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def intent_class(change: Path) -> str:
    m = re.search(r"^class:\s*(\S*)\s*$", read(change / "intent.md"), re.M)
    return m.group(1) if m else ""


def open_criticals(change: Path, name: str) -> list[str]:
    """CRITICAL rows still `open` in analyze.md or challenge.md; an absent file has none."""
    return [
        f"{name}: open CRITICAL: {row[0]} {' '.join(row[3:5])[:80]}"
        for row in table_rows(read(change / name))
        if "CRITICAL" in row and row[-1].lower() == "open"
    ]


def approval_blockers(change: Path) -> list[str]:
    """What stops the plan gate: the checklist, the analyze and challenge passes, the plan's unjustified rule
    violations and the intent's class. A file that does not exist blocks nothing."""
    out = []
    open_items = re.findall(r"^\s*[-*] \[ \] (.*)$", read(change / "checklist.md"), re.M)
    out += [f"checklist.md: unchecked: {i[:80]}" for i in open_items]
    out += open_criticals(change, "analyze.md") + open_criticals(change, "challenge.md")
    for row in table_rows(section(read(change / "plan.md"), "Justified violations"))[1:]:
        if row[0].lower() != "none" and (len(row) < 3 or any(not c or c[0] == "<" for c in row)):
            out.append(f"plan.md: unjustified violation: {row[0][:80]}")
    if (change / "intent.md").exists() and intent_class(change) not in CLASSES:
        out.append(f"intent.md: class must be one of {', '.join(CLASSES)}")
    return out


def milestone_blockers(change: Path) -> tuple[str, list[str]] | None:
    """The records a milestone must close before it passes: (reason, offending lines) or None."""
    rows = table_rows(read(change / "validation.md"))
    bad = [r for r in rows if any(c.lower() in ("not met", "partly") for c in r)]
    if bad:
        return "validation-not-met", [f"validation.md: {r[0]} {r[-1]}" for r in bad]
    findings = read(change / "findings.md")
    advisory = section(findings, "Advisory")
    open_items = re.findall(r"^\s*[-*] \[ \] (.*)$", findings.replace(advisory, ""), re.M)
    if open_items:
        return "findings-open", [f"findings.md: open: {i[:80]}" for i in open_items]
    if section(findings, "Converge") and "Converged:" not in findings:
        return "not-converged", ["findings.md: ## Converge has no `Converged: round <n>` line"]
    return None


def end(line: str, code: int) -> int:
    print(line)
    return code


def approve(change: Path, cfg: dict) -> int:
    problems = approval_blockers(change)
    if problems:
        print("\n".join(problems[:TAIL]))
        return end(f"APPROVE FAIL {change.name} problems={len(problems)}", 1)
    lock = {
        "approved_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),  # noqa: UP017 -- runs on macOS python3 3.9
        "sha": sh("git", "rev-parse", "HEAD"),
        "class": intent_class(change) or None,
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


def metrics(change: Path, report: dict, retries: int, started: float) -> dict:
    """The operational numbers of one gate run, for the report: what ran and how it ended,
    how many earlier runs of this scope failed, review rounds, seconds, findings still open."""
    checks = report["checks"]
    findings = read(change / "findings.md")
    advisory = section(findings, "Advisory")
    open_findings = re.findall(r"^\s*[-*] \[ \] ", findings.replace(advisory, ""), re.M)
    rounds = [int(n) for n in re.findall(r"Converged: round (\d+)", findings)]
    return {
        "checks_run": sum(1 for c in checks if not c.get("cached")),
        "checks_cached": sum(1 for c in checks if c.get("cached")),
        "checks_passed": sum(1 for c in checks if c["status"] == "pass"),
        "checks_failed": sum(1 for c in checks if c["status"] != "pass"),
        "retries": retries,
        "review_rounds": max(rounds, default=0),
        "elapsed_s": round(time.monotonic() - started, 1),
        "open_findings": len(open_findings)
        + len(open_criticals(change, "analyze.md"))
        + len(open_criticals(change, "challenge.md")),
    }


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
    started_run = time.monotonic()
    try:
        retries = json.loads((out_dir / "state.json").read_text()).get("attempts", {}).get(scope, 0)
    except (OSError, ValueError):
        retries = 0
    kit, changelog = kit_version()
    notice = message(cfg.get("sdlcVersion"), kit, changelog)
    if notice:
        print(f"WARN {notice}")  # never blocks; the last line stays the verdict

    def finish(line: str, code: int) -> int:
        report["result"] = line
        report["sha"] = sh("git", "rev-parse", "HEAD")
        report["metrics"] = metrics(change, report, retries, started_run)
        (out_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        rows = "\n".join(
            f"| {c['name']} | {c['status']} | {c['seconds']} |" for c in report["checks"]
        )
        failed = next((c for c in report["checks"] if c["status"] != "pass"), None)
        detail = f"\n\n## {failed['name']}\n\n```\n{failed['tail']}\n```\n" if failed else ""
        stats = "\n".join(f"- {k.replace('_', ' ')}: {v}" for k, v in report["metrics"].items())
        (out_dir / "report.md").write_text(
            f"# verify {scope} {change.name}\n\n| check | status | s |\n|---|---|---|\n{rows}\n"
            f"{detail}\n## Metrics\n\n{stats}\n\n`{line}`\n",
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

    if scope == "milestone" and (blocker := milestone_blockers(change)):
        print("\n".join(blocker[1][:TAIL]))
        return finish(f"VERIFY BLOCKED reason={blocker[0]}", 3)

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
    head = sh("git", "rev-parse", "HEAD")

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

    # A PASS names one frozen head: a merge or an edit during the checks means they tested
    # something other than the commit the line would name.
    still_dirty = [
        line
        for line in sh("git", "status", "--porcelain").splitlines()
        if f"{change.name}/verify/" not in line
    ]
    if sh("git", "rev-parse", "HEAD") != head or still_dirty:
        print(
            "HEAD or the tree changed while the checks ran: nothing may merge or edit during a gate."
        )
        return finish(f"VERIFY FAIL {scope} {change.name} check=moved", 1)
    return finish(f"VERIFY PASS {scope} {change.name} {head}", 0)


def checker_exists(cmd: str, repo: Path) -> bool:
    """The program a check runs exists. shortcut: reads only the first command of a `a && b`
    line, so a broken second command is not seen; split it into two checks to audit both."""
    try:
        words = shlex.split(cmd)
    except ValueError:
        return False
    while words and re.fullmatch(r"\w+=\S*", words[0]):  # leading VAR=value
        words.pop(0)
    if not words:
        return False
    if words[0] in ("python3", "python", "bash", "sh") and len(words) > 1:
        return (repo / words[1]).exists() or words[1].startswith("-")
    return (repo / words[0]).exists() if "/" in words[0] else shutil.which(words[0]) is not None


def ci_jobs(repo: Path) -> list[dict]:
    """Jobs of .github/workflows/*.yml as {key, name, needs, body}. shortcut: a line scan for the
    two-space `jobs:` layout (no YAML parser, stdlib only); an anchored or flow-style file shows
    up as no jobs, so the check reads `local`, never a false `yes`."""
    jobs: list[dict] = []
    for path in sorted((repo / ".github" / "workflows").glob("*.y*ml")):
        in_jobs = in_needs = False
        for line in path.read_text(encoding="utf-8").splitlines():
            if re.match(r"^jobs:\s*$", line):
                in_jobs = True
            elif in_jobs and (m := re.match(r"^  ([\w-]+):\s*$", line)):
                jobs.append({"key": m[1], "name": m[1], "needs": [], "body": "", "file": path.name})
            elif in_jobs and line and not line.startswith(" "):
                in_jobs = False
            elif in_jobs and jobs:
                jobs[-1]["body"] += line + "\n"
                if m := re.match(r"^    name:\s*(.+?)\s*$", line):
                    jobs[-1]["name"] = m[1].strip("'\"")
                if m := re.match(r"^    needs:\s*(.*)$", line):
                    jobs[-1]["needs"] += re.findall(r"[\w-]+", m[1])
                    in_needs = not m[1]
                elif in_needs and (m := re.match(r"^\s+- ([\w-]+)\s*$", line)):
                    jobs[-1]["needs"].append(m[1])
                elif re.match(r"^    \S", line):
                    in_needs = False
    return jobs


def required_contexts(branch: str) -> set[str] | None:
    """Required status checks of the default branch via `gh api` (rulesets first, then classic
    branch protection); None when gh or the API cannot say."""
    for path in (
        f"repos/{{owner}}/{{repo}}/rules/branches/{branch}",
        f"repos/{{owner}}/{{repo}}/branches/{branch}/protection/required_status_checks",
    ):
        try:
            data = json.loads(sh("gh", "api", path))
        except ValueError:
            continue
        if isinstance(data, list):
            return {
                c["context"]
                for rule in data
                if rule.get("type") == "required_status_checks"
                for c in rule.get("parameters", {}).get("required_status_checks", [])
            }
        if isinstance(data, dict):
            return set(data.get("contexts", [])) | {c["context"] for c in data.get("checks", [])}
    return None


def required_job_keys(jobs: list[dict], contexts: set[str]) -> set[str]:
    """Jobs whose name is a required context, plus everything they `needs`, transitively."""
    wanted = {c.rsplit(" / ", 1)[-1] for c in contexts}
    keys = {j["key"] for j in jobs if {j["key"], j["name"]} & wanted}
    while extra := {n for j in jobs if j["key"] in keys for n in j["needs"]} - keys:
        keys |= extra
    return keys


def last_runs(repo: Path, cfg: dict) -> dict[str, tuple[float, str, str]]:
    """run command -> (mtime, status, sha) from the newest verify/report.json that ran it."""
    found: dict[str, tuple[float, str, str]] = {}
    for path in (repo / cfg.get("changesDir", "changes")).rglob("verify/report.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for c in data.get("checks", []):
            if path.stat().st_mtime > found.get(c["run"], (0.0, "", ""))[0]:
                found[c["run"]] = (path.stat().st_mtime, c["status"], str(data.get("sha", ""))[:7])
    return found


def audit(cfg: dict, repo: Path, evidence: bool = True) -> int:
    """Read-only: installed, configured, executed and passed are four separate answers."""
    problems, unknown = [], 0
    jobs = ci_jobs(repo)
    branch = cfg.get("defaultBranch") or "main"
    contexts = required_contexts(branch)
    needed = required_job_keys(jobs, contexts) if contexts is not None else set()
    runs = last_runs(repo, cfg)
    print(
        f"default branch {branch}: required statuses "
        + (
            ", ".join(sorted(contexts)) or "none"
            if contexts is not None
            else "unknown (gh api failed)"
        )
    )
    for scope, checks in (cfg.get("checks") or {}).items():
        for i, check in enumerate(checks, 1):
            check = check if isinstance(check, dict) else {"run": check}
            cmd, name = check["run"], check.get("name") or f"check-{i}"
            prefix = cmd.split("{id}")[0].strip()
            mine = [j for j in jobs if prefix and prefix in j["body"]]
            when = next((v for k, v in sorted(runs.items()) if k.startswith(prefix)), None)
            if not mine:
                required = "local"
            elif contexts is None:
                required = "unknown"
            else:
                required = "yes" if any(j["key"] in needed for j in mine) else "no"
            unknown += required == "unknown"
            invoked = ", ".join([f"gate {scope}"] + [f"ci {j['file']}:{j['key']}" for j in mine])
            ran = (
                "never" if not when else
                f"{when[1]} @{when[2]} {dt.datetime.fromtimestamp(when[0]):%Y-%m-%d}"
            )  # fmt: skip
            installed = checker_exists(cmd, repo)
            print(
                f"check {scope}/{name}: installed={'yes' if installed else 'NO'} "
                f"invoked by [{invoked}] required={required} last run: {ran}"
            )
            if not installed:
                problems.append(f"{scope}/{name}: the checker `{cmd.split()[0]}` does not exist")
            if evidence and not when:
                problems.append(f"{scope}/{name}: never ran (no verify/report.json has it)")
            if required == "no":
                problems.append(f"{scope}/{name}: a CI job runs it but it is not a required status")
    settings = repo / ".claude" / "settings.json"
    registered: dict[str, str] = {}
    if settings.exists():
        for event, groups in (
            json.loads(settings.read_text(encoding="utf-8")).get("hooks", {}).items()
        ):
            for g in groups:
                for h in g.get("hooks", []):
                    if m := re.search(r"\.claude/hooks/([\w.-]+\.sh)", h.get("command", "")):
                        registered[m[1]] = f"{event} {g.get('matcher', '*')}"
    on_disk = {
        p.name: p for p in (repo / ".claude" / "hooks").glob("*.sh") if p.name != "sdlc-config.sh"
    }  # sdlc-config.sh is sourced by the others, never registered
    for hook in sorted(set(registered) | set(on_disk)):
        path = on_disk.get(hook)
        installed = path is not None and os.access(path, os.X_OK)
        print(
            f"hook {hook}: installed={'yes' if installed else 'NO'} "
            f"invoked by [{registered.get(hook, 'NOT REGISTERED')}] "
            "last run: no record (a hook leaves no log)"
        )
        if not installed:
            problems.append(f"{hook}: registered but missing or not executable")
        if hook not in registered:
            problems.append(f"{hook}: installed but not registered in .claude/settings.json")
    print("\n".join(f"PROBLEM {p}" for p in problems[:TAIL]))
    verdict = "FAIL" if problems else "PASS"
    return end(f"AUDIT {verdict} problems={len(problems)} unknown={unknown}", 1 if problems else 0)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scope", choices=("approve", "lint", "feature", "milestone", "audit"))
    parser.add_argument("id", nargs="?")
    parser.add_argument("--no-evidence", action="store_true", help="audit: skip the never-ran test")
    parser.add_argument("--visual-check")
    parser.add_argument("--visual-run", action="append", default=[])
    args = parser.parse_args(argv[1:])
    if bool(args.visual_check) != bool(args.visual_run):
        parser.error("--visual-check and at least one --visual-run must be supplied together")
    if args.visual_run and args.scope not in ("feature", "milestone"):
        parser.error("visual checks apply only to feature and milestone gates")
    if args.scope != "audit" and not args.id:
        parser.error(f"{args.scope} needs a change id")
    repo = root()
    cfg = json.loads((repo / "sdlc.json").read_text(encoding="utf-8"))
    if args.scope == "audit":
        return audit(cfg, repo, not args.no_evidence)
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
