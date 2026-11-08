"""adopt.py renders the chain into a repo; this proves the render, not the chain.

A throwaway git repo per test (node or python by marker file), adopt run on it, then:
every generated file exists, no `{{TOKEN}}` survives, hooks are executable and do what
sdlc.json says, a second run writes nothing, CODEOWNERS follows `codeowners`.
The rendered guardrail test itself runs in the adopting repo's CI, not here.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent
ADOPT = SCRIPTS / "adopt.py"
# Read, not imported: importing adopt.py runs it. A fork may flip the default, and these tests
# must hold either way.
TIERS_DEFAULT = (
    re.search(r"^TIERS_DEFAULT = (True|False)$", ADOPT.read_text(), re.M).group(1) == "True"
)
TOKEN = re.compile(r"\{\{[A-Z_]+\}\}|\{\{#\w+\}\}|\{\{/\w+\}\}")


def _env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def _repo(tmp_path: Path, kind: str) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    env = _env()
    subprocess.run(["git", "init", "-q", "-b", "master"], cwd=repo, check=True, env=env)
    (repo / ("package.json" if kind == "node" else "pyproject.toml")).write_text(
        "{}\n" if kind == "node" else "[project]\nname='x'\n"
    )
    (repo / "CLAUDE.md").write_text("# repo\n")
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / ".github" / "workflows" / "ci.yml").write_text("name: Checks\non: [push]\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=env)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"],
        cwd=repo,
        check=True,
        env=env,
    )
    return repo


def _adopt(repo: Path, *args: str, tiers: str | None = "yes") -> subprocess.CompletedProcess[str]:
    """Runs adopt as the skill does: with the engineer's Ship/Show/Ask answer, `yes` unless the
    test says otherwise. `tiers=None` runs it with no answer, where TIERS_DEFAULT applies."""
    if tiers and "--tiers" not in args:
        args = (*args, "--tiers", tiers)
    return subprocess.run(
        [sys.executable, str(ADOPT), *args], cwd=repo, capture_output=True, text=True, env=_env()
    )


def _sections(out: str) -> dict[str, list[str]]:
    parts = re.split(r"-#-#- (\w+) -#-#-\n", out)
    return {
        parts[i]: [line for line in parts[i + 1].splitlines() if line and line != "(nothing)"]
        for i in range(1, len(parts), 2)
    }


GENERATED = [
    "sdlc.json",
    ".claude/settings.json",
    ".claude/hooks/sdlc-config.sh",
    ".claude/hooks/chain-gate.sh",
    ".claude/hooks/gate-bash.sh",
    ".claude/hooks/lint-on-edit.sh",
    ".claude/hooks/plan-gate.sh",
    ".claude/hooks/pr-gate.sh",
    ".claude/hooks/session-check.sh",
    ".claude/hooks/verify-on-stop.sh",
    ".github/tiers.json",
    ".github/workflows/ship-show-ask.yml",
    "scripts/ship_show_ask.py",
    "scripts/verify_gate.py",
    "scripts/marks.py",
    "scripts/sdlc_status.py",
    "REVIEW.md",
    "docs/sdlc.md",
]


@pytest.mark.parametrize(
    "kind,test_file", [("node", "tests/sdlc.test.ts"), ("python", "tests/test_sdlc.py")]
)
def test_adopt_renders_everything_without_leftover_tokens(
    tmp_path: Path, kind: str, test_file: str
) -> None:
    repo = _repo(tmp_path, kind)
    result = _adopt(repo)
    assert result.returncode == 0, result.stderr
    for rel in GENERATED + [test_file]:
        assert (repo / rel).is_file(), rel
    for rel in GENERATED + [test_file, "CLAUDE.md"]:
        text = (repo / rel).read_text(encoding="utf-8")
        assert not TOKEN.search(text), f"{rel}: unrendered token {TOKEN.search(text).group(0)}"
    for hook in (repo / ".claude" / "hooks").glob("*.sh"):
        assert os.access(hook, os.X_OK), hook.name
    changes = [p for p in (repo / "changes").iterdir() if p.is_dir() and p.name != "archive"]
    first = f"{dt.date.today().isoformat()}-adopt-sdlc"
    assert [c.name for c in changes] == [first]
    assert "## Problem" in (changes[0] / "intent.md").read_text()
    plan = (changes[0] / "plan.md").read_text()
    for section in ("## Order of work", "## Done", "## Revisions", "## Design changes"):
        assert section in plan, section
    assert f"change: {first}" in plan and "linear: none" in plan
    assert (
        "/goal" in (repo / "CLAUDE.md").read_text()
        and "sdlc-run" in (repo / "CLAUDE.md").read_text()
    )
    assert "docs/sdlc.md" in (repo / "CLAUDE.md").read_text()
    for name in ("claude-review.yml", "claude.yml", "ci-triage.yml"):
        assert not (repo / ".github" / "workflows" / name).exists(), f"{name}: no Claude in CI"
    assert not (repo / ".github" / "CODEOWNERS").exists(), "no codeowners named -> no file"
    assert "notify:" not in (repo / ".github" / "workflows" / "ship-show-ask.yml").read_text(), (
        "no showChannel -> no notify job"
    )


def test_second_run_writes_nothing(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    _adopt(repo)
    second = _sections(_adopt(repo).stdout)
    assert second["WROTE"] == [], second["WROTE"]


def test_pretooluse_keeps_every_hook(tmp_path: Path) -> None:
    # The spec used to be a dict keyed by event, so the second PreToolUse entry overwrote
    # the first and one of the two gates was simply absent from every adopted repo.
    repo = _repo(tmp_path, "node")
    _adopt(repo)
    settings = json.loads((repo / ".claude" / "settings.json").read_text(encoding="utf-8"))
    pre = [h["command"] for g in settings["hooks"]["PreToolUse"] for h in g["hooks"]]
    assert any("gate-bash.sh" in c for c in pre), pre
    assert any("chain-gate.sh" in c for c in pre), pre
    assert any("pr-gate.sh" in c for c in pre), pre
    matchers = {g.get("matcher") for g in settings["hooks"]["PreToolUse"]}
    assert matchers == {"Bash", "Edit|Write"}, matchers
    # And a second adopt does not append them again.
    _adopt(repo)
    again = json.loads((repo / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert len([h for g in again["hooks"]["PreToolUse"] for h in g["hooks"]]) == 3


def test_dry_run_touches_nothing(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "python")
    out = _sections(_adopt(repo, "--dry-run").stdout)
    assert "sdlc.json" in out["WROTE"]
    assert not (repo / "sdlc.json").exists()


def test_codeowners_and_notify_follow_sdlc_json(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    _adopt(repo)
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["codeowners"] = ["@alice", "@bob"]
    cfg["showChannel"] = "C123"
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    _adopt(repo)
    owners = (repo / ".github" / "CODEOWNERS").read_text()
    tiers = json.loads((repo / ".github" / "tiers.json").read_text())
    rules = [line.split() for line in owners.splitlines() if line and not line.startswith("#")]
    assert len(rules) == len(tiers["ask"])
    assert all(r[1:] == ["@alice", "@bob"] for r in rules)
    assert "/k8s/  @alice @bob" in owners
    ssa = (repo / ".github" / "workflows" / "ship-show-ask.yml").read_text()
    assert "notify:" in ssa and 'CHANNEL: "C123"' in ssa
    cfg["codeowners"] = []
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    _adopt(repo)
    assert not (repo / ".github" / "CODEOWNERS").exists()


def test_rendered_hooks_read_sdlc_json(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "python")
    _adopt(repo)
    hooks = repo / ".claude" / "hooks"
    env = {**_env(), "CLAUDE_PROJECT_DIR": str(repo)}
    cfg = json.loads((repo / "sdlc.json").read_text())
    for rule in cfg["blocked"]:
        for cmd in rule["samples"]:
            r = subprocess.run(
                [str(hooks / "gate-bash.sh")],
                input=json.dumps({"tool_input": {"command": cmd}}),
                capture_output=True,
                text=True,
                env=env,
            )
            assert r.returncode == 2 and "BLOCKED" in r.stderr, cmd
    ok = subprocess.run(
        [str(hooks / "gate-bash.sh")],
        input=json.dumps({"tool_input": {"command": "git status"}}),
        capture_output=True,
        text=True,
        env=env,
    )
    assert ok.returncode == 0
    # verify-on-stop reads `verify` from sdlc.json: a failing verify blocks the stop.
    cfg["verify"] = "sh -c 'echo verify-ran; exit 1'"
    cfg.pop("verifyStop", None)  # the python preset has one; this test is about `verify`
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    (repo / "x.py").write_text("x = 1\n")
    r = subprocess.run(
        [str(hooks / "verify-on-stop.sh")],
        input=json.dumps({"stop_hook_active": False}),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 2 and "verify-ran" in r.stderr


def test_v3_keys_are_preserved_and_only_presets_add_them(tmp_path: Path) -> None:
    (tmp_path / "node").mkdir()
    (tmp_path / "python").mkdir()
    node = _repo(tmp_path / "node", "node")
    python = _repo(tmp_path / "python", "python")
    _adopt(node)
    _adopt(python)
    node_cfg = json.loads((node / "sdlc.json").read_text())
    py_cfg = json.loads((python / "sdlc.json").read_text())
    assert node_cfg["verifyStop"] == "pnpm format && pnpm lint && pnpm typecheck"
    assert py_cfg["verifyStop"] == "uv run ruff format --check . && uv run ruff check ."
    for key in ("planGate", "testGlobs", "prototypeDirs", "feedback"):
        assert key not in node_cfg and key not in py_cfg

    node_cfg.update(
        verifyStop="pnpm fast",
        planGate="self",
        testGlobs=["custom/**/*.test.ts"],
        prototypeDirs=["design/prototypes"],
        feedback=["docs/feedback/*.md"],
    )
    (node / "sdlc.json").write_text(json.dumps(node_cfg, indent=2) + "\n")
    _adopt(node)
    after = json.loads((node / "sdlc.json").read_text())
    assert after["verifyStop"] == "pnpm fast"
    assert after["planGate"] == "self"
    assert after["testGlobs"] == ["custom/**/*.test.ts"]
    assert after["prototypeDirs"] == ["design/prototypes"]
    assert after["feedback"] == ["docs/feedback/*.md"]


def _old_cfg(repo: Path, milestone: list[str]) -> None:
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg.pop("verifyStop", None)
    cfg["checks"]["milestone"] = milestone
    (repo / "sdlc.json").write_text(json.dumps(cfg, indent=2) + "\n")


def test_migrates_a_whole_suite_repeat_and_adds_verify_stop(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    _adopt(repo)
    _old_cfg(repo, ["pnpm test", "pnpm test:e2e --repeat-each 3"])
    for name in ("2026-10-01-open", "2026-10-02-draft"):
        (repo / "changes" / name).mkdir(parents=True)
    (repo / "changes" / "2026-10-01-open" / "lock.json").write_text("{}\n")
    (repo / "changes" / "archive" / "2026-09-01-old").mkdir(parents=True)
    (repo / "changes" / "archive" / "2026-09-01-old" / "lock.json").write_text("{}\n")

    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=_env())
    res = _adopt(repo)
    assert res.returncode == 0, res.stderr
    out = _sections(res.stdout)
    cfg = json.loads((repo / "sdlc.json").read_text())
    assert cfg["checks"]["milestone"] == ["pnpm test", "pnpm test:e2e --max-failures=10"]
    assert cfg["verifyStop"] == "pnpm format && pnpm lint && pnpm typecheck"
    assert any("verifyStop added" in w for w in out["WROTE"])
    assert any("--repeat-each 3" in w and "--max-failures=10" in w for w in out["WROTE"])
    approve = [m for m in out["MANUAL"] if "verify_gate.py approve" in m]
    assert len(approve) == 1 and "2026-10-01-open" in approve[0]


@pytest.mark.parametrize(
    "existing",
    [
        None,
        "pnpm format && pnpm lint && pnpm typecheck",
        "pnpm run format && pnpm lint && pnpm run typecheck",
    ],
)
def test_verify_stop_follows_an_npm_lockfile(tmp_path: Path, existing: str | None) -> None:
    repo = _repo(tmp_path, "node")
    (repo / "package-lock.json").write_text("{}\n")
    _adopt(repo)
    _old_cfg(repo, ["npm test"])
    if existing:
        cfg = json.loads((repo / "sdlc.json").read_text())
        cfg["verifyStop"] = existing
        (repo / "sdlc.json").write_text(json.dumps(cfg) + "\n")
    _adopt(repo)
    stop = json.loads((repo / "sdlc.json").read_text())["verifyStop"]
    assert stop == "npm run format && npm run lint && npm run typecheck"


@pytest.mark.parametrize(
    ("old", "new"),
    [
        # samplewerk: the repeat sat behind a wrapper script and adopt missed it
        ("sh scripts/e2e.sh --repeat-each 3", "sh scripts/e2e.sh --max-failures=10"),
        (
            "pnpm test:e2e --repeat-each=3 --project chromium",
            "pnpm test:e2e --project chromium --max-failures=10",
        ),
        ("pnpm test:e2e --max-failures=5 --repeat-each 3", "pnpm test:e2e --max-failures=5"),
    ],
)
def test_drops_a_whole_suite_repeat_in_place(tmp_path: Path, old: str, new: str) -> None:
    repo = _repo(tmp_path, "node")
    _adopt(repo)
    _old_cfg(repo, [old])
    _adopt(repo)
    assert json.loads((repo / "sdlc.json").read_text())["checks"]["milestone"] == [new]


@pytest.mark.parametrize(
    "cmd",
    ["pnpm test:e2e --only-changed --repeat-each 3", "pnpm test:e2e --grep @x --repeat-each 3"],
)
def test_leaves_a_scoped_repeat_alone(tmp_path: Path, cmd: str) -> None:
    repo = _repo(tmp_path, "node")
    _adopt(repo)
    _old_cfg(repo, [cmd])
    out = _sections(_adopt(repo).stdout)
    assert json.loads((repo / "sdlc.json").read_text())["checks"]["milestone"] == [cmd]
    assert not any("verify_gate.py approve" in m for m in out["MANUAL"])


def test_keeps_repo_owned_files_and_docs_tail(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    _adopt(repo)
    (repo / "REVIEW.md").write_text("# mine\n")
    docs = repo / "docs" / "sdlc.md"
    docs.write_text(docs.read_text() + "\n## Local rule\n\nkeep me\n")
    out = _sections(_adopt(repo).stdout)
    assert "REVIEW.md" in out["KEPT"]
    assert (repo / "REVIEW.md").read_text() == "# mine\n"
    assert "keep me" in docs.read_text()
    assert docs.read_text().count("# The SDLC") == 1


def test_keeps_docs_tail_under_the_run_sdlc_marker(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    _adopt(repo)
    docs = repo / "docs" / "sdlc.md"
    old = docs.read_text().replace("sdlc-run adopt keeps", "run-sdlc adopt keeps")
    docs.write_text(old + "\n## Local rule\n\nkeep me\n")
    _adopt(repo)
    assert "keep me" in docs.read_text()


def test_ticket_names_the_first_change(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    _adopt(repo, "--ticket", "REV-947")
    first = repo / "changes" / f"{dt.date.today().isoformat()}-REV-947-adopt-sdlc"
    assert (first / "plan.md").exists()
    assert "linear: REV-947" in (first / "facts.md").read_text()


def test_migrates_goals_and_claude_plans(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "python")
    env = _env()
    goal = repo / "goals" / "2026-09-05-ai-native-sdlc"
    goal.mkdir(parents=True)
    fm = "---\nlinear: CPTO-947\ntype: %s\ngoal: 2026-09-05-ai-native-sdlc\nauthor: t@t\nstatus: approved\ncreated: 2026-09-05\n---\n"
    (goal / "intent.md").write_text(
        fm % "intent"
        + "# Intent\n\n## Problem\n\n## Proposed outcome\n\n## Affected users and systems\n\n## Constraints\n\n## Open questions\n"
    )
    (goal / "facts.md").write_text(fm % "facts" + "# Facts\n")
    (goal / "plan.md").write_text(fm % "plan" + "# Plan\n\n## Order of work\n\n1. x\n")
    (goal / "goal.md").write_text(
        fm % "goal" + "# Goal\n\n## Done condition\n\n- make verify exits 0\n"
    )
    plans = repo / ".claude" / "plans"
    plans.mkdir(parents=True)
    (plans / "2026-08-01T1200-handover-x.md").write_text("old handover\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=env)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "old layout"],
        cwd=repo,
        check=True,
        env=env,
    )

    out = _sections(_adopt(repo).stdout)
    dest = repo / "changes" / "archive" / "2026" / "2026-09" / "2026-09-05-CPTO-947-ai-native-sdlc"
    assert dest.is_dir() and not (repo / "goals").exists()
    assert not (dest / "goal.md").exists()
    plan = (dest / "plan.md").read_text()
    assert "## Done" in plan and "make verify exits 0" in plan
    assert "change: 2026-09-05-CPTO-947-ai-native-sdlc" in plan and "archived_at:" in plan
    assert (repo / "docs" / "history" / "plans" / "2026-08-01T1200-handover-x.md").exists()
    assert not (repo / ".claude" / "plans").exists()
    # A migrated repo has an archived change, so no adopt-sdlc change is invented on top.
    assert any("migrated" in w for w in out["WROTE"])


def test_keep_list_protects_a_generated_file(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    _adopt(repo)
    wf = repo / ".github" / "workflows" / "ship-show-ask.yml"
    wf.write_text("# hand-tuned\n")
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["keep"] = [".github/workflows/ship-show-ask.yml"]
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    out = _sections(_adopt(repo).stdout)
    assert wf.read_text() == "# hand-tuned\n"
    assert any("ship-show-ask.yml (sdlc.json keep)" in k for k in out["KEPT"])


def test_linear_safe_rewrites_repo_paths_and_refuses_local_ones(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    env = _env()
    subprocess.run(
        ["git", "remote", "add", "origin", "git@github.com:example-org/example.git"],
        cwd=repo,
        check=True,
        env=env,
    )
    (repo / "docs").mkdir(exist_ok=True)
    (repo / "docs" / "x.md").write_text("x")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=env)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "docs"],
        cwd=repo,
        check=True,
        env=env,
    )
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, env=env
    ).stdout.strip()
    body = repo / "body.md"
    body.write_text(
        "See docs/x.md and `docs/x.md` but not docs/missing.md nor https://github.com/example-org/example/blob/abc/docs/x.md\n"
    )
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "linear-safe.py"), str(body)],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr
    assert f"[docs/x.md](https://github.com/example-org/example/blob/{sha}/docs/x.md)" in r.stdout
    assert "docs/missing.md" in r.stdout and "[docs/missing.md]" not in r.stdout
    assert r.stdout.count("blob/abc/docs/x.md") == 1
    body.write_text("open ~/projects/x/specs/a.md or /Users/me/y.md\n")
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "linear-safe.py"), "--check", str(body)],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 2 and "REFUSED" in r.stderr and "1:" in r.stderr


def test_migrates_dot_changes_and_specs_to_changes_and_designs(tmp_path: Path) -> None:
    """The 2026-09-07 layout decision: `.changes/` -> `changes/`, `specs/` -> `docs/designs/`,
    `specsDir` -> `designsDir`, `spec:` -> `design:`, and the CLAUDE.md section refreshed."""
    repo = _repo(tmp_path, "node")
    env = _env()
    cfg = json.loads((SCRIPTS.parent / "templates" / "presets" / "node.json").read_text())
    cfg["changesDir"] = ".changes"
    cfg["specsDir"] = "specs"
    cfg.pop("designsDir", None)
    (repo / "sdlc.json").write_text(json.dumps(cfg, indent=2) + "\n")
    change = repo / ".changes" / "REV-1-x"
    change.mkdir(parents=True)
    fm = "---\nlinear: REV-1\ntype: %s\nchange: REV-1-x\nspec: specs/2026-09-01-x.md\nauthor: t@t\nstatus: approved\ncreated: 2026-09-01\n---\n"
    (change / "facts.md").write_text(fm % "facts" + "# Facts\n")
    (change / "plan.md").write_text(
        fm % "plan"
        + "# Plan\n\n## Spec changes\n\nnone\n\n## Order of work\n\n- [ ] 1. x\n\n## Done\n\n- x\n\n## Revisions\n"
    )
    (repo / "specs").mkdir()
    (repo / "specs" / "2026-09-01-x.md").write_text("# x\n\n## Milestones\n\n- REV-1-x\n")
    (repo / "REVIEW.md").write_text("# Review\n\nwhat `.changes/<date>-<slug>/plan.md` says\n")
    (repo / "CLAUDE.md").write_text(
        "# repo\n\n## How work moves: the SDLC\n\nold text with `.changes/<TICKET>-<slug>/` and specs in `specs/`.\nthe reference is docs/sdlc.md\n\n## Verifying your work\n\n    pnpm test\n\nThe Stop hook runs it for you when source files are dirty.\n"
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=env)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "old layout"],
        cwd=repo,
        check=True,
        env=env,
    )

    out = _sections(_adopt(repo).stdout)
    migrated = repo / "changes" / "2026-09-01-REV-1-x"
    assert (migrated / "plan.md").exists() and not (repo / ".changes").exists()
    assert (repo / "docs" / "designs" / "2026-09-01-x.md").exists() and not (
        repo / "specs"
    ).exists()
    plan = (migrated / "plan.md").read_text()
    assert "change: 2026-09-01-REV-1-x" in plan
    assert "design: docs/designs/2026-09-01-x.md" in plan and "spec:" not in plan
    assert "## Design changes" in plan
    new_cfg = json.loads((repo / "sdlc.json").read_text())
    assert (
        new_cfg["changesDir"] == "changes"
        and new_cfg["designsDir"] == "docs/designs"
        and "specsDir" not in new_cfg
    )
    claude = (repo / "CLAUDE.md").read_text()
    assert ".changes/" not in claude and "docs/designs/" in claude
    assert "`changes/<date>-<slug>/plan.md`" in (
        repo / "REVIEW.md"
    ).read_text() and claude.startswith("# repo\n")
    assert any(".changes/ -> changes/" in w for w in out["WROTE"])
    # No adopt-sdlc change invented on top of an existing change.
    assert not list((repo / "changes").glob("*-adopt-sdlc"))


def test_runs_the_repos_own_prettier_over_what_it_wrote(tmp_path: Path) -> None:
    """A repo with a `prettier --check` gate rejects a freshly written template, because the
    templates cannot match every printWidth and quote style. adopt calls the repo's prettier."""
    repo = _repo(tmp_path, "node")
    bin_dir = repo / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)
    stub = bin_dir / "prettier"
    stub.write_text('#!/bin/sh\nprintf "%s\\n" "$@" >> "$(dirname "$0")/../../prettier-argv.txt"\n')
    stub.chmod(0o755)

    _adopt(repo)

    argv = (repo / "prettier-argv.txt").read_text().splitlines()
    assert argv[0] == "--write", argv[:3]
    formatted = [a for a in argv if not a.startswith("--")]
    assert any(a.endswith("tests/sdlc.test.ts") for a in formatted), formatted
    assert any(a.endswith(".github/workflows/ship-show-ask.yml") for a in formatted), formatted
    # sdlc.json on a SECOND run is the real case: it exists, so it takes the merge path
    # instead of write(), and it still has to reach prettier or the repo rejects the commit.
    (repo / "prettier-argv.txt").unlink()
    _adopt(repo)
    again = [
        a for a in (repo / "prettier-argv.txt").read_text().splitlines() if not a.startswith("--")
    ]
    assert any(a.endswith("sdlc.json") for a in again), again
    # Shell scripts and other non-prettier files are not handed to it.
    assert not any(a.endswith(".sh") for a in formatted), formatted


def test_without_prettier_installed_adopt_still_succeeds(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    out = _adopt(repo)
    assert out.returncode == 0, out.stderr
    assert not (repo / "node_modules").exists()


def test_stamps_templates_hash_and_status_reports_stale(tmp_path: Path) -> None:
    """The copied hooks, workflows and guardrail test run in CI, where no plugin exists, so
    they cannot read the skill. `adopt` stamps what it copied; `status.sh` says when a repo
    has fallen behind the installed kit."""
    repo = _repo(tmp_path, "node")
    _adopt(repo)
    want = subprocess.run(
        [sys.executable, str(ADOPT), "--templates-hash"], capture_output=True, text=True, env=_env()
    ).stdout.strip()
    assert len(want) == 12
    assert json.loads((repo / "sdlc.json").read_text())["kitTemplates"] == want

    def status() -> str:
        return subprocess.run(
            ["bash", str(SCRIPTS / "status.sh")],
            cwd=repo,
            capture_output=True,
            text=True,
            env=_env(),
        ).stdout

    assert "templates=current" in status()

    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["kitTemplates"] = "deadbeef1234"
    (repo / "sdlc.json").write_text(json.dumps(cfg, indent=2) + "\n")
    assert f"templates=stale (deadbeef1234 -> {want})" in status()

    _adopt(repo)
    assert json.loads((repo / "sdlc.json").read_text())["kitTemplates"] == want
    assert "templates=current" in status()


def test_nests_the_archive_and_fixes_a_misnamed_folder(tmp_path: Path) -> None:
    """A flat archive becomes <year>/<year-month>/, and a folder whose name-date is not its
    `created` date is renamed on the way. Measured in a real repo: 52 archived changes in
    15 days, 2 of them named by their ARCHIVE date, so a name could not be read."""
    repo = _repo(tmp_path, "node")
    env = _env()
    fm = (
        "---\nlinear: %s\ntype: plan\nchange: %s\ndesign: null\nauthor: t@t\n"
        "status: approved\ncreated: %s\narchived_at: %s\n---\n\n# Plan\n\n"
        "## Order of work\n\n- [ ] 1. x\n\n## Done\n\n- x\n\n## Revisions\n"
    )
    arch = repo / "changes" / "archive"
    # Named by its creation date: only nested.
    ok = arch / "2026-08-11-REV-900-good-name"
    ok.mkdir(parents=True)
    (ok / "plan.md").write_text(fm % ("REV-900", ok.name, "2026-08-11", "2026-08-12"))
    # Named by its ARCHIVE date: renamed to 2026-09-09, then nested under 2026-09.
    bad = arch / "2026-09-10-REV-980-status-enum"
    bad.mkdir(parents=True)
    (bad / "plan.md").write_text(fm % ("REV-980", bad.name, "2026-09-09", "2026-09-10"))
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=env)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "flat archive"],
        cwd=repo,
        check=True,
        env=env,
    )
    _adopt(repo)

    assert (arch / "2026" / "2026-08" / "2026-08-11-REV-900-good-name" / "plan.md").is_file()
    renamed = arch / "2026" / "2026-09" / "2026-09-09-REV-980-status-enum"
    assert renamed.is_file() is False and renamed.is_dir()
    assert "change: 2026-09-09-REV-980-status-enum" in (renamed / "plan.md").read_text()
    # The flat folders are gone, and no empty shells are left behind.
    assert not ok.exists() and not bad.exists()
    assert sorted(p.name for p in arch.iterdir() if p.is_dir()) == ["2026"]

    # Idempotent: a second adopt moves nothing.
    assert _sections(_adopt(repo).stdout)["WROTE"] == []


def test_migrates_legacy_change_ids_and_drops_pending(tmp_path: Path) -> None:
    """Ids from before the date prefix are renamed, and `PENDING` becomes what it always
    meant: a change with no Linear issue. Open and archived folders both."""
    repo = _repo(tmp_path, "node")
    env = _env()
    fm = "---\nlinear: %s\ntype: plan\nchange: %s\ndesign: null\nauthor: t@t\nstatus: approved\ncreated: %s\n---\n\n# Plan\n\n## Order of work\n\n- [ ] 1. x\n\n## Done\n\n- x\n\n## Revisions\n"
    keyed = repo / "changes" / "REV-971-booking-form"
    keyed.mkdir(parents=True)
    (keyed / "plan.md").write_text(fm % ("REV-971", "REV-971-booking-form", "2026-09-02"))
    (keyed / "facts.md").write_text(fm % ("REV-971", "REV-971-booking-form", "2026-09-02"))
    ticketless = repo / "changes" / "PENDING-guardrail-flag-evasion"
    ticketless.mkdir(parents=True)
    (ticketless / "plan.md").write_text(
        fm % ("pending", "PENDING-guardrail-flag-evasion", "2026-09-03")
    )
    (ticketless / "facts.md").write_text(
        fm % ("pending", "PENDING-guardrail-flag-evasion", "2026-09-03")
    )
    archived = repo / "changes" / "archive" / "2026-09-04-PENDING-hubspot-downloads"
    archived.mkdir(parents=True)
    (archived / "plan.md").write_text(
        (fm % ("pending", "2026-09-04-PENDING-hubspot-downloads", "2026-09-04")).replace(
            "status: approved", "status: approved\narchived_at: 2026-09-04"
        )
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=env)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "legacy ids"],
        cwd=repo,
        check=True,
        env=env,
    )

    _adopt(repo)

    kept_key = repo / "changes" / "2026-09-02-REV-971-booking-form"
    now_dated = repo / "changes" / "2026-09-03-guardrail-flag-evasion"
    moved = repo / "changes" / "archive" / "2026" / "2026-09" / "2026-09-04-hubspot-downloads"
    assert kept_key.is_dir() and not keyed.exists()
    assert now_dated.is_dir() and not ticketless.exists()
    assert moved.is_dir() and not archived.exists()
    for name in ("plan.md", "facts.md"):
        assert f"change: {kept_key.name}" in (kept_key / name).read_text()
        assert "linear: REV-971" in (kept_key / name).read_text()
        assert f"change: {now_dated.name}" in (now_dated / name).read_text()
        assert "linear: none" in (now_dated / name).read_text()
    assert "linear: none" in (moved / "plan.md").read_text()
    assert f"change: {moved.name}" in (moved / "plan.md").read_text()
    # An existing change means no adopt-sdlc change is invented on top.
    assert not list((repo / "changes").glob("*-adopt-sdlc"))


def test_adopt_removes_the_claude_workflows_and_the_claude_key(tmp_path: Path) -> None:
    """3.7.0: no Claude in CI. A repo adopted before keeps claude-review.yml, claude.yml,
    ci-triage.yml and `claude` in sdlc.json; adopt takes all of them out (git rm) and never asks
    for ANTHROPIC_API_KEY. ship-show-ask.yml is untouched."""
    repo = _repo(tmp_path, "node")
    env = _env()
    assert _adopt(repo).returncode == 0
    wf = repo / ".github" / "workflows"
    for name in ("claude-review.yml", "claude.yml", "ci-triage.yml"):
        (wf / name).write_text("name: old\n")
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["claude"] = True
    (repo / "sdlc.json").write_text(json.dumps(cfg, indent=2) + "\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=env)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "adopted before 3.7"],
        cwd=repo,
        check=True,
        env=env,
    )

    for flag in ((), ("--upgrade",)):
        res = _adopt(repo, *flag)
        assert res.returncode == 0, res.stdout + res.stderr
        out = _sections(res.stdout)
        for name in ("claude-review.yml", "claude.yml", "ci-triage.yml"):
            assert not (wf / name).exists(), name
        assert "claude" not in json.loads((repo / "sdlc.json").read_text())
        assert not any("ANTHROPIC_API_KEY" in m for m in out["MANUAL"])
        if not flag:
            assert any("claude-review.yml (removed" in w for w in out["WROTE"])
            assert any("claude removed" in w for w in out["WROTE"])
            assert any("no merge-gate" in m for m in out["MANUAL"])
    assert (wf / "ship-show-ask.yml").exists()
    tracked = subprocess.run(
        ["git", "ls-files", ".github/workflows"], cwd=repo, capture_output=True, text=True, env=env
    ).stdout
    assert "claude-review.yml" not in tracked, "git rm, not just unlink"


def test_milestone_and_project_prs_merge_with_a_merge_commit() -> None:
    """3.7.0: a stacked milestone keeps its predecessor as ancestry only if milestone PRs are
    merge commits; everything else still squashes."""
    wf = (ADOPT.parent.parent / "templates/workflows/ship-show-ask.yml").read_text()
    assert "milestone/*|project/*) how=--merge" in wf and "how=--squash" in wf
    assert '--auto "$how"' in wf and "--auto --squash" not in wf


TIER_FILES = (
    ".github/workflows/ship-show-ask.yml",
    "scripts/ship_show_ask.py",
    ".github/tiers.json",
    ".github/CODEOWNERS",
)


def _commit(repo: Path, msg: str) -> None:
    env = _env()
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=env)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", msg],
        cwd=repo,
        check=True,
        env=env,
    )


def _set_cfg(repo: Path, **fields: object) -> None:
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg.update(fields)
    (repo / "sdlc.json").write_text(json.dumps(cfg, indent=2) + "\n")


@pytest.mark.parametrize("kind", ["node", "python"])
def test_tiers_false_writes_no_tier_files_and_no_tier_docs(tmp_path: Path, kind: str) -> None:
    """sdlc.json `tiers: false`, set before the first adopt: one owner, no Ship/Show/Ask."""
    repo = _repo(tmp_path, kind)
    cfg = json.loads((SCRIPTS.parent / "templates" / "presets" / f"{kind}.json").read_text())
    cfg.update(tiers=False, codeowners=["@alice"], showChannel="C123")
    (repo / "sdlc.json").write_text(json.dumps(cfg, indent=2) + "\n")
    result = _adopt(repo, tiers=None)
    assert result.returncode == 0, result.stderr
    for rel in TIER_FILES:
        assert not (repo / rel).exists(), rel
    docs = (repo / "docs" / "sdlc.md").read_text()
    assert "Ship / Show / Ask" not in docs and "ship-show-ask" not in docs
    assert "## Merging: auto-merge on green" in docs and "gh pr merge <n> --merge --auto" in docs
    assert "CODE_MANAGER_APP" not in docs and "SDLC_COOWNER" not in docs
    assert "`ask` needs a human" not in (repo / "CLAUDE.md").read_text()
    for rel in ("docs/sdlc.md", "CLAUDE.md"):
        text = (repo / rel).read_text()
        assert not TOKEN.search(text), f"{rel}: unrendered {TOKEN.search(text).group(0)}"
    manual = "\n".join(_sections(result.stdout)["MANUAL"])
    for word in ("CODE_MANAGER_APP", "SDLC_COOWNER", "SDLC_SLACK_BOT_TOKEN", "code_owner", "App"):
        assert word not in manual, word
    assert "ship_show_ask" not in manual


def test_tiers_false_removes_existing_tier_files(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    _adopt(repo)
    _set_cfg(repo, codeowners=["@alice"])
    _adopt(repo)
    for rel in TIER_FILES:
        assert (repo / rel).exists(), rel
    claude_before = (repo / "CLAUDE.md").read_text()
    assert "`ask` needs a human" in claude_before
    _commit(repo, "adopted with tiers")

    _set_cfg(repo, tiers=False)
    out = _sections(_adopt(repo, tiers=None).stdout)
    for rel in TIER_FILES:
        assert not (repo / rel).exists(), rel
        assert f"{rel} (removed: sdlc.json tiers=false)" in out["WROTE"], rel
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=repo, capture_output=True, text=True, env=_env()
    ).stdout
    assert not [rel for rel in TIER_FILES if rel in tracked], "git rm, not just unlink"
    assert "## Merging" in (repo / "docs" / "sdlc.md").read_text()
    claude_after = (repo / "CLAUDE.md").read_text()
    assert "`ask` needs a human" not in claude_after
    assert "There are no Ship/Show/Ask tiers here" in claude_after
    # The swap leaves a whole sentence, not a dangling fragment: an earlier replacement was
    # a lowercase clause with no full stop, which rendered as an orphan line mid-paragraph.
    assert "auto-merges on green too." in claude_after
    # And the next run leaves it alone.
    assert _sections(_adopt(repo, tiers=None).stdout)["WROTE"] == []


@pytest.mark.parametrize("kind", ["node", "python"])
def test_no_answer_renders_like_answering_the_kit_default(tmp_path: Path, kind: str) -> None:
    """No `--tiers` and no `tiers` key is byte-identical to answering TIERS_DEFAULT."""
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    default, explicit = _repo(tmp_path / "a", kind), _repo(tmp_path / "b", kind)
    _adopt(default, tiers=None)
    _adopt(explicit, tiers="yes" if TIERS_DEFAULT else "no")
    generated = [
        p.relative_to(default)
        for p in default.rglob("*")
        if p.is_file() and ".git" not in p.parts and p.name != "sdlc.json"
    ]
    for rel in generated:
        assert (explicit / rel).read_bytes() == (default / rel).read_bytes(), rel


@pytest.mark.parametrize("kind", ["node", "python"])
def test_tiers_yes_renders_the_tiers(tmp_path: Path, kind: str) -> None:
    default = _repo(tmp_path, kind)
    _adopt(default, tiers="yes")
    docs = (default / "docs" / "sdlc.md").read_text()
    assert "## Tiers: Ship / Show / Ask by blast radius" in docs and "## Merging" not in docs
    assert "labels the PR, requests reviewers" in docs and "CODE_MANAGER_APP_CLIENT_ID" in docs
    for rel in TIER_FILES[:3]:
        assert (default / rel).exists(), rel


@pytest.mark.parametrize("answer", ["yes", "no"])
def test_tiers_answer_on_first_adopt_is_written_to_sdlc_json(tmp_path: Path, answer: str) -> None:
    """The skill asks "Use Ship/Show/Ask?" and passes the answer; sdlc.json records it."""
    repo = _repo(tmp_path, "node")
    result = _adopt(repo, "--tiers", answer)
    assert result.returncode == 0, result.stderr
    assert json.loads((repo / "sdlc.json").read_text())["tiers"] is (answer == "yes")
    for rel in TIER_FILES[:3]:
        assert (repo / rel).exists() is (answer == "yes"), rel


def test_tiers_answer_on_upgrade_switches_an_adopted_repo(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    _adopt(repo, "--tiers", "yes")
    _commit(repo, "adopted with tiers")
    out = _sections(_adopt(repo, "--tiers", "no").stdout)
    assert "sdlc.json: tiers false (Ship/Show/Ask: no)" in out["WROTE"]
    assert json.loads((repo / "sdlc.json").read_text())["tiers"] is False
    for rel in TIER_FILES[:3]:
        assert not (repo / rel).exists(), rel
    # The same answer again changes nothing.
    assert _sections(_adopt(repo, "--tiers", "no").stdout)["WROTE"] == []


def test_without_an_answer_a_missing_tiers_key_is_written_as_the_default(tmp_path: Path) -> None:
    """The guardrail test in the repo reads a missing key as true, so adopt never leaves it out."""
    repo = _repo(tmp_path, "node")
    _adopt(repo)
    _set_cfg(repo, tiers=False)
    _adopt(repo, tiers=None)
    assert json.loads((repo / "sdlc.json").read_text())["tiers"] is False, "a set value stays"
    cfg = json.loads((repo / "sdlc.json").read_text())
    del cfg["tiers"]
    (repo / "sdlc.json").write_text(json.dumps(cfg, indent=2) + "\n")
    out = _sections(_adopt(repo, tiers=None).stdout)
    assert f"sdlc.json: tiers {str(TIERS_DEFAULT).lower()} (the kit default)" in out["WROTE"]
    assert json.loads((repo / "sdlc.json").read_text())["tiers"] is TIERS_DEFAULT


def test_tiers_takes_only_yes_or_no(tmp_path: Path) -> None:
    result = _adopt(_repo(tmp_path, "node"), "--tiers", "maybe")
    assert result.returncode != 0 and "--tiers takes yes or no" in result.stderr


def test_tiers_no_notes_the_ruleset_cleanup_once(tmp_path: Path) -> None:
    """Switching Ship/Show/Ask off leaves the App bypass and the tier secrets behind; MANUAL
    says so once, on the run that removed the files, and never again."""
    repo = _repo(tmp_path, "node")
    _adopt(repo, "--tiers", "yes")
    _set_cfg(repo, codeowners=["@alice"])
    _adopt(repo, "--tiers", "yes")
    _commit(repo, "adopted with tiers")
    out = _sections(_adopt(repo, "--tiers", "no").stdout)
    manual = [m for m in out["MANUAL"] if "bypass actors" in m]
    assert len(manual) == 1, out["MANUAL"]
    for name in (
        "CODE_MANAGER_APP_CLIENT_ID",
        "CODE_MANAGER_APP_PRIVATE_KEY",
        "SDLC_SLACK_BOT_TOKEN",
        "SDLC_COOWNER",
    ):
        assert name in manual[0], name
    again = _sections(_adopt(repo, "--tiers", "no").stdout)
    assert again["WROTE"] == []
    assert not any("bypass actors" in m for m in again["MANUAL"])


def test_tiers_no_keeps_files_in_keep_and_hand_written_ones(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    _adopt(repo, "--tiers", "yes")
    _set_cfg(repo, codeowners=["@alice"], keep=[".github/workflows/ship-show-ask.yml"])
    _adopt(repo, "--tiers", "yes")
    (repo / "scripts/ship_show_ask.py").write_text("# the repo's own classifier\n")
    (repo / ".github/tiers.json").write_text('{"order": ["ask", "show", "ship"]}\n')
    _commit(repo, "own tier files")
    out = _sections(_adopt(repo, "--tiers", "no").stdout)
    for rel in (
        ".github/workflows/ship-show-ask.yml",
        "scripts/ship_show_ask.py",
        ".github/tiers.json",
    ):
        assert (repo / rel).exists(), rel
    assert ".github/workflows/ship-show-ask.yml (sdlc.json keep)" in out["KEPT"]
    assert "scripts/ship_show_ask.py (hand-written, not adopt's)" in out["KEPT"]
    assert ".github/tiers.json (hand-written, not adopt's)" in out["KEPT"]
    # The generated CODEOWNERS went, so the ruleset note fires once.
    assert not (repo / ".github/CODEOWNERS").exists()
    assert sum("bypass actors" in m for m in out["MANUAL"]) == 1


def test_tiers_no_on_a_repo_without_tier_files_prints_no_ruleset_note(tmp_path: Path) -> None:
    out = _sections(_adopt(_repo(tmp_path, "node"), "--tiers", "no").stdout)
    assert not any("bypass actors" in m for m in out["MANUAL"])


@pytest.mark.parametrize(
    "rel,text",
    [
        (".github/workflows/ship-show-ask.yml", "name: ship-show-ask\n"),
        (".github/CODEOWNERS", "# GENERATED by `run-sdlc adopt`\n/k8s/  @alice\n"),
    ],
)
def test_tiers_no_keeps_a_file_without_the_full_generated_header(
    tmp_path: Path, rel: str, text: str
) -> None:
    repo = _repo(tmp_path, "node")
    _adopt(repo, "--tiers", "no")
    (repo / rel).parent.mkdir(parents=True, exist_ok=True)
    (repo / rel).write_text(text)
    _commit(repo, "a tier-like file of the repo's own")
    out = _sections(_adopt(repo, "--tiers", "no").stdout)
    assert (repo / rel).exists()
    assert f"{rel} (hand-written, not adopt's)" in out["KEPT"]


def test_tiers_no_removing_codeowners_prints_a_ruleset_note(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    _adopt(repo, "--tiers", "yes")
    _set_cfg(repo, codeowners=["@alice"])
    _adopt(repo, "--tiers", "yes")
    _commit(repo, "adopted with codeowners")
    out = _sections(_adopt(repo, "--tiers", "no").stdout)
    assert not (repo / ".github/CODEOWNERS").exists()
    assert any("require_code_owner_review" in m for m in out["MANUAL"]), out["MANUAL"]


def test_default_branch_comes_from_the_remote_when_origin_head_is_unset(tmp_path: Path) -> None:
    # `gh repo create --push` leaves no refs/remotes/origin/HEAD; only `git clone` sets it.
    repo = _repo(tmp_path, "node")
    env = _env()
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True, env=env)
    subprocess.run(["git", "branch", "-qm", "main"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=repo, check=True, env=env)
    subprocess.run(["git", "push", "-q", "origin", "main"], cwd=repo, check=True, env=env)
    assert _adopt(repo, "--preset", "node").returncode == 0
    assert json.loads((repo / "sdlc.json").read_text())["defaultBranch"] == "main"


DECISION_LOG = """---
title: UX decision log
---

# UX decision log

Every answer the owner gives, appended in order.

| Date | Decision | Answer | By whom |
| --- | --- | --- | --- |
| 2026-09-28 | Round-1 A-001: adopt the design system | Accept | Owner |

## 2026-09-29 Owner Survey Answers

Calvin answered all of them.

### DEC-01 · Use HubSpot first

**Replaced on 2026-10-11 by 2026-10-11 LeadHub hosts no signup form (owner):** no form.

- **Question:** who owns signup intake?

### DEC-02 · Who may export leads

- Partner admins.
- One bullet. Replaced by 2026-10-11 LeadHub hosts no signup form (owner): only this bullet.

## 2026-10-11 LeadHub hosts no signup form (owner)

HubSpot is the only signup.

## 2026-10-12 Settled by Claude: rows keep their hover

Superseded by IG-3**: nobody can resolve this one.
"""


def test_splits_an_appended_decision_log_into_one_file_per_decision(tmp_path: Path) -> None:
    """`cct:ux-decision-log` appended every answer to one log: 2,910 lines in a real repo,
    read whole for one answer. adopt splits it into one ADR per decision, links
    what replaced what, writes the index, and leaves a pointer that a second run ignores."""
    repo = _repo(tmp_path, "node")
    (repo / "docs" / "ux").mkdir(parents=True)
    (repo / "docs" / "ux" / "decisions.md").write_text(DECISION_LOG)
    nested = repo / "docs" / "designs" / "2026" / "2026-09"
    nested.mkdir(parents=True)
    (nested / "2026-09-01-spec-old.md").write_text("---\ntitle: Old spec\nstatus: shipped\n---\n")
    out = _sections(_adopt(repo).stdout)

    designs = repo / "docs" / "designs"
    files = {p.stem: p.read_text() for p in designs.rglob("*-adr-*.md")}
    assert sorted(files) == [
        "2026-09-28-adr-round-1-a-001",
        "2026-09-29-adr-dec-01-use-hubspot-first",
        "2026-09-29-adr-dec-02-who-may-export-leads",
        "2026-10-11-adr-leadhub-hosts-no-signup-form-owner",
        "2026-10-12-adr-settled-by-claude-rows-keep-their",
    ]
    # The designs folder already nests by year-month, so the new files do too.
    assert (
        designs / "2026" / "2026-10" / "2026-10-11-adr-leadhub-hosts-no-signup-form-owner.md"
    ).is_file()
    dec01 = files["2026-09-29-adr-dec-01-use-hubspot-first"]
    assert "status: superseded" in dec01
    assert "superseded_by: [2026-10-11-adr-leadhub-hosts-no-signup-form-owner]" in dec01
    assert "Calvin answered all of them." in dec01, "the round's lead travels with each child"
    # A replacement inside one bullet amends the decision; the rest of it still holds.
    dec02 = files["2026-09-29-adr-dec-02-who-may-export-leads"]
    assert "status: accepted" in dec02
    assert "amended_by: [2026-10-11-adr-leadhub-hosts-no-signup-form-owner]" in dec02
    new = files["2026-10-11-adr-leadhub-hosts-no-signup-form-owner"]
    assert "decided_by: owner" in new
    assert "2026-09-29-adr-dec-01-use-hubspot-first" in new and "2026-09-29-adr-dec-02" in new
    assert "decided_by: claude" in files["2026-10-12-adr-settled-by-claude-rows-keep-their"]
    assert any("link by hand" in m and "IG-3" in m for m in out["MANUAL"])

    index = (designs / "INDEX.md").read_text()
    assert "[Old spec](2026/2026-09/2026-09-01-spec-old.md) · shipped" in index
    replaced = index.split("## Replaced")[1]
    assert "DEC-01" in replaced and "DEC-02" not in replaced
    log = (repo / "docs" / "ux" / "decisions.md").read_text()
    assert "(moved)" in log and "## " not in log

    # Idempotent: the pointer holds no decisions, so nothing moves twice.
    assert _sections(_adopt(repo).stdout)["WROTE"] == []


def test_adopt_copies_marks_script_verbatim(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "python")
    assert _adopt(repo).returncode == 0
    source = ADOPT.parents[1] / "templates/scripts/marks.py"
    assert (repo / "scripts/marks.py").read_bytes() == source.read_bytes()


def test_template_tests_commit_with_an_identity() -> None:
    """2026-10-27: a guardrail test ran `git commit` with no identity and failed on every CI
    runner of every repo refreshed to that kit, while passing on every laptop."""
    tests = SCRIPTS.parent / "templates" / "tests"
    bare = [
        f"{path.name}:{n}"
        for path in sorted(tests.glob("*"))
        if path.is_file()
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if re.search(r"[\"']commit[\"']|\bcommit -q", line) and "user.email" not in line
    ]
    assert not bare, f"git commit without -c user.name/-c user.email: {bare}"


STEPS = ("lint", "unit", "build", "e2e", "deploy")


def test_ci_paths_defaults_cover_the_six_stacks() -> None:
    defaults = json.loads((SCRIPTS.parent / "templates" / "ci-paths.json").read_text())
    stacks = {"typescript", "python", "rust", "rails", "kotlin", "scala"}
    assert stacks <= set(defaults)
    for name in stacks:
        block = defaults[name]
        assert block["docs"] and block["all"], name
        for step in STEPS:
            assert block[step]["include"], (name, step)
            assert isinstance(block[step]["exclude"], list), (name, step)


@pytest.mark.parametrize(("kind", "stack"), [("node", "typescript"), ("python", "python")])
def test_adopt_writes_ci_paths_once_and_keeps_the_repos_own(
    tmp_path: Path, kind: str, stack: str
) -> None:
    defaults = json.loads((SCRIPTS.parent / "templates" / "ci-paths.json").read_text())
    repo = _repo(tmp_path, kind)
    assert _adopt(repo).returncode == 0
    cfg = json.loads((repo / "sdlc.json").read_text())
    assert cfg["ciPaths"] == defaults[stack]
    cfg["ciPaths"]["unit"]["exclude"].append("mine/*")
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=_env())
    assert _adopt(repo).returncode == 0
    assert "mine/*" in json.loads((repo / "sdlc.json").read_text())["ciPaths"]["unit"]["exclude"]
    cfg.pop("ciPaths")
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=_env())
    res = _adopt(repo)
    assert any("ciPaths added" in w for w in _sections(res.stdout)["WROTE"])
    assert json.loads((repo / "sdlc.json").read_text())["ciPaths"] == defaults[stack]


def test_ci_defaults_name_code_config_specs_and_commands() -> None:
    tpl = SCRIPTS.parent / "templates"
    paths = json.loads((tpl / "ci-paths.json").read_text())
    commands = json.loads((tpl / "ci-commands.json").read_text())
    for name in ("typescript", "python", "rust", "rails", "kotlin", "scala"):
        assert paths[name]["code"] and paths[name]["config"] and paths[name]["specs"], name
        assert {"install", "lint", "unit", "build", "e2e", "e2eTouched"} <= set(commands[name]), (
            name
        )
        assert "{shard}" in commands[name]["e2e"] or "{total}" in commands[name]["e2e"], name


def test_ci_template_changes_script_and_actionlint() -> None:
    res = subprocess.run(
        ["bash", str(SCRIPTS / "test_ci_changes.sh")], capture_output=True, text=True, env=_env()
    )
    assert res.returncode == 0, res.stdout + res.stderr
    if shutil.which("actionlint"):
        tpl = SCRIPTS.parent / "templates" / "ci" / "github-actions.yml"
        lint = subprocess.run(["actionlint", str(tpl)], capture_output=True, text=True)
        assert lint.returncode == 0, lint.stdout


def test_adopt_keeps_verification_local_for_a_repo_without_ci(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "python")
    (repo / ".github/workflows/ci.yml").unlink()
    res = _adopt(repo)
    assert res.returncode == 0, res.stderr
    assert not (repo / ".github/workflows/ci.yml").exists()
    manual = " ".join(_sections(res.stdout)["MANUAL"])
    assert "scripts/ci-local" in manual and "pre-push hook" in manual
    assert "local-ci and decision4" in manual and "never post them by hand" in manual
    cfg = json.loads((repo / "sdlc.json").read_text())
    assert cfg["ciCommands"]["lint"] and cfg["ciCommands"]["e2eTouched"]
    assert _adopt(repo).returncode == 0
    assert not (repo / ".github/workflows/ci.yml").exists()


def test_adopt_preserves_existing_required_ci_during_migration(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    before = (repo / ".github/workflows/ci.yml").read_text()
    res = _adopt(repo)
    manual = " ".join(_sections(res.stdout)["MANUAL"])
    assert "Keep existing required checks until migration is applied" in manual
    assert "GitHub keeps cloud/GitHub work and schedules" in manual
    assert (repo / ".github/workflows/ci.yml").read_text() == before


def test_adopt_adds_missing_ci_path_keys_without_touching_values(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    assert _adopt(repo).returncode == 0
    cfg = json.loads((repo / "sdlc.json").read_text())
    for key in ("code", "config", "specs"):
        cfg["ciPaths"].pop(key)
    cfg["ciPaths"]["docs"] = ["mine/*"]
    cfg["ciCommands"]["lint"] = "make lint"
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=_env())
    res = _adopt(repo)
    assert any("ciPaths gained code, config, specs" in w for w in _sections(res.stdout)["WROTE"])
    got = json.loads((repo / "sdlc.json").read_text())
    assert got["ciPaths"]["docs"] == ["mine/*"] and got["ciCommands"]["lint"] == "make lint"
    assert got["ciPaths"]["code"] and got["ciPaths"]["specs"]


KIT = re.search(r"^  version:\s*(\S+)", (SCRIPTS.parent / "SKILL.md").read_text(), re.M).group(1)


def _stamp(repo: Path, value: str | None) -> None:
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg.pop("sdlcVersion", None)
    if value:
        cfg["sdlcVersion"] = value
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=_env())


def test_adopt_stamps_the_kit_version_on_a_fresh_repo(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    assert _adopt(repo).returncode == 0
    assert json.loads((repo / "sdlc.json").read_text())["sdlcVersion"] == KIT


@pytest.mark.parametrize("old", [None, "3.0.0", "3.2.0"])
def test_upgrade_stamps_and_lists_the_manual_migrations_since_the_old_stamp(
    tmp_path: Path, old: str | None
) -> None:
    repo = _repo(tmp_path, "node")
    assert _adopt(repo).returncode == 0
    _stamp(repo, old)
    res = _adopt(repo, "--upgrade")
    out = _sections(res.stdout)
    assert json.loads((repo / "sdlc.json").read_text())["sdlcVersion"] == KIT
    assert any(f"sdlcVersion {old or 'none'} -> {KIT}" in w for w in out["WROTE"])
    manual = " ".join(out["MANUAL"])
    assert f"upgrade {KIT}" in manual
    assert ("upgrade 3.2.0" in manual) == (old in (None, "3.0.0"))


def test_upgrade_with_the_current_stamp_changes_nothing(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    assert _adopt(repo).returncode == 0
    res = _adopt(repo, "--upgrade")
    assert not any("sdlcVersion" in w for w in _sections(res.stdout)["WROTE"])
    assert not any(m.startswith("upgrade ") for m in _sections(res.stdout)["MANUAL"])


def test_upgrade_does_not_stamp_a_repo_newer_than_the_kit(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    assert _adopt(repo).returncode == 0
    _stamp(repo, "99.0.0")
    res = _adopt(repo, "--upgrade")
    assert json.loads((repo / "sdlc.json").read_text())["sdlcVersion"] == "99.0.0"
    assert "newer than this kit" in " ".join(_sections(res.stdout)["MANUAL"])


def test_sdlc_version_line_for_missing_older_equal_and_newer(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    assert _adopt(repo).returncode == 0
    script = SCRIPTS.parent / "templates" / "scripts" / "sdlc_version.py"

    def line(stamp: str | None) -> str:
        _stamp(repo, stamp)
        return subprocess.run(
            [sys.executable, str(script), str(repo)], capture_output=True, text=True, env=_env()
        ).stdout.strip()

    assert line(None).startswith(
        f"This repo runs sdlc-run none; the kit is {KIT}. Run `adopt --upgrade`"
    )
    older = line("3.0.0")
    assert "runs sdlc-run 3.0.0" in older and "changes: " in older and "3.2.0:" in older
    assert line(KIT) == ""
    assert "newer than the installed kit" in line("99.0.0") and "Update the cct plugin" in line(
        "99.0.0"
    )


def test_ci_blueprint_points_to_local_contract_and_labels_legacy_workflow() -> None:
    text = (SCRIPTS.parent / "references/ci-blueprint.md").read_text()
    assert "[local-first contract](local-first.md)" in text
    assert "local-ci" in text and "decision4" in text
    assert "not the default" in text
    assert "Do not delete an existing required check" in text


def _tree(repo: Path) -> dict[str, bytes | None]:
    """Every path in the repo outside .git (directories too, as None) with its bytes."""
    out: dict[str, bytes | None] = {}
    for p in sorted(repo.rglob("*")):
        rel = p.relative_to(repo)
        if rel.parts[0] == ".git":
            continue
        out[str(rel)] = p.read_bytes() if p.is_file() else None
    return out


def _upgrade_fixture(tmp_path: Path) -> Path:
    """An adopted repo whose kit-owned files differ from the kit's copies, a flat archive that a
    plain adopt would re-nest, an old stamp and checks that a plain adopt would rewrite."""
    repo = _repo(tmp_path, "node")
    assert _adopt(repo).returncode == 0
    fm = (
        "---\nlinear: X-1\ntype: plan\nchange: %s\ndesign: null\nauthor: t@t\n"
        "status: approved\ncreated: 2026-08-11\narchived_at: 2026-08-12\n---\n\n# Plan\n"
    )
    flat = repo / "changes" / "archive" / "2026-08-11-X-1-old"
    flat.mkdir(parents=True)
    (flat / "plan.md").write_text(fm % flat.name)
    for rel in ("scripts/verify_gate.py", "docs/sdlc.md", "tests/sdlc.test.ts", "REVIEW.md"):
        f = repo / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text((f.read_text() if f.exists() else "") + "\n# the repo's own edit\n")
    (repo / ".claude/hooks/gate-bash.sh").write_text("#!/bin/sh\n# hand-tuned\n")
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["sdlcVersion"] = "3.0.0"
    cfg.pop("ciCommands")
    cfg["ciPaths"].pop("code")
    cfg["checks"]["milestone"] = ["pnpm test:e2e --repeat-each 3"]
    (repo / "sdlc.json").write_text(json.dumps(cfg, indent=2) + "\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=_env())
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "drift"],
        cwd=repo,
        check=True,
        env=_env(),
    )
    return repo


def test_upgrade_writes_only_sdlc_json_and_lists_the_rest_for_review(tmp_path: Path) -> None:
    repo = _upgrade_fixture(tmp_path)
    before = _tree(repo)
    before_cfg = json.loads((repo / "sdlc.json").read_text())
    res = _adopt(repo, "--upgrade")
    assert res.returncode == 0, res.stderr
    after = _tree(repo)
    changed = sorted(
        k for k in set(before) | set(after) if before.get(k, "gone") != after.get(k, "gone")
    )
    assert changed == ["sdlc.json"], changed
    cfg = json.loads((repo / "sdlc.json").read_text())
    assert cfg["sdlcVersion"] == KIT and cfg["ciCommands"] and cfg["ciPaths"]["code"]
    # no value the repo set is touched
    assert (
        cfg["checks"] == before_cfg["checks"] and cfg["kitTemplates"] == before_cfg["kitTemplates"]
    )
    out = _sections(res.stdout)
    assert all(w.startswith("sdlc.json") for w in out["WROTE"]), out["WROTE"]
    manual = "\n".join(out["MANUAL"])
    for rel in (
        "scripts/verify_gate.py",
        "docs/sdlc.md",
        "tests/sdlc.test.ts",
        ".claude/hooks/gate-bash.sh",
    ):
        assert f"review diff: {rel} differs from the kit's copy" in manual, rel
    assert "changes/archive/2026-08-11-X-1-old" in manual and "layout migration" in manual
    # git sees the one modified file and nothing new
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, env=_env()
    ).stdout
    assert status.split() == ["M", "sdlc.json"], status


def test_upgrade_dry_run_writes_nothing(tmp_path: Path) -> None:
    repo = _upgrade_fixture(tmp_path)
    before = _tree(repo)
    assert _adopt(repo, "--upgrade", "--dry-run").returncode == 0
    assert _tree(repo) == before


def test_upgrade_replace_shows_the_diff_and_applies_only_the_named_file(tmp_path: Path) -> None:
    repo = _upgrade_fixture(tmp_path)
    before = _tree(repo)
    shown = _adopt(repo, "--upgrade", "--replace", "scripts/verify_gate.py", "--dry-run")
    assert "the repo's own edit" in shown.stdout and "-#-#- DIFF -#-#-" in shown.stdout
    assert _tree(repo) == before
    res = _adopt(repo, "--upgrade", "--apply", "--replace", "scripts/verify_gate.py")
    assert res.returncode == 0, res.stderr
    kit = (ADOPT.parents[1] / "templates/scripts/verify_gate.py").read_bytes()
    assert (repo / "scripts/verify_gate.py").read_bytes() == kit
    after = _tree(repo)
    changed = sorted(
        k for k in set(before) | set(after) if before.get(k, "gone") != after.get(k, "gone")
    )
    assert changed == ["scripts/verify_gate.py", "sdlc.json"], changed
    assert "verify_gate.py (replaced" in " ".join(_sections(res.stdout)["WROTE"])


def test_upgrade_refuses_a_repo_that_is_not_adopted(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    res = _adopt(repo, "--upgrade")
    assert res.returncode != 0 and "not adopted" in res.stderr


def test_upgrade_adds_builders_claude_when_missing(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    assert _adopt(repo).returncode == 0
    cfg = json.loads((repo / "sdlc.json").read_text())
    assert cfg["builders"] == "claude"
    cfg.pop("builders")
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=_env())
    res = _adopt(repo, "--upgrade")
    assert res.returncode == 0, res.stdout + res.stderr
    cfg = json.loads((repo / "sdlc.json").read_text())
    assert cfg["builders"] == "claude"
    assert cfg["builderModel"] == "sonnet"
    assert cfg["builderEffort"] == "high"
    assert any("builders added" in w for w in _sections(res.stdout)["WROTE"])


def test_upgrade_keeps_builders_codex(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    assert _adopt(repo).returncode == 0
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["builders"] = "codex"
    cfg["builderModel"] = "gpt-5.5-codex"
    cfg["builderEffort"] = "xhigh"
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=_env())
    res = _adopt(repo, "--upgrade")
    assert res.returncode == 0, res.stdout + res.stderr
    cfg = json.loads((repo / "sdlc.json").read_text())
    assert (cfg["builders"], cfg["builderModel"], cfg["builderEffort"]) == (
        "codex",
        "gpt-5.5-codex",
        "xhigh",
    )
    assert not any("sdlc-feature-builder" in w for w in _sections(res.stdout)["WROTE"])


def test_codex_builders_without_a_model_get_the_codex_default(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    assert _adopt(repo).returncode == 0
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["builders"] = "codex"
    cfg.pop("builderModel")
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=_env())
    res = _adopt(repo, "--upgrade")
    assert res.returncode == 0, res.stdout + res.stderr
    assert json.loads((repo / "sdlc.json").read_text())["builderModel"] == "gpt-5.5"


def test_an_unknown_builder_effort_stops_adopt(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    assert _adopt(repo).returncode == 0
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["builderEffort"] = "max"
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=_env())
    res = _adopt(repo, "--upgrade")
    assert res.returncode != 0
    assert "builderEffort must be one of" in res.stderr


def test_an_unknown_builders_value_stops_adopt(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    assert _adopt(repo).returncode == 0
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["builders"] = "gpt"
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=_env())
    res = _adopt(repo, "--upgrade")
    assert res.returncode != 0
    assert 'builders must be "claude" or "codex"' in res.stderr


def test_upgrade_keeps_rules(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    assert _adopt(repo).returncode == 0
    cfg = json.loads((repo / "sdlc.json").read_text())
    assert "rules" not in cfg  # optional: the defaults live in the docs, not in the file
    cfg["rules"] = ["CLAUDE.md", "docs/policy.md"]
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=_env())
    for flags in ([], ["--upgrade"]):
        res = _adopt(repo, *flags)
        assert res.returncode == 0, res.stdout + res.stderr
        assert json.loads((repo / "sdlc.json").read_text())["rules"] == cfg["rules"]


def test_rules_must_be_a_list_of_paths(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    assert _adopt(repo).returncode == 0
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["rules"] = "CLAUDE.md"
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=_env())
    res = _adopt(repo, "--upgrade")
    assert res.returncode != 0 and "rules must be a list of repo paths" in res.stderr


def test_adopt_installs_decision4_without_replacing_repo_policy(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "python")
    policy = "version: 1\nentries:\n  - select:\n      paths: ['src/**']\n    floor: Answer\n"
    (repo / "boundary-map.yaml").write_text(policy)
    template = repo / ".github/pull_request_template.md"
    template.write_text("## Team checklist\n- [ ] Human review\n")
    result = _adopt(repo)
    assert result.returncode == 0, result.stderr
    assert (repo / "boundary-map.yaml").read_text() == policy
    assert "## Team checklist\n- [ ] Human review" in template.read_text()
    assert "Decision4 writing rules:" in template.read_text()
    assert "PULL_REQUEST_TEMPLATE.md" not in [p.name for p in (repo / ".github").iterdir()]
    assert not (repo / ".github/scripts/decision4.py").exists()
    assert not (repo / "tests/decision4").exists()
    assert "decision4-check.yml@" in (repo / ".github/workflows/decision4.yml").read_text()
    assert "Decision4 handoff contract (v1)" in (repo / "AGENTS.md").read_text()
    before = template.read_text()
    assert _adopt(repo).returncode == 0
    assert template.read_text() == before
    assert (repo / "boundary-map.yaml").read_text() == policy


def test_adopt_creates_missing_decision4_map_and_keeps_check_invocation(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    runner = repo / "tests/decision4/run.sh"
    runner.parent.mkdir(parents=True)
    runner.write_text("# custom repo gate\n")
    result = _adopt(repo)
    assert result.returncode == 0, result.stderr
    assert "floor: Repair" in (repo / "boundary-map.yaml").read_text()
    assert runner.read_text() == "# custom repo gate\n"
    assert not (repo / ".github/scripts/decision4.py").exists()
    assert (repo / ".github/workflows/decision4.yml").is_file()
    assert "Decision4 writing rules:" in (repo / ".github/PULL_REQUEST_TEMPLATE.md").read_text()
