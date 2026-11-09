"""Fresh evidence, missing rules, secret-path refusal and idempotent issue publication."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def load(name: str, path: Path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


audit = load("tested_harness_audit", HERE / "harness-audit.py")
legacy = load("tested_legacy_guards", HERE / "legacy-guards-test.py")
sync = load("tested_harness_sync", HERE / "sync-harness-audit.py")


class HarnessAudit(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="harness-audit-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "repo"
        self.root.mkdir()
        for source, destination in (
            ("harness-audit.py", "harness-audit"),
            ("legacy-guards-test.py", "legacy-guards-test.py"),
        ):
            self.write("scripts/" + destination, (HERE / source).read_text())
        self.write("fixture.json", "{}\n")
        self.config = {
            "version": 1,
            "owner": "example-owner",
            "default_branch": "main",
            "legacy": [],
            "checks": [
                {
                    "id": "probe",
                    "owner": "example-owner",
                    "kind": "execution",
                    "tools": [[sys.executable, "--version"]],
                    "configs": ["fixture.json"],
                    "rules": ["controlled checker"],
                    "reason": "A fresh controlled test execution",
                }
            ],
        }
        self.write(audit.CONFIG, json.dumps(self.config))
        self.write(
            audit.LOCK,
            json.dumps(
                {
                    "pin": "0" * 40,
                    "version": 1,
                    "repository": audit.SOURCE_REPOSITORY,
                    "source": audit.SOURCE_DIRECTORY,
                    "files": {
                        "scripts/" + name: audit.digest(self.root / "scripts" / name)
                        for name in ("harness-audit", "legacy-guards-test.py")
                    },
                }
            ),
        )
        self.gate(
            "printf 'fresh checker; base=%s\\n' \"$CI_LOCAL_BASE_REF\" > \"$logs/probe.log\"\nprintf 'PASS probe (0s)\\n'\n"
        )
        self.git("init", "-q", "-b", "main")
        self.commit()
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def git(self, *args):
        result = subprocess.run(
            [
                "git",
                "-c",
                "user.name=Audit Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                *args,
            ],
            cwd=self.root,
            env={k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "fixture", "--allow-empty")

    def gate(self, body):
        self.write(
            "scripts/ci-local",
            "#!/bin/bash\nset -euo pipefail\nCHECK_NAMES=(probe)\nCHECK_COMMANDS=('true')\n# END REPO CONFIG\nhead=$(git rev-parse HEAD)\nlogs=$(git rev-parse --absolute-git-dir)/ci-local/$head\nmkdir -p \"$logs\"\n"
            + body,
        )

    def execute(self):
        self.write(audit.CONFIG, json.dumps(self.config))
        self.commit()
        config, checks, gaps = audit.configuration(self.root)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("HARNESS_AUDIT_ACTIVE", None)
            return audit.audit(self.root, config, checks, gaps)

    def test_fresh_execution_binds_head_tree_and_comparison_base(self):
        report = self.execute()
        self.assertEqual(report["gaps"], [])
        self.assertEqual(report["head"], self.git("rev-parse", "HEAD"))
        self.assertEqual(report["tree"], self.git("rev-parse", "HEAD^{tree}"))
        self.assertEqual(report["base_tip"], self.git("rev-parse", "origin/main"))
        self.assertTrue(all(report["checks"][0]["states"].values()))
        self.assertIn(report["base_tip"], (Path(report["artifact"]) / "probe.log").read_text())

    def test_missing_tool_and_unproved_ruleset_are_owned_gaps(self):
        row = self.config["checks"][0]
        row["tools"] = [["nonexistent-audit-tool-xyz", "--version"]]
        row["kind"] = "ruleset"
        report = self.execute()
        states = report["checks"][0]["states"]
        self.assertFalse(states["installed"])
        self.assertFalse(states["applied"])
        self.assertTrue(all(gap["owner"] == "example-owner" for gap in report["gaps"]))

    def test_old_log_cannot_make_a_new_execution_claim(self):
        self.gate("printf 'PASS probe (0s)\\n'\n")
        self.commit()
        head = self.git("rev-parse", "HEAD")
        stale = self.write(f".git/ci-local/{head}/probe.log", "old green result\n")
        os.utime(stale, (1, 1))
        config, checks, gaps = audit.configuration(self.root)
        report = audit.audit(self.root, config, checks, gaps)
        self.assertFalse(report["checks"][0]["states"]["executed"])
        self.assertFalse(report["checks"][0]["states"]["passed"])

    def test_skip_and_empty_suite_are_not_passes(self):
        for text in ("SKIPPED absent scanner", "No test files found", "Checked 0 files"):
            with self.subTest(text=text):
                self.gate(
                    f"printf '%s\\n' '{text}' > \"$logs/probe.log\"\nprintf 'PASS probe (0s)\\n'\n"
                )
                report = self.execute()
                self.assertFalse(report["checks"][0]["states"]["passed"])

    def test_ruleset_requires_actual_refusal_and_allowed_evidence(self):
        row = self.config["checks"][0]
        row["kind"] = "ruleset"
        row["applied"] = {
            "command": "printf 'allowed\\n'",
            "required_output": ["refused", "allowed"],
        }
        self.assertFalse(self.execute()["checks"][0]["states"]["applied"])
        row["applied"]["command"] = "printf 'refused\\nallowed\\n'"
        self.assertTrue(self.execute()["checks"][0]["states"]["applied"])

    def test_dirty_and_recursive_runs_are_refused(self):
        config, checks, gaps = audit.configuration(self.root)
        self.write("untracked.txt", "unverified\n")
        with self.assertRaisesRegex(ValueError, "local edits"):
            audit.audit(self.root, config, checks, gaps)
        with patch.dict(os.environ, {"HARNESS_AUDIT_ACTIVE": "1"}):
            with self.assertRaisesRegex(ValueError, "Recursive"):
                audit.audit(self.root, config, checks, gaps)

    def test_secret_paths_and_escaping_links_are_refused_without_opening_them(self):
        with self.assertRaisesRegex(ValueError, "Withheld"):
            audit.config_hashes(self.root, [".env.local"])
        (self.root / "outside").symlink_to(self.root.parent, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "leaves"):
            audit.safe_path(self.root, "outside/config.json")

    def test_reset_cannot_remove_tracked_product_configuration(self):
        with self.assertRaisesRegex(ValueError, "tracked"):
            audit.reset_caches(self.root, ["fixture.json"])
        self.assertTrue((self.root / "fixture.json").is_file())

    def test_installed_legacy_fixture_engine_on_current_chain_templates(self):
        fixture = self.root / "chain-source"
        for name in ("chain-gate.sh", "sdlc-config.sh"):
            destination = fixture / ".claude/hooks" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(HERE.parent / "templates/hooks" / name, destination)
        self.assertEqual(
            legacy.chain_cases(fixture),
            [
                "chain/" + name
                for name in ("forbidden-edit", "missing-evidence", "stale-lock", "allowed")
            ],
        )

    def test_consumer_config_refusal_fixtures_use_the_canonical_auditor(self):
        source = self.root / "consumer-source"
        for original, copied in (
            ("harness-audit.py", "harness-audit"),
            ("legacy-guards-test.py", "legacy-guards-test.py"),
        ):
            destination = source / "scripts" / copied
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(HERE / original, destination)
        self.assertEqual(
            legacy.config_cases(source),
            ["config/allowed", "config/missing-check", "config/stale-lock"],
        )

    def test_existing_issue_is_updated_once_and_each_gap_owner_is_assigned(self):
        report = self.execute()
        report["gaps"] = [
            {
                "check": "scanner",
                "state": "applied",
                "owner": "scanner-owner",
                "reason": "No refusal proof",
            }
        ]
        calls = []

        def github(argv, root, **kwargs):
            calls.append(argv)
            if argv[1:3] == ["repo", "view"]:
                output = "example/project\n"
            elif argv[1:3] == ["issue", "list"]:
                output = json.dumps([{"number": 7, "title": audit.ISSUE_TITLE, "state": "OPEN"}])
            else:
                output = "https://github.com/example/project/issues/7\n"
            return subprocess.CompletedProcess(argv, 0, output, "")

        with patch.object(audit, "command", side_effect=github):
            audit.update_issue(self.root, report, "example-owner")
        edits = [argv for argv in calls if argv[1:3] == ["issue", "edit"]]
        self.assertEqual(len(edits), 1)
        self.assertFalse(any(argv[1:3] == ["issue", "create"] for argv in calls))
        self.assertIn("scanner-owner", edits[0])
        body = (Path(report["artifact"]) / "issue.md").read_text()
        self.assertIn("**scanner / applied:** Owner @scanner-owner", body)

    def test_sync_dry_run_changes_nothing_and_write_preserves_local_ownership(self):
        target = self.root / "consumer"
        target.mkdir()
        local = target / audit.CONFIG
        local.write_text('{"owner":"local-owner"}\n')
        payloads = {path: b"#!/usr/bin/env python3\n" for path in sync.ASSETS.values()}
        self.assertEqual(len(sync.sync(target, payloads, "0" * 40, False)), 3)
        self.assertFalse((target / "scripts").exists())
        self.assertEqual(len(sync.sync(target, payloads, "0" * 40, True)), 3)
        self.assertEqual(json.loads(local.read_text())["owner"], "local-owner")
        lock = json.loads((target / audit.LOCK).read_text())
        for name, expected in lock["files"].items():
            self.assertEqual(audit.digest(target / name), expected)
            self.assertTrue((target / name).stat().st_mode & 0o111)
        self.assertEqual(sync.sync(target, payloads, "0" * 40, False), [])

    def test_sync_refuses_a_link_before_writing_any_asset(self):
        target = self.root / "consumer"
        (target / "scripts").mkdir(parents=True)
        (target / "scripts/legacy-guards-test.py").symlink_to(self.root / "fixture.json")
        payloads = {path: b"safe fixture\n" for path in sync.ASSETS.values()}
        with self.assertRaisesRegex(ValueError, "linked"):
            sync.sync(target, payloads, "0" * 40, True)
        self.assertFalse((target / "scripts/harness-audit").exists())
        self.assertEqual((self.root / "fixture.json").read_text(), "{}\n")

    def test_legacy_registration_is_an_actual_hook_command_not_a_name_in_permissions(self):
        hook = self.write(".claude/hooks/guard.sh", "#!/bin/sh\nexit 0\n")
        hook.chmod(0o755)
        self.write(
            ".claude/settings.json",
            json.dumps({"hooks": {}, "permissions": {"deny": ["Read(.claude/hooks/guard.sh)"]}}),
        )
        output = self.root / ".git/legacy-evidence"
        output.mkdir()
        (output / "probe.log").write_text("PASS refused\nPASS allowed\n")
        entry = {
            "path": ".claude/hooks/guard.sh",
            "kind": "guard",
            "via": [".claude/settings.json"],
            "via_check": "probe",
            "required_output": ["PASS refused", "PASS allowed"],
            "invoked_by": "PreToolUse",
            "reason": "Fixture guard",
        }
        checks = [{"id": "probe", "states": {"passed": True}}]
        result = audit.legacy_evidence(self.root, entry, output, checks, "example-owner")
        self.assertFalse(result["states"]["configured"])
        self.assertFalse(result["states"]["applied"])
        self.write(
            ".claude/settings.json",
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {"hooks": [{"command": '"$CLAUDE_PROJECT_DIR"/.claude/hooks/guard.sh'}]}
                        ]
                    }
                }
            ),
        )
        self.assertTrue(
            audit.legacy_evidence(self.root, entry, output, checks, "example-owner")["states"][
                "applied"
            ]
        )
        hook.chmod(0o644)
        result = audit.legacy_evidence(self.root, entry, output, checks, "example-owner")
        self.assertFalse(result["states"]["installed"])
        self.assertFalse(result["states"]["applied"])


if __name__ == "__main__":
    unittest.main()
