"""adopt.py renders the chain into a repo; this proves the render, not the chain.

A throwaway git repo per test (node or python by marker file), adopt run on it, then:
every generated file exists, no `{{TOKEN}}` survives, hooks are executable and do what
sdlc.json says, a second run writes nothing, CODEOWNERS is repository-owned.
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
    ".claude/hooks/helper-guard.sh",
    ".claude/hooks/lint-on-edit.sh",
    ".claude/hooks/plan-gate.sh",
    ".claude/hooks/pr-gate.sh",
    ".claude/hooks/session-check.sh",
    ".claude/hooks/turn-start.sh",
    ".claude/hooks/verify-on-stop.sh",
    ".github/tiers.json",
    ".github/workflows/ship-show-ask.yml",
    "scripts/ship_show_ask.py",
    "scripts/verify_gate.py",
    "scripts/marks.py",
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
    # a fresh adoption is on layout 4 (sdlc.json says so), so its first change is too: one spec.md, pinned
    assert sorted(p.name for p in changes[0].iterdir()) == ["decisions.json", "spec.md"]
    assert json.loads((changes[0] / "decisions.json").read_text()) == {"layout": 4}
    spec_md = (changes[0] / "spec.md").read_text()
    assert "## Asks" in spec_md and "## Requirements" in spec_md
    assert f"change: {first}" in spec_md and "linear: none" in spec_md
    assert "scope: S" in spec_md and "ux: none" in spec_md and "<S |" not in spec_md
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


def test_adopt_deletes_a_repo_copy_of_sdlc_status(tmp_path: Path) -> None:
    """sdlc_status.py runs from the plugin; an older adopt copied it into scripts/."""
    repo = _repo(tmp_path, "node")
    (repo / "scripts").mkdir(exist_ok=True)
    stale = repo / "scripts" / "sdlc_status.py"
    stale.write_text("# old copy\n")
    out = _sections(_adopt(repo).stdout)
    assert not stale.exists()
    assert any(
        "scripts/sdlc_status.py (removed: now runs from the plugin)" in w for w in out["WROTE"]
    )
    assert not (repo / "scripts" / "sdlc_status.py").exists() and _adopt(repo).returncode == 0
    assert not stale.exists()


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
    assert any("helper-guard.sh" in c for c in pre), pre  # a helper's heavy call outside the queue
    matchers = {g.get("matcher") for g in settings["hooks"]["PreToolUse"]}
    assert matchers == {"Bash", "Edit|MultiEdit|Write"}, matchers  # MultiEdit is an edit tool: the gate must see it
    # And a second adopt does not append them again.
    _adopt(repo)
    again = json.loads((repo / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert len([h for g in again["hooks"]["PreToolUse"] for h in g["hooks"]]) == len(pre)


def test_dry_run_touches_nothing(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "python")
    out = _sections(_adopt(repo, "--dry-run").stdout)
    assert "sdlc.json" in out["WROTE"]
    assert not (repo / "sdlc.json").exists()


@pytest.mark.parametrize("kind", ["node", "python"])
@pytest.mark.parametrize("tiers", ["yes", "no"])
@pytest.mark.parametrize(
    "contents",
    [
        None,
        "# team routing\n* @team\n",
        "# GENERATED by `run-sdlc adopt` from sdlc.json (codeowners) x .github/tiers.json (ask).\n/k8s/ @alice\n",
    ],
)
def test_adopt_never_manages_codeowners(
    tmp_path: Path, kind: str, tiers: str, contents: str | None
) -> None:
    repo = _repo(tmp_path, kind)
    path = repo / ".github/CODEOWNERS"
    if contents is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
    _adopt(repo, "--tiers", tiers)
    for owners in (["@alice", "@bob"], []):
        _set_cfg(repo, codeowners=owners)
        for args in (("--dry-run",), (), ("--tiers", "no" if tiers == "yes" else "yes")):
            result = _adopt(repo, *args, tiers=None)
            assert result.returncode == 0, result.stderr
            assert path.exists() == (contents is not None)
            if contents is not None:
                assert path.read_bytes() == contents.encode()
            assert not any("CODEOWNERS" in line for line in _sections(result.stdout)["WROTE"])
            assert not any(
                "require_code_owner_review" in line for line in _sections(result.stdout)["MANUAL"]
            )


def test_notify_follows_sdlc_json(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    _adopt(repo)
    _set_cfg(repo, showChannel="C123")
    _adopt(repo)
    ssa = (repo / ".github/workflows/ship-show-ask.yml").read_text()
    assert "notify:" in ssa and 'CHANNEL: "C123"' in ssa


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
    assert (first / "spec.md").exists() and not (first / "plan.md").exists()
    assert "linear: REV-947" in (first / "spec.md").read_text()


def test_migrates_goals_and_claude_plans(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "python")
    env = _env()
    goal = repo / "goals" / "2026-09-05-ai-native-sdlc"
    goal.mkdir(parents=True)
    fm = "---\nlinear: ABC-947\ntype: %s\ngoal: 2026-09-05-ai-native-sdlc\nauthor: t@t\nstatus: approved\ncreated: 2026-09-05\n---\n"
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
    dest = repo / "changes" / "archive" / "2026" / "2026-09" / "2026-09-05-ABC-947-ai-native-sdlc"
    assert dest.is_dir() and not (repo / "goals").exists()
    assert not (dest / "goal.md").exists()
    plan = (dest / "plan.md").read_text()
    assert "## Done" in plan and "make verify exits 0" in plan
    assert "change: 2026-09-05-ABC-947-ai-native-sdlc" in plan and "archived_at:" in plan
    assert (repo / "docs" / "history" / "plans" / "2026-08-01T1200-handover-x.md").exists()
    assert not (repo / ".claude" / "plans").exists()
    # A migrated repo has an archived change, so no adopt-sdlc change is invented on top.
    assert any("migrated" in w for w in out["WROTE"])


def test_adopt_says_when_the_removed_coowner_step_was_in_use_F20(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    _adopt(repo)
    wf = repo / ".github" / "workflows" / "ship-show-ask.yml"
    wf.write_text(wf.read_text() + "      - run: echo ${{ vars.SDLC_COOWNER }}\n")
    notice = [m for m in _sections(_adopt(repo).stdout)["MANUAL"] if "SDLC_COOWNER" in m]
    assert len(notice) == 1 and "CODEOWNERS" in notice[0]
    assert "SDLC_COOWNER" not in wf.read_text()
    assert not [m for m in _sections(_adopt(repo).stdout)["MANUAL"] if "SDLC_COOWNER" in m]


def test_upgrade_tells_a_feature_prs_repo_it_now_delivers_one_milestone_pr(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    _adopt(repo)
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg.update({"delivery": "feature-prs", "milestones": {"merge": "local"}})
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    res = _adopt(repo, "--upgrade")
    assert res.returncode == 0, res.stderr
    notes = [m for m in _sections(res.stdout)["MANUAL"] if "feature-prs" in m]
    assert len(notes) == 1 and "one milestone PR" in notes[0]


def test_upgrade_refuses_while_a_feature_prs_change_is_approved_and_unmerged(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    _adopt(repo)
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "delivery": "feature-prs"}))
    change = next((repo / "changes").glob("*-adopt-sdlc"))
    (change / "lock.json").write_text("{}\n")  # approved, its folder not removed: not merged
    before = (repo / "sdlc.json").read_text()
    res = _adopt(repo, "--upgrade")
    assert res.returncode != 0 and change.name in res.stderr
    assert "finish or re-approve it as one milestone PR first" in res.stderr
    assert (repo / "sdlc.json").read_text() == before
    (change / "lock.json").unlink()  # nothing approved is in flight: only the note
    assert _adopt(repo, "--upgrade").returncode == 0


def test_change_templates_name_the_local_route_F12() -> None:
    tpl = Path(__file__).resolve().parents[1] / "templates" / "change"
    for name in ("plan.md", "milestone.md"):
        assert "local mode" in (tpl / name).read_text(), name
    assert "no `origin/project/<slug>`" in (tpl / "plan.md").read_text()


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


@pytest.mark.parametrize("marker", ["biome.json", "biome.jsonc", "package.json"])
def test_a_biome_repo_gets_its_own_biome_not_prettier(tmp_path: Path, marker: str) -> None:
    """A repo whose formatter is biome (a biome config, or @biomejs/biome in package.json) rejects
    unformatted kit files in its first CI run: adopt runs that biome, and no prettier."""
    repo = _repo(tmp_path, "node")
    if marker == "package.json":
        (repo / marker).write_text('{"devDependencies": {"@biomejs/biome": "2.0.0"}}\n')
    else:
        (repo / marker).write_text("{}\n")
    bin_dir = repo / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)
    for name in ("biome", "prettier"):
        stub = bin_dir / name
        stub.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" >> "$(dirname "$0")/../../{name}-argv.txt"\n')
        stub.chmod(0o755)

    out = _adopt(repo)

    argv = (repo / "biome-argv.txt").read_text().splitlines()
    assert argv[:2] == ["format", "--write"], argv[:3]
    formatted = [a for a in argv if not a.startswith("--") and a != "format"]
    assert any(a.endswith("tests/sdlc.test.ts") for a in formatted) and any(a.endswith("sdlc.json") for a in formatted), formatted
    assert not any(a.endswith((".yml", ".md", ".sh")) for a in formatted), formatted  # biome does not format these
    pretty = [a for a in (repo / "prettier-argv.txt").read_text().splitlines() if not a.startswith("--") and a != "warn"]
    assert pretty and all(a.endswith((".yml", ".yaml", ".md")) for a in pretty), pretty  # prettier keeps the types biome never gets
    assert any(w.startswith("biome format --write on") for w in _sections(out.stdout)["WROTE"])


def test_biome_with_its_formatter_disabled_leaves_everything_to_prettier(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    (repo / "biome.json").write_text('{"formatter": {"enabled": false}, "linter": {"enabled": true}}\n')
    bin_dir = repo / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)
    for name in ("biome", "prettier"):
        stub = bin_dir / name
        stub.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" >> "$(dirname "$0")/../../{name}-argv.txt"\n')
        stub.chmod(0o755)
    _adopt(repo)
    assert not (repo / "biome-argv.txt").exists()
    assert any(a.endswith("tests/sdlc.test.ts") for a in (repo / "prettier-argv.txt").read_text().splitlines())


def test_a_biome_repo_without_biome_installed_is_left_alone(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    (repo / "biome.json").write_text("{}\n")
    out = _adopt(repo)
    assert out.returncode == 0, out.stderr
    assert not any("biome" in w or "prettier" in w for w in _sections(out.stdout)["WROTE"])


def _worktree_with_main_prettier(tmp_path: Path, lock_in_worktree: str) -> tuple[Path, Path]:
    """A node repo whose main checkout has prettier installed (and a lockfile), and a linked worktree without node_modules."""
    repo = _repo(tmp_path, "node")
    (repo / "package-lock.json").write_text('{"lock": 1}\n')
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=_env())
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "lock"], cwd=repo, check=True, env=_env())
    bin_dir = repo / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)
    stub = bin_dir / "prettier"
    stub.write_text('#!/bin/sh\nprintf "%s\\n" "$@" >> "$(dirname "$0")/../../prettier-argv.txt"\n')
    stub.chmod(0o755)
    wt = tmp_path / "wt"
    subprocess.run(["git", "worktree", "add", "-q", "-b", "feat", str(wt)], cwd=repo, check=True, env=_env())
    (wt / "package-lock.json").write_text(lock_in_worktree)
    return repo, wt


def test_a_worktree_without_node_modules_uses_the_main_checkouts_formatter_when_the_lockfile_is_the_same(tmp_path: Path) -> None:
    repo, wt = _worktree_with_main_prettier(tmp_path, '{"lock": 1}\n')
    out = _adopt(wt)
    assert out.returncode == 0, out.stderr
    argv = (repo / "prettier-argv.txt").read_text().splitlines()
    assert any(a.endswith("tests/sdlc.test.ts") for a in argv) and any(w.startswith("prettier --write on") for w in _sections(out.stdout)["WROTE"])


def test_a_worktree_with_another_lockfile_prints_the_format_command_instead(tmp_path: Path) -> None:
    repo, wt = _worktree_with_main_prettier(tmp_path, '{"lock": 2}\n')
    out = _adopt(wt)
    assert out.returncode == 0, out.stderr
    assert not (repo / "prettier-argv.txt").exists()
    line = next(m for m in _sections(out.stdout)["MANUAL"] if "prettier is not installed in this worktree" in m)
    assert "run `prettier --write " in line and "tests/sdlc.test.ts" in line


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


def _adopt_knowing(repo: Path, texts: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    """adopt with `texts` (workflow name -> content) added to its list of kit workflow versions."""
    code = (
        "import hashlib, sys\n"
        f"sys.path.insert(0, {str(ADOPT.parent)!r}); sys.argv = ['adopt.py', *{[*args, '--tiers', 'yes']!r}]\n"
        "import adopt\n"
        f"for n, t in {texts!r}.items():\n"
        "    adopt.KIT_WORKFLOWS[n].add(hashlib.sha256(adopt.workflow_shape(t).encode()).hexdigest()[:16])\n"
        "sys.exit(adopt.main())\n"
    )
    return subprocess.run([sys.executable, "-c", code], cwd=repo, capture_output=True, text=True, env=_env())


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
    kit_texts = {n: "name: old\n" for n in ("claude-review.yml", "claude.yml", "ci-triage.yml")}
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
        res = _adopt_knowing(repo, kit_texts, *flag)
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
    assert "CODE_MANAGER_APP" not in docs
    assert "`ask` needs a human" not in (repo / "CLAUDE.md").read_text()
    for rel in ("docs/sdlc.md", "CLAUDE.md"):
        text = (repo / rel).read_text()
        assert not TOKEN.search(text), f"{rel}: unrendered {TOKEN.search(text).group(0)}"
    manual = "\n".join(_sections(result.stdout)["MANUAL"])
    for word in ("CODE_MANAGER_APP", "SDLC_SLACK_BOT_TOKEN", "code_owner", "App"):
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
    assert not (repo / ".github/CODEOWNERS").exists()
    assert not any("bypass actors" in m for m in out["MANUAL"])


def test_tiers_no_on_a_repo_without_tier_files_prints_no_ruleset_note(tmp_path: Path) -> None:
    out = _sections(_adopt(_repo(tmp_path, "node"), "--tiers", "no").stdout)
    assert not any("bypass actors" in m for m in out["MANUAL"])


@pytest.mark.parametrize(
    "rel,text",
    [
        (".github/workflows/ship-show-ask.yml", "name: ship-show-ask\n"),
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


def test_adopt_copies_the_heavy_work_scripts_verbatim(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "python")
    assert _adopt(repo).returncode == 0
    for name in ("heavy.py", "db.py", "evidence.py", "preflight.py", "capture.py"):
        source = ADOPT.parents[1] / "templates/scripts" / name
        assert (repo / "scripts" / name).read_bytes() == source.read_bytes(), name


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


def test_adopt_names_required_checks_as_the_gate_for_a_repo_without_ci(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "python")
    (repo / ".github/workflows/ci.yml").unlink()
    res = _adopt(repo)
    assert res.returncode == 0, res.stderr
    assert not (repo / ".github/workflows/ci.yml").exists()
    manual = " ".join(_sections(res.stdout)["MANUAL"])
    assert "required checks are the merge gate" in manual
    assert "ci-local" not in manual and "local-ci" not in manual
    cfg = json.loads((repo / "sdlc.json").read_text())
    assert cfg["ciCommands"]["lint"] and cfg["ciCommands"]["e2eTouched"]
    assert _adopt(repo).returncode == 0
    assert not (repo / ".github/workflows/ci.yml").exists()


def test_adopt_preserves_existing_required_ci(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    before = (repo / ".github/workflows/ci.yml").read_text()
    res = _adopt(repo)
    manual = " ".join(_sections(res.stdout)["MANUAL"])
    assert "Keep existing required checks" in manual
    assert "required checks are the merge gate" in manual
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
    assert "required checks are the gate" in text
    assert "local-ci" not in text and "ci-local" not in text
    assert "do not delete an existing required check" in text


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
    shown = _adopt(repo, "--upgrade", "--replace", "tests/sdlc.test.ts", "--dry-run")
    assert "the repo's own edit" in shown.stdout and "-#-#- DIFF -#-#-" in shown.stdout
    assert _tree(repo) == before
    res = _adopt(repo, "--upgrade", "--apply", "--replace", "tests/sdlc.test.ts")
    assert res.returncode == 0, res.stderr
    assert "the repo's own edit" not in (repo / "tests/sdlc.test.ts").read_text()
    after = _tree(repo)
    changed = sorted(
        k for k in set(before) | set(after) if before.get(k, "gone") != after.get(k, "gone")
    )
    assert changed == ["sdlc.json", "tests/sdlc.test.ts"], changed
    assert "sdlc.test.ts (replaced" in " ".join(_sections(res.stdout)["WROTE"])


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


def _classify(cfg: dict, repo: Path, *cmd: str) -> str:
    heavy = ADOPT.parents[1] / "templates/scripts/heavy.py"
    out = subprocess.run(
        [sys.executable, str(heavy), "classify", "--", *cmd], cwd=repo, capture_output=True, text=True, env=_env()
    )
    return out.stdout.strip()


def test_adopt_seeds_heavy_patterns_from_the_milestone_checks_and_ci_commands(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "python")
    assert _adopt(repo).returncode == 0
    cfg = json.loads((repo / "sdlc.json").read_text())
    patterns = cfg["heavy"]["patterns"]
    assert patterns and all("ruff" not in p and "mypy" not in p for p in patterns), patterns
    # the suite the repo's own milestone check runs now queues, lint never does
    assert _classify(cfg, repo, "sh", "-c", "uv run pytest -q --ignore=e2e") == "heavy"
    assert _classify(cfg, repo, "sh", "-c", "uv run pytest e2e --splits 4 --group 1 --reruns 1") == "heavy"
    assert _classify(cfg, repo, "sh", "-c", "uv run ruff check .") == "light"
    assert _classify(cfg, repo, "uv", "run", "pytest", "tests/test_one.py") == "light"


def test_adopt_never_overwrites_heavy_patterns_and_seeds_a_repo_that_has_none(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "python")
    assert _adopt(repo).returncode == 0
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["heavy"] = {"patterns": ["my-own-suite"], "slots": 2}
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=_env())
    assert _adopt(repo, "--upgrade").returncode == 0
    assert json.loads((repo / "sdlc.json").read_text())["heavy"] == {"patterns": ["my-own-suite"], "slots": 2}

    cfg["heavy"] = {"slots": 2}  # the key's other settings stay; patterns arrive
    cfg["checks"]["milestone"] = ["pnpm lint", "sh scripts/run-suite.sh {id}", {"name": "api", "run": "make verify-api"}]
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=_env())
    res = _adopt(repo, "--upgrade")
    assert res.returncode == 0, res.stdout + res.stderr
    heavy = json.loads((repo / "sdlc.json").read_text())["heavy"]
    assert heavy["slots"] == 2 and any("run\\-suite" in p for p in heavy["patterns"]), heavy
    assert any("heavy.patterns added" in w for w in _sections(res.stdout)["WROTE"])
    assert _classify(cfg, repo, "sh", "-c", "sh scripts/run-suite.sh 2026-x") == "heavy"
    assert _classify(cfg, repo, "pnpm", "lint") == "light"


def test_adopt_seeds_nothing_when_the_classifier_already_knows_every_suite(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    assert _adopt(repo).returncode == 0
    assert "heavy" not in json.loads((repo / "sdlc.json").read_text())


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


def test_adopt_installs_advisory_decision4_and_never_a_gate(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "python")
    policy = "version: 1\nentries:\n  - select: {paths: ['src/**']}\n    floor: Answer\n"
    (repo / "boundary-map.yaml").write_text(policy)
    template = repo / ".github/pull_request_template.md"
    template.write_text("## Team checks\n- [ ] Human review\n")
    result = _adopt(repo)
    assert result.returncode == 0, result.stderr
    assert (repo / "boundary-map.yaml").read_text() == policy
    body = template.read_text()
    assert body.startswith("## Team checks\n- [ ] Human review\n")
    assert "## How hard is it to undo this PR after merging?" in body
    assert "## Decision record" in body and "advisory" in body
    assert "PULL_REQUEST_TEMPLATE.md" not in [p.name for p in (repo / ".github").iterdir()]
    agents = (repo / "AGENTS.md").read_text()
    assert "## Decision4: how hard is this change to undo?" in agents
    assert "Nothing blocks a merge on it" in agents
    assert "§7" not in agents and "put-right" not in agents
    assert "@AGENTS.md" in (repo / "CLAUDE.md").read_text()
    assert not (repo / ".github/workflows/decision4.yml").exists()
    assert not (repo / "scripts/decision4-shared.sh").exists()
    assert "decision4" not in " ".join(_sections(result.stdout)["MANUAL"]).replace("Decision4", "")
    before = (body, agents)
    assert _adopt(repo).returncode == 0
    assert (template.read_text(), (repo / "AGENTS.md").read_text()) == before


def test_adopt_creates_the_starter_map_and_pr_template(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    assert _adopt(repo).returncode == 0
    assert "floor: Undo" in (repo / "boundary-map.yaml").read_text()
    assert "Decision record" in (repo / ".github/PULL_REQUEST_TEMPLATE.md").read_text()
    assert not (repo / ".github/workflows/decision4.yml").exists()


# The hooks read goal state and block history through two helpers that sit beside them; a hook
# without goal_active.py blocks (F15), so adopt must ship both.
HOOK_HELPERS = ("goal_active.py", "block_state.py")
TEMPLATE_HOOKS = Path(__file__).resolve().parents[1] / "templates" / "hooks"


def test_adopt_copies_the_hook_helpers_F15(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    assert _adopt(repo).returncode == 0
    for name in HOOK_HELPERS:
        copied = repo / ".claude" / "hooks" / name
        assert copied.is_file(), name
        assert copied.read_text() == (TEMPLATE_HOOKS / name).read_text(), name
    # an older copy is refreshed, not kept
    stale = repo / ".claude" / "hooks" / "goal_active.py"
    stale.write_text("# old copy\n")
    out = _sections(_adopt(repo).stdout)
    assert stale.read_text() == (TEMPLATE_HOOKS / "goal_active.py").read_text()
    assert any("goal_active.py" in w for w in out["WROTE"]), out["WROTE"]


def test_a_second_adopt_leaves_the_hook_helpers_untouched_F15(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "python")
    _adopt(repo)
    hooks = repo / ".claude" / "hooks"
    before = {p.name: p.read_bytes() for p in hooks.iterdir()}
    assert set(HOOK_HELPERS) <= set(before)
    second = _sections(_adopt(repo).stdout)
    assert second["WROTE"] == [], second["WROTE"]
    assert {p.name: p.read_bytes() for p in hooks.iterdir()} == before


def test_the_ignore_allow_list_keeps_the_python_helpers_F15(tmp_path: Path) -> None:
    """A global ignore of `.claude/**` is why adopt writes `!.claude/hooks/*.sh`; the helpers
    are `.py` and need their own line, or they work on one laptop and vanish from the commit."""
    repo = _repo(tmp_path, "node")
    (repo / ".git" / "info" / "exclude").write_text(".claude/**\n")  # stands in for a global ignore

    def ignored(rel: str) -> bool:
        return (
            subprocess.run(["git", "check-ignore", "-q", rel], cwd=repo, env=_env()).returncode == 0
        )

    assert ignored(".claude/hooks/goal_active.py"), "the fixture must hide the helpers"
    assert _adopt(repo).returncode == 0
    lines = (repo / ".gitignore").read_text().splitlines()
    assert "!.claude/hooks/*.sh" in lines and "!.claude/hooks/*.py" in lines, lines
    for rel in (".claude/hooks/gate-bash.sh", *(f".claude/hooks/{n}" for n in HOOK_HELPERS)):
        assert not ignored(rel), rel
    before = (repo / ".gitignore").read_text()
    assert _sections(_adopt(repo).stdout)["WROTE"] == []
    assert (repo / ".gitignore").read_text() == before  # one allow-list, not two


GENERATED_D4 = """name: Decision4
on:
  pull_request:
    types: [opened, edited, synchronize, reopened]
concurrency:
  group: decision4-${{ github.event.pull_request.number }}
  cancel-in-progress: true
permissions:
  contents: read
  pull-requests: read
jobs:
  decision4:
    uses: example-org/blueprints/.github/workflows/decision4-check.yml@770383e955d0b66199f13bbae0e825aa9fface08 # shared Decision4 v1
"""


def _commit_all(repo: Path) -> None:
    env = _env()
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=env)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "old"],
        cwd=repo, check=True, env=env,
    )  # fmt: skip


def test_adopt_keeps_a_decision4_workflow_that_only_mentions_blueprints_F3(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path, "node")
    wf = repo / ".github" / "workflows" / "decision4.yml"
    wf.write_text("name: mine\n# see example-org/blueprints/docs\njobs:\n  mine:\n    runs-on: x\n")
    (repo / ".decision4.lock").write_text("mine\n")
    _commit_all(repo)
    assert _adopt(repo).returncode == 0
    assert wf.exists() and (repo / ".decision4.lock").exists()


def test_adopt_honours_keep_for_the_generated_decision4_files_F3(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    _adopt(repo)
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["keep"] = [*cfg.get("keep", []), ".github/workflows/decision4.yml"]
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    wf = repo / ".github" / "workflows" / "decision4.yml"
    wf.write_text(GENERATED_D4)
    (repo / ".decision4.lock").write_text("b0b2060\n")
    _commit_all(repo)
    assert _adopt(repo).returncode == 0
    assert wf.exists() and (repo / ".decision4.lock").exists()


def test_adopt_removes_a_generated_decision4_workflow_only(tmp_path: Path) -> None:
    """3.17.0: Decision4 has been advisory (no workflow) since 3.12.0, but adopt left the generated
    workflow behind and it kept failing on every PR event. adopt takes it and its lock out (git
    rm); a decision4.yml that calls neither shared checker is the repo's own and stays."""
    repo = _repo(tmp_path, "node")
    env = _env()
    wf = repo / ".github" / "workflows" / "decision4.yml"
    wf.write_text(GENERATED_D4)
    (repo / ".decision4.lock").write_text("b0b2060\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=env)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "old"],
        cwd=repo,
        check=True,
        env=env,
    )
    res = _adopt(repo)
    assert res.returncode == 0, res.stdout + res.stderr
    assert not wf.exists() and not (repo / ".decision4.lock").exists()
    assert any("decision4.yml (removed" in w for w in _sections(res.stdout)["WROTE"])
    assert (repo / "boundary-map.yaml").exists(), "the advisory map stays"

    wf.write_text("name: Decision4\njobs:\n  mine:\n    runs-on: ubuntu-latest\n")
    assert _adopt(repo).returncode == 0
    assert wf.exists(), "a repo's own workflow is not ours to delete"


def test_adopt_reports_a_milestone_list_without_the_full_e2e_and_keeps_the_presets_repeat(
    tmp_path: Path,
) -> None:
    """Review finding 1: a repo with an E2E suite and no full E2E entry gets a MANUAL line (adopt
    never re-locks), and the preset's own x3 repeat is not rewritten as a whole-suite repeat."""
    repo = _upgrade_fixture(tmp_path)
    (repo / "e2e").mkdir()
    (repo / "e2e" / "a.spec.ts").write_text("x")
    preset = json.loads((SCRIPTS.parent / "templates/presets/node.json").read_text())
    repeat = next(
        c for c in preset["checks"]["milestone"] if isinstance(c, dict) and c["name"] == "e2e-repeat"
    )
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["checks"]["milestone"] = ["pnpm test", repeat]
    (repo / "sdlc.json").write_text(json.dumps(cfg, indent=2) + "\n")
    res = _adopt(repo)
    assert res.returncode == 0, res.stderr
    assert any("no full E2E entry" in m for m in _sections(res.stdout)["MANUAL"])
    assert json.loads((repo / "sdlc.json").read_text())["checks"]["milestone"][1] == repeat


def test_the_scoped_e2e_pattern_is_the_same_in_adopt_and_the_gate() -> None:
    find = lambda path: re.search(r"^E2E_SCOPED = re\.compile\(\n(.*?)\n\)", path.read_text(), re.M | re.S).group(1)  # noqa: E731
    assert find(ADOPT) == find(SCRIPTS.parent / "templates/scripts/verify_gate.py")


OLD_REVIEW_SENTENCE = "The review (`cct:review-code-run` with one `review-fix-run` round) runs once per milestone,"
NEW_REVIEW_SENTENCE = (
    "The review (`cct:review-code-run changes <parent> --codex`, then one fix round on its "
    "findings) runs once per milestone,"
)


def test_adopt_migrates_the_old_review_fix_run_sentence_and_keeps_the_custom_rules(tmp_path: Path) -> None:
    """Review finding 17: REVIEW.md is repo-owned and kept, but the one known template sentence
    that starts `review-fix-run` (a second review) is replaced in place."""
    repo = _repo(tmp_path, "node")
    (repo / "REVIEW.md").write_text(
        f"# Review\n\n{OLD_REVIEW_SENTENCE}\non the milestone diff.\n\n## Mine\n\nNever flag semicolons.\n"
    )
    res = _adopt(repo)
    assert res.returncode == 0, res.stderr
    text = (repo / "REVIEW.md").read_text()
    assert NEW_REVIEW_SENTENCE in text and "review-fix-run" not in text
    assert "## Mine\n\nNever flag semicolons." in text
    assert any("REVIEW.md: review-fix-run sentence" in w for w in _sections(res.stdout)["WROTE"])
    again = _sections(_adopt(repo).stdout)
    assert not any("REVIEW.md" in w for w in again["WROTE"])  # idempotent


def test_the_plan_template_does_not_tell_the_closer_to_run_unit_and_e2e_beside_the_gate() -> None:
    plan = " ".join((SCRIPTS.parent / "templates/change/plan.md").read_text().split())
    branch = plan.split("**One milestone**", 1)[1].split("## Goal handover", 1)[0]
    assert "unit, E2E (changed and flaky specs ×3) and" not in branch
    assert "only runner of the full suite" in branch


# 3.20.3: the lists of kit versions come from the history, so an unedited copy is never "customised".
def _hashes_in_history(template: str) -> set[str]:
    """sha256[:16] of every blob `template` has at any commit reachable from HEAD. Not `git log -- path`:
    that prunes a merge whose result matches one parent, and hid the 3.20.0 copy once."""
    import hashlib

    if subprocess.run(["git", "rev-parse", "--is-shallow-repository"], cwd=ADOPT.parent, capture_output=True, text=True).stdout.strip() == "true":
        pytest.skip("a shallow checkout has no history to walk")
    commits = subprocess.run(["git", "rev-list", "HEAD"], cwd=ADOPT.parent, capture_output=True, text=True, check=True).stdout.split()
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=ADOPT.parent, capture_output=True, text=True, check=True).stdout.strip()
    rel = (ADOPT.parents[1] / "templates" / template).relative_to(top).as_posix()
    listing = subprocess.run(
        ["git", "cat-file", "--batch-check"], cwd=top, capture_output=True, text=True, check=True,
        input="".join(f"{c}:{rel}\n" for c in commits),
    ).stdout  # fmt: skip
    blobs = {line.split()[0] for line in listing.splitlines() if line.split()[1:2] == ["blob"]}
    return {
        hashlib.sha256(subprocess.run(["git", "cat-file", "blob", b], cwd=top, capture_output=True, check=True).stdout).hexdigest()[:16]
        for b in blobs
    }


def _listed(name: str) -> set[str]:
    return set(re.findall(r'"([0-9a-f]{16})"', re.search(rf"^{name} = \{{(.*?)\}}", ADOPT.read_text(), re.M | re.S).group(1)))


@pytest.mark.parametrize(
    ("template", "name"),
    [
        ("scripts/spec.py", "KIT_SPEC"),
        ("scripts/heavy.py", "KIT_HEAVY"),
        ("scripts/db.py", "KIT_DB"),
        ("scripts/evidence.py", "KIT_EVIDENCE"),
        ("scripts/preflight.py", "KIT_PREFLIGHT"),
        ("scripts/capture.py", "KIT_CAPTURE"),
        ("hooks/helper-guard.sh", "KIT_HELPER_GUARD"),
    ],
)
def test_the_kit_version_lists_cover_every_shipped_copy_C5(template: str, name: str) -> None:
    import hashlib

    listed = _listed(name)
    missing = _hashes_in_history(template) - listed
    assert not missing, f"{name} lacks {sorted(missing)}: add them (and the next version's hash when {template} changes)"
    now = hashlib.sha256((ADOPT.parents[1] / "templates" / template).read_bytes()).hexdigest()[:16]
    assert now in listed, f"{name} lacks the current {template}: {now}"


def test_upgrade_reports_the_e2e_gap_and_the_old_review_sentence(tmp_path: Path) -> None:
    """`--upgrade` hid two migrations that a plain adopt reports: the repo-specific E2E gap and the
    REVIEW.md sentence that starts a second review."""
    repo = _upgrade_fixture(tmp_path)
    (repo / "e2e").mkdir()
    (repo / "e2e" / "a.spec.ts").write_text("x")
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["checks"]["milestone"] = ["pnpm test"]
    (repo / "sdlc.json").write_text(json.dumps(cfg, indent=2) + "\n")
    (repo / "REVIEW.md").write_text(f"# Review\n\n{OLD_REVIEW_SENTENCE}\non the milestone diff.\n")
    res = _adopt(repo, "--upgrade")
    assert res.returncode == 0, res.stderr
    manual = _sections(res.stdout)["MANUAL"]
    assert any("no full E2E entry" in m for m in manual), manual
    assert any("REVIEW.md" in m and "review-fix-run" in m and NEW_REVIEW_SENTENCE in m for m in manual), manual
    assert (repo / "REVIEW.md").read_text().count("review-fix-run") == 1  # --upgrade writes nothing


def test_a_root_specs_folder_of_living_rules_is_never_moved_into_designs(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    for holds in ("rules/R1.md", "manifest.yaml"):
        f = repo / "specs" / "billing" / holds
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x\n")
    env = _env()
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=env)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "rules"], cwd=repo, check=True, env=env)
    _adopt(repo)
    assert (repo / "specs" / "billing" / "rules" / "R1.md").exists()
    assert not (repo / "docs" / "designs" / "billing").exists()


def test_adopt_installs_spec_py_with_the_gate_scripts(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    _adopt(repo)
    assert (repo / "scripts" / "spec.py").exists()


NEW_KIT_PATHS = [
    "scripts/spec.py",
    "scripts/heavy.py",
    "scripts/db.py",
    "scripts/evidence.py",
    "scripts/preflight.py",
    "scripts/capture.py",
    ".claude/hooks/helper-guard.sh",
]


@pytest.mark.parametrize("rel", NEW_KIT_PATHS)
def test_a_plain_adopt_never_overwrites_a_repos_own_file_at_a_new_kit_path_H2(tmp_path: Path, rel: str) -> None:
    repo = _repo(tmp_path, "node")
    mine = "# the repo's own, uncommitted\n"
    (repo / rel).parent.mkdir(parents=True, exist_ok=True)
    (repo / rel).write_text(mine)
    res = _adopt(repo)
    assert res.returncode == 0, res.stderr
    assert (repo / rel).read_text() == mine
    assert any(rel in m and "not overwritten" in m for m in _sections(res.stdout)["MANUAL"])
    again = _adopt(repo)  # and the second run says the same, writes nothing there
    assert (repo / rel).read_text() == mine
    assert not any(w.startswith(rel) for w in _sections(again.stdout)["WROTE"])


@pytest.mark.parametrize("rel", NEW_KIT_PATHS)
def test_a_plain_adopt_writes_a_new_kit_path_when_free_or_an_unedited_kit_copy_H2(tmp_path: Path, rel: str) -> None:
    repo = _repo(tmp_path, "node")
    assert _adopt(repo).returncode == 0  # the path is free: written
    kit = (ADOPT.parents[1] / "templates" / rel.replace(".claude/hooks/", "hooks/")).read_bytes()
    assert (repo / rel).read_bytes() == kit
    assert _adopt(repo).returncode == 0  # an unedited kit copy: still the kit's
    assert (repo / rel).read_bytes() == kit


# 3.21.0: `--migrate` is the one way across kit versions.
def _fake_gh(tmp_path: Path, head: str, *more: str, open_heads: tuple[str, ...] = ()) -> dict[str, str]:
    """A gh whose merged PRs are the ones from branches `head` and `more` (`gh pr list --head B --state merged`
    answers for exactly the branch asked), and whose open PRs are `open_heads`."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    merged = " ".join((head, *more))
    opened = ",".join(f'{{"headRefName": "{h}"}}' for h in open_heads)
    (bin_dir / "gh").write_text(
        "#!/bin/sh\n"
        'case "$*" in\n'
        '  *"--state merged"*)\n'
        '    while [ $# -gt 0 ]; do [ "$1" = --head ] && b="$2"; shift; done\n'
        f'    for m in {merged}; do [ "$m" = "$b" ] && {{ echo "[{{\\"headRefName\\": \\"$b\\"}}]"; exit 0; }}; done\n'
        "    echo '[]' ;;\n"
        f"  *) echo '[{opened}]' ;;\n"
        "esac\n"
    )
    (bin_dir / "gh").chmod(0o755)
    return {**_env(), "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}


def _oldest_blob(rel: str) -> bytes:
    """The oldest kit version of an installed hook or script, from the history."""
    sub = "hooks" if rel.startswith(".claude/hooks/") else "scripts"
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=ADOPT.parent, capture_output=True, text=True, check=True).stdout.strip()
    path = (ADOPT.parents[1] / "templates" / sub / Path(rel).name).relative_to(top).as_posix()
    commits = subprocess.run(["git", "log", "--format=%H", "--", path], cwd=top, capture_output=True, text=True, check=True).stdout.split()
    if not commits:
        pytest.skip("no history to take an older kit version from")
    return subprocess.run(["git", "show", f"{commits[-1]}:{path}"], cwd=top, capture_output=True, check=True).stdout


def _stamped_3_18(tmp_path: Path) -> Path:
    repo = _repo(tmp_path, "node")
    assert _adopt(repo).returncode == 0
    fm = "---\nlinear: none\ntype: plan\nchange: %s\ndesign: null\nauthor: t@t\nstatus: approved\ncreated: %s\narchived_at: 2026-10-20\n---\n\n# Plan\n"
    for name in ("2026-10-01-merged-one", "2026-10-02-unmerged-one"):
        folder = repo / "changes" / "archive" / "2026" / "2026-10" / name
        folder.mkdir(parents=True)
        (folder / "plan.md").write_text(fm % (name, name[:10]))
    live = repo / "changes" / "2026-11-01-inflight"
    live.mkdir()
    (live / "lock.json").write_text("{}")
    (repo / "scripts/verify_gate.py").write_bytes(_oldest_blob("scripts/verify_gate.py"))
    (repo / "scripts/db.py").write_text("# the repo's own database helper\n")
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["sdlcVersion"] = "3.18.0"
    cfg["keep"] = [".claude/hooks/lint-on-edit.sh"]
    (repo / "sdlc.json").write_text(json.dumps(cfg, indent=2) + "\n")
    (repo / ".claude/hooks/lint-on-edit.sh").write_text("#!/bin/sh\n# the repo's own\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=_env())
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "3.18"], cwd=repo, check=True, env=_env())
    return repo


def test_migrate_brings_a_3_18_repo_to_this_kit_in_one_run(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    env = _fake_gh(tmp_path, "milestone/merged-one-1")
    res = subprocess.run([sys.executable, str(ADOPT), "--migrate", "--tiers", "yes"], cwd=repo, capture_output=True, text=True, env=env)
    assert res.returncode == 0, res.stderr
    kit = ADOPT.parents[1] / "templates"
    # every kit-owned file is the kit's copy, as one set
    assert (repo / "scripts/verify_gate.py").read_bytes() == (kit / "scripts/verify_gate.py").read_bytes()
    assert (repo / "scripts/spec.py").read_bytes() == (kit / "scripts/spec.py").read_bytes()
    assert (repo / ".claude/hooks/pr-gate.sh").read_bytes() == (kit / "hooks/pr-gate.sh").read_bytes()
    # a file the kit did not ship stays untouched and the run says so; no second copy is written
    assert (repo / "scripts/db.py").read_text() == "# the repo's own database helper\n"
    assert not (repo / "scripts/sdlc").exists()
    manual = "\n".join(_sections(res.stdout)["MANUAL"])
    assert "scripts/db.py: a file of your own" in manual
    # a `keep` file stays, with a line
    assert "the repo's own" in (repo / ".claude/hooks/lint-on-edit.sh").read_text()
    assert "lint-on-edit.sh is in sdlc.json `keep`" in manual
    # the merged archive is gone, the one gh cannot confirm stays and is listed
    assert not (repo / "changes/archive/2026/2026-10/2026-10-01-merged-one").exists()
    assert (repo / "changes/archive/2026/2026-10/2026-10-02-unmerged-one").exists()
    assert "2026-10-02-unmerged-one: kept, gh could not confirm" in manual
    # the version is stamped; a change with no unmerged branch is not in flight, so no gate run
    assert json.loads((repo / "sdlc.json").read_text())["sdlcVersion"] != "3.18.0"
    assert "2026-11-01-inflight" not in manual


def test_migrate_keeps_every_archive_when_gh_is_missing(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    bare = tmp_path / "nogh"
    bare.mkdir()
    for tool in ("git", "node"):  # a PATH that has git but no gh
        if found := shutil.which(tool):
            (bare / tool).symlink_to(found)
    env = {**_env(), "PATH": str(bare)}
    res = subprocess.run([sys.executable, str(ADOPT), "--migrate", "--tiers", "yes"], cwd=repo, capture_output=True, text=True, env=env)
    assert res.returncode == 0, res.stderr
    for name in ("2026-10-01-merged-one", "2026-10-02-unmerged-one"):
        assert (repo / "changes/archive/2026/2026-10" / name).exists()
        assert f"{name}: kept, gh could not confirm" in "\n".join(_sections(res.stdout)["MANUAL"])


@pytest.mark.parametrize("gate_file", ["scripts/verify_gate.py", ".claude/hooks/pr-gate.sh", ".claude/hooks/pass_proof.py", "scripts/marks.py"])
def test_replacing_one_gate_file_says_use_migrate_and_writes_nothing(tmp_path: Path, gate_file: str) -> None:
    repo = _upgrade_fixture(tmp_path)
    before = _tree(repo)
    res = _adopt(repo, "--upgrade", "--apply", "--replace", gate_file)
    assert res.returncode != 0 and "--migrate" in res.stderr
    assert _tree(repo) == before


def _migrate(repo: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(ADOPT), "--migrate", "--tiers", "yes", *args], cwd=repo, capture_output=True, text=True, env=env)


def test_migrate_dry_run_changes_nothing(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    before = _tree(repo)
    res = _migrate(repo, _fake_gh(tmp_path, "milestone/merged-one-1"), "--dry-run")
    assert res.returncode == 0, res.stderr
    assert _tree(repo) == before
    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True).stdout
    assert status == ""


def test_migrate_keeps_an_archive_when_the_merged_pr_is_from_another_branch(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    res = _migrate(repo, _fake_gh(tmp_path, "dependabot/npm/left-pad-2026-10-01-merged-one"))
    assert res.returncode == 0, res.stderr
    assert (repo / "changes/archive/2026/2026-10/2026-10-01-merged-one").exists()
    assert "2026-10-01-merged-one: kept, gh could not confirm" in "\n".join(_sections(res.stdout)["MANUAL"])


def test_migrate_removes_tracked_files_only_and_lists_a_folder_with_untracked_files(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    folder = repo / "changes/archive/2026/2026-10/2026-10-01-merged-one"
    (folder / "notes.txt").write_text("not tracked\n")
    res = _migrate(repo, _fake_gh(tmp_path, "milestone/merged-one-1"))
    assert res.returncode == 0, res.stderr
    assert not (folder / "plan.md").exists() and (folder / "notes.txt").read_text() == "not tracked\n"
    assert "2026-10-01-merged-one: kept, untracked files remain" in "\n".join(_sections(res.stdout)["MANUAL"])


def test_migrate_takes_the_branch_from_the_changes_own_decisions(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    folder = repo / "changes/archive/2026/2026-10/2026-10-02-unmerged-one"
    (folder / "decisions.json").write_text('{"project": {"slug": "big-one"}}')
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=_env())
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "d"], cwd=repo, check=True, env=_env())
    res = _migrate(repo, _fake_gh(tmp_path, "project/big-one"))
    assert res.returncode == 0, res.stderr
    assert not folder.exists()


def _commit_everything(repo: Path, message: str = "x") -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=_env())
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", message], cwd=repo, check=True, env=_env())


def test_migrate_keeps_an_archive_a_tracked_file_outside_it_names(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    (repo / "PRODUCT.md").write_text("See changes/archive/2026/2026-10/2026-10-01-merged-one/plan.md for the history.\n")
    _commit_everything(repo)
    res = _migrate(repo, _fake_gh(tmp_path, "milestone/merged-one-1", "milestone/unmerged-one-1"))
    assert res.returncode == 0, res.stderr
    assert (repo / "changes/archive/2026/2026-10/2026-10-01-merged-one/plan.md").exists()
    assert "2026-10-01-merged-one: kept, referenced by PRODUCT.md" in "\n".join(_sections(res.stdout)["MANUAL"])
    assert not (repo / "changes/archive/2026/2026-10/2026-10-02-unmerged-one").exists()  # nothing names this one


def test_a_reference_from_another_removed_archive_does_not_keep_it(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    other = repo / "changes/archive/2026/2026-10/2026-10-02-unmerged-one/plan.md"
    other.write_text(other.read_text() + "\nBuilds on 2026-10-01-merged-one.\n")
    _commit_everything(repo)
    res = _migrate(repo, _fake_gh(tmp_path, "milestone/merged-one-1", "milestone/unmerged-one-1"))
    assert res.returncode == 0, res.stderr
    assert not (repo / "changes/archive/2026/2026-10/2026-10-01-merged-one").exists()
    assert not other.exists()


def _again(tmp_path: Path) -> Path:
    (tmp_path / "again").mkdir()
    return tmp_path / "again"


def test_migrate_adds_the_review_tally_line_when_review_md_lacks_it(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    (repo / "REVIEW.md").write_text("# Review\n\n## Cap the nits\n\nFive at most.\n\n## Do not report\n\n- lockfiles\n")
    _commit_everything(repo)
    res = _migrate(repo, _fake_gh(tmp_path, "milestone/merged-one-1"))
    assert res.returncode == 0, res.stderr
    text = (repo / "REVIEW.md").read_text()
    assert "IMPORTANT: <n>  NITS: <m>" in text
    assert text.index("Five at most.") < text.index("IMPORTANT: <n>") < text.index("## Do not report")
    assert any("REVIEW.md" in w and "tally" in w for w in _sections(res.stdout)["WROTE"])
    again = _migrate(repo, _fake_gh(_again(tmp_path), "milestone/merged-one-1"))
    assert (repo / "REVIEW.md").read_text() == text and again.returncode == 0  # once


def test_migrate_says_so_when_review_md_has_no_place_for_the_tally(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    (repo / "REVIEW.md").write_text("# Review\n\nBe kind.\n")
    _commit_everything(repo)
    res = _migrate(repo, _fake_gh(tmp_path, "milestone/merged-one-1"))
    assert (repo / "REVIEW.md").read_text() == "# Review\n\nBe kind.\n"
    assert any("REVIEW.md" in m and "IMPORTANT: <n>  NITS: <m>" in m for m in _sections(res.stdout)["MANUAL"])


def _lists_kit_scripts(repo: Path) -> None:
    """Three files that list kit scripts for the repo's own tooling, and the new kit script (capture.py) is absent."""
    subprocess.run(["git", "rm", "-q", "scripts/capture.py"], cwd=repo, check=True, env=_env())
    (repo / "pyproject.toml").write_text('[tool.ruff]\nextend-exclude = [\n    "scripts/db.py",\n    "scripts/heavy.py",\n]\n')
    (repo / "Makefile").write_text("GENERATED = \\\n\tscripts/db.py \\\n\tscripts/heavy.py\n")
    (repo / "tests").mkdir(exist_ok=True)
    (repo / "tests/test_kit.py").write_text('KIT_OWNED = ("scripts/db.py", "scripts/heavy.py")\n')
    (repo / "changes/notes.md").write_text('    "scripts/db.py",\n')  # inside changes/: never touched
    _commit_everything(repo)


def test_migrate_adds_a_new_kit_script_to_the_repos_own_lists(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    _lists_kit_scripts(repo)
    res = _migrate(repo, _fake_gh(tmp_path, "milestone/merged-one-1"))
    assert res.returncode == 0, res.stderr
    assert (repo / "pyproject.toml").read_text() == (
        '[tool.ruff]\nextend-exclude = [\n    "scripts/db.py",\n    "scripts/capture.py",\n    "scripts/heavy.py",\n]\n'
    )
    assert (repo / "Makefile").read_text() == "GENERATED = \\\n\tscripts/db.py \\\n\tscripts/capture.py \\\n\tscripts/heavy.py\n"
    assert (repo / "changes/notes.md").read_text() == '    "scripts/db.py",\n'
    assert "scripts/capture.py" not in (repo / "sdlc.json").read_text()
    out = _sections(res.stdout)
    assert any("pyproject.toml" in w and "scripts/capture.py" in w and "scripts/db.py" in w for w in out["WROTE"])
    assert any("tests/test_kit.py" in m and "scripts/capture.py" in m for m in out["MANUAL"])  # an inline tuple it cannot copy
    assert (repo / "tests/test_kit.py").read_text() == 'KIT_OWNED = ("scripts/db.py", "scripts/heavy.py")\n'
    before = (repo / "pyproject.toml").read_text()
    _commit_everything(repo, "migrated")
    assert _migrate(repo, _fake_gh(_again(tmp_path), "milestone/merged-one-1")).returncode == 0
    assert (repo / "pyproject.toml").read_text() == before  # the script is installed now: nothing to add twice


def test_migrate_adds_a_new_kit_script_before_the_last_element_of_a_list(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    subprocess.run(["git", "rm", "-q", "scripts/capture.py"], cwd=repo, check=True, env=_env())
    (repo / "pyproject.toml").write_text('[tool.ruff]\nextend-exclude = [\n    "src/x.py",\n    "scripts/db.py"\n]\n')
    (repo / "tests").mkdir(exist_ok=True)
    (repo / "tests/test_kit.py").write_text('KIT_OWNED = (\n    "tests/a.py",\n    "scripts/db.py"\n)\nONLY = [\n    "scripts/db.py"\n]\nPLAIN = [\n    a\n    scripts/db.py\n]\n')
    _commit_everything(repo)
    res = _migrate(repo, _fake_gh(tmp_path, "milestone/merged-one-1"))
    assert res.returncode == 0, res.stderr
    assert (repo / "pyproject.toml").read_text() == '[tool.ruff]\nextend-exclude = [\n    "src/x.py",\n    "scripts/capture.py",\n    "scripts/db.py"\n]\n'
    assert (repo / "tests/test_kit.py").read_text() == (
        'KIT_OWNED = (\n    "tests/a.py",\n    "scripts/capture.py",\n    "scripts/db.py"\n)\n'
        'ONLY = [\n    "scripts/db.py"\n]\nPLAIN = [\n    a\n    scripts/db.py\n]\n'
    )  # one file takes one insertion: the first list


def test_a_comment_above_the_last_element_keeps_the_list_valid(tmp_path: Path) -> None:
    import ast

    import tomllib

    repo = _stamped_3_18(tmp_path)
    subprocess.run(["git", "rm", "-q", "scripts/capture.py"], cwd=repo, check=True, env=_env())
    (repo / "pyproject.toml").write_text('[tool.ruff]\nextend-exclude = [\n    "src/x.py",\n    # the repo\'s own helper\n    "scripts/db.py"\n]\n')
    (repo / "tests").mkdir(exist_ok=True)
    (repo / "tests/test_kit.py").write_text('KIT = (\n    "tests/a.py",\n    # the repo\'s own helper\n    "scripts/db.py"\n)\n')
    (repo / "trap.toml").write_text('note = """\n"scripts/db.py"\n"""\n')  # a line that looks like an element but is prose
    _commit_everything(repo)
    res = _migrate(repo, _fake_gh(tmp_path, "milestone/merged-one-1"))
    assert res.returncode == 0, res.stderr
    assert tomllib.loads((repo / "pyproject.toml").read_text())["tool"]["ruff"]["extend-exclude"] == ["src/x.py", "scripts/capture.py", "scripts/db.py"]
    assert [n.value for n in ast.walk(ast.parse((repo / "tests/test_kit.py").read_text())) if isinstance(n, ast.Constant)] == ["tests/a.py", "scripts/capture.py", "scripts/db.py"]
    assert "# the repo's own helper\n    \"scripts/db.py\"" in (repo / "pyproject.toml").read_text()  # the comment stays with its element
    assert (repo / "trap.toml").read_text() == 'note = """\n"scripts/db.py"\n"""\n'  # an edit that does not leave a list is not written
    assert any("trap.toml" in m for m in _sections(res.stdout)["MANUAL"])


def test_the_list_editor_skips_make_recipes_symlinks_and_kept_files(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    subprocess.run(["git", "rm", "-q", "scripts/capture.py"], cwd=repo, check=True, env=_env())
    (repo / "Makefile").write_text("build:\n\tscripts/db.py\n")
    outside = tmp_path / "shared-lint.toml"
    outside.write_text('x = [\n    "scripts/db.py",\n]\n')
    (repo / "lint.toml").symlink_to(outside)
    (repo / "kept.toml").write_text('x = [\n    "scripts/db.py",\n]\n')
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["keep"] = [*cfg.get("keep", []), "kept.toml"]
    (repo / "sdlc.json").write_text(json.dumps(cfg, indent=2) + "\n")
    _commit_everything(repo)
    res = _migrate(repo, _fake_gh(tmp_path, "milestone/merged-one-1"))
    assert res.returncode == 0, res.stderr
    assert (repo / "Makefile").read_text() == "build:\n\tscripts/db.py\n"
    assert outside.read_text() == 'x = [\n    "scripts/db.py",\n]\n' and (repo / "lint.toml").is_symlink()
    assert (repo / "kept.toml").read_text() == 'x = [\n    "scripts/db.py",\n]\n'


def test_a_symlink_into_an_archive_keeps_it_and_a_retained_flat_archive_stays_put(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    (repo / "latest.md").symlink_to("changes/archive/2026/2026-10/2026-10-01-merged-one/plan.md")
    flat = repo / "changes/archive/2026-10-03-flat-one"
    flat.mkdir()
    (flat / "plan.md").write_text("---\ncreated: 2026-10-03\n---\n# Plan\n")
    (repo / "PRODUCT.md").write_text("History: changes/archive/2026-10-03-flat-one/plan.md\n")
    _commit_everything(repo)
    res = _migrate(repo, _fake_gh(tmp_path, "milestone/merged-one-1", "milestone/flat-one-1"))
    assert res.returncode == 0, res.stderr
    manual = "\n".join(_sections(res.stdout)["MANUAL"])
    assert (repo / "changes/archive/2026/2026-10/2026-10-01-merged-one/plan.md").exists() and "referenced by latest.md" in manual
    assert (flat / "plan.md").exists() and "2026-10-03-flat-one: not moved" in manual


def test_migrate_upgrades_a_short_tally_line_in_place(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    (repo / "REVIEW.md").write_text("# Review\n\n## Cap the nits\n\nFive.\n\n## Output\n\nTally: `IMPORTANT: <n>  NITS: <m>` please.\n")
    _commit_everything(repo)
    res = _migrate(repo, _fake_gh(tmp_path, "milestone/merged-one-1"))
    assert res.returncode == 0, res.stderr
    assert (repo / "REVIEW.md").read_text() == "# Review\n\n## Cap the nits\n\nFive.\n\n## Output\n\nTally: `IMPORTANT: <n>  NITS: <m>  SHA: <head sha>` please.\n"


def test_migrate_dry_run_reports_the_list_edit_without_making_it(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    _lists_kit_scripts(repo)
    before = (repo / "pyproject.toml").read_text()
    res = _migrate(repo, _fake_gh(tmp_path, "milestone/merged-one-1"), "--dry-run")
    assert (repo / "pyproject.toml").read_text() == before
    assert any("pyproject.toml" in w and "scripts/capture.py" in w for w in _sections(res.stdout)["WROTE"])


@pytest.mark.parametrize(
    ("decisions", "removed"),
    [
        ('{"milestone": "milestone/merged-two"}', True),  # a whole branch name
        ('{"milestone": "merged-two"}', True),  # a bare slug
        ('{"milestone": {"slug": "merged-two"}}', True),
        ('{"milestone": null}', False),  # no slug named: the folder name's slug is unmerged-one
        ('{"milestone": ["merged-two"]}', False),  # unreadable shape: the branch is unknown
        ('{"milestone": {"slug": 7}}', False),
        ('{"project": 7}', False),
        ('["milestone/merged-two"]', False),
    ],
)
def test_migrate_reads_every_shape_decisions_json_has_had_and_never_crashes(tmp_path: Path, decisions: str, removed: bool) -> None:
    repo = _stamped_3_18(tmp_path)
    folder = repo / "changes/archive/2026/2026-10/2026-10-02-unmerged-one"
    (folder / "decisions.json").write_text(decisions)
    _commit_all(repo)
    res = _migrate(repo, _fake_gh(tmp_path, "milestone/merged-two-1"))
    assert res.returncode == 0, res.stderr
    assert (not folder.exists()) is removed
    if not removed:
        assert "2026-10-02-unmerged-one: kept, gh could not confirm" in "\n".join(_sections(res.stdout)["MANUAL"])


def test_migrate_takes_a_feature_branch_the_plan_declares(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    for name, branch in (("2026-10-01-merged-one", "feature/rev-9-merged-one"), ("2026-10-02-unmerged-one", "feature/rev-9-unmerged")):
        plan = repo / "changes/archive/2026/2026-10" / name / "plan.md"
        plan.write_text(plan.read_text() + f"\nbranch: {branch}\n\nHost files come from gh. The dependabot/npm/x branch is not ours.\n")
    _commit_all(repo)
    res = _migrate(repo, _fake_gh(tmp_path, "feature/rev-9-merged-one", "feature/rev-9-unmerged-extra"))
    assert res.returncode == 0, res.stderr
    assert not (repo / "changes/archive/2026/2026-10/2026-10-01-merged-one").exists()
    assert (repo / "changes/archive/2026/2026-10/2026-10-02-unmerged-one").exists()  # a longer name is another branch


def test_migrate_asks_gh_about_each_archives_own_branch_not_a_window_of_recent_prs(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    env = _fake_gh(tmp_path, "milestone/merged-one-1")
    log = tmp_path / "gh.log"
    gh = tmp_path / "bin" / "gh"
    gh.write_text(f"#!/bin/sh\necho \"$@\" >> {log}\n" + gh.read_text().split("\n", 1)[1])
    res = _migrate(repo, env)
    assert res.returncode == 0, res.stderr
    asked = [line for line in log.read_text().splitlines() if "--state merged" in line]
    assert any("--head milestone/merged-one-1 " in line for line in asked) and any("--head milestone/unmerged-one " in line for line in asked)
    assert all("--limit 1" in line for line in asked) and not any(line.startswith("api") for line in log.read_text().splitlines())
    kept = "\n".join(_sections(res.stdout)["MANUAL"])
    assert "2026-10-02-unmerged-one: kept, gh could not confirm a merged PR from 2026-10-02-unmerged-one's own branch (looked for milestone/unmerged-one" in kept


def test_migrate_removes_a_flat_layout_archive_in_the_same_run(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    flat = repo / "changes/archive"
    subprocess.run(["git", "mv", "changes/archive/2026/2026-10/2026-10-01-merged-one", "changes/archive/2026-10-01-merged-one"], cwd=repo, check=True)
    subprocess.run(["git", "mv", "changes/archive/2026/2026-10/2026-10-02-unmerged-one", "changes/archive/2026-10-02-unmerged-one"], cwd=repo, check=True)
    _commit_all(repo)
    res = _migrate(repo, _fake_gh(tmp_path, "milestone/merged-one-1"))
    assert res.returncode == 0, res.stderr
    assert not (flat / "2026-10-01-merged-one").exists()
    assert not list(flat.glob("2026/*/2026-10-01-merged-one"))
    assert (flat / "2026/2026-10/2026-10-02-unmerged-one").exists()  # kept, and nested by the layout migration
    assert "2026-10-01-merged-one: kept" not in "\n".join(_sections(res.stdout)["MANUAL"])


def test_migrate_lists_an_unmerged_branch_but_not_one_whose_pr_merged(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    for branch in ("milestone/inflight-1", "milestone/inflight-2"):
        subprocess.run(["git", "checkout", "-qb", branch], cwd=repo, check=True, env=_env())
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", branch], cwd=repo, check=True, env=_env())
        subprocess.run(["git", "checkout", "-q", "-"], cwd=repo, check=True, env=_env())
    res = _migrate(repo, _fake_gh(tmp_path, "milestone/inflight-1"))
    assert res.returncode == 0, res.stderr
    manual = "\n".join(_sections(res.stdout)["MANUAL"])
    assert "2026-11-01-inflight is in flight on milestone/inflight-2" in manual
    assert "milestone/inflight-1" not in manual


def test_migrate_keeps_a_workflow_that_matches_no_kit_version(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    mine = "name: Claude\non: [issue_comment]\njobs: {}\n"
    (repo / ".github/workflows/claude.yml").write_text(mine)
    res = _migrate(repo, _fake_gh(tmp_path, "milestone/merged-one-1"))
    assert res.returncode == 0, res.stderr
    assert (repo / ".github/workflows/claude.yml").read_text() == mine
    assert any("claude.yml" in m and "matches no kit version" in m for m in _sections(res.stdout)["MANUAL"])


def test_the_kit_workflow_hashes_are_the_shapes_older_kits_wrote(tmp_path: Path) -> None:
    import hashlib

    import adopt

    text = "name: Claude\njobs:\n  c:\n    steps:\n      - uses: a/b@1\n        with:\n          fetch-depth: 1\n\n      - uses: x\n        with:\n          y: z\n      - name: Run Claude Code\n        with:\n          --allowedTools \"Edit,Read\"\n"
    other = text.replace("uses: x", "uses: q").replace("Edit,Read", "Edit")
    assert adopt.workflow_shape(text) == adopt.workflow_shape(other)
    mine = tmp_path / "claude.yml"
    mine.write_text(text)
    assert not adopt.kit_workflow(mine)
    adopt.KIT_WORKFLOWS["claude.yml"].add(hashlib.sha256(adopt.workflow_shape(text).encode()).hexdigest()[:16])
    try:
        assert adopt.kit_workflow(mine)
    finally:
        adopt.KIT_WORKFLOWS["claude.yml"].discard(hashlib.sha256(adopt.workflow_shape(text).encode()).hexdigest()[:16])


def _commit_all(repo: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=_env())
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"], cwd=repo, check=True, env=_env())


def test_migrate_needs_no_preset_and_adds_no_ci_defaults_when_sdlc_json_exists(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg.pop("ciPaths", None)
    cfg.pop("ciCommands", None)
    (repo / "sdlc.json").write_text(json.dumps(cfg, indent=2) + "\n")
    (repo / "package.json").unlink()  # nothing says node or python
    _commit_all(repo)
    res = _migrate(repo, _fake_gh(tmp_path, "milestone/merged-one-1"))
    assert res.returncode == 0, res.stderr
    after = json.loads((repo / "sdlc.json").read_text())
    assert "ciPaths" not in after and "ciCommands" not in after


def test_migrate_keeps_a_kit_owned_file_that_matches_no_kit_version_and_force_kit_replaces_it(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    rel = ".claude/hooks/gate-bash.sh"
    (repo / rel).write_text("#!/usr/bin/env bash\n# hardened by the repo\nexit 0\n")
    _commit_all(repo)
    env = _fake_gh(tmp_path, "milestone/merged-one-1")
    res = _migrate(repo, env)
    assert res.returncode == 0, res.stderr
    assert "hardened by the repo" in (repo / rel).read_text()
    assert any(rel in m and "matches no shipped kit version" in m and f"--force-kit {rel}" in m for m in _sections(res.stdout)["MANUAL"])
    res = _migrate(repo, env, "--force-kit", rel)
    assert res.returncode == 0, res.stderr
    assert (repo / rel).read_bytes() == (ADOPT.parents[1] / "templates/hooks/gate-bash.sh").read_bytes()


def test_the_kit_hashes_cover_every_hook_and_script_the_kit_shipped() -> None:
    import hashlib

    data = json.loads((ADOPT.parent / "kit-hashes.json").read_text())
    for sub, installed in (("hooks", ".claude/hooks"), ("scripts", "scripts")):
        for f in (ADOPT.parents[1] / "templates" / sub).glob("*"):
            if f.is_file():
                assert hashlib.sha256(f.read_bytes()).hexdigest()[:16] in data[f"{installed}/{f.name}"], (
                    f"{installed}/{f.name}: run `python3 kit_hashes.py --write <kit repos>`"
                )
    for rel in (".claude/hooks/pr-gate.sh", "scripts/verify_gate.py"):
        assert _hashes_in_history(("hooks/" if "hooks" in rel else "scripts/") + Path(rel).name) <= set(data[rel])


def test_migrate_names_a_makefile_or_package_script_that_still_runs_the_removed_status_script(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    (repo / "scripts/sdlc_status.py").write_text("# old copy\n")
    (repo / "Makefile").write_text("all:\nGENERATED = scripts/verify_gate.py scripts/sdlc_status.py\n")
    (repo / "package.json").write_text('{\n  "scripts": {\n    "st": "python3 scripts/sdlc_status.py map"\n  }\n}\n')
    _commit_all(repo)
    before = (repo / "Makefile").read_text(), (repo / "package.json").read_text()
    res = _migrate(repo, _fake_gh(tmp_path, "milestone/merged-one-1"))
    assert res.returncode == 0, res.stderr
    manual = "\n".join(_sections(res.stdout)["MANUAL"])
    assert "Makefile:2" in manual and "package.json:3" in manual and "scripts/sdlc_status.py" in manual
    assert not (repo / "scripts/sdlc_status.py").exists()
    assert (repo / "Makefile").read_text() == before[0] and (repo / "package.json").read_text() == before[1]


def test_migrate_lists_only_changes_with_an_unmerged_branch_or_open_pr_and_names_the_branch(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)  # changes/2026-11-01-inflight holds a lock.json
    done = repo / "changes" / "2026-11-02-finished"
    done.mkdir()
    (done / "lock.json").write_text("{}")
    _commit_all(repo)
    subprocess.run(["git", "branch", "milestone/inflight-1"], cwd=repo, check=True, env=_env())
    subprocess.run(["git", "checkout", "-q", "milestone/inflight-1"], cwd=repo, check=True, env=_env())
    (repo / "work.txt").write_text("x")
    _commit_all(repo)
    subprocess.run(["git", "checkout", "-q", "master"], cwd=repo, check=True, env=_env())
    res = _migrate(repo, _fake_gh(tmp_path, "milestone/merged-one-1"))
    assert res.returncode == 0, res.stderr
    manual = "\n".join(_sections(res.stdout)["MANUAL"])
    assert "2026-11-01-inflight" in manual and "milestone/inflight-1" in manual
    assert "python3 scripts/verify_gate.py milestone 2026-11-01-inflight" in manual
    assert "2026-11-02-finished" not in manual


def test_migrate_never_creates_a_change_folder(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    assert _adopt(repo).returncode == 0
    for folder in (repo / "changes").glob("*-adopt-sdlc"):
        shutil.rmtree(folder)
    _commit_all(repo)
    res = _migrate(repo, _fake_gh(tmp_path, "milestone/x-1"))
    assert res.returncode == 0, res.stderr
    assert not list((repo / "changes").glob("*-adopt-sdlc"))


def test_the_installed_guardrail_test_reads_the_docs_path_from_sdlc_json(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "python")
    assert _adopt(repo).returncode == 0
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["docs"] = "documentation/sdlc.md"
    (repo / "sdlc.json").write_text(json.dumps(cfg, indent=2) + "\n")
    assert _adopt(repo).returncode == 0
    assert (repo / "documentation/sdlc.md").is_file()
    test = (repo / "tests/test_sdlc.py").read_text()
    assert 'CFG.get("docs"' in test and '(REPO_ROOT / "docs" / "sdlc.md")' not in test


def test_adopt_flags_migrations_without_a_db_test_block(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    (repo / "db" / "migrations").mkdir(parents=True)
    (repo / "db" / "migrations" / "001.sql").write_text("create table a (id int);")
    (repo / "node_modules" / "x" / "migrations").mkdir(parents=True)
    (repo / "node_modules" / "x" / "migrations" / "0.sql").write_text("-- vendored")
    subprocess.run(["git", "add", "-A", "-f", "."], cwd=repo, check=True, env=_env())
    res = _adopt(repo)
    assert res.returncode == 0, res.stderr
    line = next(m for m in _sections(res.stdout)["MANUAL"] if "db.test" in m)
    for word in ("container", "port", "template", "migrate", "migrations", "db/migrations"):
        assert word in line
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["db"] = {"test": {"container": "c", "port": 55432, "template": "t"}}
    (repo / "sdlc.json").write_text(json.dumps(cfg, indent=2) + "\n")
    again = _adopt(repo)
    assert not any("db.test" in m for m in _sections(again.stdout)["MANUAL"])


def test_adopt_stays_quiet_about_databases_when_the_repo_has_no_migrations(tmp_path: Path) -> None:
    res = _adopt(_repo(tmp_path, "node"))
    assert not any("db.test" in m for m in _sections(res.stdout)["MANUAL"])


# --- 3.24.0: layout 4 is the default for a new adoption, never a silent switch ---------------------


def _layout_manual(out: str) -> list[str]:
    return [m for m in _sections(out).get("MANUAL", []) if '"layout": 4' in m]


def test_a_fresh_adoption_writes_layout_4(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    assert _adopt(repo).returncode == 0
    assert json.loads((repo / "sdlc.json").read_text())["layout"] == 4


@pytest.mark.parametrize("args", [(), ("--upgrade",)])
def test_an_adopted_repo_keeps_its_layout_value(tmp_path: Path, args: tuple[str, ...]) -> None:
    repo = _repo(tmp_path, "node")
    _adopt(repo)
    cfg = json.loads((repo / "sdlc.json").read_text())
    for value in (3, None):
        if value is None:
            cfg.pop("layout")
        else:
            cfg["layout"] = value
        (repo / "sdlc.json").write_text(json.dumps(cfg))
        _adopt(repo, *args)
        assert json.loads((repo / "sdlc.json").read_text()).get("layout") == value


def test_upgrade_offers_the_layout_switch_once_and_only_without_a_layout(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    _adopt(repo)
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg.pop("layout")
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    assert len(_layout_manual(_adopt(repo, "--upgrade").stdout)) == 1
    assert _layout_manual(_adopt(repo).stdout) == []  # plain adopt of an adopted repo says nothing
    cfg["layout"] = 3
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    assert _layout_manual(_adopt(repo, "--upgrade").stdout) == []


def test_a_toml_edit_is_refused_when_it_cannot_be_checked(monkeypatch) -> None:
    """Without tomllib (Python < 3.11) a TOML list edit cannot be validated, so it is not made."""
    import builtins
    import importlib.util

    spec = importlib.util.spec_from_file_location("adopt_mod", Path(__file__).with_name("adopt.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    real = builtins.__import__

    def no_tomllib(name, *a, **k):
        if name == "tomllib":
            raise ImportError(name)
        return real(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", no_tomllib)
    before = 'x = [\n  "scripts/db.py",\n]\n'
    after = 'x = [\n  "scripts/capture.py",\n  "scripts/db.py",\n]\n'
    assert mod.list_still_valid("pyproject.toml", before, after, "scripts/capture.py", "scripts/db.py") is False


def test_migrate_does_not_guess_a_branch_from_paths_in_the_plan_and_reads_the_intake_file(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    folder = repo / "changes/archive/2026/2026-10/2026-10-01-merged-one"
    (folder / "plan.md").write_text((folder / "plan.md").read_text() + "\nWe depend on feature/rev-9-merged-one and src/app/x.\n")
    _commit_all(repo)
    res = _migrate(repo, _fake_gh(tmp_path, "feature/rev-9-merged-one"))
    assert res.returncode == 0, res.stderr
    assert folder.exists()  # a branch the plan merely mentions confirms nothing
    (folder / "state").mkdir()
    (folder / "state" / "intake.json").write_text(json.dumps({"milestone": {"slug": "custom-name"}}))
    (folder / "decisions.json").unlink(missing_ok=True)
    _commit_all(repo)
    res = _migrate(repo, _fake_gh(_again(tmp_path), "milestone/custom-name-1"))
    assert res.returncode == 0, res.stderr
    assert not folder.exists()  # layout 4 keeps its decisions in state/intake.json


def test_migrate_keeps_an_archive_a_keep_file_links_to(tmp_path: Path) -> None:
    repo = _stamped_3_18(tmp_path)
    (repo / "NOTES.md").write_text("see changes/archive/2026/2026-10/2026-10-01-merged-one for why\n")
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "keep": ["NOTES.md"]}))
    _commit_all(repo)
    res = _migrate(repo, _fake_gh(tmp_path, "milestone/merged-one-1"))
    assert res.returncode == 0, res.stderr
    assert (repo / "changes/archive/2026/2026-10/2026-10-01-merged-one").exists()
    assert "referenced by NOTES.md" in "\n".join(_sections(res.stdout)["MANUAL"])


def test_the_formatter_fallback_needs_no_node_modules_and_the_active_managers_lockfile(tmp_path: Path) -> None:
    repo, wt = _worktree_with_main_prettier(tmp_path, '{"lock": 1}\n')
    (wt / "node_modules").mkdir()  # the worktree has dependencies of its own: no borrowing
    out = _adopt(wt)
    assert out.returncode == 0 and not (repo / "prettier-argv.txt").exists()


def test_a_leftover_lockfile_cannot_mask_the_active_one(tmp_path: Path) -> None:
    repo, wt = _worktree_with_main_prettier(tmp_path, '{"lock": 1}\n')  # package-lock.json identical
    (repo / "pnpm-lock.yaml").write_text("a: 1\n")
    (wt / "pnpm-lock.yaml").write_text("a: 2\n")  # the manager in use differs
    (wt / "package.json").write_text('{"packageManager": "pnpm@9.0.0"}\n')
    out = _adopt(wt)
    assert out.returncode == 0 and not (repo / "prettier-argv.txt").exists()
    assert any("prettier is not installed in this worktree" in m for m in _sections(out.stdout)["MANUAL"])


def test_adopt_widens_an_older_chain_gate_matcher_and_the_dogfood_settings_register_multi_edit(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "node")
    _adopt(repo)
    path = repo / ".claude" / "settings.json"
    settings = json.loads(path.read_text(encoding="utf-8"))
    for g in settings["hooks"]["PreToolUse"]:
        if any("chain-gate.sh" in h["command"] for h in g["hooks"]):
            g["matcher"] = "Edit|Write"  # what 3.26.0 and before registered
    path.write_text(json.dumps(settings))
    _adopt(repo)
    again = json.loads(path.read_text(encoding="utf-8"))
    gate = [g["matcher"] for g in again["hooks"]["PreToolUse"] if any("chain-gate.sh" in h["command"] for h in g["hooks"])]
    assert gate == ["Edit|MultiEdit|Write"]
    own = json.loads((Path(__file__).resolve().parents[5] / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert [g["matcher"] for g in own["hooks"]["PreToolUse"] if any("chain-gate.sh" in h["command"] for h in g["hooks"])] == ["Edit|MultiEdit|Write"]
