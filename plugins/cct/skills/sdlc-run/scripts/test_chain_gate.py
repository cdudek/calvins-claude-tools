"""chain-gate.sh, the milestone-process rules: building only inside /goal, and the criteria
locked once the engineer approved. The transcript fixtures pin the undocumented goal_status
entry; if Claude Code changes its shape, these tests are where it shows."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1] / "templates" / "hooks"
ID = "2026-10-09-trial"
PLAN = "---\nstatus: approved\n---\n\n## Goal handover\n\nDeliver feature 1 of change trial.\n"


def _goal(met: bool, sentinel: bool = False) -> dict:
    att = {"type": "goal_status", "met": met, "condition": "Deliver feature 1 of change"}
    if sentinel:
        att["sentinel"] = True
    return {"type": "attachment", "attachment": att}


TRANSCRIPTS = {
    "active": [{"type": "user"}, _goal(False, sentinel=True)],
    "evaluated-not-met": [_goal(False, sentinel=True), {"type": "assistant"}, _goal(False)],
    "met": [_goal(False, sentinel=True), _goal(True)],
    "none": [{"type": "user"}, {"type": "assistant"}],
}


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / ".claude" / "hooks").mkdir(parents=True)
    for name in ("chain-gate.sh", "sdlc-config.sh", "goal_active.py", "block_state.py"):
        if (HOOKS / name).exists():  # the helpers sit beside the hook; absent in older trees
            shutil.copy(HOOKS / name, repo / ".claude" / "hooks" / name)
    (repo / "sdlc.json").write_text(json.dumps({"changesDir": "changes"}))
    change = repo / "changes" / ID
    change.mkdir(parents=True)
    (change / "decisions.json").write_text(
        json.dumps(
            {"size": "M", "kind": "feature", "milestone": {"kind": "single", "slug": "trial"}}
        )
    )
    (change / "intent.md").write_text("---\nstatus: approved\n---\n")
    (change / "facts.md").write_text("---\nstatus: approved\n---\n")
    (change / "plan.md").write_text(PLAN)
    (change / "lock.json").write_text("{}\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    subprocess.run(["git", "init", "-q", "-b", "feat/trial"], cwd=repo, check=True, env=env)
    return repo


def _edit(repo: Path, file: str, transcript: str | None) -> subprocess.CompletedProcess[str]:
    path = ""
    if transcript is not None:
        t = repo.parent / f"{transcript}.jsonl"
        if transcript in TRANSCRIPTS:
            t.write_text("".join(json.dumps(e) + "\n" for e in TRANSCRIPTS[transcript]))
        path = str(t)
    payload = {"tool_input": {"file_path": file}, "transcript_path": path}
    return subprocess.run(
        ["bash", str(repo / ".claude" / "hooks" / "chain-gate.sh")],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(repo)},
    )


@pytest.mark.parametrize("transcript", ["active", "evaluated-not-met"])
def test_source_edit_inside_an_active_goal_is_allowed(repo: Path, transcript: str) -> None:
    assert _edit(repo, "src/app.ts", transcript).returncode == 0


@pytest.mark.parametrize("transcript", ["none", "met"])
def test_source_edit_without_an_active_goal_is_refused(repo: Path, transcript: str) -> None:
    r = _edit(repo, "src/app.ts", transcript)
    assert r.returncode == 2 and "inside /goal" in r.stderr


def test_unreadable_transcript_fails_open_with_a_warning(repo: Path) -> None:
    r = _edit(repo, "src/app.ts", "missing")
    assert r.returncode == 0 and "transcript unreadable" in r.stderr


def test_source_edit_before_the_lock_is_refused(repo: Path) -> None:
    (repo / "changes" / ID / "lock.json").unlink()
    r = _edit(repo, "src/app.ts", "active")
    assert r.returncode == 2 and "verify_gate.py approve" in r.stderr


@pytest.mark.parametrize(
    "file",
    [f"changes/{ID}/facts.md", f"changes/{ID}/done.json", f"changes/{ID}/lock.json", "sdlc.json"],
)
def test_protected_paths_are_refused_after_approval(repo: Path, file: str) -> None:
    r = _edit(repo, file, "active")
    assert r.returncode == 2 and "protectedEdit" in r.stderr
    decisions = repo / "changes" / ID / "decisions.json"
    d = json.loads(decisions.read_text())
    d["protectedEdit"] = "2026-10-09 engineer: 'F3 was wrong, change it'"
    decisions.write_text(json.dumps(d))
    assert _edit(repo, file, "active").returncode == 0


def test_facts_wait_for_the_confirmed_intent(repo: Path) -> None:
    (repo / "changes" / ID / "intent.md").write_text("---\nstatus: draft\n---\n")
    (repo / "changes" / ID / "lock.json").unlink()
    r = _edit(repo, f"changes/{ID}/facts.md", "active")
    assert r.returncode == 2 and "intent.md is not approved" in r.stderr


def test_a_v3_folder_without_milestone_keeps_its_rules(repo: Path) -> None:
    change = repo / "changes" / ID
    (change / "decisions.json").write_text(json.dumps({"size": "M", "kind": "feature"}))
    (change / "plan.md").write_text("---\nstatus: approved\n---\n\n## Goal handover\n\n/goal x\n")
    assert _edit(repo, "src/app.ts", "none").returncode == 0


# Negative fixtures (3.9.0): what the hook must refuse, and the paths it must leave alone.
def test_a_change_folder_without_the_dialog_is_refused(repo: Path) -> None:
    r = _edit(repo, "changes/2026-10-10-other/intent.md", "active")
    assert r.returncode == 2 and "Stage 1.1 dialog has not run" in r.stderr


def test_spec_files_wait_for_the_approved_intent(repo: Path) -> None:
    (repo / "changes" / ID / "intent.md").write_text("---\nstatus: draft\n---\n")
    r = _edit(repo, f"changes/{ID}/spec/ia.md", "active")
    assert r.returncode == 2 and "intent.md is not approved" in r.stderr


@pytest.mark.parametrize(
    "stale",
    [
        ("plan.md", "---\nstatus: draft\n---\n\n## Goal handover\n\nx\n", "not approved yet"),
        ("plan.md", "---\nstatus: approved\n---\n\n## Goal handover\n\n", "empty ## Goal"),
    ],
)
def test_a_lock_over_a_plan_that_moved_does_not_open_the_source(
    repo: Path, stale: tuple[str, str, str]
) -> None:
    name, text, needle = stale
    (repo / "changes" / ID / name).write_text(text)
    r = _edit(repo, "src/app.ts", "active")
    assert r.returncode == 2 and needle in r.stderr


def test_snapshots_are_protected_once_locked(repo: Path) -> None:
    r = _edit(repo, "e2e/__screenshots__/home.png", "active")
    assert r.returncode == 2 and "protectedEdit" in r.stderr


@pytest.mark.parametrize(
    "file",
    [
        "docs/sdlc.md",
        "README.md",
        ".claude/settings.json",
        f"changes/{ID}/validation.md",
        f"changes/{ID}/findings.md",
        "changes/archive/2026/2026-10/2026-10-01-old/facts.md",
    ],
)
def test_permitted_paths_pass_without_a_goal(repo: Path, file: str) -> None:
    assert _edit(repo, file, "none").returncode == 0


def test_a_branch_with_no_change_folder_gets_no_opinion(repo: Path) -> None:
    subprocess.run(["git", "checkout", "-q", "-b", "chore/unrelated"], cwd=repo, check=True)
    assert _edit(repo, "src/app.ts", "none").returncode == 0


READY = "---\nverdict: ready\nstatus: approved\n---\n"
NOT_READY = "---\nverdict: not-ready\nstatus: draft\n---\n"


def _spec_repo(repo: Path, **verdicts: str) -> None:
    """A v3 change whose only open question is the readiness verdict file(s) in spec/."""
    change = repo / "changes" / ID
    skips = {a: "skip -- t" for a in ("brief", "ia", "interaction", "screens", "prototype")}
    (change / "decisions.json").write_text(
        json.dumps({"size": "M", "kind": "feature", "skips": skips})
    )
    (change / "spec").mkdir()
    (change / "plan.md").unlink()
    (change / "lock.json").unlink()
    for name, text in verdicts.items():
        (change / "spec" / f"{name}.md").write_text(text)


@pytest.mark.parametrize(
    ("files", "allowed"),
    [
        ({"readiness": READY}, True),
        ({"validation": READY}, True),  # a folder written before the rename keeps working
        ({"readiness": NOT_READY, "validation": READY}, False),  # the new name wins
        ({"readiness": READY, "validation": NOT_READY}, True),
        ({}, False),
    ],
)
def test_plan_waits_for_a_ready_verdict_under_either_name(
    repo: Path, files: dict[str, str], allowed: bool
) -> None:
    _spec_repo(repo, conformance="# c\n", **files)
    r = _edit(repo, f"changes/{ID}/plan.md", "active")
    assert (r.returncode == 0) == allowed, r.stderr


@pytest.mark.parametrize(
    ("name", "text", "stage"),
    [
        ("readiness", READY, "facts"),
        ("validation", READY, "facts"),  # written before the rename
        ("validation", NOT_READY, "spec-review"),
        (None, "", "spec-review"),
    ],
)
def test_status_reads_the_verdict_under_either_name(
    repo: Path, name: str | None, text: str, stage: str
) -> None:
    _spec_repo(repo)
    change = repo / "changes" / ID
    (change / "decisions.json").write_text(json.dumps({"size": "M", "kind": "feature"}))
    for a in ("brief", "ia", "interaction", "screens", "conformance"):
        (change / "spec" / f"{a}.md").write_text("# x\n")
    (change / "spec" / "prototype").mkdir()
    (change / "spec" / "prototype" / "index.md").write_text("# x\n")
    if name:
        (change / "spec" / f"{name}.md").write_text(text)
    out = subprocess.run(
        ["bash", str(Path(__file__).parent / "status.sh"), ID],
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(repo)},
    ).stdout
    assert stage in out.split("templates=")[1], out


def test_writing_into_the_session_transcripts_is_refused(repo: Path, tmp_path: Path) -> None:
    """3.21.0: the transcript is the evidence for an owner quote, so no Write or Edit may touch
    ~/.claude/projects, whatever the repo or the goal."""
    home = tmp_path / "home"
    target = home / ".claude/projects/some-repo/session.jsonl"
    for file in (str(target), "~/.claude/projects/x.jsonl", str(home / ".claude/projects/../projects/a")):
        payload = {"tool_input": {"file_path": file}, "transcript_path": ""}
        r = subprocess.run(
            ["bash", str(repo / ".claude" / "hooks" / "chain-gate.sh")],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(repo), "HOME": str(home)},
        )
        assert r.returncode == 2 and "session transcripts" in r.stderr, file


def test_the_transcript_guard_holds_in_a_repo_without_sdlc_json(tmp_path: Path) -> None:
    """3.21.0: the guard does not depend on the repo having adopted the chain."""
    home = tmp_path / "home"
    bare = tmp_path / "bare"
    bare.mkdir()
    r = subprocess.run(
        ["bash", str(HOOKS / "chain-gate.sh")],
        input=json.dumps({"tool_input": {"file_path": str(home / ".claude/projects/p/s.jsonl")}}),
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(bare), "HOME": str(home)},
    )
    assert r.returncode == 2 and "session transcripts" in r.stderr


def _visual(repo: Path, allow: list[str] | None = None) -> None:
    (repo / "changes" / ID / "lock.json").write_text('{"screens": "required", "scopeFolders": ["src/screens"]}\n')
    cfg = {"changesDir": "changes"}
    if allow:
        cfg["scopeGuard"] = {"allow": allow}
    (repo / "sdlc.json").write_text(json.dumps(cfg))


@pytest.mark.parametrize(
    "file",
    [
        "db/migrations/0001_add_table.sql",
        "apps/web/migrations/0002.py",
        "drizzle/0003.sql",
        "prisma/schema.prisma",
        "db/migrate/20260101_x.rb",
        "alembic/versions/a1.py",
        "src/auth/session.ts",
        "src/lib/oauth_helper.py",
        "src/permissions/roles.ts",
        "src/app/settings/page.tsx",
        "packages/db/drizzle/0001.sql",
        "services/api/prisma/migrations/1/migration.sql",
        "src/lib/auth.service.ts",
        "src/login.tsx",
        "src/lib/rbac.ts",
        "src/components/acl-list.tsx",
    ],
)
def test_a_visual_change_refuses_data_auth_and_new_pages(repo: Path, file: str) -> None:
    _visual(repo)
    r = _edit(repo, file, "active")
    assert r.returncode == 2
    assert "a visual change does not add data, auth or new pages" in r.stderr
    assert "sdlc-run" in r.stderr


def test_a_visual_change_allows_its_own_folders_and_existing_pages(repo: Path) -> None:
    _visual(repo)
    assert _edit(repo, "src/screens/settings/page.tsx", "active").returncode == 0
    (repo / "src/app").mkdir(parents=True)
    (repo / "src/app/page.tsx").write_text("x")  # an existing route is a restyle, not a new page
    _commit(repo)
    assert _edit(repo, "src/app/page.tsx", "active").returncode == 0
    assert _edit(repo, "src/components/button.tsx", "active").returncode == 0
    assert _edit(repo, "src/components/author.tsx", "active").returncode == 0  # not auth
    assert _edit(repo, "src/components/authorList.tsx", "active").returncode == 0
    for name in ("LoginForm.tsx", "authGuard.ts", "useSession.ts", "permissions/x.ts"):
        assert _edit(repo, f"src/{name}", "active").returncode == 2, name


def _commit(repo: Path) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run([*git, "add", "-A"], check=True, env=env)
    subprocess.run([*git, "commit", "-qm", "c"], check=True, env=env)
    return subprocess.run([*git, "rev-parse", "HEAD"], check=True, env=env, capture_output=True, text=True).stdout.strip()


def test_a_route_staged_after_approval_is_still_new(repo: Path) -> None:
    _visual(repo)
    (repo / "src").mkdir()
    (repo / "src/seed.txt").write_text("x")
    approved = _commit(repo)
    (repo / "changes" / ID / "lock.json").write_text(json.dumps({"screens": "required", "scopeFolders": [], "sha": approved}))
    (repo / "src/app").mkdir(parents=True)
    (repo / "src/app/page.tsx").write_text("x")
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    subprocess.run(["git", "-C", str(repo), "add", "src/app/page.tsx"], check=True, env=env)
    assert _edit(repo, "src/app/page.tsx", "active").returncode == 2  # staged by a scaffolder
    _commit(repo)
    assert _edit(repo, "src/app/page.tsx", "active").returncode == 2  # committed since approval: still new


def test_a_route_that_existed_at_the_approval_commit_is_a_restyle(repo: Path) -> None:
    (repo / "src/app").mkdir(parents=True)
    (repo / "src/app/page.tsx").write_text("x")
    approved = _commit(repo)
    _visual(repo)
    (repo / "changes" / ID / "lock.json").write_text(json.dumps({"screens": "required", "sha": approved}))
    assert _edit(repo, "src/app/page.tsx", "active").returncode == 0


@pytest.mark.parametrize("source", ["none", {"kind": "none"}, ""])
def test_a_visual_source_of_none_is_not_visual_work(repo: Path, source: object) -> None:
    (repo / "changes" / ID / "decisions.json").write_text(json.dumps({"size": "M", "kind": "feature", "milestone": {"kind": "single", "slug": "trial"}, "visualSource": source}))
    assert _edit(repo, "db/migrations/0001.sql", "active").returncode == 0


def test_the_hook_and_the_gate_agree_on_what_a_visual_source_is() -> None:
    import re as _re

    sys.path.insert(0, str(HOOKS.parent / "scripts"))
    import verify_gate

    src = (HOOKS / "chain-gate.sh").read_text()
    ns: dict = {}
    exec(_re.search(r"(def has_visual_source.*?)\n\n\n", src, _re.S)[1], ns)  # noqa: S102
    for v in (None, "", "none", " None ", {}, {"kind": "none"}, "x", {"kind": "images", "path": "a"}, {"path": "a"}, 5):
        assert ns["has_visual_source"](v) == verify_gate.has_visual_source(v), v


def test_the_scope_guard_allow_list_lets_a_path_through(repo: Path) -> None:
    _visual(repo, allow=["prisma/**"])
    assert _edit(repo, "prisma/schema.prisma", "active").returncode == 0
    assert _edit(repo, "drizzle/0003.sql", "active").returncode == 2


def test_a_change_without_visual_work_may_edit_migrations(repo: Path) -> None:
    assert _edit(repo, "db/migrations/0001.sql", "active").returncode == 0


def test_a_malformed_scope_guard_config_fails_closed_not_open(repo: Path) -> None:
    _visual(repo)
    (repo / "sdlc.json").write_text(json.dumps({"changesDir": "changes", "scopeGuard": ["x"]}))
    assert _edit(repo, "prisma/schema.prisma", "active").returncode == 2
    (repo / "sdlc.json").write_text(json.dumps({"changesDir": "changes", "scopeGuard": {"allow": [1, None], "routes": "x"}}))
    assert _edit(repo, "prisma/schema.prisma", "active").returncode == 2
    (repo / "sdlc.json").write_text(json.dumps({"changesDir": "changes", "scopeGuard": {"allow": 5}}))
    assert _edit(repo, "src/auth/x.ts", "active").returncode == 2


def test_an_unreadable_lock_refuses(repo: Path) -> None:
    _visual(repo)
    (repo / "changes" / ID / "lock.json").write_text("{not json")
    r = _edit(repo, "src/components/button.tsx", "active")
    assert r.returncode == 2 and "lock.json cannot be read" in r.stderr


def test_allowed_folders_come_from_the_lock_not_the_plan(repo: Path) -> None:
    _visual(repo)
    (repo / "changes" / ID / "plan.md").write_text(PLAN + "\n## Where things go\n\n- `src/evil/`: x\n")
    assert _edit(repo, "src/evil/page.tsx", "active").returncode == 2
    assert _edit(repo, "src/screens/page.tsx", "active").returncode == 0


def test_a_dotdot_folder_in_the_lock_allows_nothing(repo: Path) -> None:
    _visual(repo)
    (repo / "changes" / ID / "lock.json").write_text('{"screens": "required", "scopeFolders": ["../x", ""]}')
    assert _edit(repo, "src/screens/page.tsx", "active").returncode == 2


@pytest.mark.parametrize("file", ["src/app/layout.mjs", "src/app/route.cjs", "src/app/page.mts"])
def test_more_route_names_and_extensions_count(repo: Path, file: str) -> None:
    _visual(repo)
    assert _edit(repo, file, "active").returncode == 2


def test_routes_are_configurable_and_untracked_means_new(repo: Path) -> None:
    _visual(repo)
    (repo / "sdlc.json").write_text(json.dumps({"changesDir": "changes", "scopeGuard": {"routes": ["**/view.vue"]}}))
    assert _edit(repo, "src/a/view.vue", "active").returncode == 2
    assert _edit(repo, "src/app/page.tsx", "active").returncode == 0  # not a configured route
    (repo / "sdlc.json").write_text(json.dumps({"changesDir": "changes"}))
    (repo / "src/app").mkdir(parents=True)
    (repo / "src/app/page.tsx").write_text("x")  # on disk but never committed: still new
    assert _edit(repo, "src/app/page.tsx", "active").returncode == 2
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    subprocess.run(["git", "-C", str(repo), "add", "src/app/page.tsx"], check=True, env=env)
    assert _edit(repo, "src/app/page.tsx", "active").returncode == 2  # staged is not committed
    _commit(repo)
    assert _edit(repo, "src/app/page.tsx", "active").returncode == 0
