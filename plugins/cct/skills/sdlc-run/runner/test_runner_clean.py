"""sdlc clean: only shipped copies and exact owned fragments go; everything else stays."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import clean
import pytest

TPL = Path(clean.__file__).resolve().parents[1] / "templates"
# The 3.x hooks and scripts are gone from the plugin; these stand in for shipped files, with their hashes listed as shipped.
KIT_HOOK = b"#!/usr/bin/env bash\n# a shipped 3.x hook\nexit 0\n"
KIT_SCRIPT = b"# a shipped 3.x script\nprint('kit')\n"


@pytest.fixture(autouse=True)
def shipped_hashes(monkeypatch):
    real = clean.kit_hashes()
    real[".claude/hooks/turn-start.sh"] = {clean._h16(KIT_HOOK)}
    real["scripts/verify_gate.py"] = {clean._h16(KIT_SCRIPT)}
    monkeypatch.setattr(clean, "kit_hashes", lambda: real)
HOOK = ".claude/hooks/turn-start.sh"
HOOK_CMD = '"$CLAUDE_PROJECT_DIR"/.claude/hooks/turn-start.sh'


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout


def put(repo: Path, rel: str, text: str | bytes) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text if isinstance(text, bytes) else text.encode())


def commit(repo: Path, msg: str = "3.x install") -> None:
    git(repo, "add", "-A", "-f")
    git(repo, "commit", "-qm", msg)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "t")
    put(tmp_path, "README.md", "# product\n")
    commit(tmp_path, "init")
    return tmp_path


def section_text() -> str:
    tpl = (TPL / "CLAUDE-section.md").read_text()
    tpl = re.sub(r"\{\{#(\w+)\}\}.*?\{\{/\1\}\}\n?", "", tpl, flags=re.S)
    return re.sub(r"\{\{[A-Z_]+\}\}", "value", tpl).strip("\n")


def install_kit(repo: Path) -> None:
    put(repo, HOOK, KIT_HOOK)
    put(
        repo,
        ".claude/settings.json",
        json.dumps(
            {
                "hooks": {
                    "UserPromptSubmit": [
                        {"hooks": [{"type": "command", "command": HOOK_CMD, "timeout": 5}]},
                        {"hooks": [{"type": "command", "command": "./my-own-hook.sh"}]},
                    ]
                }
            },
            indent=2,
        )
        + "\n",
    )
    put(repo, "CLAUDE.md", "# product\n\nOwn rule: be kind.\n\n" + section_text() + "\n")
    put(repo, ".github/workflows/ci.yml", "name: CI\non: [push]\n")
    put(repo, "changes/2026-01-01-x/plan.md", "# plan\n")
    put(repo, "docs/designs/one.md", "# design\n")
    put(repo, ".github/workflows/claude.yml", "name: custom\n")
    commit(repo)


def test_exact_hook_removed(repo: Path) -> None:
    install_kit(repo)
    inv = clean.inventory(repo)
    assert [e["path"] for e in inv["exact"]] == [HOOK]
    clean.apply(repo)
    assert not (repo / HOOK).exists()


def test_edited_script_kept(repo: Path) -> None:
    put(
        repo,
        "scripts/verify_gate.py",
        KIT_SCRIPT + b"# mine\n",
    )
    commit(repo)
    inv = clean.inventory(repo)
    assert [e["path"] for e in inv["edited"]] == ["scripts/verify_gate.py"] and not inv["exact"]
    assert clean.apply(repo)["changed"] is False
    assert (repo / "scripts/verify_gate.py").read_bytes().endswith(b"# mine\n")


def test_settings_only_kit_entry_removed(repo: Path) -> None:
    install_kit(repo)
    clean.apply(repo)
    data = json.loads((repo / ".claude/settings.json").read_text())
    cmds = [h["command"] for g in data["hooks"]["UserPromptSubmit"] for h in g["hooks"]]
    assert cmds == ["./my-own-hook.sh"]


def test_settings_with_only_kit_hooks_is_deleted(repo: Path) -> None:
    put(
        repo,
        ".claude/settings.json",
        json.dumps(
            {
                "hooks": {
                    "Stop": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": '"$CLAUDE_PROJECT_DIR"/.claude/hooks/verify-on-stop.sh',
                                }
                            ]
                        }
                    ]
                }
            }
        ),
    )
    commit(repo)
    clean.apply(repo)
    assert not (repo / ".claude/settings.json").exists()


def test_claude_md_only_block_removed(repo: Path) -> None:
    install_kit(repo)
    clean.apply(repo)
    text = (repo / "CLAUDE.md").read_text()
    assert "Own rule: be kind." in text and clean.HEADING_CLAUDE not in text


def test_native_ci_changes_and_designs_untouched(repo: Path) -> None:
    install_kit(repo)
    inv = clean.inventory(repo)
    assert {"changes/", "docs/designs/", ".github/workflows/ci.yml"} <= {
        p["path"] for p in inv["preserved"]
    }
    clean.apply(repo)
    for rel in (".github/workflows/ci.yml", "changes/2026-01-01-x/plan.md", "docs/designs/one.md"):
        assert (repo / rel).is_file()


def test_unknown_file_kept(repo: Path) -> None:
    install_kit(repo)
    assert ".github/workflows/claude.yml" in [u["path"] for u in clean.inventory(repo)["unknown"]]
    clean.apply(repo)
    assert (repo / ".github/workflows/claude.yml").is_file()


def test_gitignore_and_sdlc_json(repo: Path) -> None:
    put(
        repo,
        ".gitignore",
        "node_modules/\n# verify_gate.py output; lock.json is committed\n/changes/*/verify/\n",
    )
    put(repo, "sdlc.json", json.dumps({"_comment": "Read by the sdlc-run skill, the hooks in .claude/hooks/", "verify": "make test", "tiers": False}))
    commit(repo)
    clean.apply(repo)
    assert (repo / ".gitignore").read_text() == "node_modules/\n"
    assert not (repo / "sdlc.json").exists()


def test_sdlc_json_with_own_keys_left(repo: Path) -> None:
    put(repo, "sdlc.json", json.dumps({"_comment": "Read by the sdlc-run skill", "verify": "make test", "myKey": 1}))
    commit(repo)
    inv = clean.inventory(repo)
    assert not inv["fragments"] and "myKey" in inv["unknown"][0]["reason"]


def test_dry_run_changes_nothing(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    install_kit(repo)
    assert clean.main([str(repo)]) == 0
    out = capsys.readouterr().out
    assert out.rstrip().endswith("DRY RUN: nothing changed (use --apply)") and HOOK in out
    assert git(repo, "status", "--porcelain") == "" and git(repo, "branch", "--list").split() == [
        "*",
        "main",
    ]


def test_apply_one_commit_then_noop(repo: Path) -> None:
    install_kit(repo)
    before = int(git(repo, "rev-list", "--count", "main"))
    res = clean.apply(repo)
    assert res["changed"] and git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip() == "sdlc-clean"
    assert int(git(repo, "rev-list", "--count", "HEAD")) == before + 1
    msg = git(repo, "log", "-1", "--format=%B")
    assert msg.startswith(clean.SUBJECT) and f"- {HOOK}" in msg and "Kept:" in msg
    head = git(repo, "rev-parse", "HEAD")
    assert clean.apply(repo)["changed"] is False
    assert clean.main([str(repo), "--apply"]) == 0
    assert git(repo, "rev-parse", "HEAD") == head and git(repo, "status", "--porcelain") == ""


def test_nothing_to_remove_makes_no_branch(repo: Path) -> None:
    assert clean.apply(repo)["changed"] is False
    assert git(repo, "branch", "--list").split() == ["*", "main"]


def test_dirty_tree_refused(repo: Path) -> None:
    install_kit(repo)
    put(repo, "scratch.txt", "wip")
    with pytest.raises(clean.CleanError, match="not clean"):
        clean.apply(repo)
    assert clean.main([str(repo), "--apply"]) == 0
    assert git(repo, "branch", "--list").split() == ["*", "main"]


def test_sdlc_json_of_only_kit_key_names_but_no_marker_is_kept(repo: Path) -> None:
    put(repo, "sdlc.json", json.dumps({"verify": "make test", "tiers": False}))  # the repo's own file that reuses the names
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "own sdlc.json")
    inv = clean.inventory(repo)
    assert not any(f["path"] == "sdlc.json" for f in inv["fragments"])
    assert any(u["path"] == "sdlc.json" and "no kit marker" in u["reason"] for u in inv["unknown"])


def test_apply_renders_its_report_from_before_the_removal_and_exits_zero(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    install_kit(repo)
    assert clean.main([str(repo), "--apply"]) == 0  # used to crash: FileNotFoundError on the hook it had just deleted
    out = capsys.readouterr().out
    assert f"{HOOK}  [" in out and "would remove the file (3 lines)" in out
    assert "committed on sdlc-clean" in out
    assert not (repo / HOOK).exists() and git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip() == "sdlc-clean"
