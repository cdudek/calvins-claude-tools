"""Exercise the hook through its JSON protocol; publishing commands are never executed."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HOOK = Path(__file__).with_name("local-gate.py")


class LocalGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.repo = self.root / "repo with spaces"
        self.repo.mkdir()
        self.env = dict(
            os.environ,
            GIT_AUTHOR_NAME="test",
            GIT_COMMITTER_NAME="test",
            GIT_AUTHOR_EMAIL="test@example.com",
            GIT_COMMITTER_EMAIL="test@example.com",
        )
        self.git("init", "-q", "-b", "main")
        self.git("commit", "-qm", "initial", "--allow-empty")

    def git(self, *args, cwd=None):
        return subprocess.check_output(
            ["git", "-C", str(cwd or self.repo), *args],
            env=self.env,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()

    def gate(self, package=False):
        if package:
            (self.repo / "package.json").write_text(
                json.dumps({"scripts": {"ci:local": "scripts/check"}})
            )
        else:
            (self.repo / "scripts").mkdir()
            (self.repo / "scripts/ci-local").write_text("#!/bin/sh\nexit 0\n")
        self.git("add", ".")
        self.git("commit", "-qm", "declare gate")

    def marker(self, cwd=None):
        cwd = cwd or self.repo
        common = Path(self.git("rev-parse", "--git-common-dir", cwd=cwd))
        if not common.is_absolute():
            common = cwd / common
        marker = common / "ci-local" / (self.git("rev-parse", "HEAD", cwd=cwd) + ".ok")
        marker.parent.mkdir(exist_ok=True)
        marker.touch()
        return marker

    def run_hook(
        self, command="git push origin main", cwd=None, allowed=False, **payload
    ):
        data = {
            "tool_name": "Bash",
            "cwd": str(cwd or self.repo),
            "tool_input": {"command": command},
            **payload,
        }
        result = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(data),
            text=True,
            capture_output=True,
            env=self.env,
        )
        self.assertEqual(
            result.returncode, 0 if allowed else 2, (command, result.stderr)
        )
        self.assertEqual(result.stdout, "")
        if not allowed:
            self.assertIn("Local gate blocked publication", result.stderr)
        return result

    def test_unrelated_and_quoted_commands(self):
        self.gate()
        for cmd in (
            "git status",
            "gh pr view",
            "gh pr list",
            "echo 'git push'",
            "printf '%s' 'gh pr create'",
            "gh issue create",
            "",
        ):
            with self.subTest(command=cmd):
                self.run_hook(cmd, allowed=True)

    def test_no_gate_allows_dirty_repo(self):
        (self.repo / "file").touch()
        for cmd in ("git push", "gh pr create", "gh pr ready"):
            self.run_hook(cmd, allowed=True)

    def test_package_without_gate(self):
        (self.repo / "package.json").write_text('{"scripts":{"test":"true"}}')
        self.run_hook(allowed=True)

    def test_bad_package_does_not_declare_gate(self):
        for content in ("invalid", "[]", '{"scripts":null}'):
            (self.repo / "package.json").write_text(content)
            self.run_hook(allowed=True)

    def test_not_a_repo(self):
        self.run_hook(cwd=self.root, allowed=True)

    def test_missing_marker(self):
        self.gate()
        result = self.run_hook()
        self.assertIn(
            "Run scripts/ci-local first: no green local run for HEAD "
            + self.git("rev-parse", "HEAD"),
            result.stderr,
        )

    def test_package_gate(self):
        self.gate(package=True)
        self.run_hook()
        self.marker()
        self.run_hook(allowed=True)

    def test_green_clean_head(self):
        self.gate()
        self.marker()
        for cmd in (
            "git push",
            "git push -u origin main",
            "gh pr create --title 'git push; text'",
            "gh pr ready 3",
        ):
            self.run_hook(cmd, allowed=True)

    def test_other_commit_marker_not_valid(self):
        self.gate()
        self.marker()
        self.git("commit", "-qm", "new head", "--allow-empty")
        self.run_hook()

    def test_marker_must_be_file(self):
        self.gate()
        marker = self.marker()
        marker.unlink()
        marker.mkdir()
        self.run_hook()

    def test_tracked_unstaged_staged_deleted_and_untracked_dirty(self):
        self.gate()
        self.marker()
        gate = self.repo / "scripts/ci-local"
        original = gate.read_text()
        gate.write_text(original + "# changed\n")
        self.assertIn("dirty", self.run_hook().stderr)
        self.git("add", ".")
        self.assertIn("dirty", self.run_hook("gh pr create").stderr)
        self.git("reset", "--hard", "-q", "HEAD")
        gate.unlink()
        # Keep gate declaration while testing a deleted tracked file.
        (self.repo / "package.json").write_text('{"scripts":{"ci:local":"true"}}')
        self.assertIn("dirty", self.run_hook("gh pr ready").stderr)
        self.git("reset", "--hard", "-q", "HEAD")
        (self.repo / "package.json").unlink()
        (self.repo / "untracked").touch()
        self.assertIn("dirty", self.run_hook().stderr)

    def test_removing_gate_does_not_bypass_guard(self):
        self.gate()
        self.marker()
        (self.repo / "scripts/ci-local").unlink()
        self.assertIn("dirty", self.run_hook().stderr)

    def test_removing_package_gate_does_not_bypass_guard(self):
        self.gate(package=True)
        self.marker()
        (self.repo / "package.json").write_text('{"scripts":{}}')
        self.assertIn("dirty", self.run_hook().stderr)

    def test_ignored_files_do_not_dirty_worktree(self):
        self.gate()
        self.marker()
        (self.repo / ".git/info/exclude").write_text("ignored\n")
        (self.repo / "ignored").touch()
        self.run_hook(allowed=True)

    def test_subdirectory(self):
        self.gate()
        self.run_hook(cwd=self.repo / "scripts")
        self.marker()
        self.run_hook(cwd=self.repo / "scripts", allowed=True)

    def test_worktree_uses_common_dir_and_own_head(self):
        self.gate()
        worktree = self.root / "linked"
        self.git("worktree", "add", "-qb", "linked", str(worktree))
        self.run_hook(cwd=worktree)
        self.marker(cwd=worktree)
        self.run_hook(cwd=worktree, allowed=True)
        self.git("commit", "--allow-empty", "-qm", "linked change", cwd=worktree)
        self.run_hook(cwd=worktree)
        self.run_hook(allowed=True)
        self.marker(cwd=worktree)
        (worktree / "untracked").touch()
        self.run_hook(cwd=worktree)
        self.run_hook(allowed=True)

    def test_cd_and_git_C_resolve_target_not_hook_cwd(self):
        self.gate()
        for cmd in (
            f'cd "{self.repo}" && git push',
            f'cd -- "{self.repo}" && git push',
            f'git -C "{self.repo}" push',
            f'git -C "{self.root}" -C "{self.repo.name}" push',
            f'cd "{self.repo}"; gh pr ready',
        ):
            self.run_hook(cmd, cwd=self.root)
        self.marker()
        self.run_hook(f'cd "{self.repo}" && gh pr create', cwd=self.root, allowed=True)

    def test_environment_and_command_prefix(self):
        self.gate()
        for cmd in (
            "env EXAMPLE=yes git push",
            "EXAMPLE=yes gh pr create",
            "command git push",
            "/usr/bin/git push",
            "git -c color.ui=false push",
        ):
            self.run_hook(cmd)

    def test_shell_wrapper(self):
        self.gate()
        self.run_hook("bash -lc 'git push'")
        self.marker()
        self.run_hook("sh -c 'gh pr create'", allowed=True)

    def test_later_publication_is_not_hidden_by_exemption(self):
        self.gate()
        for cmd in (
            "git push --tags; git push origin main",
            "git push --delete origin old && gh pr create",
            "echo ok\ngit push",
        ):
            self.run_hook(cmd)

    def test_tags_and_deletions_exempt_even_when_dirty(self):
        self.gate()
        self.git("tag", "v1")
        (self.repo / "dirty").touch()
        for cmd in (
            "git push origin --tags",
            "git push --delete origin old",
            "git push -d origin old",
            "git push origin tag v1",
            "git push origin refs/tags/v1",
            "git push origin +refs/tags/v1:refs/tags/v1",
            "git push origin v1",
            "git push origin HEAD:refs/tags/v2",
            "git push --repo=origin --tags",
            "git push origin :old",
        ):
            self.run_hook(cmd, allowed=True)

    def test_mixed_and_branch_pushes_require_gate(self):
        self.gate()
        self.git("tag", "v1")
        self.git("tag", "main")
        for cmd in (
            "git push origin --tags main",
            "git push origin --follow-tags",
            "git push origin --all",
            "git push origin --mirror",
            "git push origin v1 main",
            "git push origin main",
            "git push origin refs/tags/v1:refs/heads/main",
            "git push --push-option ci.skip origin main",
            "git push --repo origin main --tags",
            "git push --push-option --delete origin main",
        ):
            self.run_hook(cmd)

    def test_gh_global_flags(self):
        self.gate()
        self.run_hook("gh --repo example/project pr create")
        self.run_hook("gh -R example/project pr ready")

    def test_earlier_mutation_cannot_reuse_green_head(self):
        self.gate()
        self.marker()
        for cmd in (
            "git commit --allow-empty -m change && git push",
            "touch new-file; gh pr create",
            "touch new-file; bash -c 'git push'",
        ):
            self.assertIn("separate Bash calls", self.run_hook(cmd).stderr)

    def test_control_flow_and_line_continuation(self):
        self.gate()
        for cmd in (
            "if true; then git push; fi",
            "if gh pr create; then true; fi",
            "while false; do git push; done",
            "git \\\n push",
        ):
            self.run_hook(cmd)

    def test_unborn_head_blocks_declared_gate(self):
        self.gate()
        self.git("checkout", "--orphan", "unborn")
        self.assertIn("HEAD unknown", self.run_hook().stderr)

    def test_invalid_shell_still_respects_gate_declaration(self):
        self.run_hook("git push '", allowed=True)
        self.gate()
        self.run_hook("git push '")

    def test_non_bash_payload(self):
        self.gate()
        self.run_hook(tool_name="Read", allowed=True)

    def test_registration(self):
        hooks = json.loads(HOOK.with_name("hooks.json").read_text())["hooks"][
            "PreToolUse"
        ]
        entry = next(entry for entry in hooks if entry["matcher"] == "Bash")
        self.assertIn(
            'python3 "${CLAUDE_PLUGIN_ROOT}/hooks/local-gate.py"',
            entry["hooks"][0]["command"],
        )

    def test_never_reads_environment_files_or_evaluates_shell(self):
        self.gate(package=True)
        sentinel = self.root / "executed"
        self.run_hook(f'echo $(touch "{sentinel}"); git push')
        self.assertFalse(sentinel.exists())
        spec = importlib.util.spec_from_file_location("local_gate", HOOK)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        original = Path.read_text
        reads = []

        def read(path, *args, **kwargs):
            reads.append(path.name)
            self.assertFalse(path.name.startswith(".env"))
            return original(path, *args, **kwargs)

        with patch.object(Path, "read_text", read):
            with self.assertRaises(module.Blocked):
                module.check(self.repo)
        self.assertEqual(reads, ["package.json"])

    def test_inspection_error_cannot_reuse_marker(self):
        self.gate()
        self.marker()
        spec = importlib.util.spec_from_file_location("local_gate", HOOK)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        original = module.git

        def fail(cwd, *args):
            if args[0] == "status":
                raise ValueError("stubbed git failure")
            return original(cwd, *args)

        with patch.object(module, "git", fail):
            with self.assertRaisesRegex(module.Blocked, "cannot verify"):
                module.check(self.repo)


if __name__ == "__main__":
    unittest.main()
