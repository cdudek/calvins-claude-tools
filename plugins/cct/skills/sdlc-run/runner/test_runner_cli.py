"""The whole loop through the CLI, as the orchestrating session drives it (builder work done by hand in the worktree)."""
import json
import os
from pathlib import Path

import testkit as tk


def sdlc(home, *args, cwd=None, gate="approved"):
    """The CLI in-process (so the gate runner can be replaced the way a test may, not through the environment)."""
    import io
    from contextlib import redirect_stderr, redirect_stdout

    import discover
    import sdlc as cli

    out, err = io.StringIO(), io.StringIO()
    old, discover.GATE_RUN = os.environ.get("SDLC_HOME"), (lambda cmd: (0, json.dumps({"decision": "approved" if gate == "approved" else "dismissed"})))
    old_path, discover.plannotator_path = discover.plannotator_path, (lambda: "/opt/fake/plannotator")  # a test seam, not an environment one
    os.environ["SDLC_HOME"] = str(home)
    old_cwd = os.getcwd()
    try:
        if cwd:
            os.chdir(cwd)
        with redirect_stdout(out), redirect_stderr(err):
            rc = cli.main(list(args))
    finally:
        os.chdir(old_cwd)
        os.environ["SDLC_HOME"] = old or ""
        discover.GATE_RUN = discover._plannotator
        discover.plannotator_path = old_path
    return rc, out.getvalue().strip(), err.getvalue().strip()


def test_plan_to_ready_through_the_cli(tmp_path):
    home = tmp_path / "home"
    repo = tk.make_repo(tmp_path, "app", {"feature.py": "def greet():\n    return 'hi'\n", "Makefile": "test:\n\ttrue\n"})
    rc, rid, _ = sdlc(home, "plan", str(repo), "--slug", "greet")
    assert rc == 0 and rid.endswith("-app-greet")
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    (scratch / "spec.py").write_text(tk.SPEC)
    (scratch / "tasks.json").write_text(json.dumps({"milestones": [{"id": "m1", "repo": "app", "needs": [], "tasks": [{"id": "t1", "needs": [], "paths": ["feature.py"]}]}]}))
    chk = lambda i, **k: {"id": i, "repo": "app", "runner": tk.RUN, "pins": ["tests/test_feature.py"], **k}  # noqa: E731
    (scratch / "contract.json").write_text(json.dumps({"checks": [chk("spec", milestone="m1", task="t1", expect={"kind": "fails_on_base"}),
                                                                  chk("full", milestone=None, due="each", expect={"kind": "pass"})],
                                                       "limits": {"builders": 8, "max_dispatches": 6}}))
    rc, out, err = sdlc(home, "draft", rid, "--tasks", str(scratch / "tasks.json"), "--contract", str(scratch / "contract.json"),
                        "--input", f"app:tests/test_feature.py={scratch / 'spec.py'}")
    assert rc == 0, err
    assert sdlc(home, "check", rid)[0] == 2  # not approved yet
    rc, screen, _ = sdlc(home, "screen", rid)
    assert "plannotator annotate" in screen
    assert sdlc(home, "check", rid)[0] == 2 and not (home / "runs" / rid / "approval.json").exists()
    assert sdlc(home, "gate", rid, gate="false")[0] == 2 and not (home / "runs" / rid / "approval.json").exists()  # dismissed: nothing approved
    assert sdlc(home, "gate", rid)[0] == 2  # approve needs --by
    assert sdlc(home, "gate", rid, "--by", "owner")[0] == 0 and (home / "runs" / rid / "approval.json").exists()
    assert sdlc(home, "gate", rid, "--by", "owner")[0] == 2  # a second approval would reset caps and deadline
    assert json.loads(sdlc(home, "next", rid)[1]) == ["t1"]
    rc, out, err = sdlc(home, "dispatch", rid, "t1")
    wt = Path(json.loads(out)[0]["worktree"])
    (wt / "feature.py").write_text("def greet():\n    return 'hello'\n")
    tk.git(wt, "add", "-A")
    tk.git(wt, "commit", "-qm", "greet")
    assert sdlc(home, "submit", rid, "t1")[0] == 0
    rc, out, _ = sdlc(home, "verify", rid, "--task", "t1")
    assert rc == 0 and out.startswith("PASS"), out
    assert sdlc(home, "integrate", rid, "t1")[0] == 0
    assert sdlc(home, "milestone", rid, "m1")[0] == 0
    assert sdlc(home, "final", rid)[0] == 0
    rc, line, _ = sdlc(home, "check", rid)
    assert rc == 0 and line.startswith("READY run=" + rid), line
    assert tk.git(repo, "status", "--porcelain", "--untracked-files=all") == ""  # nothing was left in the repo
    assert sdlc(home, "list")[1].startswith(rid)
    assert sdlc(home, "done", rid)[0] == 0 and not (home / "active" / rid).exists()  # a finished run leaves the active folder
    assert sdlc(home, "stop", rid)[0] == 0 and sdlc(home, "check", rid)[0] == 2
    assert sdlc(home, "gate", rid, "restart", gate="false")[0] == 2 and sdlc(home, "check", rid)[0] == 2  # restart needs the owner's gate
    assert sdlc(home, "gate", rid, "restart")[0] == 0
