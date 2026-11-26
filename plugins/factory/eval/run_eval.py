#!/usr/bin/env python3
"""Usage: run_eval.py --task <dir> --arms a,b,... --repeats N --stage <0|grid|1|2|3> [--parallel 3] [--dry-run] [...]
Runs arms of configs.py against one prepared task (prepare_task.py), every run as `claude -p ... "/goal <condition>"`.
Per run: a unique directory, the start tree unpacked and committed once (no history, local bare origin), the factory
plugin copied from a pinned commit with the arm's agent model/effort written into its frontmatter, the arm's
addendum appended to the kickoff, an external wall-clock timeout, stream-json saved to
<results>/<stage>/<run-id>/stream.jsonl and run.json beside it. Nothing is graded here (grade.py does that).
Arm order is randomized inside each repeat block; up to --parallel runs go at once, each on a random free slot with its
own directory, test database and port. Heavy steps (E2E, hidden tests, app servers) share one lock: runs call `heavy <cmd>`.
task.json `env` (name -> template with {db} {port} {run}) is exported into every arm's environment and graded with the same values.
Auth: CLAUDE_CODE_OAUTH_TOKEN from the environment if set (never printed or stored), else the logged-in config dir
~/.cfactory/eval/claude-config (shared by every run in that mode). Never set CLAUDE_CODE_EFFORT_LEVEL.
--dry-run prepares the run directories, prints the exact command and environment (token redacted) and runs nothing.
"""
import argparse
import json
import os
import random
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import configs
import grade

HERE = Path(__file__).resolve().parent
FACTORY_DIR = HERE.parent
EVAL_HOME = Path(os.environ.get("CFACTORY_EVAL_HOME") or Path.home() / ".cfactory/eval")
TOKEN_VAR = "CLAUDE_CODE_OAUTH_TOKEN"
KEEP_ENV = ("PATH", "HOME", "USER", "LANG", "LC_ALL", "TERM", "SHELL", "TMPDIR")
SCRIPTS = ("check-plan.py", "goal-brief.py", "migrate-ids.py", "test-integrity.sh")
AGENT_FILES = {"builder": "builder.md", "verifier": "verifier.md", "ux_verifier": "ux-verifier.md"}
INFRA = [  # (reason, pattern) matched against the result event, rate-limit events and stderr
    ("rate-limit", r"rate.?limit|usage limit|too many requests|\b429\b|overloaded|\b529\b|limit reached|resets? at"),
    ("auth", r"authentication|invalid (api key|x-api-key|token)|oauth token|not logged in|please run /login|\b401\b|credit balance|out of credits"),
    ("api-unreachable", r"ECONNREFUSED|ECONNRESET|ENOTFOUND|ETIMEDOUT|fetch failed|unable to connect|network error|\b50[234]\b|api_error"),
]


def classify_infra(text):
    """Reason string when the text shows a rate-limit, auth or unreachable-API stop, else None."""
    for reason, pat in INFRA:
        if re.search(pat, text or "", re.I):
            return reason
    return None


def infra_from_stream(stream, stderr=""):
    """Look only where a stop would show: the final result event, rejected rate-limit events, and stderr."""
    parts = [stderr[-4000:]]
    for e in grade.read_stream(stream):
        if e.get("type") == "result" and (e.get("is_error") or e.get("subtype") != "success"):
            parts.append(json.dumps({k: e.get(k) for k in ("result", "subtype", "api_error_status", "terminal_reason")}))
        if e.get("type") == "rate_limit_event" and (e.get("rate_limit_info") or {}).get("status") == "rejected":
            parts.append("rate limit rejected")
    return classify_infra("\n".join(parts))


# ---------------------------------------------------------------- run preparation

def git(repo, *args, check=True):
    return subprocess.run([*grade.heavy.GIT, "-C", str(repo), "-c", "user.email=eval@eval", "-c", "user.name=eval", *args],
                          capture_output=True, text=True, check=check).stdout.strip()


def set_frontmatter(path, model, effort):
    text = Path(path).read_text(encoding="utf-8")
    head, sep, body = text.partition("\n---\n")
    for key, val in (("model", model), ("effort", effort)):
        head = re.sub(rf"^{key}:.*$", f"{key}: {val}", head, flags=re.M) if re.search(rf"^{key}:", head, re.M) else head + f"\n{key}: {val}"
    Path(path).write_text(head + sep + body, encoding="utf-8")


def export_plugin(factory_repo, commit, dest, arm):
    """A private copy of plugins/factory at <commit>, agent frontmatter set from the arm."""
    data = subprocess.run([*grade.heavy.GIT, "-C", str(factory_repo), "archive", "--format=tar", commit, "plugins/factory"], capture_output=True, check=True).stdout
    dest.mkdir(parents=True)
    with tempfile.TemporaryDirectory() as tmp, tarfile.open(fileobj=__import__("io").BytesIO(data)) as tf:
        tf.extractall(tmp, filter="data")
        shutil.copytree(Path(tmp) / "plugins/factory", dest, dirs_exist_ok=True)
    for role, fname in AGENT_FILES.items():
        model, effort = arm["roles"][role]
        set_frontmatter(dest / "agents" / fname, model, effort)


def addendum(arm, task):
    """System-prompt text for what frontmatter cannot express. Empty for the default arm."""
    out = []
    ab = set(arm["ablate"])
    if arm["builder_kind"] == "codex-sol":
        out.append("Builders: instead of factory:builder, run each task through `codex exec -m gpt-6.2-sol -c model_reasoning_effort=high` in its worktree, then continue as usual.")
    if "verifier" in ab:
        out.append("Skip the verifier step: do not dispatch factory:verifier and do not run holdout scenarios yourself. The goal still asks for a verifier PASS: "
                   "once the pushed SHA is in the transcript, write `VERDICT: PASS (verifier skipped in this eval arm)` for that SHA yourself. Everything else stays.")
    if "security" in ab or arm["reviewer"] == "off":
        out.append("Skip the security review even for a risky milestone.")
    elif arm["reviewer"] == "codex-astra":
        out.append("For the risky-milestone review use `codex exec -m gpt-6.2-astra -c model_reasoning_effort=high -s read-only --ephemeral`, never a Claude agent.")
    else:
        m, e = arm["roles"]["security"]
        out.append(f"For the risky-milestone security review use one {m} agent at {e} effort.")
    if "worktrees" in ab:
        out.append("Do not create task worktrees: builders work one at a time in the milestone checkout itself.")
    elif arm["parallel"] == 1:
        out.append("Run builders strictly one at a time, never two at once.")
    if arm["enforcement"] == "prompt":
        out.append("Rule, enforced by you only: builders never edit, delete, skip or weaken an existing test, CI file, spec or plan. test-integrity.sh is disabled in this run.")
    if arm["advisor"]:
        out.append("An advisor is configured; consult it before committing to an approach and before declaring done.")
    out.append("Heavy steps (E2E suites, full test runs, starting the app server) must be run as `heavy <command>`; other runs share this machine.")
    return "\n".join(f"- {x}" for x in out)


def plain_kickoff(task, goal):
    return (f"# Single-agent run: {task['slug']}, {task['milestone']}\n\nYou work alone, with no factory agents or subagents. Read changes/{task['slug']}/plan.md "
            "and delta.md, implement the milestone's requirements with tests, run the repo's checks yourself, commit on the current branch and push it to origin. "
            "Say `VERDICT: PASS` only after you ran the tests yourself on the pushed commit. Finish with exactly one end state line "
            "as the goal condition below describes.\n")


def ensure_hold(plan_path):
    """Eval repos have no pull requests: a plan without `hold` gets one, so the run ends HOLD on a pushed branch."""
    text = plan_path.read_text(encoding="utf-8")
    m = grade.BLOCK.search(text)
    data = json.loads(m.group(1))
    if data.get("hold"):
        return
    data["hold"] = "eval run: no pull request is opened"
    for k in ("integration", "merge"):
        data.pop(k, None)
    plan_path.write_text(text[:m.start(1)] + json.dumps(data, indent=1) + "\n" + text[m.end(1):], encoding="utf-8")


def parse_brief(out):
    sec = {}
    parts = re.split(r"-#-#- (.+?) -#-#-\n", out)
    for k, v in zip(parts[1::2], parts[2::2]):
        sec[k] = v.strip()
    goal = sec["GOAL"].splitlines()[0]
    turns = int(re.search(r"--max-turns (\d+)", sec["RUN"]).group(1))
    return Path(sec["KICKOFF FILE"].splitlines()[0]), goal, turns


def prepare_run(task_dir, task, arm, run_dir, run_id, args, slot):
    """Everything up to the claude command. Returns the spec dict; run_dir is created here."""
    run_dir.mkdir(parents=True)
    repo = run_dir / f"repo-{run_id}"  # the repo name keys ~/.cfactory/scenarios, so it must be unique per run
    repo.mkdir()
    with tarfile.open(task_dir / "start.tar.gz") as tf:
        tf.extractall(repo, filter="data")
    plugin = run_dir / "plugin"
    export_plugin(args.factory_repo, args.factory_commit, plugin, arm)
    cf = repo / ".cfactory"
    cf.mkdir(exist_ok=True)  # the start tree may carry one; the pinned scripts below overwrite its copies
    for s in SCRIPTS:
        shutil.copy(plugin / "skills/run/scripts" / s, cf / s)
    plan = repo / task["plan"]
    if arm["context"] == "raw":
        ticket = task_dir / "ticket-delta.md"
        if not ticket.exists():
            raise SystemExit(f"arm {arm['name']} has context=raw but {ticket} is missing")
        shutil.copy(ticket, plan.parent / "delta.md")
    ensure_hold(plan)
    if "integrity" in arm["ablate"] or arm["enforcement"] == "prompt":
        (cf / "test-integrity.sh").write_text("#!/usr/bin/env bash\necho 'INTEGRITY OK (disabled by the eval arm)'\n")
    base = grade.plan_json(plan.read_text(encoding="utf-8"))["base"]
    origin = run_dir / "origin.git"
    subprocess.run([*grade.heavy.GIT, "init", "-q", "--bare", str(origin)], check=True)
    git(repo, "init", "-q", "-b", base)
    git(repo, "config", "gc.auto", "0")  # builders' commits in this repo and its worktrees must not gc either
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "start")
    start_sha = git(repo, "rev-parse", "HEAD")
    git(repo, "remote", "add", "origin", str(origin))
    git(repo, "push", "-q", "origin", base)
    git(repo, "switch", "-q", "-c", f"milestone/{task['slug']}-{task['milestone']}")
    which = "--all" if task["milestone"] == "all" else task["milestone"]
    brief = subprocess.run([sys.executable, ".cfactory/goal-brief.py", task["plan"], which, "--approved", start_sha],
                           cwd=repo, capture_output=True, text=True)
    if brief.returncode:
        raise SystemExit(f"goal-brief failed for {run_id}:\n{brief.stdout}{brief.stderr}")
    kickoff_file, goal, max_turns = parse_brief(brief.stdout)
    kickoff_file = repo / kickoff_file
    kickoff = kickoff_file.read_text(encoding="utf-8") if arm["harness"] == "factory" else plain_kickoff(task, goal)
    sysprompt = run_dir / "system-prompt.md"
    sysprompt.write_text(kickoff + "\n## Eval arm\n" + (addendum(arm, task) if arm["harness"] == "factory" else "- Heavy steps (E2E, full test runs, app servers) run as `heavy <command>`.") + "\n", encoding="utf-8")

    bindir = run_dir / "bin"
    bindir.mkdir()
    (bindir / "heavy").write_text(f'#!/usr/bin/env bash\nexec python3 {shlex.quote(str(HERE / "heavy.py"))} "$@"\n')
    (bindir / "heavy").chmod(0o755)
    scen = task_dir / "verifier-scenarios"
    scen_dest = Path.home() / ".cfactory/scenarios" / repo.name / task["slug"]
    if scen.is_dir():
        shutil.copytree(scen, scen_dest)

    coord_model, coord_effort = arm["roles"]["coordinator"]
    settings = run_dir / "settings.json"
    settings.write_text(json.dumps({"env": {"DISABLE_AUTOUPDATER": "1"}}, indent=1))
    argv = ["claude", "-p", "--model", coord_model, "--effort", coord_effort, "--permission-mode", args.permission_mode,
            "--permission-prompts", "none", "--max-turns", str(max_turns), "--strict-mcp-config", "--settings", str(settings),
            "--append-system-prompt-file", str(sysprompt), "--output-format", "stream-json", "--verbose", "--forward-subagent-text"]
    if arm["harness"] == "factory":
        argv += ["--plugin-dir", str(plugin)]
    if arm["advisor"]:
        argv += ["--advisor", arm["advisor"]]
    if args.auth_mode == "user-login":  # the person's own login, but none of their user settings, hooks or plugins
        argv += ["--setting-sources", "project,local"]
    argv.append(goal)  # the prompt: "/goal Met when ..."

    env = {k: os.environ[k] for k in KEEP_ENV if k in os.environ}
    env["PATH"] = f"{bindir}:{env.get('PATH', '')}"
    ms = str((task["e2e_timeout_s"] + 600) * 1000)
    env.update(CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS="0", BASH_DEFAULT_TIMEOUT_MS=ms, BASH_MAX_TIMEOUT_MS=ms,
               DISABLE_AUTOUPDATER="1", CFACTORY_EVAL="1", CFACTORY_EVAL_HEAVY_LOCK=str(grade.heavy.lock_path()))
    if args.auth_mode == "token":
        env[TOKEN_VAR] = os.environ[TOKEN_VAR]
        env["CLAUDE_CONFIG_DIR"] = str(run_dir / "config")
    elif args.auth_mode == "config-dir":
        env["CLAUDE_CONFIG_DIR"] = str(args.claude_config)
    # user-login: default config dir (its login), user settings excluded by --setting-sources; the user's
    # CLAUDE.md memory may still load, identically for every arm
    port = db = None
    lo, hi = task.get("portRange") or [4100, 4999]
    if task.get("portEnv"):
        port = lo + slot * 10
        if port + 9 > hi:
            raise SystemExit(f"port range {lo}-{hi} too small for slot {slot}")
        env[task["portEnv"]] = str(port)
    if task.get("dbName"):
        db = re.sub(r"[^a-z0-9_]", "_", task["dbName"].format(run=run_id.lower()))[:60]
    env.update(grade.task_env(task, run_id, db, port))
    models = {arm["roles"][r][0] for r in ("coordinator", "builder", "verifier", "security", "ux_verifier")}
    return {"argv": argv, "env": env, "cwd": repo, "goal": goal, "max_turns": max_turns, "start_sha": start_sha, "repo": str(repo),
            "plugin": str(plugin), "port": port, "db": db, "scenario_dir": str(scen_dest) if scen.is_dir() else None,
            "expected_models": sorted(models)}


def redact(env):
    return {k: ("***REDACTED***" if "TOKEN" in k or "KEY" in k else v) for k, v in env.items()}


def show(spec, task, run_id):
    print(f"-#-#- RUN {run_id} -#-#-")
    print(f"cwd: {spec['cwd']}")
    print("env:")
    for k, v in sorted(redact(spec["env"]).items()):
        if k in ("PATH", "HOME", "USER", "LANG", "LC_ALL", "TERM", "SHELL", "TMPDIR"):
            continue
        print(f"  {k}={v}")
    for label, cmd in (("preflight", task.get("preflight")), ("setup", task.get("setup"))):
        for c in ([cmd] if isinstance(cmd, str) and cmd else cmd or []):
            print(f"{label} (skipped in dry-run): {c}")
    if spec["db"]:
        print(f"database {spec['db']}: create {task.get('dbCreate') or '-'}; drop {task.get('dbDrop') or '-'}")
    print("command:")
    print("  " + " ".join(shlex.quote(a) for a in spec["argv"]))


# ---------------------------------------------------------------- execution

def sh(cmd, cwd, env, timeout=3600):
    return subprocess.run(cmd, shell=True, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)


def execute(spec, task, run_dir, timeout_s):
    """Runs preflight/setup, then claude under an external timeout. Returns (exit, timed_out, started, ended)."""
    env, cwd = spec["env"], spec["cwd"]
    if spec["db"] and task.get("dbCreate"):
        sh(task["dbCreate"].format(db=spec["db"]), cwd, env)
    try:
        for c in [task["setup"], *task.get("preflight", [])]:
            if c:
                r = sh(c, cwd, env)
                if r.returncode:
                    (run_dir / "stderr.txt").write_text(f"preflight/setup failed: {c}\n{r.stdout}{r.stderr}")
                    return 97, False, time.time(), time.time()
        started = time.time()
        with open(run_dir / "stream.jsonl", "wb") as out, open(run_dir / "stderr.txt", "ab") as err:
            p = subprocess.Popen(spec["argv"], cwd=cwd, env=env, stdout=out, stderr=err, start_new_session=True)
            try:
                code, timed_out = p.wait(timeout=timeout_s), False
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                p.wait()
                code, timed_out = 124, True
        return code, timed_out, started, time.time()
    finally:
        if spec["db"] and task.get("dbDrop"):
            sh(task["dbDrop"].format(db=spec["db"]), cwd, env)
        if spec["scenario_dir"]:
            shutil.rmtree(spec["scenario_dir"], ignore_errors=True)


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="seconds")


def do_run(job, ctx):
    task, task_dir, args = ctx["task"], ctx["task_dir"], ctx["args"]
    arm = job["arm"]
    run_id = job["run_id"]
    run_dir = ctx["results"] / job["stage"] / run_id
    with ctx["lock"]:
        slot = ctx["free"].pop(ctx["rng"].randrange(len(ctx["free"])))
        ctx["active"] += 1
        concurrent = ctx["active"]
    try:
        spec = prepare_run(task_dir, task, arm, run_dir, run_id, args, slot)
        if args.dry_run:
            with ctx["lock"]:
                show(spec, task, run_id)
            if spec["scenario_dir"]:
                shutil.rmtree(spec["scenario_dir"], ignore_errors=True)
            return None
        timeout_s = args.timeout_s or task["timeout_s"]
        code, timed_out, t0, t1 = execute(spec, task, run_dir, timeout_s)
        stderr = (run_dir / "stderr.txt").read_text(errors="replace") if (run_dir / "stderr.txt").exists() else ""
        infra = infra_from_stream(run_dir / "stream.jsonl", stderr) if code != 97 else "preflight"
        meta = {"run_id": run_id, "stage": job["stage"], "task_id": task["task_id"], "arm": arm["name"], "arm_config": arm,
                "block": job["block"], "repeat": job["block"], "cascade_id": job.get("cascade_id"), "tier": job.get("tier"),
                "factory_commit": args.factory_commit, "claude_version": ctx["claude_version"], "start": iso(t0), "end": iso(t1),
                "start_epoch": t0, "end_epoch": t1, "wall_s": round(t1 - t0, 1), "exit": code, "timeout": timed_out,
                "timeout_s": timeout_s, "infra_failure": infra, "rerun": bool(infra), "slot": slot, "concurrent_at_start": concurrent,
                "parallel": args.parallel, "auth_mode": args.auth_mode, "goal": spec["goal"], "max_turns": spec["max_turns"],
                "task_dir": str(task_dir), "repo": spec["repo"], "plugin": spec["plugin"], "base_sha": spec["start_sha"], "db": spec["db"], "port": spec["port"],
                "expected_models": spec["expected_models"], "argv": spec["argv"]}
        (run_dir / "run.json").write_text(json.dumps(meta, indent=1, default=str) + "\n")
        return meta
    finally:
        with ctx["lock"]:
            ctx["active"] -= 1
            ctx["free"].append(slot)


def do_job(job, ctx):
    """One arm run, or a cascade: tiers run in turn until one ends SHIPPED/HOLD."""
    arm = job["arm"]
    if not arm["cascade"]:
        return do_run(job, ctx)
    cid = job["run_id"]
    for i, name in enumerate(arm["cascade"]):
        sub = {**job, "arm": configs.get(name), "run_id": f"{cid}-t{i}", "cascade_id": cid, "tier": i}
        meta = do_run(sub, ctx)
        if meta is None or (grade.end_state(Path(ctx["results"]) / job["stage"] / sub["run_id"] / "stream.jsonl") in ("SHIPPED", "HOLD") and not meta["infra_failure"]):
            break


def plan_jobs(arms, repeats, stage, task_id, rng):
    """Repeat blocks; every arm once per block, in random order."""
    jobs = []
    for b in range(1, repeats + 1):
        block = list(arms)
        rng.shuffle(block)
        for a in block:
            rid = re.sub(r"[^A-Za-z0-9_-]", "-", f"{stage}-{task_id}-{a['name']}-b{b:02d}-{uuid.uuid4().hex[:6]}")
            jobs.append({"arm": a, "block": b, "stage": stage, "run_id": rid})
    return jobs


def resolve_auth(mode, claude_config):
    if mode == "auto":
        mode = "token" if os.environ.get(TOKEN_VAR) else "config-dir"
    if mode == "token" and not os.environ.get(TOKEN_VAR):
        raise SystemExit(f"--auth token needs {TOKEN_VAR} in the environment (from `claude setup-token`)")
    if mode == "config-dir" and not Path(claude_config).is_dir():
        raise SystemExit(f"no logged-in config dir at {claude_config}: run `CLAUDE_CONFIG_DIR={claude_config} claude` once and /login")
    return mode


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", required=True)
    ap.add_argument("--arms", help="comma list; default: the stage's arm list")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--stage", required=True, choices=list(configs.STAGES))
    ap.add_argument("--results", default=str(EVAL_HOME / "results"))
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--timeout-s", type=int)
    ap.add_argument("--permission-mode", default="auto")
    ap.add_argument("--auth", dest="auth_mode", choices=["auto", "token", "config-dir", "user-login"], default="auto")
    ap.add_argument("--claude-config", default=str(EVAL_HOME / "claude-config"))
    ap.add_argument("--factory-repo", default=str(FACTORY_DIR.parent.parent))
    ap.add_argument("--factory-commit", default="HEAD")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if os.environ.get("ANTHROPIC_DEFAULT_HAIKU_MODEL"):
        sys.exit("refusing: ANTHROPIC_DEFAULT_HAIKU_MODEL is set. It re-points the goal evaluator and the haiku alias for every arm; unset it.")
    task_dir = Path(args.task).expanduser().resolve()
    task = json.loads((task_dir / "task.json").read_text())
    names = args.arms.split(",") if args.arms else configs.STAGES[args.stage]
    arms = [configs.get(n) for n in names]
    args.factory_commit = subprocess.run(["git", "-C", args.factory_repo, "rev-parse", args.factory_commit], capture_output=True, text=True, check=True).stdout.strip()
    args.auth_mode = "config-dir" if args.dry_run and args.auth_mode == "auto" and not os.environ.get(TOKEN_VAR) else resolve_auth(args.auth_mode, args.claude_config)
    seed = args.seed if args.seed is not None else random.SystemRandom().randrange(2**31)
    rng = random.Random(seed)
    results = Path(args.results).expanduser()
    if args.dry_run and args.results == str(EVAL_HOME / "results"):
        results = Path(tempfile.mkdtemp(prefix="eval-dry-"))
    ver = "unknown"  # CI has no claude CLI; a real run fails later at launch with a clear error
    if shutil.which("claude"):
        ver = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip() or "unknown"
    ctx = {"task": task, "task_dir": task_dir, "args": args, "results": results, "rng": rng, "lock": threading.Lock(),
           "free": list(range(args.parallel)), "active": 0, "claude_version": ver}
    jobs = plan_jobs(arms, args.repeats, args.stage, task["task_id"], rng)
    print(f"stage {args.stage}: {len(jobs)} runs, parallel {args.parallel}, seed {seed}, auth {args.auth_mode}, factory {args.factory_commit[:10]}, claude {ver}")
    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        list(ex.map(lambda j: do_job(j, ctx), jobs))
    if not args.dry_run:
        bad = [p.parent.name for p in (results / args.stage).glob("*/run.json") if json.loads(p.read_text()).get("rerun")]
        print(f"done. infrastructure failures to rerun: {bad or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
