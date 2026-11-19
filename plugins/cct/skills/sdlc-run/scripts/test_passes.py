"""Pass records: the gate writes a copy of its bound report into <git-common-dir>/sdlc/passes/<change>/
<scope>-<key>.json, and the readers (pr-gate.sh, sdlc_status.py) take the newest bound report of either copy.

Each test pins one way the first attempt (cct#40) broke: the format regex, selective replace, the project
failure, visual-loop key reuse and the legacy exception. The table at the end runs writer x scope x record x
PR on this code and on origin/main's."""

# ruff: noqa: F811, F401, E402, I001 -- the imported fixtures (hook_repo, status_repo) are used as test arguments
from __future__ import annotations

import itertools
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from test_verify_gate import ID, _approve, _gate, _git, _last, _repo

SKILL = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SKILL / "templates" / "scripts"), str(SKILL / "templates" / "hooks")]
import pass_proof  # noqa: E402
import verify_gate  # noqa: E402

GATE = "a" * 40


def _common(repo: Path) -> Path:
    out = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    return Path(out)


def _passes(repo: Path, change: str = ID) -> Path:
    return _common(repo) / "sdlc" / "passes" / change


def _milestone_repo(tmp_path: Path, branch: str, rows: int = 2) -> Path:
    repo = _repo(tmp_path, ["true"])
    cfg = {
        **json.loads((repo / "sdlc.json").read_text()),
        "checks": {"milestone": ["true"], "feature": ["true"]},
    }
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    plan = "".join(f"| M{i} a | F1 | none |\n" for i in range(1, rows + 1))
    (repo / "changes" / ID / "plan.md").write_text(
        f"## Milestones\n\n| Milestone | Features | needs |\n|---|---|---|\n{plan}"
    )
    _git(repo, "commit", "-qam", "plan")
    _git(repo, "checkout", "-qb", branch)
    _approve(repo)
    return repo


# --- the writer ------------------------------------------------------------------------------------


@pytest.mark.parametrize(("branch", "key"), [("milestone/trial-2", "2"), ("milestone/trial", "1")])
def test_a_milestone_gate_writes_a_shared_copy_of_its_report(
    tmp_path: Path, branch: str, key: str
) -> None:
    repo = _milestone_repo(tmp_path, branch)
    assert _last(_gate(repo, "milestone", ID)).startswith("VERIFY PASS milestone")
    shared = _passes(repo) / f"milestone-{key}.json"
    assert shared.read_text() == (repo / "changes" / ID / "verify" / "report.json").read_text()
    assert sorted(p.name for p in _passes(repo).iterdir()) == [shared.name]  # no temp file is left


def test_a_visual_run_does_not_move_the_milestone_key(tmp_path: Path) -> None:
    """Round 2: the visual loop shadowed the milestone number, so M2's pass landed in M1's slot."""
    repo = _milestone_repo(tmp_path, "milestone/trial-2")
    checker = SKILL.parent / "ux-assessment-run/scripts/visual-check.py"
    run = tmp_path / "run"
    run.mkdir()
    shot = run / "screen.png"
    shot.write_bytes(b"x")
    import hashlib

    (run / "visual.json").write_text(
        json.dumps(
            {
                "screenshots": [
                    {
                        "file": "screen.png",
                        "screen_state": "default",
                        "width": 1280,
                        "opened_with": "Read call-1",
                        "sha256": hashlib.sha256(b"x").hexdigest(),
                        "observations": "Aligned labels and legible controls.",
                        "verdict": "compliant",
                        "issues": [],
                    }
                ]
            }
        )
    )
    r = _gate(repo, "milestone", ID, "--visual-check", str(checker), "--visual-run", str(run))
    assert _last(r).startswith("VERIFY PASS milestone"), r.stdout
    verify = repo / "changes" / ID / "verify"
    assert (verify / "milestone-2.json").is_file() and not (verify / "milestone-1.json").exists()
    assert [p.name for p in _passes(repo).iterdir()] == ["milestone-2.json"]


def test_two_legal_feature_branches_never_share_a_record(tmp_path: Path) -> None:
    """Round 3: `feat/cart-ui` and `feat/cart/ui` both became `feature-feat-cart-ui`."""
    repo = _repo(tmp_path, ["true"])
    _approve(repo)
    names = set()
    for branch in ("feat/cart-ui", "feat/cart/ui"):
        _git(repo, "checkout", "-q", "-B", branch)
        assert _last(_gate(repo, "feature", ID)).startswith("VERIFY PASS feature")
        names |= {p.name for p in _passes(repo).iterdir()}
    assert len(names) == 2 and all(n.startswith("feature-") and "/" not in n for n in names)


def test_a_failing_rerun_replaces_the_shared_copy(tmp_path: Path) -> None:
    repo = _milestone_repo(tmp_path, "milestone/trial-1", rows=1)
    assert _last(_gate(repo, "milestone", ID)).startswith("VERIFY PASS")
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["checks"]["milestone"] = ["false"]
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    _gate(repo, "milestone", ID)  # the criteria moved: a fail or a block, either way not a pass
    data = json.loads((_passes(repo) / "milestone-1.json").read_text())
    assert not data["result"].startswith("VERIFY PASS")


def test_the_writer_and_the_reader_name_the_same_file(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true"])
    for scope, branch, number in [
        ("milestone", "milestone/trial-2", 2),
        ("feature", "feat/a/b", None),
        ("project", "project/big", None),
    ]:
        key = pass_proof.pass_key(scope, branch, number)
        theirs = verify_gate.pass_record(scope, ID, branch, number, repo)
        assert theirs == pass_proof.shared(repo, ID, scope, key), scope
    assert verify_gate.pass_record("milestone", ID, "main", None, repo) is None
    assert pass_proof.shared(repo, ID, "milestone", None) is None
    assert pass_proof.shared(repo, "../x", "milestone", "1") is None


# --- the readers -----------------------------------------------------------------------------------


def _record(path: Path, result: str, mtime: int, **fields) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"scope": "milestone", "id": ID, "sha": GATE, "result": result, **fields})
    )
    os.utime(path, ns=(mtime, mtime))
    return path


BIND = {"format": 2, "change": ID, "owner": "", "milestone": 1}
PASS = f"VERIFY PASS milestone {ID} {GATE}"


def _chain(files, **kw):
    return pass_proof.chain(files, "milestone", ID, kw.get("number", 1), kw.get("owner"))


def test_the_newest_bound_report_wins_and_a_newer_non_pass_blocks(tmp_path: Path) -> None:
    old = _record(tmp_path / "a.json", PASS, 1, **BIND)
    fail = _record(tmp_path / "b.json", f"VERIFY FAIL milestone {ID} check=x", 2, **BIND)
    new = _record(tmp_path / "c.json", PASS, 3, **BIND)
    assert [ok for ok, _ in _chain([old, fail])] == [False]
    assert [ok for ok, _ in _chain([old, fail, new])] == [
        True,
        False,
    ]  # the pass is newest; the fail stops the walk
    assert [ok for ok, _ in _chain([fail, new])] == [True, False]


def test_a_non_pass_of_another_milestone_or_owner_blocks_nothing(tmp_path: Path) -> None:
    ok = _record(tmp_path / "a.json", PASS, 1, **BIND)
    other = _record(tmp_path / "b.json", "VERIFY FAIL milestone x", 2, **{**BIND, "milestone": 2})
    stranger = _record(
        tmp_path / "c.json", "VERIFY FAIL milestone x", 3, **{**BIND, "owner": "project/y"}
    )
    assert [p for p, _ in _chain([ok, other, stranger], owner="")] == [True]


@pytest.mark.parametrize("drop", ["change", "owner", "milestone"])
def test_a_report_with_a_format_and_a_missing_binding_holds_nothing(
    tmp_path: Path, drop: str
) -> None:
    fields = {k: v for k, v in BIND.items() if k != drop}
    rec = _record(tmp_path / "a.json", PASS, 1, **fields)
    assert not [1 for ok, _ in _chain([rec], owner="") if ok]


def test_an_old_report_without_format_or_binding_holds_as_before(tmp_path: Path) -> None:
    rec = _record(tmp_path / "a.json", PASS, 1)
    assert [ok for ok, _ in _chain([rec], owner="")] == [True]


def test_a_feature_report_with_a_format_needs_its_change(tmp_path: Path) -> None:
    ok = {
        "scope": "feature",
        "sha": GATE,
        "result": f"VERIFY PASS feature {ID} {GATE}",
        "format": 2,
    }
    assert not pass_proof.bound(ok, "feature", ID)
    assert pass_proof.bound({**ok, "change": ID, "owner": ""}, "feature", ID)


def test_the_gate_text_is_never_read_to_pick_a_mode() -> None:
    """Round 3: a regex over verify_gate.py's source missed the real writer (a trailing comment)."""
    for path in (
        SKILL / "templates/hooks/pass_proof.py",
        SKILL / "templates/hooks/pr-gate.sh",
        SKILL / "scripts/sdlc_status.py",
    ):
        assert not re.search(r"REPORT_FORMAT|writer_format", path.read_text()), path.name


def test_only_pass_proof_reads_the_passes_folder() -> None:
    shipped = [
        p
        for root in (SKILL / "scripts", SKILL / "templates", SKILL.parents[1] / "blueprint")
        for p in root.rglob("*")
        if p.is_file() and p.suffix in {".py", ".sh"} and not p.name.startswith("test_")
    ]
    named = {
        p.name for p in shipped if re.search(r"""["']passes["']""", p.read_text(encoding="utf-8"))
    }
    assert named == {"pass_proof.py", "verify_gate.py"}
    gate = (SKILL / "templates" / "scripts" / "verify_gate.py").read_text()
    assert len(re.findall(r"""["']passes["']""", gate)) == 1 and "os.replace" in gate


def test_the_shipped_copies_are_byte_identical() -> None:
    top = SKILL.parents[3]
    pairs = [
        (top / "scripts/verify_gate.py", SKILL / "templates/scripts/verify_gate.py"),
        (
            top / "scripts/verify_gate.py",
            SKILL.parents[1] / "blueprint/web-nextjs-cloud-run/scripts/verify_gate.py",
        ),
        (top / ".claude/hooks/pass_proof.py", SKILL / "templates/hooks/pass_proof.py"),
        (top / ".claude/hooks/pr-gate.sh", SKILL / "templates/hooks/pr-gate.sh"),
    ]
    for a, b in pairs:
        assert a.read_bytes() == b.read_bytes(), (a, b)


# --- the table: writer x scope x record x PR, on this code and on origin/main's --------------------

DRIVER = r"""
import json, sys
from pathlib import Path
code, repo, change, scope, n, prs = sys.argv[1:7]
sys.path.insert(0, code)
import sdlc_status
def gh(root, *args):
    return json.loads(prs).get(args[args.index("--head") + 1], [])
print(json.dumps(sdlc_status.goal(Path(repo), Path(repo) / "changes" / change, scope, int(n) if n != "-" else None, gh=gh)))
"""

SLUG = "redesign-r2"
TID = "2026-10-09-redesign-r2"
SCOPES = ["feature", "milestone-numbered", "milestone-unnumbered", "project"]
WRITERS = [
    "old",
    "new",
]  # old: origin/main's writer (bound, no `format`, no shared copy); new: this one
RECORDS = ["none", "pass", "newer-fail", "other-owner", "missing-binding"]
PRS = ["open", "merged", "branch-deleted"]
STAMP = 1_000_000_000


def _pr(state: str, base: str) -> list:
    return [
        {
            "number": 7,
            "baseRefName": base,
            "labels": [],
            "headRefOid": GATE,
            "state": state,
            "mergedAt": "2026-11-11T10:00:00Z" if state == "MERGED" else None,
            "autoMergeRequest": {"mergeMethod": "MERGE"} if state == "OPEN" else None,
        }
    ]


def _fixture(root: Path, scope: str) -> tuple[Path, list[str], str, str, int | None]:
    """(repo, head branches the goal asks GitHub about, scope word, --milestone, milestone number)."""
    repo = root / "repo"
    change = repo / "changes" / TID
    change.mkdir(parents=True)
    (repo / "sdlc.json").write_text("{}")
    decisions: dict = {"milestone": {"kind": "new", "slug": SLUG}}
    rows = {
        "feature": "## Feature PRs\n\n| # | Feature | Facts | Branch | State |\n|---|---|---|---|---|\n| 1 | cart | F1 | `redesign-r2/1-cart` | todo |\n",
        "milestone-numbered": "## Milestones\n\n| Milestone | Features | needs |\n|---|---|---|\n| M1 a | F1 | none |\n| M2 b | F2 | none |\n",
        "milestone-unnumbered": "## Milestones\n\n| Milestone | Features | needs |\n|---|---|---|\n| M1 a | F1 | none |\n",
        "project": "",
    }
    if scope == "project":
        decisions["project"] = {"slug": "big", "branch": True}
    (change / "decisions.json").write_text(json.dumps(decisions))
    (change / "plan.md").write_text(rows[scope])
    (change / "lock.json").write_text("{}")
    subprocess.run(["git", "init", "-q", "-b", "x"], cwd=repo, check=True, env=_clean_env())
    return (
        repo,
        {
            "feature": ["redesign-r2/1-cart"],
            "project": ["project/big"],
            "milestone-numbered": ["milestone/redesign-r2-2"],
            "milestone-unnumbered": [
                "milestone/redesign-r2-1"
            ],  # the goal asks for -1; the unnumbered branch is M1
        }[scope],
        word_of(scope),
        {"feature": "1", "milestone-numbered": "2", "milestone-unnumbered": "1"}.get(scope, "-"),
        ({"milestone-numbered": 2, "milestone-unnumbered": 1}.get(scope)),
    )


def _clean_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def word_of(scope: str) -> str:
    return {"feature": "feature", "project": "project"}.get(scope, "milestone")


def _report(word: str, number: int | None, record: str, writer: str) -> dict:
    subject = "big" if word == "project" else TID
    result = (
        f"VERIFY FAIL {word} {subject} check=x"
        if record == "newer-fail"
        else f"VERIFY PASS {word} {subject} {GATE}"
    )
    data: dict = {"scope": word, "id": subject, "result": result, "sha": GATE}
    if writer == "new":
        data["format"] = 2
    if word != "project":
        data["change"], data["owner"] = TID, "project/other" if record == "other-owner" else ""
    if word == "milestone":
        data["milestone"] = number
    if record == "missing-binding":  # a report from before the binding keys, or one that lost them
        for key in ("change", "owner", "milestone"):
            data.pop(key, None)
    return data


def _lay(repo: Path, scope: str, record: str, writer: str, pr: str, number: int | None) -> None:
    """What the writer left on disk, then what the removal of the worktree took with it."""
    if record == "none":
        return
    word = word_of(scope)
    data = _report(word, number, record, writer)
    verify = repo / "changes" / TID / "verify"
    checkout = (
        [repo / ".git/sdlc/projects/big/verify/report.json"]
        if word == "project"
        else [verify / "report.json"]
    )
    if word == "milestone":
        checkout.append(verify / f"milestone-{number}.json")
    copy = None
    if writer == "new":
        key = {"feature": "redesign-r2%2F1-cart", "project": "0"}.get(word) or str(number)
        copy = repo / ".git/sdlc/passes" / data["id"] / f"{word}-{key}.json"
    for path in [*checkout, *([copy] if copy else [])]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
        os.utime(path, ns=(STAMP, STAMP))
    if (
        pr == "branch-deleted"
    ):  # the worktree went with the branch; the shared copy and the project report stay
        for path in checkout:
            if word != "project":
                path.unlink()


def _expected(writer: str, scope: str, record: str, pr: str) -> bool:
    """DONE only with a bound PASS that is still readable."""
    gone = pr == "branch-deleted" and scope != "project"  # a project report lives in the common dir
    readable = writer == "new" or not gone
    if record in ("none", "newer-fail"):
        return False
    if record == "other-owner":  # a project report names no owner
        return readable and scope == "project"
    if (
        record == "missing-binding"
    ):  # no `format`: the old reader's rule; with one: it holds nothing
        return readable and (writer == "old" or scope == "project")
    return readable


def _run_goal(code: Path, repo: Path, word: str, n: str, prs: dict) -> tuple[int, str]:
    r = subprocess.run(
        [sys.executable, "-c", DRIVER, str(code), str(repo), TID, word, n, json.dumps(prs)],
        capture_output=True,
        text=True,
        env=_clean_env(),
    )
    assert r.returncode == 0, r.stderr
    return tuple(json.loads(r.stdout))  # type: ignore[return-value]


@pytest.fixture(scope="module")
def main_scripts(tmp_path_factory):
    """origin/main's sdlc-run scripts, exported to a temp dir; None where there is no origin/main."""
    top = SKILL.parents[3]
    if subprocess.run(
        ["git", "-C", str(top), "rev-parse", "--verify", "-q", "origin/main"], capture_output=True
    ).returncode:
        return None
    dest = tmp_path_factory.mktemp("main")
    archive = subprocess.run(
        ["git", "-C", str(top), "archive", "origin/main", "plugins/cct/skills/sdlc-run"],
        capture_output=True,
    )
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive.stdout, check=True)
    return dest / "plugins/cct/skills/sdlc-run/scripts"


def _both(tmp_path: Path, main_scripts, scope: str, lay) -> dict:
    results = {}
    for name, code in (("new", SKILL / "scripts"), ("main", main_scripts)):
        if code is None:
            continue
        repo, heads, word, n, number = _fixture(tmp_path / name, scope)
        lay(repo, number)
        (pr,) = [lay.pr]
        state = "OPEN" if pr == "open" else "MERGED"
        base = "milestone/redesign-r2" if word == "feature" else "main"
        results[name] = _run_goal(code, repo, word, n, {h: _pr(state, base) for h in heads})
    return results


@pytest.mark.parametrize(
    ("writer", "scope", "record", "pr"),
    list(itertools.product(WRITERS, SCOPES, RECORDS, PRS)),
    ids=str,
)
def test_table_done_only_with_a_bound_pass_and_nothing_moves_toward_done(
    tmp_path: Path, main_scripts, writer: str, scope: str, record: str, pr: str
) -> None:
    def lay(repo: Path, number: int | None) -> None:
        _lay(repo, scope, record, writer, pr, number)

    lay.pr = pr  # type: ignore[attr-defined]
    got = _both(tmp_path, main_scripts, scope, lay)
    assert (got["new"][0] == 0) == _expected(writer, scope, record, pr), got
    if "main" in got and got["new"][0] == 0 and got["main"][0] != 0:
        # what moved toward DONE: the shared copy outliving the worktree, and the unbound pre-3.20.5
        # report that the kit has always read by its result line (main refuses it for a milestone)
        assert (
            (writer, record, pr) == ("new", "pass", "branch-deleted")
            or (writer == "old" and record == "missing-binding" and scope != "project")
            or (writer, record) == ("new", "other-owner")
            and scope == "project"
        ), got


@pytest.mark.parametrize(("scope", "pr"), list(itertools.product(SCOPES, PRS)), ids=str)
def test_a_retained_old_writers_newer_failure_beats_an_older_shared_pass(
    tmp_path: Path, main_scripts, scope: str, pr: str
) -> None:
    """Round 3, High 3: a 3.20.1/3.20.2 writer fails and updates only the checkout's report."""

    def lay(repo: Path, number: int | None) -> None:
        _lay(repo, scope, "pass", "new", "open", number)
        word = word_of(scope)
        old = {
            "scope": word,
            "id": "big" if word == "project" else TID,
            "result": f"VERIFY FAIL {word} x check=y",
            "sha": GATE,
        }
        verify = repo / "changes" / TID / "verify"
        targets = (
            [repo / ".git/sdlc/projects/big/verify/report.json"]
            if word == "project"
            else [verify / "report.json"]
        )
        if word == "milestone":
            targets.append(verify / f"milestone-{number}.json")
        for path in targets:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(old))
            os.utime(path, ns=(STAMP + 10, STAMP + 10))
        if (
            pr == "branch-deleted" and word != "project"
        ):  # the failure lived in the removed checkout
            for path in targets:
                path.unlink()

    lay.pr = pr  # type: ignore[attr-defined]
    got = _both(tmp_path, main_scripts, scope, lay)
    gone = pr == "branch-deleted" and scope != "project"
    assert (got["new"][0] == 0) == gone, (
        got
    )  # only the removal of the failure's own copy reopens it
    if "main" in got:
        assert got["main"][0] != 0 or got["new"][0] == 0, got


# --- the hook (pr-gate.sh) reads both copies ---------------------------------------------------------

from test_pr_gate import ID as HOOK_ID  # noqa: E402,F401
from test_pr_gate import _git as hook_git
from test_pr_gate import _local, _run
from test_pr_gate import repo as hook_repo


def _put(path: Path, data: dict, stamp: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    os.utime(path, ns=(stamp, stamp))


def _hook_common(repo: Path) -> Path:
    return Path(hook_git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))


def _milestone_pass(repo: Path, **over) -> dict:
    sha = hook_git(repo, "rev-parse", "HEAD")
    return {
        "scope": "milestone",
        "id": HOOK_ID,
        "sha": sha,
        "result": f"VERIFY PASS milestone {HOOK_ID} {sha}",
        "format": 2,
        "change": HOOK_ID,
        "owner": "",
        "milestone": 1,
        **over,
    }


def test_the_hook_takes_the_shared_copy_when_the_checkout_report_is_gone(hook_repo: Path) -> None:
    assert _run(hook_repo, "git push -u origin milestone/trial-1").returncode == 2
    _put(
        _hook_common(hook_repo) / "sdlc/passes" / HOOK_ID / "milestone-1.json",
        _milestone_pass(hook_repo),
        STAMP,
    )
    assert _run(hook_repo, "git push -u origin milestone/trial-1").returncode == 0


def test_the_hook_refuses_a_shared_copy_of_another_milestone_or_owner(hook_repo: Path) -> None:
    for over in ({"milestone": 2}, {"owner": "project/other"}, {"change": "other"}):
        _put(
            _hook_common(hook_repo) / "sdlc/passes" / HOOK_ID / "milestone-1.json",
            _milestone_pass(hook_repo, **over),
            STAMP,
        )
        assert _run(hook_repo, "git push -u origin milestone/trial-1").returncode == 2, over


def test_a_newer_failure_in_the_checkout_beats_an_older_shared_pass(hook_repo: Path) -> None:
    """A retained old writer fails and updates only the checkout's report."""
    _put(
        _hook_common(hook_repo) / "sdlc/passes" / HOOK_ID / "milestone-1.json",
        _milestone_pass(hook_repo),
        STAMP,
    )
    fail = {
        "scope": "milestone",
        "id": HOOK_ID,
        "result": f"VERIFY FAIL milestone {HOOK_ID} check=x",
        "sha": "f" * 40,
    }
    _put(hook_repo / "changes" / HOOK_ID / "verify" / "report.json", fail, STAMP + 10)
    assert _run(hook_repo, "git push -u origin milestone/trial-1").returncode == 2
    _put(
        hook_repo / "changes" / HOOK_ID / "verify" / "report.json", fail, STAMP - 10
    )  # an older failure does not
    assert _run(hook_repo, "git push -u origin milestone/trial-1").returncode == 0


def test_a_failed_project_rerun_beats_the_older_project_pass(hook_repo: Path) -> None:
    """Round 3, High 3: a retained 3.20.1/3.20.2 writer updates only the project's own report."""
    _local(hook_repo)
    hook_git(hook_repo, "checkout", "-q", "project/trial")
    sha = hook_git(hook_repo, "rev-parse", "project/trial")
    common = _hook_common(hook_repo) / "sdlc"
    passed = {
        "scope": "project",
        "id": "trial",
        "sha": sha,
        "result": f"VERIFY PASS project trial {sha}",
        "format": 2,
    }
    _put(common / "passes/trial/project-0.json", passed, STAMP)
    assert _run(hook_repo, "git push -u origin project/trial").returncode == 0
    fail = {
        "scope": "project",
        "id": "trial",
        "sha": sha,
        "result": "VERIFY FAIL project trial check=x",
    }
    _put(common / "projects/trial/verify/report.json", fail, STAMP + 10)
    assert _run(hook_repo, "git push -u origin project/trial").returncode == 2
    _put(
        common / "projects/trial/verify/report.json", passed, STAMP + 20
    )  # a newer pass reopens it
    assert _run(hook_repo, "git push -u origin project/trial").returncode == 0


# --- a local milestone: the shared receipts outlive the removed worktree -------------------------------

from test_sdlc_status import ID as ST_ID  # noqa: E402,F401
from test_sdlc_status import _bound, _merge, _no_gh, _sh, _two_milestones, sdlc_status
from test_sdlc_status import repo as status_repo


def _shared_receipt(repo: Path, n: int, sha: str, verdict: str = "PASS") -> None:
    data = {
        "scope": "milestone",
        "id": ST_ID,
        "result": f"VERIFY {verdict} milestone {ST_ID} {sha}",
        "sha": sha,
        "format": 2,
        **_bound(repo, "milestone", n),
    }
    _put(repo / ".git/sdlc/passes" / ST_ID / f"milestone-{n}.json", data, STAMP)


def _finished_local(repo: Path) -> tuple[str, str]:
    m1, m2 = _two_milestones(repo)
    _merge(repo, "milestone/redesign-r2-2")
    _sh(repo, "branch", "-D", "milestone/redesign-r2-1", "milestone/redesign-r2-2")
    return m1, m2


def test_a_deleted_local_milestone_is_done_by_the_shared_receipts_alone(status_repo: Path) -> None:
    m1, m2 = _finished_local(status_repo)
    got = sdlc_status.goal(
        status_repo, status_repo / "changes" / ST_ID, "milestone", None, gh=_no_gh
    )
    assert got[0] == 1  # no checkout report, no receipt: nothing proves it
    _shared_receipt(status_repo, 1, m1)
    _shared_receipt(status_repo, 2, m2)
    got = sdlc_status.goal(
        status_repo, status_repo / "changes" / ST_ID, "milestone", None, gh=_no_gh
    )
    assert got == (0, f"GOAL {ST_ID} DONE merged=project/big gate={m2}")


def test_a_newer_checkout_failure_reopens_a_local_milestone_with_a_shared_pass(
    status_repo: Path,
) -> None:
    m1, m2 = _finished_local(status_repo)
    _shared_receipt(status_repo, 1, m1)
    _shared_receipt(status_repo, 2, m2)
    verify = status_repo / "changes" / ST_ID / "verify"
    old_fail = {
        "scope": "milestone",
        "id": ST_ID,
        "result": f"VERIFY FAIL milestone {ST_ID} check=x",
        "sha": m1,
    }
    _put(verify / "milestone-1.json", old_fail, STAMP + 10)
    got = sdlc_status.goal(
        status_repo, status_repo / "changes" / ST_ID, "milestone", None, gh=_no_gh
    )
    assert got[0] == 1 and "receipt-not-merged:1" in got[1]
