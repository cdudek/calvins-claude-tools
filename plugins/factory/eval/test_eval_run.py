import contextlib
import io
import json
import os
import random
import shutil
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import eval_fixtures as fx
import prepare_task
import run_eval


class Run(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.task, *_ = fx.prepare(self.tmp.name)
        self.results = Path(self.tmp.name) / "results"

    def dry(self, *argv, env=None):
        buf = io.StringIO()
        keep = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_DEFAULT_HAIKU_MODEL")}
        with mock.patch.dict(os.environ, {**keep, **(env or {})}, clear=True), contextlib.redirect_stdout(buf):
            run_eval.main(["--task", str(self.task), "--stage", "grid", "--dry-run", "--results", str(self.results), "--seed", "3", *argv])
        return buf.getvalue()

    def test_dry_run_prints_command_env_and_redacts_the_token(self):
        out = self.dry("--arms", "default", "--parallel", "1", env={"CLAUDE_CODE_OAUTH_TOKEN": "sk-secret-123"})
        self.assertNotIn("sk-secret-123", out)
        self.assertIn("CLAUDE_CODE_OAUTH_TOKEN=***REDACTED***", out)
        for pin in ("CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0", "DISABLE_AUTOUPDATER=1", "CFACTORY_EVAL=1", "BASH_DEFAULT_TIMEOUT_MS=", "CFACTORY_EVAL_HEAVY_LOCK="):
            self.assertIn(pin, out)
        self.assertNotIn("CLAUDE_CODE_EFFORT_LEVEL", out)
        self.assertIn("--effort medium", out)
        self.assertIn("--max-turns", out)
        self.assertIn("--plugin-dir", out)
        self.assertIn("'/goal Met when any one of these is true.", out)
        self.assertIn("APP_PORT=4100", out)
        self.assertIn("DB_NAME=evaldb_", out)

    def prepared(self, **extra):
        """A task in its own directory, optionally with task.json overrides."""
        tmp = Path(self.tmp.name) / "other"
        tmp.mkdir()
        task, *_ = fx.prepare(str(tmp), extra=["--env", "TEST_DATABASE_URL=postgres://u@127.0.0.1:5433/{db}", "--env", "TAG={run}-{port}"])
        return task

    def test_task_env_is_exported_and_shown_in_the_dry_run(self):
        self.task = self.prepared()
        out = self.dry("--arms", "default", "--parallel", "1")
        self.assertRegex(out, r"TEST_DATABASE_URL=postgres://u@127\.0\.0\.1:5433/evaldb_grid_t1_default_b01_\w+\n")
        self.assertRegex(out, r"TAG=grid-t1-default-b01-\w+-4100\n")
        self.assertIn("DB_NAME=evaldb_", out)

    def test_a_cfactory_folder_in_the_start_tree_does_not_crash_and_the_pinned_scripts_win(self):
        self.task = self.prepared()
        tree = Path(self.tmp.name) / "tree"
        with tarfile.open(self.task / "start.tar.gz") as tf:
            tf.extractall(tree, filter="data")
        (tree / ".cfactory").mkdir()
        (tree / ".cfactory/check-plan.py").write_text("stale")
        prepare_task.pack(tree, self.task / "start.tar.gz")
        self.dry("--arms", "default", "--parallel", "1")
        repo = next(next((self.results / "grid").iterdir()).glob("repo-*"))
        self.assertNotEqual((repo / ".cfactory/check-plan.py").read_text(), "stale")
        self.assertTrue((repo / ".cfactory/goal-brief.py").exists())
        self.assertEqual(run_eval.git(repo, "config", "gc.auto"), "0")

    def test_config_dir_mode_when_no_token(self):
        out = self.dry("--arms", "default", "--parallel", "1")
        self.assertIn("auth config-dir", out)
        self.assertIn("claude-config", out)
        self.assertNotIn("CLAUDE_CODE_OAUTH_TOKEN", out)

    def test_agent_frontmatter_is_overridden_per_arm(self):
        self.dry("--arms", "grid_haiku_low", "--parallel", "1")
        run = next((self.results / "grid").iterdir())
        builder = (run / "plugin/agents/builder.md").read_text()
        self.assertIn("model: haiku", builder)
        self.assertIn("effort: low", builder)
        prompt = (run / "system-prompt.md").read_text()
        self.assertIn("Skip the verifier step", prompt)
        self.assertIn("Skip the security review", prompt)
        self.assertIn("heavy <command>", prompt)
        self.assertTrue((run / "bin/heavy").stat().st_mode & 0o100)

    def test_parallel_runs_get_own_directories_ports_and_databases(self):
        out = self.dry("--arms", "default,pb1,grid_sonnet_low", "--parallel", "3")
        runs = list((self.results / "grid").iterdir())
        self.assertEqual(len(runs), 3)
        self.assertEqual(len({r.name for r in runs}), 3)
        ports = [l for l in out.splitlines() if l.strip().startswith("APP_PORT=")]
        self.assertEqual(len(set(ports)), len(ports))
        self.assertEqual(len({l for l in out.splitlines() if l.strip().startswith("DB_NAME=")}), 3)

    def test_raw_context_needs_a_ticket_delta(self):
        with self.assertRaises(SystemExit) as cm:
            self.dry("--arms", "pb2", "--parallel", "1")
        self.assertIn("ticket-delta.md", str(cm.exception))
        shutil.rmtree(self.results, ignore_errors=True)
        (self.task / "ticket-delta.md").write_text("## ADDED\n- req-1: Doubling returns twice the number, as the ticket says. [outcome-1]\n")
        self.dry("--arms", "pb2", "--parallel", "1")

    def test_plain_arm_has_no_plugin_and_same_goal_line(self):
        out = self.dry("--arms", "plain_sonnet,default", "--parallel", "1")
        cmds = [l for l in out.splitlines() if l.startswith("  claude ")]
        self.assertEqual(len(cmds), 2)
        plain = next(c for c in cmds if "--plugin-dir" not in c)
        goals = {c[c.index("'/goal"):] if "'/goal" in c else c[c.index("/goal"):] for c in cmds}
        self.assertEqual(len(goals), 1, "plain and factory arms get the same goal condition")
        self.assertIn("claude -p", plain)

    def test_refuses_when_the_haiku_alias_is_repointed(self):
        with self.assertRaises(SystemExit):
            self.dry("--arms", "default", env={"ANTHROPIC_DEFAULT_HAIKU_MODEL": "x"})

    def test_blocks_are_randomized_and_complete(self):
        arms = [run_eval.configs.get(n) for n in ("default", "pb1", "pb2", "pb3")]
        jobs = run_eval.plan_jobs(arms, 3, "1", "t", random.Random(1))
        self.assertEqual(len(jobs), 12)
        for b in (1, 2, 3):
            self.assertEqual(sorted(j["arm"]["name"] for j in jobs if j["block"] == b), ["default", "pb1", "pb2", "pb3"])
        self.assertEqual(len({j["run_id"] for j in jobs}), 12)

    def test_infra_classification(self):
        c = run_eval.classify_infra
        self.assertEqual(c("API Error: 429 rate limit exceeded"), "rate-limit")
        self.assertEqual(c("Invalid API key. Please run /login"), "auth")
        self.assertEqual(c("fetch failed: ECONNREFUSED"), "api-unreachable")
        self.assertIsNone(c("BLOCKED: owner decides"))

    def test_infra_from_stream_looks_at_the_result_and_rate_limit_events(self):
        p = Path(self.tmp.name) / "s.jsonl"
        fx.write_stream(p, fx.stream())
        self.assertIsNone(run_eval.infra_from_stream(p))
        fx.write_stream(p, fx.stream(error="You've hit your usage limit"))
        self.assertEqual(run_eval.infra_from_stream(p), "rate-limit")
        fx.write_stream(p, [{"type": "rate_limit_event", "rate_limit_info": {"status": "rejected"}}])
        self.assertEqual(run_eval.infra_from_stream(p), "rate-limit")


if __name__ == "__main__":
    unittest.main()
