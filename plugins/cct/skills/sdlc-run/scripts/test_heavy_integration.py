"""Group B of 3.21.0: the heavy-job queue and fail-fast wired into the gate, the hooks and the
status code (docs/designs/heavy-integration.md), plus the two risks left by the layout-4 work."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from test_sdd_wiring import ID, approved, base_repo, commit, gate, last, rule, sh, v4

SCRIPTS = Path(__file__).resolve().parents[1] / "templates" / "scripts"


# ---------------------------------------------------------------- risk: no resolvable parent


def _lose_the_parent(repo: Path) -> None:
    """master is gone and the configured default never existed: nothing to diff against."""
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "defaultBranch": "trunk"}))
    commit(repo, "config")
    sh(repo, "git", "branch", "-m", "master", "elsewhere")


def test_approve_without_a_resolvable_parent_is_an_env_handoff_with_a_fix_line(tmp_path: Path) -> None:
    repo = base_repo(tmp_path)
    v4(repo)
    commit(repo)
    _lose_the_parent(repo)
    r = gate(repo, "approve", ID)
    assert r.returncode == 3, r.stdout + r.stderr
    assert last(r) == "APPROVE BLOCKED reason=env"
    assert "Fix:" in r.stdout and "trunk" in r.stdout and "Traceback" not in r.stderr


def test_the_milestone_gate_without_a_resolvable_parent_is_an_env_handoff(tmp_path: Path) -> None:
    repo = base_repo(tmp_path)
    c = v4(repo)
    approved(repo, c)
    rule(repo, "billing", 1)
    commit(repo)
    _lose_the_parent(repo)
    r = gate(repo, "milestone", ID)
    assert r.returncode == 3, r.stdout + r.stderr
    assert last(r) == "VERIFY BLOCKED reason=env"
    assert "Fix:" in r.stdout and "Traceback" not in r.stderr


# ---------------------------------------------------------------- risk: marks.py without spec.py


def test_marks_py_runs_without_spec_py_unless_layout_4_is_in_use(tmp_path: Path) -> None:
    lone = tmp_path / "lone"
    lone.mkdir()
    (lone / "marks.py").write_text((SCRIPTS / "marks.py").read_text())
    imported = subprocess.run(
        [sys.executable, "-c", "import marks"], cwd=lone, capture_output=True, text=True
    )
    assert imported.returncode == 0, imported.stderr
    repo = tmp_path / "repo"
    change = repo / "changes" / "2026-10-21-old"
    change.mkdir(parents=True)
    (repo / "sdlc.json").write_text("{}")
    r = subprocess.run(
        [sys.executable, str(lone / "marks.py"), "check", change.name],
        cwd=repo, capture_output=True, text=True,
    )  # fmt: skip
    assert "ModuleNotFoundError" not in r.stderr and "Traceback" not in r.stderr, r.stderr


# ---------------------------------------------------------------- the gate runs under the queue

import os  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402
import shlex  # noqa: E402
import time  # noqa: E402

from test_verify_gate import ID as GID  # noqa: E402
from test_verify_gate import _approve, _env, _git, _last, _repo  # noqa: E402

HEAVY = SCRIPTS / "heavy.py"


def _milestone(tmp_path: Path, checks: list, **extra: object) -> Path:
    repo = _repo(tmp_path, [])
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "checks": {"milestone": checks}, **extra}))
    _git(repo, "commit", "-qam", "milestone checks")
    _approve(repo)
    return repo


MARK = {"patterns": ["heavy-marker"]}  # the repo's own override: any command with this word queues


def _run_gate(
    repo: Path, queue: Path, *prefix: str, timeout: int = 90, gate: Path | None = None, **env_extra: str
) -> subprocess.CompletedProcess[str]:
    env = {**_env(), "SDLC_HEAVY_DIR": str(queue), "SDLC_HEAVY_SLOTS": "1", "SDLC_HEAVY_POLL": "0.1", **env_extra}
    return subprocess.run(
        [*prefix, sys.executable, str(gate or SCRIPTS / "verify_gate.py"), "milestone", GID],
        cwd=repo, capture_output=True, text=True, env=env, timeout=timeout,
    )  # fmt: skip


def test_a_heavy_check_runs_in_a_slot_and_a_light_one_does_not(tmp_path: Path) -> None:
    seen = tmp_path / "seen"
    repo = _milestone(
        tmp_path,
        [
            {"name": "light", "run": f"echo \"light=$SDLC_HEAVY_SLOT\" >> {seen}"},
            {"name": "suite", "run": f"echo \"heavy-marker=$SDLC_HEAVY_SLOT\" >> {seen}"},
        ],
        heavy=MARK,
    )
    r = _run_gate(repo, tmp_path / "queue")
    assert _last(r).startswith(f"VERIFY PASS milestone {GID}"), r.stdout + r.stderr
    lines = set(seen.read_text().split())
    assert lines == {"light=", "heavy-marker=0"}, lines


def test_a_gate_already_inside_a_slot_passes_straight_through(tmp_path: Path) -> None:
    repo = _milestone(tmp_path, [{"name": "suite", "run": "echo heavy-marker"}], heavy=MARK)
    r = _run_gate(
        repo, tmp_path / "queue", sys.executable, str(HEAVY), "run", "--wait-timeout", "5", "--", timeout=60
    )
    assert _last(r).startswith(f"VERIFY PASS milestone {GID}"), r.stdout + r.stderr


def _hold_the_slot(queue: Path, pid: int, **extra: object) -> None:
    """A ticket for a live process that holds slot 0 (the real holder is `sleep`, started by the test)."""
    (queue / "tickets").mkdir(parents=True, exist_ok=True)
    now = time.time()
    (queue / "tickets" / f"{time.time_ns() - 10**9:020d}-{pid}.json").write_text(
        json.dumps({"pid": pid, "cmd": ["sleep", "30"], "slot": 0, "since": now, "started": now, "worktree": "/w", **extra})
    )


def test_a_slot_held_past_its_own_deadline_is_an_env_handoff_naming_the_holder(tmp_path: Path) -> None:
    queue = tmp_path / "queue"
    repo = _milestone(tmp_path, [{"name": "suite", "run": "echo heavy-marker"}], heavy={**MARK, "waitTimeout": 1})
    holder = subprocess.Popen(["sleep", "30"])
    try:
        _hold_the_slot(queue, holder.pid, cap=1, started=time.time() - 100)  # outlived its own deadline
        r = _run_gate(repo, queue, SDLC_HEAVY_GRACE="0")
    finally:
        holder.kill()
        holder.wait()
    assert r.returncode == 3 and _last(r) == "VERIFY BLOCKED reason=env", r.stdout + r.stderr
    assert "sleep" in r.stdout and "suite" in r.stdout and "no slot after" in r.stdout


def test_the_gate_waits_without_a_deadline_while_the_holder_is_alive(tmp_path: Path) -> None:
    queue = tmp_path / "queue"
    repo = _milestone(tmp_path, [{"name": "suite", "run": "echo heavy-marker"}], heavy={**MARK, "waitTimeout": 1})
    holder = subprocess.Popen(
        [sys.executable, str(HEAVY), "run", "--run-timeout", "0", "--", "sleep", "3"],
        env={**_env(), "SDLC_HEAVY_DIR": str(queue)}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):  # until the holder has its slot
            if list((queue / "tickets").glob("*.json")):
                break
            time.sleep(0.1)
        r = _run_gate(repo, queue)
    finally:
        holder.kill()
        holder.wait()
    assert _last(r).startswith(f"VERIFY PASS milestone {GID}"), r.stdout + r.stderr  # waited 3 s with a 1 s deadline


def test_the_gate_takes_one_slot_for_every_heavy_check_and_nested_heavy_calls_pass(tmp_path: Path) -> None:
    seen, queue = tmp_path / "seen", tmp_path / "queue"
    nested = f"{sys.executable} {HEAVY} run --wait-timeout 2 -- sh -c 'echo nested >> {seen}'"
    repo = _milestone(
        tmp_path,
        [
            {"name": "suite", "run": f"echo \"heavy-marker holder=$SDLC_HEAVY_HOLDER slot=$SDLC_HEAVY_SLOT tickets=$(ls {queue}/tickets | wc -l)\" >> {seen}"},
            {"name": "e2e", "run": f"echo heavy-marker; {nested}; echo \"heavy-marker holder=$SDLC_HEAVY_HOLDER\" >> {seen}"},
        ],
        heavy=MARK,
    )
    r = _run_gate(repo, queue)
    assert _last(r).startswith(f"VERIFY PASS milestone {GID}"), r.stdout + r.stderr
    lines = seen.read_text().splitlines()
    holders = {w.split("=")[1] for line in lines for w in line.split() if w.startswith("holder=")}
    assert len(holders) == 1 and holders != {""}, lines
    first = lines[0].split()
    assert first[0] == "heavy-marker" and first[2] == "slot=0" and "".join(first[3:]) == "tickets=1", lines
    assert "nested" in lines
    assert list((queue / "tickets").glob("*.json")) == [], "the slot is released at the end"


def test_the_gate_reports_seconds_queue_wait_and_total(tmp_path: Path) -> None:
    repo = _milestone(tmp_path, [{"name": "lint", "run": "true"}, {"name": "suite", "run": "echo heavy-marker"}], heavy=MARK)
    r = _run_gate(repo, tmp_path / "queue")
    line = next(x for x in r.stdout.splitlines() if x.startswith("timing:"))
    assert re.fullmatch(r"timing: queue wait \d+(\.\d)?s, total \d+(\.\d)?s; \w+ [\d.]+s, \w+ [\d.]+s", line), line
    report = json.loads((repo / "changes" / GID / "verify" / "report.json").read_text())
    assert "queue_wait_s" in report["metrics"] and _last(r).startswith("VERIFY PASS")


def test_light_checks_run_side_by_side_before_the_slot(tmp_path: Path) -> None:
    a, b = (tmp_path / "a"), (tmp_path / "b")
    both = lambda mine, other: f"touch {mine}; i=0; while [ ! -e {other} ] && [ $i -lt 100 ]; do sleep 0.05; i=$((i+1)); done; test -e {other}"  # noqa: E731
    repo = _milestone(
        tmp_path,
        [{"name": "lint", "run": both(a, b)}, {"name": "types", "run": both(b, a)}],
    )  # each waits for the other: only a parallel run can pass
    r = _run_gate(repo, tmp_path / "queue")
    assert _last(r).startswith(f"VERIFY PASS milestone {GID}"), r.stdout + r.stderr


def test_a_light_check_after_a_serial_wall_does_not_run_before_it(tmp_path: Path) -> None:
    log = tmp_path / "log"
    repo = _milestone(
        tmp_path,
        [
            {"name": "gen", "run": f"echo gen >> {log}", "serial": True},
            {"name": "lint", "run": f"echo lint >> {log}"},
            {"name": "types", "run": f"echo types >> {log}"},
        ],
    )
    r = _run_gate(repo, tmp_path / "queue")
    assert _last(r).startswith("VERIFY PASS"), r.stdout
    assert log.read_text().split()[0] == "gen"


def _gate_with_fake_db(tmp_path: Path, log: Path) -> Path:
    """The gate as a repo installs it, with a db.py that logs every call and prints `NAME URL`."""
    dest = tmp_path / "installed"
    shutil.copytree(SCRIPTS, dest, ignore=shutil.ignore_patterns("__pycache__"))
    (dest / "db.py").write_text(
        "import os, sys\n"
        "args = sys.argv[1:]\n"
        "assert args[1] != 'create' or args[-2:-1] == ['--owner-pid'] and args[-1].isdigit() and int(args[-1]) != os.getpid(), args\n"
        "if args[1] == 'create': args = args[:-2]  # the owner pid is the gate's, checked above\n"
        f"open({str(log)!r}, 'a').write(' '.join(args) + '\\n')\n"
        "if args[1] == 'create':\n"
        "    name = args[2] if len(args) > 2 else 'copy1'\n"
        "    print(name, 'postgres://127.0.0.1/' + name)\n"
    )
    return dest / "verify_gate.py"


def test_one_database_copy_for_the_whole_close_reset_between_heavy_checks(tmp_path: Path) -> None:
    log, urls = tmp_path / "dblog", tmp_path / "urls"
    repo = _milestone(
        tmp_path,
        [
            {"name": "lint", "run": "true"},
            {"name": "suite", "run": f"echo heavy-marker-suite $DATABASE_URL >> {urls}"},
            {"name": "e2e", "run": f"echo heavy-marker-e2e $DATABASE_URL >> {urls}"},
            {"name": "capture", "run": f"echo heavy-marker-capture $DATABASE_URL >> {urls}", "resetDb": False},
        ],
        heavy=MARK, db={"test": {"container": "c", "port": 1, "template": "t"}},
    )
    r = _run_gate(repo, tmp_path / "queue", gate=_gate_with_fake_db(tmp_path, log))
    assert _last(r).startswith(f"VERIFY PASS milestone {GID}"), r.stdout + r.stderr
    assert log.read_text().splitlines() == [
        "test create",  # once, when the first heavy check takes the slot
        "test drop copy1", "test create copy1",  # before the e2e check: a clean copy
        "test drop copy1",  # capture opted out of a reset; the one drop is the end of the close
    ], r.stdout
    assert set(urls.read_text().split()) - {"heavy-marker-suite", "heavy-marker-e2e", "heavy-marker-capture"} == {"postgres://127.0.0.1/copy1"}
    assert len(urls.read_text().splitlines()) == 3


def test_the_database_copy_is_dropped_when_a_check_fails(tmp_path: Path) -> None:
    log = tmp_path / "dblog"
    repo = _milestone(
        tmp_path, [{"name": "suite", "run": "echo heavy-marker; exit 1"}],
        heavy=MARK, db={"test": {"container": "c", "port": 1, "template": "t"}},
    )
    r = _run_gate(repo, tmp_path / "queue", gate=_gate_with_fake_db(tmp_path, log))
    assert r.returncode == 1 and log.read_text().splitlines() == ["test create", "test drop copy1"]
    assert list((tmp_path / "queue" / "tickets").glob("*.json")) == []


def test_an_unbuildable_database_copy_is_an_env_handoff(tmp_path: Path) -> None:
    log = tmp_path / "dblog"
    gate = _gate_with_fake_db(tmp_path, log)
    gate.with_name("db.py").write_text("import sys\nprint('docker is not running')\nsys.exit(4)\n")
    repo = _milestone(
        tmp_path, [{"name": "suite", "run": "echo heavy-marker"}],
        heavy=MARK, db={"test": {"container": "c", "port": 1, "template": "t"}},
    )
    r = _run_gate(repo, tmp_path / "queue", gate=gate)
    assert r.returncode == 3 and _last(r) == "VERIFY BLOCKED reason=env" and "docker is not running" in r.stdout


def test_a_build_check_runs_once_per_tree(tmp_path: Path) -> None:
    ran = tmp_path / "ran"
    repo = _milestone(
        tmp_path, [{"name": "build", "run": f"echo heavy-marker >> {ran}"}], heavy=MARK,
    )
    for _ in range(2):
        r = _run_gate(repo, tmp_path / "queue")
        assert _last(r).startswith("VERIFY PASS"), r.stdout
    assert len(ran.read_text().splitlines()) == 1 and "ok (cached) build" in r.stdout


def test_a_failed_preflight_stops_the_gate_before_the_first_heavy_command(tmp_path: Path) -> None:
    ran = tmp_path / "ran"
    repo = _milestone(
        tmp_path,
        [{"name": "build", "run": f"touch {shlex.quote(str(ran))}"}],
        preflight={"tools": ["no-such-tool-for-this-test"]},
    )
    r = _run_gate(repo, tmp_path / "queue")
    assert r.returncode == 3 and _last(r) == "VERIFY BLOCKED reason=env", r.stdout + r.stderr
    assert "no-such-tool-for-this-test" in r.stdout and not ran.exists()
    assert os.path.exists(repo / "changes" / GID / "verify" / "report.json")


# ---------------------------------------------------------------- S4: a refusal with no route

import pytest  # noqa: E402
from test_chain_gate import ID as CID  # noqa: E402
from test_chain_gate import _edit as chain_edit  # noqa: E402
from test_gate_bash import _bash  # noqa: E402
from test_goal_active import ID as GAID  # noqa: E402
from test_goal_active import _project, _stop, _transcript  # noqa: E402
from test_pr_gate import _run as pr_run  # noqa: E402


def test_a_rule_with_no_message_still_names_a_route(bash_repo: Path) -> None:
    (bash_repo / "sdlc.json").write_text(json.dumps({"blocked": [{"match": "uv[[:space:]]+add", "message": "  "}]}))
    r = _bash(bash_repo, "uv add httpx")
    assert r.returncode == 2 and "owner of sdlc.json" in r.stderr and "blocked[0]" in r.stderr


# ---------------------------------------------------------------- D4: the hook says why


def test_a_leftover_feature_prs_setting_gets_no_special_message_from_the_hook(pr_repo: Path) -> None:
    cfg = json.loads((pr_repo / "sdlc.json").read_text())
    cfg.update(delivery="feature-prs", milestones={"merge": "local"})
    (pr_repo / "sdlc.json").write_text(json.dumps(cfg))
    r = pr_run(pr_repo, "gh pr create --base milestone/trial-1 --head feat/x --title t --body b")
    assert r.returncode == 2 and "feature PRs" not in r.stderr, r.stderr


# ---------------------------------------------------------------- F3: authorization is bound and spent


def _protect(repo: Path, value: object) -> None:
    path = repo / "changes" / CID / "decisions.json"
    path.write_text(json.dumps({**json.loads(path.read_text()), "protectedEdit": value}))


def test_a_protected_edit_is_allowed_for_its_path_once(chain_repo: Path) -> None:
    facts = f"changes/{CID}/facts.md"
    _protect(chain_repo, {"path": facts, "words": "owner: edit the facts"})
    assert chain_edit(chain_repo, f"changes/{CID}/done.json", "active").returncode == 2  # another path
    assert chain_edit(chain_repo, facts, "active").returncode == 0
    again = chain_edit(chain_repo, facts, "active")
    assert again.returncode == 2 and "already used" in again.stderr and "protectedEdit" in again.stderr


def test_a_quote_with_no_path_is_spent_by_its_first_edit(chain_repo: Path) -> None:
    _protect(chain_repo, "owner: change it")
    assert chain_edit(chain_repo, f"changes/{CID}/facts.md", "active").returncode == 0
    assert chain_edit(chain_repo, "sdlc.json", "active").returncode == 2


def test_a_quote_for_a_revision_ends_when_the_plan_is_approved_again(chain_repo: Path) -> None:
    facts = f"changes/{CID}/facts.md"
    lock = chain_repo / "changes" / CID / "lock.json"
    lock.write_text(json.dumps({"sha": "aaa"}))
    _protect(chain_repo, {"path": facts, "words": "owner: edit the facts", "sha": "bbb"})
    assert chain_edit(chain_repo, facts, "active").returncode == 2  # the quote names another lock
    lock.write_text(json.dumps({"sha": "bbb"}))
    assert chain_edit(chain_repo, facts, "active").returncode == 0


def test_the_dispatch_names_the_change_when_the_branch_name_does_not(chain_repo: Path) -> None:
    subprocess.run(["git", "branch", "-m", "worktree-agent-4f2a"], cwd=chain_repo, check=True)
    assert chain_edit(chain_repo, "src/app.ts", "none").returncode == 0  # no slug in the branch: no opinion
    gitdir = subprocess.run(
        ["git", "rev-parse", "--absolute-git-dir"], cwd=chain_repo, capture_output=True, text=True, check=True
    ).stdout.strip()
    (Path(gitdir) / "sdlc-change").write_text(CID + "\n")
    r = chain_edit(chain_repo, "src/app.ts", "none")
    assert r.returncode == 2 and "inside /goal" in r.stderr
    assert chain_edit(chain_repo, "src/app.ts", "active").returncode == 0


def test_the_prototype_exemption_ends_at_the_lock(chain_repo: Path) -> None:
    cfg = json.loads((chain_repo / "sdlc.json").read_text())
    (chain_repo / "sdlc.json").write_text(json.dumps({**cfg, "prototypeDirs": ["proto"]}))
    r = chain_edit(chain_repo, "proto/x.ts", "none")
    assert r.returncode == 2 and "inside /goal" in r.stderr  # the change is locked: not design any more
    (chain_repo / "changes" / CID / "lock.json").unlink()
    (chain_repo / "changes" / CID / "plan.md").write_text("---\nstatus: draft\n---\n")
    assert chain_edit(chain_repo, "proto/x.ts", "none").returncode == 0  # design: open


# ---------------------------------------------------------------- F5: a stop is not a pass


def _gitdir(repo: Path) -> Path:
    return Path(
        subprocess.run(
            ["git", "rev-parse", "--absolute-git-dir"], cwd=repo, capture_output=True, text=True, check=True
        ).stdout.strip()
    )


def test_a_failed_stop_leaves_a_durable_failed_status_that_the_next_stop_keeps(tmp_path: Path) -> None:
    repo = _project(tmp_path)
    t = _transcript(tmp_path, {"type": "user"}, {"type": "assistant"})  # no goal running: verify runs
    first = _stop(repo, t)
    assert first.returncode == 2 and "verify-ran" in first.stderr
    status = json.loads((_gitdir(repo) / "sdlc-stop-status.json").read_text())
    assert status["status"] == "failed" and "verify-ran" in status["tail"]
    second = _stop(repo, t)  # the anti-recursion stamp lets the session end ...
    assert second.returncode == 0
    assert json.loads((_gitdir(repo) / "sdlc-stop-status.json").read_text())["status"] == "failed"  # ... not read as verified


def test_status_reads_the_failed_stop_and_the_heavy_queue(tmp_path: Path) -> None:
    repo = _project(tmp_path)
    t = _transcript(tmp_path, {"type": "user"}, {"type": "assistant"})
    assert _stop(repo, t).returncode == 2
    change = repo / "changes" / GAID
    (change / "milestone.md").write_text("---\nmilestone: trial\n---\n\n## Features\n\n| # | Change | Feature | PR | State |\n|---|---|---|---|---|\n")
    queue = tmp_path / "queue"
    env = {**_env(), "SDLC_HEAVY_DIR": str(queue), "SDLC_HEAVY_SLOTS": "1"}
    holder = subprocess.Popen(
        [sys.executable, str(HEAVY), "run", "--", "sleep", "20"], cwd=repo, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )  # fmt: skip
    try:
        for _ in range(100):
            if list(queue.glob("*")):
                break
            time.sleep(0.1)
        status_py = SCRIPTS.parents[1] / "scripts" / "sdlc_status.py"
        out = subprocess.run([sys.executable, str(status_py), "map", GAID], cwd=repo, capture_output=True, text=True, env=env).stdout
        shell = subprocess.run(["bash", str(SCRIPTS.parents[1] / "scripts" / "status.sh"), GAID], cwd=repo, capture_output=True, text=True, env={**env, "CLAUDE_PROJECT_DIR": str(repo)}).stdout
    finally:
        holder.kill()
        holder.wait()
    assert "verify FAILED" in out and "not a pass" in out, out
    assert "holding slot 0" in out and "sleep" in out, out
    assert "heavy=holding slot 0" in shell, shell


# ---------------------------------------------------------------- helper-guard.sh


def _helper_guard(tmp_path: Path, payload: object, install: bool = True) -> subprocess.CompletedProcess[str]:
    main, repo = tmp_path / "main", tmp_path / "guarded"  # a helper works in a linked worktree
    if not main.exists():
        main.mkdir()
        _git(main, "init", "-q")
        _git(main, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i")
        _git(main, "worktree", "add", "-q", "-b", "feat", str(repo))
    (repo / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
    (repo / "scripts").mkdir(exist_ok=True)
    shutil.copy(SCRIPTS.parent / "hooks" / "helper-guard.sh", repo / ".claude" / "hooks" / "helper-guard.sh")
    if install:
        shutil.copy(HEAVY, repo / "scripts" / "heavy.py")
    return subprocess.run(
        ["bash", str(repo / ".claude" / "hooks" / "helper-guard.sh")],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True, text=True, cwd=repo, env={**_env(), "CLAUDE_PROJECT_DIR": str(repo)},
    )  # fmt: skip


def _bash_call(command: str, **extra: object) -> dict:
    return {"tool_input": {"command": command}, "cwd": ".", **extra}


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (_bash_call("pnpm build", agent_id="a1", agent_type="builder"), 2),  # a helper, heavy, no queue
        (_bash_call("cd app && npx playwright test", agent_id="a1"), 2),
        (_bash_call("python3 scripts/heavy.py run -- pnpm build", agent_id="a1"), 0),  # in the queue
        (_bash_call("python3 scripts/heavy.py submit -- pnpm build", agent_id="a1"), 0),
        (_bash_call("pnpm lint", agent_id="a1"), 0),  # light
        (_bash_call('git commit -m "fix the build"', agent_id="a1"), 0),  # a word, not a build
        (_bash_call("pnpm build"), 0),  # the owner's own session: the fields are absent
        (_bash_call("pnpm build", agent_id=None), 0),
        (_bash_call("pnpm build", agent_id=""), 0),
        ("not json", 0),
        ("[1, 2]", 0),
        ({"tool_input": None, "agent_id": "a1"}, 0),
    ],
)
def test_the_guard_refuses_only_a_subagents_heavy_call_outside_the_queue(
    tmp_path: Path, payload: object, code: int
) -> None:
    r = _helper_guard(tmp_path, payload)
    assert r.returncode == code, r.stderr
    if code:
        assert "heavy.py run -- pnpm build" in r.stderr or "heavy.py run --" in r.stderr


def test_the_guard_has_no_opinion_in_a_repo_adopted_before_the_queue(tmp_path: Path) -> None:
    assert _helper_guard(tmp_path, _bash_call("pnpm build", agent_id="a1"), install=False).returncode == 0


# ---------------------------------------------------------------- the audit inventory sees the guard

from test_verify_gate import _audit, _audit_repo  # noqa: E402


def test_the_audit_inventories_helper_guard_registered_and_executable(tmp_path: Path) -> None:
    repo, env = _audit_repo(tmp_path, ["echo lint-it"], required=["check"])
    hook = repo / ".claude" / "hooks" / "helper-guard.sh"
    shutil.copy(SCRIPTS.parent / "hooks" / "helper-guard.sh", hook)
    assert "helper-guard.sh: installed but not registered" in _audit(repo, env).stdout
    settings = repo / ".claude" / "settings.json"
    data = json.loads(settings.read_text())
    data["hooks"].setdefault("PreToolUse", []).append(
        {"matcher": "Bash", "hooks": [{"type": "command", "command": '"$CLAUDE_PROJECT_DIR"/.claude/hooks/helper-guard.sh'}]}
    )
    settings.write_text(json.dumps(data))
    out = _audit(repo, env).stdout
    assert "hook helper-guard.sh: installed=yes invoked by [PreToolUse Bash]" in out, out


# ---------------------------------------------------------------- plan.md: Done and turn caps per delivery mode

import importlib.util  # noqa: E402

PLAN = SCRIPTS.parent / "change" / "plan.md"


def _render(**values: str) -> str:
    spec = importlib.util.spec_from_file_location("adopt_under_test", SCRIPTS.parents[1] / "scripts" / "adopt.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    base = {"CHANGE": "2026-11-19-x", "LINEAR": "none", "DESIGN": "null", "AUTHOR": "a", "DATE": "d", "TITLE": "t"}
    return mod.render(PLAN.read_text(encoding="utf-8"), {**base, **values})


def _done(text: str) -> str:
    return text.split("## Done")[1].split("## How to run")[0]


def test_done_and_turn_caps_are_the_one_milestone_pr_delivery() -> None:
    one = _render(RUN_TURNS="150", PROJECT_TURNS="30")
    assert "verify_gate.py milestone 2026-11-19-x` ends `VERIFY PASS` once" in _done(one)
    assert "verify_gate.py feature" not in _done(one)  # a feature is a commit, not a gate
    assert "Stop after 150 turns" in _done(one) and "per feature" not in one
    assert "{{" not in one and "}}" not in one.replace("${{", ""), one[:200]


def test_adopt_writes_a_first_plan_for_the_one_go_mode_without_leftover_markers(tmp_path: Path) -> None:
    from test_adopt import _adopt, _repo as adopt_repo

    repo = adopt_repo(tmp_path, "node")
    assert _adopt(repo).returncode == 0
    # a fresh adoption seeds layout 4 (one spec.md); this is the layout 3 plan template, so go back to it
    shutil.rmtree(next(repo.glob("changes/*-adopt-sdlc")))
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({k: v for k, v in cfg.items() if k != "layout"}))
    assert _adopt(repo).returncode == 0
    (plan,) = repo.glob("changes/*/plan.md")
    text = plan.read_text(encoding="utf-8")
    assert "Stop after 150 turns" in text and "{{#" not in text and "{{/" not in text
    assert "verify_gate.py feature" not in text.split("## Done")[1].split("## How to run")[0]


# ---------------------------------------------------------------- local and CI run the same commands


def _commands(value: object) -> list[str]:
    return [c.strip() for c in str(value).split("&&")]


def _local_profile(preset: str) -> set[str]:
    """What the milestone gate runs besides the browser suites: lint, types and unit tests."""
    checks = json.loads((SCRIPTS.parent / "presets" / f"{preset}.json").read_text())["checks"]["milestone"]
    runs = [c if isinstance(c, str) else c["run"] for c in checks]
    browser = re.compile(r"test:e2e|playwright|pytest e2e|-d e2e|^changed=")  # `--ignore=e2e` is a unit run
    return {r for r in runs if not browser.search(r)}


@pytest.mark.parametrize(("preset", "stack"), [("node", "typescript"), ("python", "python")])
def test_the_milestone_checks_and_the_ci_commands_do_not_drift(preset: str, stack: str) -> None:
    ci = json.loads((SCRIPTS.parent / "ci-commands.json").read_text())[stack]
    in_ci = {c for key in ("lint", "unit") for c in _commands(ci[key])}
    assert in_ci == _local_profile(preset), (
        f"{preset}: the CI `lint` and `unit` commands and the preset's milestone checks differ; "
        "change both or neither"
    )


def test_this_repos_own_milestone_checks_and_ci_commands_do_not_drift() -> None:
    cfg = json.loads((Path(__file__).resolve().parents[5] / "sdlc.json").read_text())
    runs = {c if isinstance(c, str) else c["run"] for c in cfg["checks"]["milestone"]}
    in_ci = {c for key in ("lint", "unit") for c in _commands(cfg["ciCommands"][key])}
    assert in_ci == runs, "sdlc.json checks.milestone and ciCommands lint+unit differ; change both or neither"


# ---------------------------------------------------------------- review round: security fixes


def _other_change(repo: Path, name: str = "2026-10-10-other") -> str:
    d = repo / "changes" / name
    d.mkdir()
    (d / "decisions.json").write_text(json.dumps({"size": "M", "milestone": {"kind": "single", "slug": "other"}}))
    return name


def test_a_dispatch_pointer_never_overrides_the_branchs_change(chain_repo: Path) -> None:
    other = _other_change(chain_repo)
    gitdir = _gitdir(chain_repo)
    (gitdir / "sdlc-change").write_text(other + "\n")
    r = chain_edit(chain_repo, "src/app.ts", "active")
    assert r.returncode == 2 and CID in r.stderr and other in r.stderr and "disagree" in r.stderr, r.stderr
    (gitdir / "sdlc-change").write_text(CID + "\n")
    assert chain_edit(chain_repo, "src/app.ts", "active").returncode == 0  # the same change: fine


def test_the_env_pointer_cannot_override_the_branch_either(chain_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    other = _other_change(chain_repo)
    monkeypatch.setenv("SDLC_CHANGE", other)
    r = chain_edit(chain_repo, "src/app.ts", "active")
    assert r.returncode == 2 and other in r.stderr and CID in r.stderr


@pytest.mark.parametrize("ledger", ["not json", "{}", "dir"])
def test_an_unreadable_ledger_denies_the_protected_edit(chain_repo: Path, ledger: str) -> None:
    facts = f"changes/{CID}/facts.md"
    _protect(chain_repo, {"path": facts, "words": "owner: edit the facts"})
    path = _gitdir(chain_repo) / "sdlc-protected-used.json"
    if ledger == "dir":
        path.mkdir()
    else:
        path.write_text(ledger)
    r = chain_edit(chain_repo, facts, "active")
    if ledger == "{}":  # valid JSON of the wrong shape is unreadable too
        assert r.returncode == 2 and "ledger" in r.stderr
    else:
        assert r.returncode == 2 and "ledger" in r.stderr, r.stderr


def test_no_git_dir_denies_the_protected_edit(chain_repo: Path) -> None:
    facts = f"changes/{CID}/facts.md"
    _protect(chain_repo, {"path": facts, "words": "owner: edit the facts"})
    shutil.rmtree(chain_repo / ".git")
    r = chain_edit(chain_repo, facts, "active")
    assert r.returncode == 2 and "ledger" in r.stderr, r.stderr


@pytest.mark.parametrize(
    "command",
    [
        "env FOO=1 pnpm build",
        "xargs pnpm build",
        "sh -c 'pnpm build'",
        'bash -c "cd app && pnpm build"',
        "find . -name x -exec pnpm build {} ;",
        "timeout 5 pnpm build",
        "nice -n 5 pnpm build",
        "echo heavy.py run; pnpm build",  # the words in another segment queue nothing
        "pnpm build # heavy.py run",
        "FOO=1 pnpm build",
    ],
)
def test_the_guard_sees_through_wrappers_and_refuses_a_substring_of_the_queue(tmp_path: Path, command: str) -> None:
    assert _helper_guard(tmp_path, _bash_call(command, agent_id="a1")).returncode == 2, command


@pytest.mark.parametrize(
    "command",
    [
        "timeout 5 python3 scripts/heavy.py run -- pnpm build",
        "env A=1 python3 scripts/heavy.py submit -- pnpm build",
        "sh -c 'python3 scripts/heavy.py run -- pnpm build'",
        "cd app && python3 ../scripts/heavy.py run -- pnpm build",
        "env FOO=1 pnpm lint",
        "git commit -m 'fix the build'",
    ],
)
def test_the_guard_lets_queued_and_light_commands_through(tmp_path: Path, command: str) -> None:
    assert _helper_guard(tmp_path, _bash_call(command, agent_id="a1")).returncode == 0, command


def test_status_never_runs_the_repos_checked_in_heavy_py(tmp_path: Path) -> None:
    repo = _project(tmp_path)
    marker = tmp_path / "repo-copy-ran"
    scripts = repo / "scripts"
    scripts.mkdir()
    (scripts / "heavy.py").write_text(f"open({str(marker)!r}, 'w').write('x')\nprint('holding slot 9: forged')\n")
    (repo / "changes" / GAID / "milestone.md").write_text(
        "---\nmilestone: trial\n---\n\n## Features\n\n| # | Change | Feature | PR | State |\n|---|---|---|---|---|\n"
    )
    status_py = SCRIPTS.parents[1] / "scripts" / "sdlc_status.py"
    out = subprocess.run([sys.executable, str(status_py), "map", GAID], cwd=repo, capture_output=True, text=True, env=_env()).stdout
    assert not marker.exists() and "forged" not in out, out


def test_the_blueprint_ci_has_the_templates_preflight_and_spec_jobs() -> None:
    template = (SCRIPTS.parent / "ci" / "github-actions.yml").read_text()
    blueprint = (SCRIPTS.parents[3] / "blueprint/web-nextjs-cloud-run/.github/workflows/ci.yml").read_text()
    block = template[template.index("  # Seconds, no install: sdlc.json config conflicts") : template.index("  lint:\n")]
    assert block in blueprint
    assert "preflight, spec," in blueprint and "PREFLIGHT" in blueprint  # `check` waits for both


def test_the_guard_splits_on_newlines_and_checks_every_argv(tmp_path: Path) -> None:
    assert _helper_guard(tmp_path, _bash_call("git status\npnpm build", agent_id="a1")).returncode == 2
    assert _helper_guard(tmp_path, _bash_call("echo hi\ncat x\npnpm lint", agent_id="a1")).returncode == 0


@pytest.mark.parametrize("command", ["env -S 'pnpm build'", "env --split-string='nice pnpm build'", "env -S'pnpm build'"])
def test_the_guard_reads_the_split_string_of_env(tmp_path: Path, command: str) -> None:
    assert _helper_guard(tmp_path, _bash_call(command, agent_id="a1")).returncode == 2, command
    assert _helper_guard(tmp_path, _bash_call("env -S 'pnpm lint'", agent_id="a1")).returncode == 0


# ---------------------------------------------------------------- 3.22.0 fix round


DBCFG = {"test": {"container": "c", "port": 1, "template": "t"}}


def test_the_last_failed_rerun_gets_the_same_private_environment(tmp_path: Path) -> None:
    log = tmp_path / "log"
    repo = _milestone(
        tmp_path,
        [{"name": "e2e", "run": f"echo heavy-marker playwright $DATABASE_URL $SDLC_APP_PORT >> {log}; exit 1"}],
        heavy=MARK, db=DBCFG,
    )
    r = _run_gate(repo, tmp_path / "queue", gate=_gate_with_fake_db(tmp_path, tmp_path / "dblog"), DATABASE_URL="postgres://caller/mine")
    assert r.returncode == 1, r.stdout + r.stderr
    lines = log.read_text().splitlines()
    assert len(lines) == 2, lines  # the second is the --last-failed rerun
    for line in lines:
        assert "postgres://127.0.0.1/copy1" in line and " 4100" in line and "caller" not in line, line


def test_a_database_check_is_a_serial_boundary(tmp_path: Path) -> None:
    log = tmp_path / "log"
    repo = _milestone(
        tmp_path,
        [{"name": "slow", "run": f"sleep 0.5; echo a >> {log}"}, {"name": "db", "run": f"echo b >> {log}", "resetDb": True}],
        db=DBCFG,
    )
    r = _run_gate(repo, tmp_path / "queue", gate=_gate_with_fake_db(tmp_path, tmp_path / "dblog"))
    assert _last(r).startswith("VERIFY PASS"), r.stdout + r.stderr
    assert log.read_text().split() == ["a", "b"], "the reset check never started beside the one before it"


def test_a_light_check_before_the_copy_never_sees_the_callers_database(tmp_path: Path) -> None:
    log = tmp_path / "log"
    repo = _milestone(
        tmp_path,
        [{"name": "lint", "run": f'echo "url=[$DATABASE_URL]" >> {log}'}, {"name": "suite", "run": "echo heavy-marker"}],
        heavy=MARK, db=DBCFG,
    )
    r = _run_gate(repo, tmp_path / "queue", gate=_gate_with_fake_db(tmp_path, tmp_path / "dblog"), DATABASE_URL="postgres://caller/mine")
    assert _last(r).startswith("VERIFY PASS"), r.stdout + r.stderr
    assert log.read_text().strip() == "url=[]"


def test_a_lock_without_cost_order_runs_every_check_in_declared_order(tmp_path: Path) -> None:
    log = tmp_path / "log"
    repo = _milestone(
        tmp_path,
        [{"name": "gen", "run": f"sleep 0.5; echo gen >> {log}"}, {"name": "types", "run": f"echo types >> {log}"}],
    )
    lock = next((repo / "changes").rglob("lock.json"))
    data = json.loads(lock.read_text())
    data.pop("order", None)  # an approval from before 3.18.0
    lock.write_text(json.dumps(data))
    _git(repo, "commit", "-qam", "legacy lock")
    r = _run_gate(repo, tmp_path / "queue")
    assert _last(r).startswith("VERIFY PASS"), r.stdout + r.stderr
    assert log.read_text().split() == ["gen", "types"]


def test_a_stuck_database_prepare_is_bounded_and_an_env_handoff(tmp_path: Path) -> None:
    gate = _gate_with_fake_db(tmp_path, tmp_path / "dblog")
    gate.with_name("db.py").write_text("import time\ntime.sleep(60)\n")
    repo = _milestone(
        tmp_path, [{"name": "suite", "run": "echo heavy-marker"}], heavy=MARK,
        db={"test": {**DBCFG["test"], "prepareTimeout": 1}},
    )
    t0 = time.time()
    r = _run_gate(repo, tmp_path / "queue", gate=gate)
    assert r.returncode == 3 and _last(r) == "VERIFY BLOCKED reason=env" and time.time() - t0 < 30, r.stdout
    assert list((tmp_path / "queue" / "tickets").glob("*.json")) == []


def test_a_failed_cleanup_warns_on_stderr_and_the_verdict_stays_last(tmp_path: Path) -> None:
    gate = _gate_with_fake_db(tmp_path, tmp_path / "dblog")
    db = gate.with_name("db.py")
    db.write_text(db.read_text().replace("import os, sys\n", "import os, sys\nif sys.argv[2] == 'drop': print('nope'); sys.exit(5)\n", 1))
    repo = _milestone(tmp_path, [{"name": "suite", "run": "echo heavy-marker"}], heavy=MARK, db=DBCFG)
    r = _run_gate(repo, tmp_path / "queue", gate=gate)
    assert _last(r).startswith("VERIFY PASS"), r.stdout
    assert "WARN database copy1 not dropped" in r.stderr and "WARN database" not in r.stdout


def test_cancelling_the_gate_kills_its_running_check_and_frees_the_slot(tmp_path: Path) -> None:
    pidfile = tmp_path / "pid"
    repo = _milestone(tmp_path, [{"name": "suite", "run": f"echo $$ > {pidfile}; echo heavy-marker; sleep 60"}], heavy=MARK)
    env = {**_env(), "SDLC_HEAVY_DIR": str(tmp_path / "queue"), "SDLC_HEAVY_SLOTS": "1", "SDLC_HEAVY_POLL": "0.1"}
    gate = subprocess.Popen(
        [sys.executable, str(SCRIPTS / "verify_gate.py"), "milestone", GID],
        cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )  # fmt: skip
    end = time.time() + 30
    while time.time() < end and not (pidfile.exists() and pidfile.read_text().strip()):
        time.sleep(0.1)
    check = int(pidfile.read_text())
    gate.terminate()
    gate.wait(20)
    time.sleep(0.3)
    try:
        import os

        os.kill(check, 0)
        alive = True
    except OSError:
        alive = False
    assert not alive, "the check outlived the cancelled gate"
    assert list((tmp_path / "queue" / "tickets").glob("*.json")) == []
