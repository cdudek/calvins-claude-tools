#!/usr/bin/env python3
"""Usage: prepare_task.py <repo> --start <sha> --reference <sha> --task-id <id> --plan <repo-relative plan path>
           --out ~/.factory/eval/tasks/<name> [--suite-cmd C] [--e2e-cmd C] [--setup C] [--preflight C ...]
           [--milestone M1] [--scenarios DIR] [--verifier-scenarios DIR] [--ticket-delta FILE]
           [--test-glob G ...] [--intent-from-outcome] [--timeout-s N] [--e2e-timeout-s N]
           [--env NAME=TEMPLATE ...] [--exclude-glob G ...] [--prove] [--fail-to-pass FILE ...] [--pass-to-pass-hidden FILE ...]
           [--port-env NAME] [--port-range LO HI] [--db-name TEMPLATE] [--db-env NAME] [--db-create C] [--db-drop C]
Turns a finished change into a replayable eval task, written to --out (private; refused inside <repo>):
  start.tar.gz          the tree at --start, no git history, no pax header; its plan as of --start
  hidden-tests/         files --reference added or changed that match a test glob (kept out of the run)
  scenarios/            eval-only prose scenarios, graded by the fixed grader
  verifier-scenarios/   scenarios the arm's own verifier may read (installed per run under ~/.factory/scenarios)
  ticket-delta.md       the raw-ticket delta for arms with context=raw
  task.json             everything run_eval.py and grade.py need
--env NAME=TEMPLATE exports NAME into every arm and grading run; the template may use {db} {port} {run}.
--exclude-glob leaves matching files (large assets such as evidence images) out of start.tar.gz.
--prove runs the hidden command per hidden file on the start tree and records fail_to_pass (failed at start) and
pass_to_pass_hidden (passed at start); --fail-to-pass / --pass-to-pass-hidden give the lists for tasks proven elsewhere
(files not named in --fail-to-pass are pass_to_pass_hidden unless --pass-to-pass-hidden says otherwise).
"""
import argparse
import fnmatch
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

import grade
import heavy

HERE = Path(__file__).resolve().parent
FACTORY = HERE.parents[1] / "plugins" / "factory"
MIGRATE = HERE / "migrate-ids.py"  # one-shot id rewrite for old replay trees, kept here, not in the runtime plugin
DEFAULT_GLOBS = ["*test*", "*spec*", "*/__tests__/*", "e2e/*", "*/e2e/*"]
ENTRY = re.compile(r"^###\s+(\d{4}-\d{2}-\d{2})\b")
BLOCK = re.compile(r"^```json factory[ \t]*\n(.*?)^```", re.S | re.M)


def git(repo, *args, raw=False, check=True):
    p = subprocess.run([*heavy.GIT, "-C", str(repo), *args], capture_output=True, check=check)
    return p.stdout if raw else p.stdout.decode().strip()


def strip_progress(text, start_date):
    """Drop progress-log entries (`### <date> ...` headings) dated after start_date; other text is kept."""
    out, skipping = [], False
    for line in text.splitlines(keepends=True):
        m = ENTRY.match(line)
        if m:
            skipping = m.group(1) > start_date
        elif line.startswith("## ") or (line.startswith("### ") and not m):
            skipping = False
        if not skipping:
            out.append(line)
    return "".join(out)


def outcome_sentence(plan_text):
    m = re.search(r"^## Outcome\s*\n+(.+?)(?:\n\s*\n|\n## |\Z)", plan_text, re.S | re.M)
    if not m:
        raise ValueError("the plan has no Outcome section for --intent-from-outcome")
    return " ".join(m.group(1).split())


def write_intent(folder, slug, plan_text):
    (folder / "intent.md").write_text(
        f"---\nstatus: approved\nauthor: eval\n---\n\n# Intent: {slug}\n\n## Problem\nSee the outcome.\n\n"
        f"## Outcome\n- outcome-1: {outcome_sentence(plan_text)}\n\n## Constraints\nnone\n", encoding="utf-8")


def migrate(tree):
    """Run the factory's migrate-ids.py on a throwaway git repo of the tree (it needs tracked files)."""
    g = [*heavy.GIT, "-C", str(tree), "-c", "user.email=eval@eval", "-c", "user.name=eval"]
    subprocess.run([*g, "init", "-q"], check=True)
    subprocess.run([*g, "add", "-A"], check=True)
    subprocess.run([*g, "commit", "-q", "-m", "x"], check=True)
    subprocess.run([sys.executable, str(MIGRATE), str(tree)], check=True, capture_output=True)
    shutil.rmtree(tree / ".git")


def pack(tree, dest):
    with tarfile.open(dest, "w:gz") as tf:
        for p in sorted(Path(tree).rglob("*")):
            info = tf.gettarinfo(str(p), arcname=str(p.relative_to(tree)))
            info.mtime, info.uid, info.gid, info.uname, info.gname = 0, 0, 0, "", ""
            if p.is_file() and not p.is_symlink():
                with open(p, "rb") as f:
                    tf.addfile(info, f)
            else:
                tf.addfile(info)


def export_start(repo, start, tree):
    data = git(repo, "archive", "--format=tar", start, raw=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as tf:
        tf.extractall(tree, filter="data")


def hidden_tests(repo, start, reference, globs):
    out = []
    for line in git(repo, "diff", "--name-status", "--no-renames", start, reference).splitlines():
        status, path = line.split("\t", 1)
        if status in ("A", "M") and any(fnmatch.fnmatch(path, g) for g in globs):
            out.append(path)
    return out


def reference_stat(repo, start, reference, tests):
    files, add, rem = [], 0, 0
    for line in git(repo, "diff", "--numstat", "--no-renames", start, reference).splitlines():
        a, r, path = line.split("\t", 2)
        files.append(path)
        add += int(a) if a.isdigit() else 0
        rem += int(r) if r.isdigit() else 0
    return {"files": len(files), "added": add, "removed": rem, "nontest_files": [f for f in files if f not in tests]}


def prove(out, tests, a, env_map):
    """Run the hidden command per hidden file on the packed start tree (what the arms get). Returns (fail_to_pass, pass_to_pass_hidden)."""
    tmpl = a.hidden_cmd or (a.suite_cmd + " {files}")
    db = re.sub(r"[^a-z0-9_]", "_", a.db_name.format(run="prove"))[:60] if a.db_name else None
    port = a.port_range[0] if a.port_env else None
    env = {**os.environ, "FACTORY_EVAL": "1", **grade.task_env({"env": env_map, "dbEnv": a.db_env, "portEnv": a.port_env}, "prove", db, port)}
    f2p, p2p = [], []
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp)
        with tarfile.open(out / "start.tar.gz") as tf:
            tf.extractall(tree, filter="data")
        if db and a.db_create:
            grade.sh(a.db_create.format(db=db), tree, env)
        try:
            if a.setup and grade.sh(a.setup, tree, env)[0]:
                sys.exit(f"--prove: the setup command failed: {a.setup}")
            for t in tests:
                dest, before = tree / t, None
                if dest.exists():
                    before = dest.read_bytes()
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(out / "hidden-tests" / t, dest)
                (p2p if grade.sh(tmpl.format(files=shlex.quote(t)), tree, env, a.e2e_timeout_s)[0] == 0 else f2p).append(t)
                dest.unlink()
                if before is not None:
                    dest.write_bytes(before)
        finally:
            if db and a.db_drop:
                grade.sh(a.db_drop.format(db=db), tree, env)
    return f2p, p2p


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo")
    ap.add_argument("--start", required=True)
    ap.add_argument("--reference", required=True)
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--suite-cmd", default="")
    ap.add_argument("--e2e-cmd", default="")
    ap.add_argument("--hidden-cmd", default="", help="command template for one hidden test file, {files} is replaced; default: suite command + file")
    ap.add_argument("--setup", default="")
    ap.add_argument("--preflight", action="append", default=[])
    ap.add_argument("--milestone", default="M1")
    ap.add_argument("--scenarios")
    ap.add_argument("--verifier-scenarios")
    ap.add_argument("--ticket-delta")
    ap.add_argument("--test-glob", action="append")
    ap.add_argument("--intent-from-outcome", action="store_true")
    ap.add_argument("--timeout-s", type=int, default=5400)
    ap.add_argument("--e2e-timeout-s", type=int, default=1800)
    ap.add_argument("--env", action="append", default=[], metavar="NAME=TEMPLATE", help="variable for every arm and grading run; {db} {port} {run} are replaced")
    ap.add_argument("--exclude-glob", action="append", default=[], help="leave matching files out of start.tar.gz")
    ap.add_argument("--prove", action="store_true", help="run the hidden command per hidden file at start; record fail_to_pass and pass_to_pass_hidden")
    ap.add_argument("--fail-to-pass", nargs="+", metavar="FILE", help="hidden files that fail at start (proven elsewhere)")
    ap.add_argument("--pass-to-pass-hidden", nargs="+", metavar="FILE", help="hidden files that already pass at start")
    ap.add_argument("--port-env", default="")
    ap.add_argument("--port-range", nargs=2, type=int, default=[4100, 4999])
    ap.add_argument("--db-name", default="", help="template, {run} is replaced by the run id")
    ap.add_argument("--db-env", default="")
    ap.add_argument("--db-create", default="", help="command template with {db}")
    ap.add_argument("--db-drop", default="")
    a = ap.parse_args(argv)

    repo, out = Path(a.repo).resolve(), Path(a.out).expanduser().resolve()
    if out == repo or repo in out.parents:
        sys.exit("refusing: --out is inside the repo; task data is private and lives outside it")
    start, ref = git(repo, "rev-parse", a.start), git(repo, "rev-parse", a.reference)
    start_date = git(repo, "show", "-s", "--format=%cs", start)
    env_map = {}
    for item in a.env:
        name, sep, tmpl = item.partition("=")
        if not sep or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            sys.exit(f"--env wants NAME=TEMPLATE, got {item!r}")
        env_map[name] = tmpl
    out.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / "tree"
        tree.mkdir()
        export_start(repo, start, tree)
        for p in sorted(tree.rglob("*"), reverse=True):
            if any(fnmatch.fnmatch(str(p.relative_to(tree)), g) for g in a.exclude_glob) and (p.is_file() or p.is_symlink()):
                p.unlink()
        plan_path = tree / a.plan
        folder = plan_path.parent
        if not plan_path.exists():  # the plan was written after --start: take its folder as the reference has it
            folder.mkdir(parents=True, exist_ok=True)
            names = git(repo, "ls-tree", "--name-only", ref, f"{folder.relative_to(tree)}/").splitlines()
            for n in names:
                (folder / Path(n).name).write_bytes(git(repo, "show", f"{ref}:{n}", raw=True))
        plan_text = strip_progress(plan_path.read_text(encoding="utf-8"), start_date)
        plan_path.write_text(plan_text, encoding="utf-8")
        slug = json.loads(BLOCK.search(plan_text).group(1))["change"]
        if a.intent_from_outcome:
            write_intent(folder, slug, plan_text)
            migrate(tree)
        pack(tree, out / "start.tar.gz")

    globs = a.test_glob or DEFAULT_GLOBS
    tests = hidden_tests(repo, start, ref, globs)
    for t in tests:
        dest = out / "hidden-tests" / t
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(git(repo, "show", f"{ref}:{t}", raw=True))
    for src, name in ((a.scenarios, "scenarios"), (a.verifier_scenarios, "verifier-scenarios")):
        if src:
            shutil.copytree(src, out / name, dirs_exist_ok=True)
    if a.ticket_delta:
        shutil.copy(a.ticket_delta, out / "ticket-delta.md")

    lists = {}
    if a.prove:
        lists["fail_to_pass"], lists["pass_to_pass_hidden"] = prove(out, tests, a, env_map)
    if a.fail_to_pass is not None or a.pass_to_pass_hidden is not None:
        f2p = a.fail_to_pass if a.fail_to_pass is not None else [t for t in tests if t not in (a.pass_to_pass_hidden or [])]
        p2p = a.pass_to_pass_hidden if a.pass_to_pass_hidden is not None else [t for t in tests if t not in f2p]
        stray = [t for t in (*f2p, *p2p) if t not in tests]
        if stray:
            sys.exit(f"not hidden test files of this task: {stray}")
        lists = {"fail_to_pass": f2p, "pass_to_pass_hidden": p2p}
    task = {"task_id": a.task_id, "slug": slug, "milestone": a.milestone, "plan": a.plan, "start": start, "reference": ref,
            "suite_cmd": a.suite_cmd, "e2e_cmd": a.e2e_cmd, "hidden_cmd": a.hidden_cmd, "setup": a.setup, "preflight": a.preflight,
            "timeout_s": a.timeout_s, "e2e_timeout_s": a.e2e_timeout_s, "hidden_tests": tests,
            "reference_stat": reference_stat(repo, start, ref, tests), "intent_from_outcome": a.intent_from_outcome,
            "portEnv": a.port_env, "portRange": a.port_range, "dbName": a.db_name, "dbEnv": a.db_env,
            "dbCreate": a.db_create, "dbDrop": a.db_drop, "env": env_map, **lists}
    (out / "task.json").write_text(json.dumps(task, indent=1) + "\n", encoding="utf-8")
    print(f"task {a.task_id}: {len(tests)} hidden test files{' (%d fail-to-pass)' % len(lists['fail_to_pass']) if lists else ''}, start {start[:10]}, reference {ref[:10]} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
