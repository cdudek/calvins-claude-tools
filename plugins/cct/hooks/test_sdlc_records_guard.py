"""The records guard: agents neither read nor write the runs folder; one plain runner call is the only way in."""
import json
import os
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "sdlc-records-guard.py"
RUNNER = str(Path(__file__).resolve().parent.parent / "skills" / "sdlc-run" / "runner" / "sdlc.py")


def run(tool, tool_input, home, cwd=None, env=None):
    ev = {"tool_name": tool, "tool_input": tool_input, **({"cwd": str(cwd)} if cwd else {})}
    r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(ev), capture_output=True, text=True,
                       env={**os.environ, "SDLC_HOME": str(home), **(env or {})})
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"] if r.stdout.strip() else None


def bash(cmd, home, **kw):
    return run("Bash", {"command": cmd}, home, **kw)


def test_writes_and_reads_of_the_records_are_denied(tmp_path):
    f = tmp_path / "runs" / "r1" / "receipts" / "x.json"
    for tool in ("Write", "Edit", "MultiEdit", "Read"):
        assert run(tool, {"file_path": str(f)}, tmp_path) == "deny", tool
    assert run("Grep", {"pattern": "PASS", "path": str(tmp_path / "runs")}, tmp_path) == "deny"
    assert run("Grep", {"pattern": "PASS", "path": str(tmp_path)}, tmp_path) == "deny"  # a recursive search from above
    assert run("Glob", {"pattern": "**/*.json", "path": str(tmp_path / "runs" / "r1")}, tmp_path) == "deny"
    assert run("Read", {"file_path": str(tmp_path / "briefs" / "r1" / "t1" / "brief.md")}, tmp_path) is None  # a brief is readable
    assert run("Grep", {"pattern": "x", "path": str(tmp_path / "work")}, tmp_path) is None


def test_every_way_to_name_the_folder_is_denied(tmp_path):
    home = tmp_path / ".sdlc"
    for cmd in ("rm -rf ~/.sdlc/*", "rm -rf ~/.sdlc/r*", "X=.sdlc; rm -rf ~/$X/runs", "echo hi\nrm -rf ~/.sdlc/runs",
                "cat $HOME/.sdlc/runs/r1/run.json", "ls ~/.s*", "ls ~/.sdl?/runs", "cat ~/.[s]dlc/runs/x", "rm -rf ~/.'sd'lc",
                f"cd {home}/runs && echo x > f", f"cat {home}/runs/r1/run.json", "SDLC_HOME=/x python3 -c 'pass'"):
        assert bash(cmd, home, env={"SDLC_HOME": str(home)}) == "deny", cmd


def test_only_one_plain_runner_call_may_touch_the_records(tmp_path):
    home = tmp_path / ".sdlc"
    env = {"SDLC_HOME": str(home)}
    assert bash(f"python3 {RUNNER} check r1 --note ~/.sdlc/runs/r1", home, env=env) is None
    assert bash(f"{RUNNER} status", home, env=env) is None
    for cmd in (f"python3 {RUNNER} check r1; rm -rf ~/.sdlc/runs", f"python3 {RUNNER} check ~/.sdlc && rm -rf ~/.sdlc", f"python3 {RUNNER} status | tee ~/.sdlc/runs/x",
                f"python3 {RUNNER} status `rm -rf ~/.sdlc`", f"python3 {RUNNER} status $(rm -rf ~/.sdlc)", f"python3 {RUNNER} check x\nrm -rf ~/.sdlc",
                "./sdlc check ~/.sdlc/runs/r1", "sdlc check ~/.sdlc/runs/r1", "python3 /tmp/fake/sdlc.py check ~/.sdlc/runs/r1",
                f"X=1 python3 {RUNNER} check ~/.sdlc"):
        assert bash(cmd, home, env=env) == "deny", cmd


def test_unrelated_commands_pass_including_unparsable_ones(tmp_path):
    home = tmp_path / ".sdlc"
    env = {"SDLC_HOME": str(home)}
    for cmd in ("git status", "ls *.py", "python3 -m pytest -q", "git commit -m \"it's fine\"", "cat <<EOF\nit's\nEOF", "echo 'unbalanced"):
        assert bash(cmd, home, env=env) is None, cmd
    assert bash("echo 'unbalanced ~/.sdlc", home, env=env) == "deny"
    assert bash("git status", home, cwd=home / "runs", env=env) == "deny"  # a shell inside the records is the records
    assert bash("git status", home, cwd=tmp_path, env=env) is None


def test_a_command_that_sets_the_gate_override_is_denied(tmp_path):
    assert bash("SDLC_GATE_CMD=true python3 -m pytest", tmp_path / "h") == "deny"
    assert bash("env SDLC_GATE_CMD=true sdlc gate x", tmp_path / "h") == "deny"


def test_n1_hook_bypasses_are_denied(tmp_path):
    home = tmp_path / ".sdlc"
    env = {"SDLC_HOME": str(home)}
    runner_dir = str(Path(RUNNER).parent)
    for cmd in (
        f"python3 -c \"import sys;sys.path.insert(0,'{runner_dir}');import contract,store;contract.approve('r','agent')\"",
        "python3 - <<'EOF'\nimport sys\nsys.path.insert(0, 'plugins/cct/skills/sdlc-run/runner')\nimport contract\nEOF",
        "python3 -c 'import store; store.write_json(1, 2)'",
        "python3 -c 'from engine import restart'",
        f"PATH=/tmp/fake:$PATH python3 {RUNNER} gate r1 --by x",
        f"HOME=/tmp/h python3 {RUNNER} gate r1 --by x",
        f"PYTHONPATH=/tmp/x python3 {RUNNER} gate r1 --by x",
        f"env PATH=/tmp/fake python3 {RUNNER} gate r1 --by x",
        f"env -i python3 {RUNNER} check r1",
        "./sdlc gate r1 --by x",
        "./sdlc.py gate r1 --by x",
        "python3 sdlc.py gate r1 --by x",
        "python3 ../runner/sdlc.py gate r1 --by x",
        "python3 /tmp/fake/runner/sdlc.py gate r1 --by x",
        f"python3 -I {RUNNER} gate r1 --by x",
    ):
        assert bash(cmd, home, env=env) == "deny", cmd
    assert bash(f"python3 {RUNNER} gate r1 --by owner", home, env=env) is None  # exactly one plain call of the plugin's runner
    assert bash(f"{RUNNER} check r1", home, env=env) is None
    assert bash("python3 -c 'print(1)'", home, env=env) is None
    assert bash("git commit -m 'import store'", home, env=env) is None  # prose is not an import
    assert bash("git diff plugins/cct/skills/sdlc-run/runner/engine.py", home, env=env) is None  # reading the code is not running it
    assert bash("git add sdlc.py", home, env=env) is None


def test_the_glob_is_tested_on_every_path_component(tmp_path):
    home = tmp_path / ".sdlc"
    for cmd in ("cat ~/.s?lc/runs/*/contract.json", "cat ~/.s*/runs/*/receipts/*.json", "ls ~/.sdlc/r*/*/contract.json",
                "cat ~/.[s]dlc/runs/r1/contract.json", "cat ~/.sd?c/*/run1/*.json"):
        assert bash(cmd, home, env={"SDLC_HOME": str(home)}) == "deny", cmd
    real_home = os.path.expanduser("~")
    for cmd in (f"cat {real_home}/.s?lc/runs/*/contract.json",):
        assert bash(cmd, Path(real_home) / ".sdlc") == "deny", cmd
    assert bash("ls ~/projects/*/src/*.py", home) is None


def test_boards_calls_that_name_the_records_folder_are_denied(tmp_path):
    home = tmp_path / ".sdlc"
    env = {"SDLC_HOME": str(home)}
    assert bash(f"python3 {RUNNER} boards index /tmp/export --out /tmp/idx.json", home, env=env) is None
    for cmd in (f"python3 {RUNNER} boards rows m.json --index i.json --out {home}/runs/r1/contract.json",
                f"python3 {RUNNER} boards index /tmp/export --out ~/.sdlc/runs/r1/x.json", f"python3 {RUNNER} boards index {home}/runs"):
        assert bash(cmd, home, env=env) == "deny", cmd


def install_kit(cfg, name="fakekit", version="1.0", listed=True):
    """A sibling kit installed in the plugin cache of a throw-away Claude config dir, and named in its sibling list."""
    runner = Path(cfg) / "plugins" / "cache" / "market" / name / version / "skills" / "sdlc-run" / "runner" / "sdlc.py"
    runner.parent.mkdir(parents=True)
    runner.write_text("# runner\n")
    if listed:
        (Path(cfg) / "sdlc-sibling-kits.json").write_text(json.dumps({"plugins": [name]}))
    return str(runner)


def test_a_named_sibling_kits_runner_in_the_plugin_cache_is_one_more_plain_call(tmp_path):
    home, cfg = tmp_path / ".sdlc", tmp_path / "cfg"
    env = {"SDLC_HOME": str(home), "CLAUDE_CONFIG_DIR": str(cfg)}
    sibling = install_kit(cfg)
    assert bash(f"python3 {sibling} check r1 --note ~/.sdlc/runs/r1", home, env=env) is None
    assert bash(f"{sibling} status", home, env=env) is None
    assert bash(f"python3 {RUNNER} status", home, env=env) is None  # this plugin's own runner still passes
    for cmd in (f"python3 {sibling} check r1; rm -rf ~/.sdlc/runs", f"X=1 python3 {sibling} check ~/.sdlc", f"python3 {sibling} status | tee ~/.sdlc/runs/x",
                f"PATH=/tmp/fake python3 {sibling} gate r1 --by x", f"cd {Path(sibling).parent} && python3 sdlc.py check ~/.sdlc"):
        assert bash(cmd, home, env=env) == "deny", cmd


def test_a_lookalike_runner_outside_the_plugin_cache_or_not_named_is_denied(tmp_path):
    home, cfg = tmp_path / ".sdlc", tmp_path / "cfg"
    env = {"SDLC_HOME": str(home), "CLAUDE_CONFIG_DIR": str(cfg)}
    install_kit(cfg)
    outside = tmp_path / "elsewhere" / "plugins" / "cache" / "market" / "fakekit" / "1.0" / "skills" / "sdlc-run" / "runner" / "sdlc.py"
    outside.parent.mkdir(parents=True)
    outside.write_text("# not installed here\n")
    assert bash(f"python3 {outside} check ~/.sdlc/runs/r1", home, env=env) == "deny"  # same layout, but not under this config's cache
    other = install_kit(tmp_path / "cfg2", name="otherkit", listed=False)  # installed, but never named
    env2 = {"SDLC_HOME": str(home), "CLAUDE_CONFIG_DIR": str(tmp_path / "cfg2")}
    assert bash(f"python3 {other} check ~/.sdlc/runs/r1", home, env=env2) == "deny"
    other2 = Path(cfg) / "plugins" / "cache" / "market" / "unlisted" / "1.0" / "skills" / "sdlc-run" / "runner" / "sdlc.py"
    other2.parent.mkdir(parents=True)
    other2.write_text("#")
    assert bash(f"python3 {other2} check ~/.sdlc/runs/r1", home, env=env) == "deny"  # a plugin in the cache the owner did not name
    stray = Path(cfg) / "plugins" / "cache" / "market" / "fakekit" / "1.0" / "skills" / "sdlc-run" / "runner" / "other.py"
    stray.write_text("#")
    assert bash(f"python3 {stray} check ~/.sdlc/runs/r1", home, env=env) == "deny"  # only the runner file itself
    link = Path(cfg) / "plugins" / "cache" / "market" / "fakekit" / "2.0"
    (link / "skills" / "sdlc-run").mkdir(parents=True)
    (link / "skills" / "sdlc-run" / "runner").symlink_to(outside.parent)  # a symlink leading out of the installed plugin
    assert bash(f"python3 {link / 'skills' / 'sdlc-run' / 'runner' / 'sdlc.py'} check ~/.sdlc/runs/r1", home, env=env) == "deny"
    assert bash(f"python3 {install_kit(tmp_path / 'cfg3', listed=False)} check ~/.sdlc", home, env={**env, "CLAUDE_CONFIG_DIR": str(tmp_path / "cfg3")}) == "deny"


def test_a_registry_entry_or_an_install_path_outside_the_plugin_cache_adds_nothing(tmp_path):
    home, cfg = tmp_path / ".sdlc", tmp_path / "cfg"
    env = {"SDLC_HOME": str(home), "CLAUDE_CONFIG_DIR": str(cfg)}
    runner = tmp_path / "somewhere" / "fakekit" / "skills" / "sdlc-run" / "runner" / "sdlc.py"
    runner.parent.mkdir(parents=True)
    runner.write_text("#")
    (cfg / "plugins").mkdir(parents=True)
    (cfg / "sdlc-sibling-kits.json").write_text(json.dumps({"plugins": ["fakekit"]}))
    (cfg / "plugins" / "installed_plugins.json").write_text(json.dumps({"plugins": {"fakekit@market": [{"installPath": str(runner.parents[3])}]}}))
    assert bash(f"python3 {runner} check ~/.sdlc/runs/r1", home, env=env) == "deny"  # registered, but not in the plugin cache


def test_a_version_directory_that_is_a_symlink_is_not_an_installed_plugin(tmp_path):
    home, cfg = tmp_path / ".sdlc", tmp_path / "cfg"
    env = {"SDLC_HOME": str(home), "CLAUDE_CONFIG_DIR": str(cfg)}
    real = tmp_path / "elsewhere" / "skills" / "sdlc-run" / "runner" / "sdlc.py"
    real.parent.mkdir(parents=True)
    real.write_text("#")
    ver = cfg / "plugins" / "cache" / "market" / "fakekit" / "1.0"
    ver.parent.mkdir(parents=True)
    ver.symlink_to(tmp_path / "elsewhere")
    (cfg / "sdlc-sibling-kits.json").write_text(json.dumps({"plugins": ["fakekit"]}))
    assert bash(f"python3 {ver / 'skills' / 'sdlc-run' / 'runner' / 'sdlc.py'} check ~/.sdlc/runs/r1", home, env=env) == "deny"


def test_agents_may_not_write_the_sibling_list_the_registry_or_the_plugin_cache(tmp_path):
    home, cfg = tmp_path / ".sdlc", tmp_path / "cfg"
    env = {"SDLC_HOME": str(home), "CLAUDE_CONFIG_DIR": str(cfg)}
    for tool in ("Write", "Edit", "MultiEdit"):
        for p in (cfg / "sdlc-sibling-kits.json", cfg / "plugins" / "installed_plugins.json", cfg / "plugins" / "cache" / "market" / "x" / "1" / "skills" / "a.py"):
            assert run(tool, {"file_path": str(p)}, home, env=env) == "deny", (tool, p)
    assert run("NotebookEdit", {"notebook_path": str(cfg / "plugins" / "cache" / "n.ipynb")}, home, env=env) == "deny"
    assert run("Write", {"file_path": str(cfg / "settings.json")}, home, env=env) is None  # the rest of the config dir is not covered
    assert run("Write", {"file_path": str(tmp_path / "work" / "a.py")}, home, env=env) is None
    assert run("Read", {"file_path": str(cfg / "plugins" / "installed_plugins.json")}, home, env=env) is None  # reading is not writing


def test_commands_that_name_the_sibling_list_the_registry_or_the_cache_are_denied(tmp_path):
    home, cfg = tmp_path / "deep" / ".sdlc", tmp_path / "cfg"
    env = {"SDLC_HOME": str(home), "CLAUDE_CONFIG_DIR": str(cfg)}
    sibling = install_kit(cfg)
    for cmd in (f"echo '{{\"plugins\": [\"evil\"]}}' > {cfg}/sdlc-sibling-kits.json", f"tee {cfg}/plugins/installed_plugins.json",
                f"mkdir -p {cfg}/plugins/cache/m/evil/1 && cp x {cfg}/plugins/cache/m/evil/1/f", f"rm -rf {cfg}/plugins/cache", f"cat {cfg}/plugins/cache/m/fakekit/1.0/x",
                f"touch {cfg}/plug*/cache/m/evil", f"touch {cfg}/plugins/c?che/x", "sed -i s/a/b/ ~/.claude/sdlc-sibling-kits.json",
                "echo x > ~/.claude/plugins/installed_plugins.json", "python3 -c \"open('sdlc-sibling-kits.json','w')\""):
        assert bash(cmd, home, env=env) == "deny", cmd
    assert bash("touch f", home, cwd=cfg / "plugins" / "cache" / "m", env=env) == "deny"  # a shell inside the cache
    assert bash(f"ls {cfg.parent}/*", home, env=env) is None and bash(f"ls {cfg}", home, env=env) is None  # an ancestor glob is not the cache
    assert bash(f"rm {cfg}/*", home, env=env) == "deny"  # a glob that can name the sibling list is
    assert bash(f"python3 {sibling} status", home, env=env) is None  # a named sibling's plain runner call still passes from inside the cache path


def test_an_unparsable_command_that_names_the_runner_or_its_modules_is_denied(tmp_path):
    home = tmp_path / ".sdlc"
    env = {"SDLC_HOME": str(home)}
    runner_dir = str(Path(RUNNER).parent)
    for cmd in ("./sdlc.py gate r1 --by x 'unbalanced", "sdlc.py check 'x", f"cat {runner_dir}/store.py 'unbalanced", "cat skills/sdlc-run/runner/store.py 'unbalanced",
                "echo 'unbalanced; from store import write_json", "echo \"x; import contract"):
        assert bash(cmd, home, env=env) == "deny", cmd
    assert bash("echo 'unbalanced", home, env=env) is None  # prose without those names still passes


def test_a_command_that_names_the_claude_dir_with_a_glob_expansion_brace_backtick_or_cd_is_denied(tmp_path):
    home, cfg = tmp_path / "deep" / ".sdlc", tmp_path / "cfg"
    env = {"SDLC_HOME": str(home), "CLAUDE_CONFIG_DIR": str(cfg)}
    for cmd in ("ls ~/.claude/*", "ls ~/.claude/plug?ns", "ls ~/.claude/plugins/[c]ache", "cat $HOME/.claude/x", "echo ~/.claude/{plugins,x}", "echo `id` > .claude/x",
                "cd ~/.claude && touch f", "pushd .claude", "(cd .claude; touch f)", "ls $CLAUDE_CONFIG_DIR", "CLAUDE_CONFIG_DIR=/x ls /x/*", f"ls {cfg}/pl*",
                f"cd {cfg} && ls"):
        assert bash(cmd, home, env=env) == "deny", cmd
    for cmd in ("git add .claude/settings.json", "ls src", "echo $HOME", "ls ~/*.md", "cat .claude/CLAUDE.md"):
        assert bash(cmd, home, env=env) is None, cmd  # a literal command on the repo's own .claude folder, or no .claude at all


def test_a_word_that_expands_onto_a_protected_path_is_denied_whatever_it_looks_like(tmp_path):
    home, cfg = tmp_path / "deep" / ".sdlc", tmp_path / "cfg"
    env = {"SDLC_HOME": str(home), "CLAUDE_CONFIG_DIR": str(cfg)}
    install_kit(cfg)
    (cfg / "settings.json").write_text("{}")
    (cfg / "plugins" / "installed_plugins.json").write_text("{}")
    for cmd in ("ls plugins/c*", "cat sdlc-sib*", "cat sdlc-sibling-k?ts.js?n", "touch plugins/cache/m*/new", "cat plugins/installed_p*"):
        assert bash(cmd, home, cwd=cfg, env=env) == "deny", cmd  # relative words, resolved against the command's cwd
    assert bash(f"cat {cfg}/sdlc-sibling-k?ts.json", home, cwd=tmp_path, env=env) == "deny"  # absolute, from another directory
    for cmd in ("cat settings.json", "ls plugins/zzz*", "ls set*"):
        assert bash(cmd, home, cwd=cfg, env=env) is None, cmd  # nothing protected comes out of these
