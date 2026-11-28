import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).parent / "sync-scripts.py"
PLUGIN = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("sync_scripts", HOOK)
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


def repo(tmp_path, files):
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    for name, text in files.items():
        f = tmp_path / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
    return tmp_path


def test_copies_the_scripts_and_template_into_a_factory_repo(tmp_path):
    r = repo(tmp_path, {"changes/2026-11-24-x/plan.md": "# plan\n"})
    msg = sync.sync(r)
    assert msg.startswith("factory: updated .factory/") and "commit it" in msg
    for name, src in sync.FILES.items():
        assert (r / ".factory" / name).read_bytes() == src.read_bytes()
    assert (r / ".factory/kickoff.md").read_text().startswith("@@ top")
    assert (r / ".factory/factory-status.py").is_file() and "factory-status.py" in msg


def test_second_run_is_silent_and_a_drifted_copy_is_restored(tmp_path):
    r = repo(tmp_path, {".factory/check-plan.py": "old\n"})
    assert "check-plan.py" in sync.sync(r)
    assert sync.sync(r) == ""
    (r / ".factory/goal-brief.py").write_text("edited\n")
    msg = sync.sync(r)
    assert "goal-brief.py" in msg and "check-plan.py" not in msg
    assert (r / ".factory/goal-brief.py").read_bytes() == sync.FILES["goal-brief.py"].read_bytes()


def test_a_repo_without_factory_files_is_left_alone(tmp_path):
    r = repo(tmp_path, {"README.md": "x\n"})
    assert sync.sync(r) == "" and not (r / ".factory").exists()
    assert sync.sync(tmp_path / "not-a-repo-dir-that-does-not-exist") == ""


def test_an_old_name_repo_gets_the_migration_hint_and_no_copy(tmp_path):
    r = repo(tmp_path, {f"{sync.old_dir()}/check-plan.py": "old\n", "changes/x/plan.md": "p\n"})
    msg = sync.sync(r)
    assert "migrate-name.py" in msg and str(r) in msg and not (r / ".factory").exists()


def test_the_hook_process_reads_cwd_from_stdin_and_never_fails(tmp_path):
    r = repo(tmp_path, {"changes/x/plan.md": "p\n"})
    p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps({"cwd": str(r)}), capture_output=True, text=True)
    assert p.returncode == 0 and "updated .factory/" in p.stdout and (r / ".factory/task-step.py").exists()
    p = subprocess.run([sys.executable, str(HOOK)], input="not json", capture_output=True, text=True)
    assert p.returncode == 0 and p.stdout == ""


def test_every_copied_file_exists_in_the_plugin_and_the_hook_is_registered():
    assert all(src.exists() for src in sync.FILES.values())
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())["hooks"]
    assert "sync-scripts.py" in json.dumps(hooks["SessionStart"])


def test_inlined_agent_policies_match_their_reference_files():
    """The verifier and ux-verifier cannot resolve references/ paths, so each carries a copy; this keeps the copies from drifting."""
    run = PLUGIN / "skills" / "run" / "references"
    for ref, agent in (("review-policy.md", "verifier.md"), ("ux-checks.md", "ux-verifier.md")):
        agent_text = {ln.lstrip("#").strip() for ln in (PLUGIN / "agents" / agent).read_text().splitlines()}
        body = (run / ref).read_text().split("\n", 2)[2].splitlines()
        missing = [ln for ln in body if ln.strip() and not ln.startswith("Used by") and not ln.startswith("Run by")
                   and ln.lstrip("#").strip() not in agent_text]
        assert missing == [], (agent, missing)
