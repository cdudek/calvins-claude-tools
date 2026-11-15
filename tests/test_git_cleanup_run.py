"""The git-cleanup-run skill of the agent-tracker plugin: its script (list, act) and the text of SKILL.md.

Every script test runs against a fake `claude`, a fake `gh` and a logging `git` first on PATH, with a temporary HOME and
git fixtures in a temporary folder (F82). Nothing here touches a real session, repository or `claude agents` output.
Run: python3 -m unittest discover -s tests"""
import ast
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import taxonomy  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "plugins/agent-tracker/skills/git-cleanup-run"
SCRIPT = SKILL / "scripts/cleanup.py"
HOOKS = ROOT / "plugins/agent-tracker/hooks"
TAG = "@2026-11-14-tracker-session-cleanup"
DAY = 86400
REAL_GIT = shutil.which("git")

FAKE_CLAUDE = """#!/usr/bin/env python3
import json, os, sys
d = os.environ["FAKE_DIR"]
args = sys.argv[1:]
with open(d + "/log", "a") as f:
    f.write(" ".join(args) + "\\n")
if args[:1] == ["agents"]:
    if os.path.exists(d + "/agents_fail"):
        sys.exit(1)
    n = 1
    if os.path.exists(d + "/count"):
        n = int(open(d + "/count").read()) + 1
    open(d + "/count", "w").write(str(n))
    if os.path.exists(d + "/agents_fail_from") and n >= int(open(d + "/agents_fail_from").read()):
        sys.exit(1)
    if os.path.exists(d + "/agents_fail_at") and n == int(open(d + "/agents_fail_at").read()):
        sys.exit(1)
    while n > 1 and not os.path.exists(d + "/agents.%d.json" % n):
        n -= 1
    sys.stdout.write(open(d + "/agents.%d.json" % n).read())
elif args[:1] == ["rm"] and len(args) == 2:
    if os.path.exists(d + "/rm_fail_" + args[1]):
        msg = open(d + "/rm_fail_" + args[1]).read()
        sys.stderr.write((msg if msg != "1" else "refused: not safe to remove") + "\\n")
        sys.exit(1)
else:
    sys.exit(2)
"""

FAKE_GH = """#!/usr/bin/env python3
import json, os, sys
d = os.environ["FAKE_DIR"]
args = sys.argv[1:]
with open(d + "/ghlog", "a") as f:
    f.write(" ".join(args) + "\\n")
if os.path.exists(d + "/gh_fail") or args[:2] != ["pr", "list"] or "--head" not in args:
    sys.exit(1)
branch = args[args.index("--head") + 1]
states = json.load(open(d + "/gh.json")) if os.path.exists(d + "/gh.json") else {}
print(json.dumps([{"state": s} for s in states.get(branch, [])]))
"""

LOGGING_GIT = """#!/bin/sh
echo "$@" >> "$FAKE_DIR/gitlog"
exec "$REAL_GIT" "$@"
"""


class Fx:
    """One temporary world: fake commands, a HOME with the tracker's records, git repositories."""

    def __init__(self, case):
        base = tempfile.mkdtemp()
        case.addCleanup(shutil.rmtree, base, True)
        self.tmp = Path(os.path.realpath(base))
        self.bin, self.fake, self.home = self.tmp / "bin", self.tmp / "fake", self.tmp / "home"
        for p in (self.bin, self.fake, self.home / ".claude/agent-tracker/sessions", self.home / ".claude/projects/p"):
            p.mkdir(parents=True)
        for name, body in (("claude", FAKE_CLAUDE), ("gh", FAKE_GH), ("git", LOGGING_GIT)):
            (self.bin / name).write_text(body)
            (self.bin / name).chmod(0o755)
        self.env = {
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}", "HOME": str(self.home), "FAKE_DIR": str(self.fake),
            "REAL_GIT": REAL_GIT, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
        }
        self.agents()

    # -- fake claude and gh
    def agents(self, *rows, n=1):
        (self.fake / f"agents.{n}.json").write_text(json.dumps(list(rows)))

    def gh(self, states):
        (self.fake / "gh.json").write_text(json.dumps(states))

    def flag(self, name, text="1"):
        (self.fake / name).write_text(text)

    def log(self, name="log"):
        p = self.fake / name
        return p.read_text().splitlines() if p.exists() else []

    # -- the tracker's records
    def record(self, sid, repo=None, cwd="/nowhere", active_days=60, asks=()):
        data = {"v": 1, "sessionId": sid, "cwd": str(cwd), "lastActivityAt": int((time.time() - active_days * DAY) * 1000),
                "repo": {"path": str(repo), "name": Path(repo).name} if repo else None, "asks": list(asks)}
        (self.home / ".claude/agent-tracker/sessions" / f"{sid}.json").write_text(json.dumps(data))

    def late(self, text):
        """The tracker's latechecks.json, as text (a torn file is a string that is not JSON)."""
        (self.home / ".claude/agent-tracker/latechecks.json").write_text(text)

    def transcript(self, sid, days_ago):
        f = self.home / ".claude/projects/p" / f"{sid}.jsonl"
        f.write_text("{}\n")
        t = time.time() - days_ago * DAY
        os.utime(f, (t, t))

    # -- git fixtures
    def git(self, cwd, *args, days=0):
        env = {**self.env, "GIT_AUTHOR_NAME": "Tester", "GIT_AUTHOR_EMAIL": "tester.invalid",
               "GIT_COMMITTER_NAME": "Tester", "GIT_COMMITTER_EMAIL": "tester.invalid"}
        if days:
            env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = f"{int(time.time() - days * DAY)} +0000"
        r = subprocess.run([REAL_GIT, "-C", str(cwd), *args], env=env, capture_output=True, text=True)
        assert r.returncode == 0, (args, r.stderr)
        return r.stdout.strip()

    def repo(self, name="web-app", default="main", days=60):
        origin, root = self.tmp / f"{name}-origin.git", self.tmp / name
        subprocess.run([REAL_GIT, "init", "-q", "--bare", "-b", default, str(origin)], check=True, env=self.env)
        subprocess.run([REAL_GIT, "init", "-q", "-b", default, str(root)], check=True, env=self.env)
        (root / ".gitignore").write_text("*.log\n*.tmp\n.env*\n*.pem\n*key*\ncredentials*\nbuild/\nnode_modules/\n")
        (root / "a.txt").write_text("a\n")
        self.git(root, "add", ".")
        self.git(root, "commit", "-q", "-m", "first", days=days)
        self.git(root, "remote", "add", "origin", str(origin))
        self.git(root, "push", "-q", "-u", "origin", default)
        self.git(root, "remote", "set-head", "origin", default)
        return root

    def worktree(self, root, branch, days=60):
        """A linked worktree on a new branch at the default commit; clean, pushed, merged, folder and commit `days` old."""
        path = self.tmp / f"{root.name}-wt" / branch
        self.git(root, "worktree", "add", "-q", "-b", branch, str(path))
        self.age(path, days)
        return path

    def age(self, path, days):
        t = time.time() - days * DAY
        os.utime(path, (t, t))

    def commit_in(self, path, name="b.txt", days=60):
        (path / name).write_text("b\n")
        self.git(path, "add", name)
        self.git(path, "commit", "-q", "-m", "second", days=days)
        self.age(path, 60)

    # -- the script
    def run(self, *args, stdin=None):
        r = subprocess.run([sys.executable, str(SCRIPT), *args], env=self.env, capture_output=True, text=True, input=stdin or "")
        try:
            r.out = json.loads(r.stdout)
        except ValueError:
            r.out = None
        return r

    def list(self):
        r = self.run("list")
        assert r.returncode == 0, r.stderr + r.stdout
        return r.out

    def item(self, id_):
        return next(i for i in self.list()["items"] if i["id"] == id_)


def row(id_=None, sid=None, cwd="/nowhere", pid=None, days=60, name="fix login", kind="background"):
    r = {"sessionId": sid or f"sess-{id_ or name}", "cwd": str(cwd), "name": name, "kind": kind,
         "state": "idle" if pid else "done"}
    if id_:
        r["id"] = id_
    if pid:
        r["pid"] = pid
    if days is not None:
        r["startedAt"] = int((time.time() - days * DAY) * 1000)
    return r


LIVE = row("live0001", pid=4242, days=1, name="live one")  # some row with a pid: the pid rule of F75 holds


class Base(unittest.TestCase):
    def setUp(self):
        self.fx = Fx(self)

    def tearDown(self):
        # F65, F64 at run time: whatever a test did, no stop and no banned argument reached claude, git or gh.
        calls = self.fx.log() + self.fx.log("gitlog") + self.fx.log("ghlog")
        self.assertFalse([c for c in calls if re.match(r"stop\b", c)], "claude stop was run")
        self.assertFalse([c for c in calls if re.search(r"(^| )(-f|-D|--force\S*|--discard-unpushed)( |$)", c)], "a banned argument was passed")
        self.assertFalse([c for c in calls if re.search(r"\bbranch\b.*-D|\bpush\b", c)])


class ListCollects(Base):
    def test_F48_collects_by_idle_time_and_skips_an_unknown_time(self):
        """@F48 @2026-11-14-tracker-session-cleanup list collects ended sessions and linked worktrees idle 30 days or more; an unknown time is not collected."""
        fx = self.fx
        fx.transcript("sess-newtx", days_ago=3)
        fx.agents(LIVE,
                  row("old00001", days=60), row("new00001", days=5), row("newtx001", sid="sess-newtx", days=60),
                  row("unk00001", days=None), row(pid=99, days=90, name="running old"))
        root = fx.repo()
        old, fresh = fx.worktree(root, "old-one"), fx.worktree(root, "fresh-one")
        fx.age(fresh, 2)
        fx.record("sess-w", repo=root, cwd=old)
        out = fx.list()
        ids = {i["id"] for i in out["items"]}
        self.assertEqual(ids, {"old00001", str(old)})
        self.assertEqual(out["days"], 30)
        self.assertGreaterEqual(next(i for i in out["items"] if i["id"] == "old00001")["idle_days"], 59)

    def test_F48_a_worktree_is_as_idle_as_its_newest_session(self):
        """@F48 @2026-11-14-tracker-session-cleanup the worktree idle time is the newest of the last commit, the folder and the sessions that used it."""
        fx = self.fx
        root = fx.repo()
        wt = fx.worktree(root, "login")
        fx.record("sess-a", repo=root, cwd=wt, active_days=3)
        fx.agents(LIVE)
        self.assertEqual(fx.list()["items"], [])
        fx.record("sess-a", repo=root, cwd=wt, active_days=45)
        self.assertEqual([i["id"] for i in fx.list()["items"]], [str(wt)])


class ListChecks(Base):
    def test_F49_prints_every_check_and_a_verdict(self):
        """@F49 @2026-11-14-tracker-session-cleanup list prints every check's result and a verdict, removable or needs-look with the first failed check."""
        fx = self.fx
        partly = {"n": 1, "kind": "task", "text": "x", "verdict": "partly"}
        fx.record("sess-clean", asks=[{"n": 1, "kind": "task", "text": "x", "verdict": "done"}])
        fx.record("sess-partly", asks=[partly])
        fx.record("sess-notstarted", asks=[{**partly, "verdict": "not-started"}])
        fx.agents(LIVE, row("good0001", sid="sess-clean"), row("part0001", sid="sess-partly"), row("nots0001", sid="sess-notstarted"))
        items = {i["id"]: i for i in fx.list()["items"]}
        good = items["good0001"]
        self.assertEqual((good["verdict"], good["failed"]), ("removable", None))
        self.assertEqual(good["checks"], {"pid_reported": True, "no_process": True, "job_id": True, "asks": True})
        for k in ("part0001", "nots0001"):
            self.assertEqual((items[k]["verdict"], items[k]["failed"]), ("needs-look", "asks"))
            self.assertFalse(items[k]["checks"]["asks"])
        self.assertEqual({good["type"], good["repo"], good["title"]}, {"session", "nowhere", "fix login"})

    def test_F49_an_unreadable_ask_record_is_needs_look(self):
        """@F49 @2026-11-14-tracker-session-cleanup a torn ask record makes the session needs-look; a missing one has no asks."""
        fx = self.fx
        (fx.home / ".claude/agent-tracker/sessions/sess-torn.json").write_text("{not json")
        fx.agents(LIVE, row("torn0001", sid="sess-torn"), row("none0001", sid="sess-none"))
        items = {i["id"]: i for i in fx.list()["items"]}
        self.assertEqual((items["torn0001"]["verdict"], items["torn0001"]["failed"]), ("needs-look", "asks"))
        self.assertIn("unreadable", items["torn0001"]["reason"])
        self.assertEqual(items["none0001"]["verdict"], "removable")

    def test_F49_a_worktree_prints_all_five_checks_and_the_ignored_files(self):
        """@F49 @2026-11-14-tracker-session-cleanup a worktree item carries linked, clean, pushed, merged and unused, and the ignored files."""
        fx = self.fx
        root = fx.repo()
        wt = fx.worktree(root, "login")
        fx.record("sess-a", repo=root, cwd=wt)
        fx.agents(LIVE)
        i = fx.item(str(wt))
        self.assertEqual(i["checks"], {"linked": True, "clean": True, "pushed": True, "merged": True, "unused": True})
        self.assertEqual((i["verdict"], i["type"], i["repo"], i["branch"]), ("removable", "worktree", "web-app", "login"))
        self.assertEqual(i["ignored"], {"secret": [], "other": [], "more": 0})


class LateAndJobIds(Base):
    def task(self, **extra):
        return {"n": 1, "kind": "task", "text": "x", **extra}

    def test_F49_a_late_partly_or_not_started_verdict_fails_asks(self):
        """@F49 @2026-11-14-tracker-session-cleanup a late verdict in latechecks.json counts for an ask no turn judged: partly or not-started fails asks; done, a judged ask and another session do not."""
        fx = self.fx
        fx.record("sess-late", asks=[self.task()])
        fx.record("sess-judged", asks=[self.task(verdict="done")])
        fx.record("sess-other", asks=[self.task()])
        late = {"v": 1, "by": {"sess-late": {"at": 1, "verdicts": [{"n": 1, "verdict": "not-started"}]},
                               "sess-judged": {"at": 1, "verdicts": [{"n": 1, "verdict": "partly"}]},
                               "sess-gone": {"at": 1, "verdicts": [{"n": 1, "verdict": "done"}]}}}
        fx.late(json.dumps(late))
        fx.agents(LIVE, row("late0001", sid="sess-late"), row("judg0001", sid="sess-judged"), row("othr0001", sid="sess-other"))
        items = {i["id"]: i for i in fx.list()["items"]}
        self.assertEqual((items["late0001"]["verdict"], items["late0001"]["failed"]), ("needs-look", "asks"))
        self.assertEqual(items["judg0001"]["verdict"], "removable")  # the turn's own verdict wins
        self.assertEqual(items["othr0001"]["verdict"], "removable")
        r = fx.run("act", "late0001")
        self.assertEqual((r.out["cleared"], [s["kind"] for s in r.out["skipped"]]), ([], ["needs-look"]))
        self.assertFalse([c for c in fx.log() if c.startswith("rm")])
        fx.late(json.dumps({"v": 1, "by": {"sess-late": {"at": 1, "verdicts": [{"n": 1, "verdict": "done"}]}}}))
        self.assertEqual(fx.item("late0001")["verdict"], "removable")

    def test_F49_a_torn_late_checks_file_is_needs_look(self):
        """@F49 @2026-11-14-tracker-session-cleanup a latechecks.json that does not parse, or has another shape, makes every session needs-look; a missing one changes nothing."""
        fx = self.fx
        fx.agents(LIVE, row("good0001"))
        self.assertEqual(fx.item("good0001")["verdict"], "removable")  # no file
        for text in ("{not json", json.dumps({"v": 2, "by": {}}), json.dumps({"v": 1, "by": []}),
                     json.dumps({"v": 1, "by": {"sess-good0001": {"verdicts": "x"}}})):
            fx.late(text)
            i = fx.item("good0001")
            self.assertEqual((i["verdict"], i["failed"]), ("needs-look", "asks"), text)
            self.assertIn("unreadable", i["reason"])
            fx.run("act", "good0001")
        self.assertFalse([c for c in fx.log() if c.startswith("rm")])

    def test_F80_a_job_id_that_is_not_plain_is_needs_look_and_never_reaches_claude_rm(self):
        """@F80 @2026-11-14-tracker-session-cleanup a job id outside the tracker's plain shape (a leading dash, a space, over 64 characters) is needs-look and no claude rm is run for it."""
        fx = self.fx
        bad = ["-rf", "a b", "x" * 65, "-", "a;b", ".hidden", "a\n"]
        fx.agents(LIVE, *[row(b, sid=f"sess-{n}") for n, b in enumerate(bad)], row("ok.id_1-2", sid="sess-ok"), row("x" * 64, sid="sess-64"))
        items = {i["id"]: i for i in fx.list()["items"]}
        for b in bad:
            self.assertEqual((items[b]["verdict"], items[b]["failed"]), ("needs-look", "job_id"), repr(b))
            self.assertNotIn("asks", items[b]["reason"])
            fx.run("act", "--", b)
        self.assertEqual((items["ok.id_1-2"]["verdict"], items["x" * 64]["verdict"]), ("removable", "removable"))
        self.assertFalse([c for c in fx.log() if c.startswith("rm")])
        r = fx.run("act", "ok.id_1-2")
        self.assertEqual([c["id"] for c in r.out["cleared"]], ["ok.id_1-2"])


class FiveConditions(Base):
    """The case names are the ones the tracker's TypeScript tests use for F35."""

    def wt(self, branch="login"):
        fx = self.fx
        root = fx.repo()
        wt = fx.worktree(root, branch)
        fx.record("sess-a", repo=root, cwd=wt)
        fx.agents(LIVE)
        return root, wt

    def test_F35_linked(self):
        """@F35 @2026-11-14-tracker-session-cleanup linked: the main checkout is never an item, a linked worktree is."""
        fx = self.fx
        root, wt = self.wt()
        fx.record("sess-main", repo=root, cwd=root)
        fx.age(root, 60)
        self.assertEqual([i["id"] for i in fx.list()["items"] if i["type"] == "worktree"], [str(wt)])
        self.assertTrue(fx.item(str(wt))["checks"]["linked"])

    def test_F35_clean(self):
        """@F35 @2026-11-14-tracker-session-cleanup clean: an untracked, a modified or a staged file fails, with its reason."""
        fx = self.fx
        root, wt = self.wt()
        def stage():
            (wt / "a.txt").write_text("staged\n")
            fx.git(wt, "add", "a.txt")

        for change in (lambda: (wt / "new.txt").write_text("x"), lambda: (wt / "a.txt").write_text("changed\n"), stage):
            change()
            fx.age(wt, 60)
            i = fx.item(str(wt))
            self.assertEqual((i["verdict"], i["failed"], i["reason"]), ("needs-look", "clean", "uncommitted changes"))
            self.assertEqual(i["checks"]["pushed"], True)
            fx.git(wt, "reset", "-q", "--hard")
            (wt / "new.txt").unlink(missing_ok=True)
            fx.age(wt, 60)

    def test_F35_pushed(self):
        """@F35 @2026-11-14-tracker-session-cleanup pushed: a commit that is on no remote fails, with its count."""
        fx = self.fx
        root, wt = self.wt()
        fx.commit_in(wt)
        i = fx.item(str(wt))
        self.assertEqual((i["failed"], i["reason"]), ("pushed", "1 commit not pushed"))
        self.assertTrue(i["checks"]["clean"])

    def test_F35_merged(self):
        """@F35 @2026-11-14-tracker-session-cleanup merged: unmerged fails; a merged or closed PR passes; no gh falls back to the branch alone (F38)."""
        fx = self.fx
        root, wt = self.wt()
        fx.commit_in(wt)
        fx.git(wt, "push", "-q", "-u", "origin", "login")  # pushed, but not merged into the default branch
        self.assertEqual((fx.item(str(wt))["failed"], fx.item(str(wt))["reason"]), ("merged", "branch not merged"))
        fx.gh({"login": ["MERGED"]})
        self.assertEqual(fx.item(str(wt))["verdict"], "removable")
        fx.gh({"login": ["CLOSED"]})
        self.assertEqual(fx.item(str(wt))["verdict"], "removable")
        fx.gh({"login": ["OPEN"]})
        self.assertEqual(fx.item(str(wt))["failed"], "merged")
        fx.flag("gh_fail")
        fx.gh({"login": ["MERGED"]})
        self.assertEqual(fx.item(str(wt))["failed"], "merged")  # F38: with no gh the branch alone decides
        fx.git(root, "merge", "-q", "login")
        fx.git(root, "push", "-q", "origin", "main")
        self.assertEqual(fx.item(str(wt))["verdict"], "removable")

    def test_F35_merged_default_branch_falls_back_to_main_then_master(self):
        """@F35 @2026-11-14-tracker-session-cleanup the default branch is origin HEAD, then main, then master; with none the PR alone decides."""
        fx = self.fx
        root = fx.repo(default="master")
        wt = fx.worktree(root, "login")
        fx.record("sess-a", repo=root, cwd=wt)
        fx.agents(LIVE)
        fx.git(root, "remote", "set-head", "origin", "-d")  # no origin HEAD: master is found by name
        self.assertEqual(fx.item(str(wt))["verdict"], "removable")
        fx.git(wt, "push", "-q", "origin", "login")  # the commit stays on a remote, so only the merged check can fail
        fx.git(root, "branch", "-m", "master", "trunk")  # no default branch at all
        fx.git(root, "update-ref", "-d", "refs/remotes/origin/master")
        i = fx.item(str(wt))
        self.assertEqual((i["failed"], i["checks"]["merged"]), ("merged", False))

    def test_F35_unused(self):
        """@F35 @2026-11-14-tracker-session-cleanup unused: a live row at or under the worktree fails, and act skips it as running."""
        fx = self.fx
        root, wt = self.wt()
        (wt / "sub").mkdir()
        fx.age(wt, 60)
        fx.agents(LIVE, row(pid=777, cwd=wt / "sub", days=90, name="working here"))  # a live row, but one started long ago
        i = fx.item(str(wt))
        self.assertEqual((i["failed"], i["reason"]), ("unused", "a session is running in it"))
        r = fx.run("act", str(wt))
        self.assertEqual(r.out["removed"], [])
        self.assertEqual((r.out["skipped"][0]["kind"], r.out["skipped"][0]["reason"]), ("running", "a session is running in it"))
        self.assertTrue(wt.exists())

    def test_F65_with_no_pid_in_the_read_a_row_in_the_worktree_counts_as_live(self):
        """@F65 @2026-11-14-tracker-session-cleanup with no pid in any row, a row at the worktree counts as a live session and act removes nothing."""
        fx = self.fx
        root, wt = self.wt()
        fx.agents(row("old00001", cwd=wt, days=90))
        i = fx.item(str(wt))
        self.assertEqual((i["verdict"], i["failed"]), ("needs-look", "unused"))
        r = fx.run("act", str(wt))
        self.assertEqual((r.out["removed"], [s["kind"] for s in r.out["skipped"]]), ([], ["running"]))
        self.assertTrue(wt.exists())

    def test_F35_the_first_failed_condition_is_named(self):
        """@F35 @2026-11-14-tracker-session-cleanup the first failed condition, in order linked, clean, pushed, merged, unused, is the one named."""
        fx = self.fx
        root, wt = self.wt()
        fx.commit_in(wt)
        (wt / "dirty.txt").write_text("x")
        fx.age(wt, 60)
        fx.agents(LIVE, row(pid=777, cwd=wt, days=90))
        i = fx.item(str(wt))
        self.assertEqual(i["failed"], "clean")
        self.assertEqual([k for k, v in i["checks"].items() if not v], ["clean", "pushed", "merged", "unused"])


class Ignored(Base):
    def test_F79_secret_looking_names_come_first_and_are_never_hidden(self):
        """@F79 @2026-11-14-tracker-session-cleanup the ignored-file list names secret-looking names first and never counts one in "and N more"."""
        fx = self.fx
        root = fx.repo()
        wt = fx.worktree(root, "login")
        fx.record("sess-a", repo=root, cwd=wt)
        fx.agents(LIVE)
        secrets = [".env", ".env.local", "api_key.txt", "credentials.json", "server.pem"]
        for n in secrets + ["a.log", "b.log", "c.tmp", "d.tmp", "z" * 40 + ".log"]:
            (wt / n).write_text("x")
        for d in ("build", "node_modules"):
            (wt / d).mkdir()
            (wt / d / "f").write_text("x")
        fx.age(wt, 60)
        i = fx.item(str(wt))
        self.assertEqual(i["verdict"], "removable")  # ignored files never refuse the offer
        self.assertEqual(i["ignored"]["secret"], secrets)
        self.assertEqual(i["ignored"]["other"], ["a.log", "b.log", "c.tmp"])  # files first, A to Z, at most 3
        self.assertEqual(i["ignored"]["more"], 4)  # d.tmp, the long name, build/, node_modules/

    def test_F79_folders_after_files_and_a_long_name_is_cut(self):
        """@F79 @2026-11-14-tracker-session-cleanup other names list files before folders and cut a name over 30 cells with an ellipsis."""
        fx = self.fx
        root = fx.repo()
        wt = fx.worktree(root, "login")
        fx.record("sess-a", repo=root, cwd=wt)
        fx.agents(LIVE)
        (wt / "build").mkdir()
        (wt / "build/f").write_text("x")
        (wt / ("z" * 40 + ".log")).write_text("x")
        fx.age(wt, 60)
        self.assertEqual(fx.item(str(wt))["ignored"], {"secret": [], "other": ["z" * 29 + "…", "build/"], "more": 0})


class NoPidAndNoId(Base):
    def test_F75_no_pid_in_any_row_marks_every_session_needs_look_and_act_removes_none(self):
        """@F75 @2026-11-14-tracker-session-cleanup with no pid in any row every session is needs-look and act removes none."""
        fx = self.fx
        fx.agents(row("old00001"), row("old00002"))
        out = fx.list()
        self.assertTrue(out["no_pid_reported"])
        self.assertEqual([(i["verdict"], i["failed"], i["reason"]) for i in out["items"]], [("needs-look", "pid_reported", "no pid reported")] * 2)
        r = fx.run("act", "old00001", "old00002")
        self.assertEqual((r.out["cleared"], r.out["failed"]), ([], []))
        self.assertEqual([s["kind"] for s in r.out["skipped"]], ["needs-look"] * 2)
        self.assertFalse([c for c in fx.log() if c.startswith("rm")])

    def test_F80_a_row_with_no_job_id_is_needs_look_and_never_reaches_claude_rm(self):
        """@F80 @2026-11-14-tracker-session-cleanup a row with no job id is needs-look, reason "no job id", and no claude rm is run for it."""
        fx = self.fx
        fx.agents(LIVE, row(sid="sess-noid", days=60, name="interactive", kind="interactive"))
        items = [i for i in fx.list()["items"] if i["title"] == "interactive"]
        self.assertEqual([(i["verdict"], i["failed"], i["reason"]) for i in items], [("needs-look", "job_id", "no job id")])
        for ident in (items[0]["id"], "sess-noid", "interactive"):
            fx.run("act", ident)
        self.assertFalse([c for c in fx.log() if c.startswith("rm")])


class ListIsReadOnly(Base):
    READS = ("worktree list", "status", "rev-list", "merge-base", "symbolic-ref", "rev-parse", "log", "for-each-ref")

    def test_F74_list_runs_read_commands_only(self):
        """@F74 @2026-11-14-tracker-session-cleanup list runs read commands only: the fake claude, gh and git record their argv."""
        fx = self.fx
        root = fx.repo()
        wt = fx.worktree(root, "login")
        fx.record("sess-a", repo=root, cwd=wt)
        fx.git(root, "worktree", "add", "-q", "-b", "other", str(fx.tmp / "other"))
        fx.agents(LIVE, row("old00001"))
        (fx.fake / "gitlog").unlink(missing_ok=True)
        before = fx.git(wt, "status", "--porcelain", "--ignored") + fx.git(root, "worktree", "list")
        fx.list()
        self.assertEqual([c for c in fx.log() if c], ["agents --json --all"])
        for c in fx.log("gitlog"):
            sub = re.sub(r"^-C \S+ ", "", re.sub(r"^(-c \S+ )+", "", c))
            self.assertTrue(sub.startswith(self.READS), f"git was run with a write command: {c}")
        for c in fx.log("ghlog"):
            self.assertTrue(c.startswith("pr list"), c)
        (fx.fake / "gitlog").unlink(missing_ok=True)
        self.assertEqual(before, fx.git(wt, "status", "--porcelain", "--ignored") + fx.git(root, "worktree", "list"))
        self.assertTrue(wt.exists())


class Act(Base):
    def test_F59_act_re_reads_the_session_list_and_skips_what_no_longer_passes(self):
        """@F59 @2026-11-14-tracker-session-cleanup act re-reads the session list right before acting; a session with a pid now, a failure and an unknown id are skipped or failed and named."""
        fx = self.fx
        fx.agents(LIVE, row("good0001"), row("race0001"), row("fail0001"))
        fx.agents(LIVE, row("good0001"), row("race0001", pid=555), row("fail0001"), n=2)  # the read before good0001's rm: race0001 woke up
        fx.flag("rm_fail_fail0001")
        r = fx.run("act", "good0001", "race0001", "fail0001", "nosuch99")
        self.assertEqual([c["id"] for c in r.out["cleared"]], ["good0001"])
        self.assertEqual([c["id"] for c in r.out["failed"]], ["fail0001"])
        self.assertIn("refused", r.out["failed"][0]["reason"])
        self.assertEqual({s["id"]: s["kind"] for s in r.out["skipped"]}, {"race0001": "unknown", "nosuch99": "unknown"})
        rms = [c for c in fx.log() if c.startswith("rm")]
        self.assertEqual(rms, ["rm good0001", "rm fail0001"])
        self.assertGreaterEqual(len([c for c in fx.log() if c.startswith("agents")]), 4)  # one read, then one per id

    def test_F59_an_unreadable_session_list_mid_act_keeps_what_was_done(self):
        """@F59 @2026-11-14-tracker-session-cleanup a session list that cannot be read mid-act skips the rest as unreadable and still prints cleared, removed, skipped and failed."""
        fx = self.fx
        root = fx.repo()
        wt = fx.worktree(root, "login")
        fx.record("sess-a", repo=root, cwd=wt)
        fx.agents(LIVE, row("good0001"), row("next0001"))
        fx.flag("agents_fail_from", "3")  # the first read and good0001's re-check work; the next one fails
        r = fx.run("act", "good0001", "next0001", str(wt))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(sorted(r.out), ["cleared", "failed", "removed", "skipped"])
        self.assertEqual([c["id"] for c in r.out["cleared"]], ["good0001"])
        self.assertEqual([(s["id"], s["reason"], s["kind"]) for s in r.out["skipped"]], [("next0001", "session list unreadable", "unreadable"), (str(wt), "session list unreadable", "unreadable")])
        self.assertEqual(r.out["removed"], [])
        self.assertTrue(wt.exists())
        self.assertEqual([c for c in fx.log() if c.startswith("rm")], ["rm good0001"])

    def test_F59_after_one_unreadable_read_act_reads_no_more_and_acts_on_no_later_id(self):
        """@F59 @2026-11-14-tracker-session-cleanup the session list fails on one read only; every id after it is skipped as unreadable without another read, though that read would succeed."""
        fx = self.fx
        fx.agents(LIVE, row("good0001"), row("next0001"), row("later001"))
        fx.flag("agents_fail_at", "3")  # the first read and good0001's re-check work; next0001's fails; a fourth would work
        r = fx.run("act", "good0001", "next0001", "later001")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual([c["id"] for c in r.out["cleared"]], ["good0001"])
        self.assertEqual([(s["id"], s["kind"], s["reason"]) for s in r.out["skipped"]], [("next0001", "unreadable", "session list unreadable"), ("later001", "unreadable", "session list unreadable")])
        self.assertEqual([c for c in fx.log() if c.startswith("rm")], ["rm good0001"])
        self.assertEqual(len([c for c in fx.log() if c.startswith("agents")]), 3)

    def test_F61_a_skip_from_an_unreadable_read_has_kind_unreadable(self):
        """@F61 @2026-11-14-tracker-session-cleanup a removable item skipped because the session list cannot be read has kind unreadable, not needs-look."""
        fx = self.fx
        fx.agents(LIVE, row("good0001"))
        fx.flag("agents_fail_at", "2")
        r = fx.run("act", "good0001")
        self.assertEqual([(s["id"], s["kind"]) for s in r.out["skipped"]], [("good0001", "unreadable")])
        self.assertEqual(r.out["cleared"], [])

    def test_F59_act_re_checks_a_worktree_right_before_removing_it(self):
        """@F59 @2026-11-14-tracker-session-cleanup act re-checks the worktree's status again before the removal and removes it without force from the main checkout; the branch stays."""
        fx = self.fx
        root = fx.repo()
        wt = fx.worktree(root, "login")
        fx.record("sess-a", repo=root, cwd=wt)
        fx.agents(LIVE)
        (fx.fake / "gitlog").unlink(missing_ok=True)
        r = fx.run("act", str(wt))
        self.assertEqual([w["id"] for w in r.out["removed"]], [str(wt)])
        self.assertFalse(wt.exists())
        self.assertIn("login", fx.git(root, "branch", "--list", "login"))
        calls = fx.log("gitlog")
        removal = [i for i, c in enumerate(calls) if "worktree remove" in c]
        self.assertEqual(len(removal), 1)
        self.assertTrue(calls[removal[0]].endswith(f"worktree remove {wt}"), calls[removal[0]])
        self.assertGreaterEqual(len([c for c in calls[: removal[0]] if " status " in f" {c} "]), 2)  # the list pass, then the re-check

    def test_F61_act_prints_four_lists_and_counts_only_what_succeeded(self):
        """@F61 @2026-11-14-tracker-session-cleanup act prints cleared, removed, skipped and failed, each item with its id, short name and reason."""
        fx = self.fx
        root = fx.repo()
        ok, dirty = fx.worktree(root, "login"), fx.worktree(root, "users")
        (dirty / "x.txt").write_text("x")
        fx.age(dirty, 60)
        fx.agents(LIVE, row("good0001"), row("fail0001"))
        fx.record("sess-a", repo=root, cwd=ok)
        fx.record("sess-b", repo=root, cwd=dirty)
        fx.flag("rm_fail_fail0001")
        r = fx.run("act", "good0001", "fail0001", str(ok), str(dirty))
        self.assertEqual(r.returncode, 0)
        self.assertEqual(sorted(r.out), ["cleared", "failed", "removed", "skipped"])
        self.assertEqual([c["short"] for c in r.out["cleared"]], ["nowhere · fix login"])
        self.assertEqual([c["short"] for c in r.out["removed"]], ["web-app/login"])
        self.assertEqual([c["short"] for c in r.out["failed"]], ["nowhere · fix login"])
        self.assertEqual([(s["short"], s["kind"], s["reason"]) for s in r.out["skipped"]], [("web-app/users", "needs-look", "uncommitted changes")])

    def test_F61_a_failure_reason_is_cut_at_60_cells_in_the_json(self):
        """@F61 @2026-11-14-tracker-session-cleanup the reason of a failed item is cut at 60 cells with an ellipsis in the script's JSON; a short one is kept whole."""
        fx = self.fx
        fx.agents(LIVE, row("long0001"), row("shrt0001"), row("exct0001"))
        fx.flag("rm_fail_long0001", "refused: " + "very long reason " * 10)
        fx.flag("rm_fail_shrt0001", "refused: busy")
        fx.flag("rm_fail_exct0001", "x" * 60)
        r = fx.run("act", "long0001", "shrt0001", "exct0001")
        reasons = {f["id"]: f["reason"] for f in r.out["failed"]}
        self.assertEqual(len(reasons["long0001"]), 60)
        self.assertTrue(reasons["long0001"].startswith("refused: very long reason") and reasons["long0001"].endswith("…"))
        self.assertEqual((reasons["shrt0001"], reasons["exct0001"]), ("refused: busy", "x" * 60))

    def test_F81_list_prints_a_ready_quoted_act_arg_and_the_skill_uses_it(self):
        """@F81 @2026-11-14-tracker-session-cleanup each list item carries act_arg, its id quoted for the shell; a worktree path with a quote round-trips through act and SKILL.md passes act_arg, not a hand-quoted id."""
        fx = self.fx
        root = fx.repo()
        wt = fx.worktree(root, "it's-here")
        fx.record("sess-a", repo=root, cwd=wt)
        fx.agents(LIVE, row("good0001"))
        items = {i["id"]: i for i in fx.list()["items"]}
        for ident, i in items.items():
            self.assertEqual(i["act_arg"], shlex.quote(ident))
        self.assertIn("'", str(wt))
        self.assertEqual(shlex.split(items[str(wt)]["act_arg"]), [str(wt)])
        r = fx.run("act", *shlex.split(items[str(wt)]["act_arg"]))
        self.assertEqual([w["id"] for w in r.out["removed"]], [str(wt)])
        self.assertFalse(wt.exists())
        body = skill_text().split("\n---\n", 1)[1]
        self.assertIn("act_arg", body)
        self.assertNotIn("<id>'", body)
        self.assertNotIn("single quotes", body)

    def test_F62_act_refuses_a_needs_look_id_whatever_the_answer(self):
        """@F62 @2026-11-14-tracker-session-cleanup act refuses an id that failed a check and removes nothing."""
        fx = self.fx
        root = fx.repo()
        wt = fx.worktree(root, "login")
        fx.commit_in(wt)
        fx.record("sess-a", repo=root, cwd=wt)
        fx.record("sess-p", asks=[{"n": 1, "kind": "task", "text": "x", "verdict": "partly"}])
        fx.agents(LIVE, row("part0001", sid="sess-p"))
        r = fx.run("act", str(wt), "part0001")
        self.assertEqual((r.out["cleared"], r.out["removed"], r.out["failed"]), ([], [], []))
        self.assertEqual({s["kind"] for s in r.out["skipped"]}, {"needs-look"})
        self.assertTrue(wt.exists())
        self.assertFalse([c for c in fx.log() if c.startswith("rm")])

    def test_F81_act_takes_explicit_ids_only(self):
        """@F81 @2026-11-14-tracker-session-cleanup act has no all or yes flag, reads no ids from stdin, and with no id does nothing."""
        fx = self.fx
        fx.agents(LIVE, row("good0001"))
        for args, stdin in ((("act", "--all"), None), (("act", "--yes", "good0001"), None), (("act",), "good0001\n"), (("list", "--days", "3"), None), (("act", "--al"), None)):
            r = fx.run(*args, stdin=stdin)
            self.assertEqual(r.returncode, 2, args)
        self.assertEqual(fx.log(), [])  # nothing was read or removed
        self.assertNotRegex(SCRIPT.read_text(), r"sys\.stdin|\binput\(")

    def test_F65_a_session_with_a_pid_is_never_removed_and_nothing_is_stopped(self):
        """@F65 @2026-11-14-tracker-session-cleanup the script runs no claude stop and no claude rm for a row with a pid."""
        fx = self.fx
        fx.agents(LIVE, row("live0002", pid=31, days=90))
        r = fx.run("act", "live0001", "live0002")
        self.assertEqual([s["kind"] for s in r.out["skipped"]], ["unknown", "unknown"])
        self.assertEqual([c for c in fx.log() if not c.startswith("agents")], [])
        self.assertNotRegex(SCRIPT.read_text(), r"['\"]stop['\"]")


class Safety(Base):
    def test_F66_only_act_writes(self):
        """@F66 @2026-11-14-tracker-session-cleanup list writes nothing; the only writes are claude rm and git worktree remove, after act."""
        fx = self.fx
        root = fx.repo()
        wt = fx.worktree(root, "login")
        fx.record("sess-a", repo=root, cwd=wt)
        fx.agents(LIVE, row("good0001"))
        fx.list()
        self.assertFalse([c for c in fx.log() if c.startswith("rm")])
        self.assertFalse([c for c in fx.log("gitlog") if "remove" in c])
        fx.run("act", "good0001", str(wt))
        self.assertEqual([c for c in fx.log() if not c.startswith("agents")], ["rm good0001"])

    def test_F67_no_shell_no_branch_deletion(self):
        """@F67 @2026-11-14-tracker-session-cleanup the script uses subprocess with an argument list, no shell and no branch deletion."""
        src = SCRIPT.read_text()
        self.assertIsNone(re.search(r"shell\s*=\s*True|os\.system|os\.popen|\beval\(|\bexec\(", src))
        self.assertIsNone(re.search(r"branch -[dD]|update-ref|['\"](push|prune|reset|checkout)['\"]|['\"](clean|branch)['\"]\s*[,\]]", src))
        self.assertEqual(len(re.findall(r"subprocess\.\w+\(", src)), 1)  # one wrapper holds the only call

    def test_F67_every_git_call_ignores_the_repos_own_fsmonitor_and_hooks(self):
        """@F67 @2026-11-14-tracker-session-cleanup every git call the script makes, list and act, starts with -c core.fsmonitor=false -c core.hooksPath=/dev/null, as the tracker's does."""
        fx = self.fx
        root = fx.repo()
        wt = fx.worktree(root, "login")
        fx.record("sess-a", repo=root, cwd=wt)
        fx.agents(LIVE)
        fx.list()
        fx.run("act", str(wt))
        calls = fx.log("gitlog")
        self.assertTrue(any("worktree remove" in c for c in calls) and len(calls) > 5)
        self.assertEqual([c for c in calls if not c.startswith("-c core.fsmonitor=false -c core.hooksPath=/dev/null ")], [])

    def test_F67_the_removal_waits_as_long_as_the_trackers_120_seconds(self):
        """@F67 @2026-11-14-tracker-session-cleanup git worktree remove is run with a 120 second timeout, the tracker's, not the 60 seconds of the reads."""
        tree = ast.parse(SCRIPT.read_text())
        removals = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "run" and n.args
                    and isinstance(n.args[0], ast.List) and [getattr(e, "value", None) for e in n.args[0].elts][:3] == ["git", "worktree", "remove"]]
        self.assertEqual(len(removals), 1)
        self.assertEqual({k.arg: getattr(k.value, "value", None) for k in removals[0].keywords}.get("timeout"), 120)

    def test_F67_the_removal_never_forces_and_keeps_the_branch(self):
        """@F67 @2026-11-14-tracker-session-cleanup git worktree remove runs without force and the branch stays."""
        fx = self.fx
        root = fx.repo()
        wt = fx.worktree(root, "login")
        fx.record("sess-a", repo=root, cwd=wt)
        fx.agents(LIVE)
        fx.run("act", str(wt))
        removal = [c for c in fx.log("gitlog") if "worktree remove" in c]
        self.assertEqual(len(removal), 1)
        self.assertNotIn("-", removal[0].split("remove", 1)[1].replace(str(wt), ""))
        self.assertTrue(fx.git(root, "rev-parse", "--verify", "login"))

    def test_F64_no_banned_argument_in_the_script_the_skill_or_the_tracker(self):
        """@F64 @2026-11-14-tracker-session-cleanup no source of the script, the skill or hooks/tracker passes a banned argument."""
        quoted = re.compile(r"['\"`](-f|-D|--force\S*|--discard-unpushed|--force-remove-worktree)['\"`]|branch -D|claude stop")
        bare = re.compile(r"(^|\s)(-f|-D|--force\S*|--discard-unpushed)(\s|$|[`.,;)])")
        bad = []
        for f in sorted([*HOOKS.rglob("*"), *SKILL.rglob("*")]):
            if not f.is_file() or f.suffix not in {".ts", ".tsx", ".py", ".md", ".json"}:
                continue
            for n, line in enumerate(f.read_text().splitlines(), 1):
                if quoted.search(line) or (f.suffix == ".md" and bare.search(line)):
                    bad.append(f"{f.relative_to(ROOT)}:{n}: {line.strip()[:80]}")
        self.assertEqual(bad, [])

    def test_F68_no_path_internal_name_or_address_in_the_shipped_files(self):
        """@F68 @2026-11-14-tracker-session-cleanup the script and the skill hold no local path, URL or e-mail address."""
        for f in (SCRIPT, SKILL / "SKILL.md"):
            text = f.read_text()
            self.assertNotRegex(text, r"/Users/|/home/|https?://|\b\w+@\w+\.\w+", f.name)
        self.assertEqual(self.fx_item_path_only_in_json(), True)

    def fx_item_path_only_in_json(self):
        fx = self.fx
        root = fx.repo()
        wt = fx.worktree(root, "login")
        fx.record("sess-a", repo=root, cwd=wt)
        fx.agents(LIVE)
        i = fx.item(str(wt))
        return str(wt) not in (i["label"], i["short"]) and str(root) not in i["label"]

    def test_F69_the_script_runs_claude_git_and_gh_and_reads_the_trackers_records(self):
        """@F69 @2026-11-14-tracker-session-cleanup every command the script runs is claude, git or gh; it reads the tracker's records."""
        tree = ast.parse(SCRIPT.read_text())
        first = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "run" and node.args and isinstance(node.args[0], ast.List):
                head = node.args[0].elts[0]
                self.assertIsInstance(head, ast.Constant)
                first.add(head.value)
        self.assertEqual(first, {"claude", "git", "gh"})
        self.assertIn("agent-tracker", SCRIPT.read_text())

    def test_F82_the_tests_put_a_fake_claude_and_a_fake_gh_first_on_path(self):
        """@F82 @2026-11-14-tracker-session-cleanup the script's tests run with a fake claude and gh first on PATH and a temporary HOME."""
        fx = self.fx
        first = fx.env["PATH"].split(os.pathsep)[0]
        self.assertEqual(first, str(fx.bin))
        for name in ("claude", "gh"):
            self.assertEqual(shutil.which(name, path=fx.env["PATH"]), str(fx.bin / name))
        self.assertTrue(str(fx.home).startswith(str(fx.tmp)))
        self.assertNotEqual(fx.home, Path.home())
        fx.agents(LIVE)
        fx.list()
        self.assertEqual(fx.log(), ["agents --json --all"])  # the script reached the fake, not a real claude


def skill_text():
    return (SKILL / "SKILL.md").read_text()


class SkillText(unittest.TestCase):
    def need(self, *parts):
        text = skill_text()
        for p in parts:
            self.assertIn(p, text)

    def test_F77_the_skills_name_passes_the_taxonomy_and_the_frontmatter_holds(self):
        """@F77 @2026-11-14-tracker-session-cleanup the name passes check_names, folder equals name, user_invocable is true, allowed-tools has no claude or git."""
        self.assertEqual([e for e in taxonomy.check_names({"git-cleanup-run": "P"}, set()) if e.startswith("git-cleanup-run")], [])
        fm, _ = taxonomy.parse(skill_text())
        self.assertEqual(fm["name"], "git-cleanup-run")
        self.assertEqual(SKILL.name, fm["name"])
        self.assertIs(fm["user_invocable"], True)
        self.assertLessEqual(len(fm["description"]), 1024)
        tools = re.findall(r"Bash\([^)]*\)|\w+", fm["allowed-tools"])
        self.assertEqual([t for t in tools if t.startswith("Bash")], [
            "Bash(python3 */git-cleanup-run/scripts/cleanup.py list)", "Bash(python3 */git-cleanup-run/scripts/cleanup.py act *)"])
        self.assertEqual(sorted(t for t in tools if not t.startswith("Bash")), ["Agent", "AskUserQuestion", "Read"])
        self.assertNotRegex(fm["allowed-tools"], r"Bash\((claude|git)\b")
        mine = taxonomy.triggers(fm["description"])
        others = set()
        for f in (ROOT / "plugins/cct/skills").glob("*/SKILL.md"):
            others |= taxonomy.triggers((taxonomy.parse(f.read_text())[0].get("description") or ""))
        self.assertEqual(mine & others, set())

    def test_F58_one_question_per_batch_sessions_first(self):
        """@F58 @2026-11-14-tracker-session-cleanup SKILL.md holds one AskUserQuestion per batch, sessions first, batches of 25, the options and the item line."""
        text = skill_text()
        self.need("AskUserQuestion", "batches of 25", "Clear all N (Recommended)", "Remove all N (Recommended)", "Skip these N",
                  "web-app · fix login · idle 41d", "Asks no question when no item is `removable`")
        self.assertLess(text.index("Clear all N"), text.index("Remove all N"))
        self.need("Found 5 sessions and 3 worktrees idle for 30 days or more. Nothing that is running is touched.",
                  "Nothing to clean up. Nothing idle for 30 days is ready.",
                  "Nothing is removable: Claude Code did not say which sessions have a process.")

    def test_F60_an_unclear_exception_asks_again_and_the_final_list_comes_first(self):
        """@F60 @2026-11-14-tracker-session-cleanup SKILL.md says an unmatched or ambiguous exception asks again and runs nothing, and the final list comes before act."""
        text = skill_text()
        self.need("I could not tell which one you meant. Nothing was changed.", "Clearing 4, keeping 1: web-app · fix login")
        body = text.split("\n---\n", 1)[1]  # past the frontmatter, which names the commands
        self.assertLess(body.index("Clearing 4, keeping 1"), body.index("cleanup.py act"))

    def test_F61_the_report_lines(self):
        """@F61 @2026-11-14-tracker-session-cleanup SKILL.md holds the report lines and counts only what succeeded."""
        self.need("Cleanup done.", "Cleared 5 sessions.", "Removed 3 worktrees. Branches kept.", "Could not clear: web-app · fix login: <reason>",
                  "60 cells", "Kept, needs a look: web-app/login (uncommitted changes); api/users (2 commits not pushed).", "Skipped: docs (a session is running in it).",
                  "counts only what succeeded")

    def test_F62_a_needs_look_item_is_named_and_never_asked(self):
        """@F62 @2026-11-14-tracker-session-cleanup SKILL.md names a failed item as needs a look and never offers it in a question."""
        self.need("needs a look", "never offer")

    def test_F78_the_summaries_are_read_only_haiku_and_labels_are_quoted_data(self):
        """@F78 @2026-11-14-tracker-session-cleanup SKILL.md names haiku and read-only for the subagents, passes labels as quoted data; act takes no summary."""
        text = skill_text()
        self.need("model: haiku", "read-only", "quoted data")
        self.assertNotRegex(text, r"act [^\n]*summar")
        usage = subprocess.run([sys.executable, str(SCRIPT), "act", "--help"], capture_output=True, text=True).stdout
        self.assertNotIn("summar", usage)

    def test_F66_the_skill_allows_no_claude_or_git_and_no_model_runs_a_removal(self):
        """@F66 @2026-11-14-tracker-session-cleanup SKILL.md allows only the script, and says no model runs claude rm or a worktree removal."""
        self.assertNotRegex(taxonomy.parse(skill_text())[0]["allowed-tools"], r"Bash\((claude|git) ")
        self.need("Never run `claude` or `git` yourself")

    def test_F69_the_skills_output_stays_local(self):
        """@F69 @2026-11-14-tracker-session-cleanup SKILL.md uses no publishing tool and no URL."""
        text = skill_text()
        self.assertNotRegex(text, r"Artifact|Claude Docs|https?://")


if __name__ == "__main__":
    unittest.main()
