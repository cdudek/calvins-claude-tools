"""One table over the goal check: writer version x scope x record x PR (or local merge) state.

The reader (`sdlc_status.py goal`) ships in the plugin and changes on a marketplace update; the
writer (`verify_gate.py`) is a copy in each repo and changes only when someone runs adopt. So every
writer version below meets the newest reader. Each cell simulates what that writer leaves on disk
and asks the goal check. The same table runs against the baseline ref's code (the previous kit
release, exported to a temp dir) and the cells where the answer differs are listed:

  * DONE only with a bound PASS record (the newest writer) or what the old writer's report proves;
  * never DONE where the baseline says OPEN, except the cells in FIXES;
  * every answer that is not DONE names a concrete step (never the generic fallback).

Each side runs in its own interpreter (`python3 test_goal_table.py --drive <sdlc-run dir> <out>`):
the baseline's sdlc_status imports its own verify_gate, and the two must not share sys.modules.
"""

from __future__ import annotations

import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SDLC_RUN = HERE.parent
BASELINE = os.environ.get("SDLC_BASELINE_REF", "origin/main")

WRITERS = ("3.20.1", "3.20.2", "3.20.3", "3.20.4")
SCOPES = ("feature", "numbered", "unnumbered", "single", "project")
RECORDS = ("none", "pass", "newer_fail", "other_owner", "unbound")
PRS = ("open", "merged", "deleted")
MODES = ("pr", "local")  # local: milestones.merge "local", the milestone merges into project/<slug>

ID = "2026-11-01-widget"
SLUG = "widget"
PROJECT = "p1"

# Cells where the newest reader says DONE and the baseline said OPEN, each with the reason it is a
# fix. A cell is (mode, writer, scope, record, pr). Empty until a difference is understood.
FIXES: dict[tuple, str] = {}


def cells() -> list[tuple]:
    out = []
    for mode, writer, scope, record, pr in itertools.product(MODES, WRITERS, SCOPES, RECORDS, PRS):
        if mode == "local" and scope in ("feature", "project"):
            continue  # a local merge is a milestone's
        out.append((mode, writer, scope, record, pr))
    return out


# --- the driver: runs inside one side's interpreter ----------------------------------------------


def _git(cwd: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    ident = ["-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
    out = subprocess.run(["git", *ident, *args], cwd=cwd, capture_output=True, text=True, env=env)
    return out.stdout.strip()


def _build(base: Path, mode: str, scope: str, pr: str) -> dict:
    """One throwaway repo per (mode, scope, pr); the cells rewrite its records only."""
    root = base / f"{mode}-{scope}-{pr}"
    change = root / "changes" / ID
    change.mkdir(parents=True)
    (root / "scripts").mkdir()
    local = mode == "local"
    n = {"numbered": 2, "single": 1, "unnumbered": None}.get(scope)
    decisions: dict = {"milestone": {"slug": SLUG}}
    if local or scope == "project":
        decisions["project"] = {"slug": PROJECT}
    (change / "decisions.json").write_text(json.dumps(decisions))
    plan = {
        "numbered": "## Milestones\n\n| Milestone | Features | needs |\n|---|---|---|\n| M1 a | F1 | none |\n| M2 b | F2 | none |\n",
        "single": "## Milestones\n\n| Milestone | Features | needs |\n|---|---|---|\n| M1 a | F1 | none |\n",
        "feature": "## Feature PRs\n\n| # | Feature | Facts | Branch | State |\n|---|---|---|---|---|\n| 1 | cart | F1 | `feat/x` | todo |\n",
    }.get(scope, "# Plan\n")
    (change / "plan.md").write_text(plan)
    cfg = {"defaultBranch": "main", "changesDir": "changes"}
    if local:
        cfg["milestones"] = {"merge": "local"}
    (root / "sdlc.json").write_text(json.dumps(cfg))
    _git(root, "init", "-q", "-b", "main")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "base")
    branch = f"milestone/{SLUG}-{n or 1}"
    if local:
        _git(root, "branch", f"project/{PROJECT}")
        _git(root, "switch", "-qc", branch)
        (root / "code.txt").write_text("gated\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "gated")
        sha = _git(root, "rev-parse", "HEAD")
        if pr != "open":
            _git(root, "switch", "-q", f"project/{PROJECT}")
            _git(root, "merge", "--no-ff", "-qm", f"Merge branch '{branch}'", branch)
        _git(root, "switch", "-q", "main")
        if pr == "deleted":
            _git(root, "branch", "-D", branch)
    else:
        (root / "code.txt").write_text("gated\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "gated")
        sha = _git(root, "rev-parse", "HEAD")
    head, base_ref = {
        "feature": ("feat/x", f"milestone/{SLUG}"),
        "project": (f"project/{PROJECT}", "main"),
    }.get(scope, (branch, f"project/{PROJECT}" if local else "main"))
    prs = {
        "number": 7,
        "headRefOid": sha,
        "baseRefName": base_ref,
        "labels": [],
        "state": "OPEN" if pr == "open" else "MERGED",
        "mergedAt": None if pr == "open" else "2999-01-01T00:00:00Z",  # after every first record
        "autoMergeRequest": {"mergeMethod": "MERGE"} if pr == "open" else None,
    }
    return {
        "root": root,
        "change": change,
        "sha": sha,
        "n": n,
        "head": head,
        "pr": None if local and scope != "project" else prs,
        "owner": f"project/{PROJECT}" if local else "",
    }


def _simulate(fx: dict, mode: str, writer: str, scope: str, record: str) -> None:
    """What `writer` leaves on disk for this record (the shapes the released gates wrote)."""
    root, change = fx["root"], fx["change"]
    common = root / ".git" / "sdlc"
    shutil.rmtree(common, ignore_errors=True)
    shutil.rmtree(change / "verify", ignore_errors=True)
    verify = change / "verify"
    gate_scope = {"feature": "feature", "project": "project"}.get(scope, "milestone")
    subject = PROJECT if scope == "project" else ID
    if scope == "project":
        verify = common / "projects" / PROJECT / "verify"
    (root / "scripts" / "verify_gate.py").write_text("RECEIPT_FORMAT = 2\n" if writer == "3.20.4" else f"# kit {writer}\n")
    cfg = json.loads((root / "sdlc.json").read_text())
    cfg["sdlcVersion"] = writer
    (root / "sdlc.json").write_text(json.dumps(cfg))
    if record == "none":
        return
    passing = record in ("pass", "other_owner", "unbound")
    result = f"VERIFY PASS {gate_scope} {subject} {fx['sha']}" if passing else f"VERIFY FAIL {gate_scope} {subject} check=unit"
    report = {"scope": gate_scope, "id": subject, "result": result, "sha": fx["sha"], "checks": []}
    verify.mkdir(parents=True)
    (verify / "report.json").write_text(json.dumps(report))
    n = fx["n"]
    folder = common / "receipts" / subject
    if writer in ("3.20.1", "3.20.2"):
        if gate_scope == "milestone" and n:
            folder.mkdir(parents=True)
            (folder / f"milestone-{n}.json").write_text(json.dumps({**report, "milestone": n, "change": subject}))
        return
    owner = "project/other" if record == "other_owner" else ("" if scope == "project" else fx["owner"])
    key = (
        f"milestone-{n or 1}" if gate_scope == "milestone" else "feature-feat-x" if gate_scope == "feature" else "project-0"
    )
    if writer == "3.20.3":  # no per-run key: a shared slot, and 0 for a branch without a number
        key = f"milestone-{n or 0}" if gate_scope == "milestone" else f"{gate_scope}-0"
    verdict = "pass" if passing else "fail"
    data = {**report, "verdict": verdict, "change": subject, "owner": owner, "time": "2026-01-01T00:00:00+00:00"}
    if gate_scope == "milestone":
        data["milestone"] = n or (1 if writer == "3.20.4" else 0)
    if writer == "3.20.4":
        data["key"] = key
    if record == "unbound":
        data.pop("owner")
    folder.mkdir(parents=True)
    (folder / f"{key}.json").write_text(json.dumps(data))
    if writer == "3.20.4":
        (folder / ".first").write_text("2026-01-01T00:00:00+00:00")


def drive(run_dir: Path, out: Path) -> None:
    sys.path.insert(0, str(run_dir / "scripts"))
    for sub in ("scripts", "hooks"):
        sys.path.insert(0, str(run_dir / "templates" / sub))
    import sdlc_status  # the side under test

    base = Path(tempfile.mkdtemp())
    fixtures: dict[tuple, dict] = {}
    results = {}
    for mode, writer, scope, record, pr in cells():
        fx = fixtures.get((mode, scope, pr)) or fixtures.setdefault((mode, scope, pr), _build(base, mode, scope, pr))
        _simulate(fx, mode, writer, scope, record)

        def gh(root, *args, _fx=fx):
            return [_fx["pr"]] if _fx["pr"] else []

        flag = {"feature": ("feature", 1), "project": ("project", None)}.get(scope, ("milestone", fx["n"]))
        code, line = sdlc_status.goal(fx["root"], fx["change"], flag[0], flag[1], gh=gh)
        try:
            blocker = sdlc_status.blocker(ID, line, flag[0], "main") if code else ""
        except Exception as exc:  # noqa: BLE001 -- a side that cannot explain itself is a finding
            blocker = f"ERROR {exc}"
        results["|".join((mode, writer, scope, record, pr))] = [code, line, blocker]
    out.write_text(json.dumps(results))
    shutil.rmtree(base, ignore_errors=True)


# --- the test --------------------------------------------------------------------------------


def _run_side(run_dir: Path, tmp: Path, name: str) -> dict:
    out = tmp / f"{name}.json"
    done = subprocess.run(
        [sys.executable, str(HERE / "test_goal_table.py"), "--drive", str(run_dir), str(out)],
        capture_output=True,
        text=True,
        cwd=tmp,
    )
    assert done.returncode == 0, done.stderr[-3000:]
    return json.loads(out.read_text())


def _baseline_dir(tmp: Path) -> Path | None:
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=HERE, capture_output=True, text=True).stdout.strip()
    rel = subprocess.run(["git", "rev-parse", "--show-prefix"], cwd=HERE, capture_output=True, text=True).stdout.strip()
    rel = str(Path(rel).parent)  # .../sdlc-run
    if subprocess.run(["git", "rev-parse", "--verify", "-q", f"{BASELINE}^{{commit}}"], cwd=top, capture_output=True).returncode:
        return None
    archive = subprocess.run(["git", "archive", BASELINE, "--", rel], cwd=top, capture_output=True)
    if archive.returncode:
        return None
    old = tmp / "baseline"
    old.mkdir()
    subprocess.run(["tar", "-x", "-C", str(old)], input=archive.stdout, check=True)
    return old / rel


@pytest.fixture(scope="module")
def table(tmp_path_factory: pytest.TempPathFactory) -> dict:
    tmp = tmp_path_factory.mktemp("table")
    new = _run_side(SDLC_RUN, tmp, "new")
    old_dir = _baseline_dir(tmp)
    old = _run_side(old_dir, tmp, "old") if old_dir else {}
    return {"new": new, "old": old}


def _env_ok(mode: str, pr: str) -> bool:
    return not (mode == "local" and pr == "open")  # a local branch not merged yet is not done


def test_done_only_with_a_bound_pass_record(table: dict) -> None:
    bad = []
    for cell in cells():
        mode, writer, scope, record, pr = cell
        code, line, _ = table["new"]["|".join(cell)]
        done = code == 0
        if writer == "3.20.4":
            want = record == "pass" and _env_ok(mode, pr)
        elif record in ("none", "newer_fail") or not _env_ok(mode, pr):
            want = False
        elif record == "pass":
            want = True
        else:
            continue  # an old writer's unbound record: the old report decides, see the baseline test
        if done != want:
            bad.append((cell, line))
    assert not bad, bad[:10]


def test_every_answer_that_is_not_done_names_a_step(table: dict) -> None:
    generic = [
        (k, v[1])
        for k, v in table["new"].items()
        if v[0] and (not v[2].startswith("Blocking:") or "because the goal check lists it" in v[2])
    ]
    assert not generic, generic[:10]


def test_nothing_moves_toward_done_against_the_baseline(table: dict) -> None:
    if not table["old"]:
        pytest.skip(f"{BASELINE} is not available here")
    moved = [
        k
        for k, (code, *_rest) in table["new"].items()
        if code == 0 and table["old"][k][0] != 0 and tuple(k.split("|")) not in FIXES
    ]
    assert not moved, [(k, table["old"][k][1], table["new"][k][1]) for k in moved[:10]]


def test_differences_are_listed(table: dict, capsys: pytest.CaptureFixture[str]) -> None:
    if not table["old"]:
        pytest.skip(f"{BASELINE} is not available here")
    sha = lambda line: re.sub(r"\b[0-9a-f]{12,40}\b", "SHA", line)  # noqa: E731 -- the fixtures differ in commits only
    diff = [
        (k, sha(table["old"][k][1]), sha(table["new"][k][1]))
        for k in table["new"]
        if sha(table["old"][k][1]) != sha(table["new"][k][1])
    ]
    Path(os.environ.get("SDLC_TABLE_DIFF", os.devnull)).write_text(json.dumps(diff, indent=1))
    assert isinstance(diff, list)


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--drive":
        drive(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        sys.exit("usage: test_goal_table.py --drive <sdlc-run dir> <out.json>")
