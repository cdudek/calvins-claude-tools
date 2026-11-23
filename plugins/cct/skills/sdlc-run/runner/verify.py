"""The verifier: runs approved checks in a clean checkout and writes receipts (design 3.4).

The result comes from the process this module started: its exit status and its own captured output. A results file
the candidate wrote, or anything an agent says, is never read. FAIL means the assertion ran and failed. BLOCKED means
the check could not prove anything (missing tool, zero tests, a check that passes on the base).
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import contract
import store
from store import SdlcError

JOB_DEADLINE = 30 * 60  # seconds; one job
GRACE = 2.0
TRANSIENT = re.compile(r"ECONNRESET|ETIMEDOUT|EAI_AGAIN|Temporary failure in name resolution|browser has been closed|Target closed")
SKIPS = re.compile(r"@pytest\.mark\.skip|pytest\.skip\(|unittest\.skip|\.skip\(|\bxit\(|\bxtest\(|\bxdescribe\(|\.only\(|t\.Skip\(|@Ignore")
ASSERTS = re.compile(r"\bassert\b|\bexpect\(|\bself\.assert|\bt\.(Error|Fatal)|\bshould\b")
TEST_PATH = re.compile(r"(^|/)(tests?|e2e|spec|__tests__)/|\.(test|spec)\.[a-z]+$|(^|/)test_[^/]*$|_test\.[a-z]+$")
DEFAULT_PROTECTED = [".github/workflows/*", "pytest.ini", "tox.ini", "conftest.py", "playwright.config.*", "jest.config.*",
                     "vitest.config.*", "setup.cfg", ".mocharc*", "cypress.config.*", "noxfile.py", ".coveragerc", "tsconfig*.json",
                     ".npmrc", ".pnpmfile.cjs", ".yarnrc.yml", ".yarnrc", ".pnpm-workspace.yaml"]  # no slash: matches in any folder
COUNTERS = [
    (re.compile(r"Ran (\d+) tests?"), lambda m: int(m[1])),
    (re.compile(r"collected (\d+) items?"), lambda m: int(m[1])),
]
SUMMARY = re.compile(r"(\d+) (passed|failed|errors?)\b")


@dataclass
class Job:
    exit: int
    out: str
    killed: str | None = None  # "stop" | "timeout" | None


ENV_KEEP = ("PATH", "HOME", "USER", "LOGNAME", "SHELL", "LANG", "TERM", "TMPDIR", "TZ", "CI")
ENV_KEEP_PREFIX = ("LC_", "XDG_", "PLAYWRIGHT_")


def clean_env(extra: dict | None = None, allow: list[str] | None = None) -> dict:
    """The environment a candidate command gets: no tokens or keys unless the approved contract names the variable."""
    keep = {k: v for k, v in os.environ.items() if k in ENV_KEEP or k.startswith(ENV_KEEP_PREFIX) or k in (allow or [])}
    return {**keep, **(extra or {})}


def kill_recorded(pidfile: Path) -> int | None:
    """Cancel a recorded job only if that PID still is the process we started (same start time and command)."""
    try:
        rec = json.loads(pidfile.read_text())
        pid, ident = int(rec["pid"]), rec["ident"]
    except (ValueError, KeyError, TypeError, OSError):
        return None
    if ident and store.proc_ident(pid) == ident:
        kill_group(pid)
        return pid
    return None


def kill_group(pgid: int) -> None:
    """SIGTERM the process group, then SIGKILL survivors after a short grace period."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(pgid, sig)
        except (ProcessLookupError, PermissionError):  # gone, or a zombie leader the OS will not signal
            return
        t = time.time()
        while sig == signal.SIGTERM and time.time() - t < GRACE:
            try:
                os.killpg(pgid, 0)
            except (ProcessLookupError, PermissionError):
                return
            time.sleep(0.05)


def run_job(rid: str, label: str, argv: list[str], cwd: Path, timeout: float = JOB_DEADLINE, env: dict | None = None,
            allow: list[str] | None = None) -> Job:
    """Run one job in its own process group; poll for the stop marker; cancel the group on stop or deadline."""
    jobs = store.run_dir(rid) / "jobs"
    jobs.mkdir(parents=True, exist_ok=True)
    if store.is_stopped(rid):
        return Job(143, "", "stop")
    try:
        p = subprocess.Popen(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace",
                             start_new_session=True, env=clean_env(env, allow))
    except (FileNotFoundError, PermissionError) as e:
        return Job(127, f"cannot start {argv[0]}: {e}")
    pidf = jobs / f"{label.replace('/', '_')}.pid"
    pidf.write_text(json.dumps({"pid": p.pid, "ident": store.proc_ident(p.pid)}))
    import threading
    buf: list[str] = []
    t = threading.Thread(target=lambda: buf.append(p.stdout.read()), daemon=True)
    t.start()
    start, killed = time.time(), None
    while p.poll() is None:
        if store.is_stopped(rid):
            killed = "stop"
        elif time.time() - start > timeout:
            killed = "timeout"
        if killed:
            kill_group(p.pid)
            break
        time.sleep(0.1)
    p.wait()
    if killed is None and p.returncode != 0 and store.is_stopped(rid):
        killed = "stop"  # `sdlc stop` cancelled the group before this loop saw the marker
    t.join(5)
    pidf.unlink(missing_ok=True)
    return Job(p.returncode, "".join(buf), killed)


def count_tests(out: str, regex: str | None = None) -> int | None:
    """The number of tests the process reports it ran; None when it says nothing countable."""
    if regex:
        m = re.search(regex, out)
        return int(m[1]) if m else None
    for rx, f in COUNTERS:
        m = rx.search(out)
        if m:
            return f(m)
    found = SUMMARY.findall(out)
    if found:
        return sum(int(n) for n, _ in found)
    if re.search(r"no tests ran|0 tests?\b", out):
        return 0
    return None


def classify(chk: dict, job: Job) -> tuple[str, str, int | None]:
    """verdict, reason, tests for one run of a check's runner."""
    if job.killed == "stop":
        return "BLOCKED", "stopped by the owner", None
    if job.killed == "timeout":
        return "BLOCKED", "job deadline reached (30 minutes)", None
    if job.exit in (126, 127):
        return "BLOCKED", f"env: the runner could not start ({job.out.strip()[:120] or 'exit ' + str(job.exit)})", None
    tests = count_tests(job.out, chk.get("count_regex")) if chk.get("count", True) else None
    if chk.get("count", True):
        if tests is None:
            return "BLOCKED", "proves nothing: the output reports no test count (set count_regex or count:false)", None
        if tests < chk.get("min_tests", 1):
            return "BLOCKED", f"proves nothing: {tests} tests ran", tests
    return ("PASS", "", tests) if job.exit == 0 else ("FAIL", f"exit {job.exit}", tests)


def _artifact_env(rid: str, chk: dict) -> dict:
    """A scratch override only: consumers see the packed producer, and the path never reaches a PR."""
    arts = store.load_cp(rid).get("artifacts", {})
    return {f"SDLC_ARTIFACT_{p.upper()}": json_dumps(a) for p, a in arts.items() if p in chk.get("consumes", [])}


def json_dumps(o) -> str:
    import json
    return json.dumps(o, sort_keys=True)


def _checkout(rid: str, repo: str, path: str, sha: str, name: str) -> Path:
    dest = contract.wt_path(path, rid, f"verify-{name}")
    if dest.exists():
        _drop(path, dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    contract.git(path, "worktree", "add", "--detach", "-f", str(dest), sha)
    return dest


def _drop(repo_path: str, dest: Path) -> None:
    subprocess.run(["git", "worktree", "remove", "--force", str(dest)], cwd=repo_path, capture_output=True)
    shutil.rmtree(dest, ignore_errors=True)


def overlay(rid: str, repo: str, dest: Path, pins: dict) -> None:
    """Put the approved copies of the pinned specs and fixtures into the checkout, over whatever the candidate has."""
    src = store.run_dir(rid) / "inputs" / repo
    for rel, want in pins.items():
        if not contract.safe_relpath(rel) or not (dest / rel).resolve().is_relative_to(dest.resolve()):
            raise SdlcError(f"pinned path {rel!r} is not a relative path inside the repo")
        f = src / rel
        if not f.is_file() or store.sha256(f.read_bytes()) != want:
            raise SdlcError(f"approved input {repo}/{rel} is missing or changed since approval")
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f, dest / rel)


PLACEHOLDER = re.compile(r"\{(base|head|producer_sha:([A-Za-z0-9._-]+))\}")


def resolve_argv(rid: str, argv: list[str], head: str, base: str) -> list[str]:
    """The only templating a check argv gets: {base}, {head} and {producer_sha:<repo>}, each replaced by a full SHA the runner
    knows. No shell and nothing else is expanded; a placeholder naming a repo outside the run is an error, not a literal."""
    meta = store.load_meta(rid)

    def sub(m: re.Match) -> str:
        if m[1] == "base":
            return base
        if m[1] == "head":
            return head
        if m[2] not in meta["repos"]:
            raise SdlcError(f"BLOCKED plan placeholder {m[0]} names a repo that is not in this run")
        return contract.current_head(meta, m[2])

    return [PLACEHOLDER.sub(sub, a) for a in argv]


def pinned_inputs(rid: str, repo: str) -> dict:
    """{path: sha256} of the config files the approved contract pins for a repo (playwright.config.*, tsconfig*.json, .npmrc ...)."""
    src = store.run_dir(rid) / "inputs" / repo
    out = {}
    for rel in contract.pinned_map(store.read_json(store.run_dir(rid) / "contract.json")).get(repo, []):
        f = src / rel
        out[rel] = store.sha256(f.read_bytes()) if f.is_file() else ""
    return out


def prereq_missing(chk: dict) -> str:
    for p in chk.get("prereqs", []):
        if "tool" in p and not shutil.which(p["tool"]):
            return f"env: tool {p['tool']} is not installed"
        if "env" in p and not os.environ.get(p["env"]):
            return f"env: variable {p['env']} is not set"
        if "file" in p and not Path(p["file"]).expanduser().exists():
            return f"env: file {p['file']} is missing"
        if "browser" in p:
            from board import browser_available
            ok, why = browser_available(p.get("executable"))
            if not ok:
                return f"env: browser unavailable ({why})"
    return ""


def verify_check(rid: str, chk: dict, ref: str | None = None, base_sha: str | None = None) -> dict:
    """Run one contract item on the current head of its repo and write the receipt. Returns the receipt body."""
    meta = store.load_meta(rid)
    repo = meta["repos"][chk["repo"]]
    head = contract.git(repo["path"], "rev-parse", ref) if ref else contract.current_head(meta, chk["repo"])
    key = re.sub(r"[^A-Za-z0-9]+", "-", chk["id"])
    deps = {p: contract.current_head(meta, p) for p in chk.get("consumes", []) if p in meta["repos"]}

    def done(verdict, reason, exit_code=None, tests=None, base=None):
        return contract.write_receipt(rid, chk, sha=head, verdict=verdict, exit_code=exit_code, tests=tests, base=base,
                                      reason=reason, deps=deps)["body"]

    if store.is_stopped(rid):
        return done("BLOCKED", "stopped by the owner")
    missing = prereq_missing(chk)
    if missing:
        return done("BLOCKED", missing)
    base_rec = None
    wt = None
    try:
        wt = _checkout(rid, chk["repo"], repo["path"], head, f"c-{key}")
        try:
            tamper = guard_paths(rid, meta, chk, wt)
        except SdlcError as e:
            return done("BLOCKED", str(e))
        if tamper:
            return done("BLOCKED", tamper)
        try:
            overlay(rid, chk["repo"], wt, {**chk.get("pins", {}), **pinned_inputs(rid, chk["repo"])})
        except SdlcError as e:
            return done("BLOCKED", str(e))
        if bad := install_dependencies(rid, chk, wt):
            return done("BLOCKED", bad)
        kind = chk["expect"]["kind"]
        if kind in ("fails_on_base", "negative_control"):
            base_rec = _prove_failing(rid, meta, chk, base_sha or repo["base_sha"], wt, key)
            if base_rec["verdict"] != "OK":
                return done("BLOCKED", base_rec["reason"], base=base_rec)
        env = _artifact_env(rid, chk)  # one environment for the first run and the retry
        argv = resolve_argv(rid, chk["runner"], head, base_sha or repo["base_sha"])
        job = run_job(rid, f"{chk['repo']}-{chk['id']}", argv, wt, env=env, allow=chk.get("env"))
        if job.exit != 0 and TRANSIENT.search(job.out) and _spend_retry(rid, f"{chk['repo']}:{chk['id']}"):
            job = run_job(rid, f"{chk['repo']}-{chk['id']}", argv, wt, env=env, allow=chk.get("env"))
        verdict, reason, tests = classify(chk, job)
        ev = store.run_dir(rid) / "evidence" / f"{chk['repo']}--{chk['id'].replace('/', '_')}.log"
        store.atomic_write(ev, job.out[-20000:])
        return done(verdict, reason, job.exit, tests, base_rec)
    finally:
        if wt:
            _drop(repo["path"], wt)
            _drop(repo["path"], contract.wt_path(repo["path"], rid, f"verify-b-{key}"))


def install_dependencies(rid: str, chk: dict, wt: Path) -> str:
    """A fresh checkout gets its approved dependencies through the frozen install (scripts and source builds off)."""
    import deps
    if not (chk.get("install") or store.read_json(store.run_dir(rid) / "contract.json").get("deps", {}).get(chk["repo"])
            or deps.pin_record(rid, chk["repo"])):  # a consumer with runner-pinned tarballs installs from those vendored files
        return ""
    argv = deps.frozen_install(wt)
    if not argv:
        return ""
    job = run_job(rid, f"{chk['repo']}-install", argv, wt, allow=chk.get("env"))
    return "" if job.exit == 0 else f"env: the frozen install failed ({job.out.strip()[-120:] or 'exit ' + str(job.exit)})"


def _spend_retry(rid: str, key: str) -> bool:
    spent = []
    def f(cp):
        if cp["retries"].get(key, 0) < 1:
            cp["retries"][key] = cp["retries"].get(key, 0) + 1
            spent.append(1)
    store.update_cp(rid, f)
    return bool(spent)


def _prove_failing(rid: str, meta: dict, chk: dict, base_sha: str, cand_wt: Path, key: str) -> dict:
    """Changed behaviour: the same assertions must fail on the base. An invariant: a known-bad control must fail."""
    repo = meta["repos"][chk["repo"]]
    if chk["expect"]["kind"] == "negative_control":
        argv, wt = chk["expect"].get("control"), cand_wt
        if argv:
            argv = resolve_argv(rid, argv, contract.current_head(meta, chk["repo"]), base_sha)
        if not argv:
            return {"verdict": "NO", "reason": "negative_control check names no control command"}
    else:
        argv, wt = resolve_argv(rid, chk["runner"], base_sha, base_sha), _checkout(rid, chk["repo"], repo["path"], base_sha, f"b-{key}")
        overlay(rid, chk["repo"], wt, {**chk.get("pins", {}), **pinned_inputs(rid, chk["repo"])})
    if bad := install_dependencies(rid, chk, wt):
        return {"verdict": "NO", "reason": bad}
    job = run_job(rid, f"{chk['repo']}-{chk['id']}-base", argv, wt, allow=chk.get("env"))
    tests = count_tests(job.out, chk.get("count_regex")) if chk.get("count", True) else None
    rec = {"sha": base_sha, "exit": job.exit, "tests": tests}
    if job.exit in (126, 127) or job.killed:
        return {**rec, "verdict": "NO", "reason": "base proof could not run (missing executable, stop or deadline)"}
    if job.exit == 0:
        return {**rec, "verdict": "NO", "reason": "proves nothing: the check passes on the base" if chk["expect"]["kind"] == "fails_on_base"
                else "proves nothing: the negative control passes"}
    if chk.get("count", True) and not tests:
        return {**rec, "verdict": "NO", "reason": "proves nothing: the base failed with no test collected"}
    return {**rec, "verdict": "OK", "reason": ""}


def _protected(rel: str, globs: list[str]) -> bool:
    base = rel.rsplit("/", 1)[-1]
    return any(fnmatch.fnmatch(rel, g) or ("/" not in g and fnmatch.fnmatch(base, g)) for g in globs)


def guard_paths(rid: str, meta: dict, chk: dict, wt: Path) -> str:
    """The candidate may not edit a pinned spec: its copy must equal the approved one, or be absent (overlaid)."""
    src = store.run_dir(rid) / "inputs" / chk["repo"]
    for rel in chk.get("pins", {}):
        f = wt / rel
        if f.is_file() and (src / rel).is_file() and f.read_bytes() != (src / rel).read_bytes():
            return f"test path: the candidate changed pinned input {rel}"
    return ""


BLOCK = re.compile(r"^(\s*)(?:async\s+)?def\s+(test\w*)|^(\s*)(?:it|test)\s*\(\s*['\"`]([^'\"`]+)['\"`]")
TRIVIAL = re.compile(r"assert\s+(True|1)\b|assertTrue\(\s*True\s*\)|assertEqual\(\s*(\w+)\s*,\s*\2\s*\)|expect\(\s*true\s*\)|assert\s+not\s+False")


def assertions_per_test(text: str) -> dict[str, int]:
    """Meaningful assertions per test name: a trivial `assert True` never counts."""
    out: dict[str, int] = {}
    cur = None
    for line in text.splitlines():
        m = BLOCK.match(line)
        if m:
            cur = m.group(2) or m.group(4)
            out.setdefault(cur, 0)
        elif cur and ASSERTS.search(line) and not TRIVIAL.search(line):
            out[cur] += 1
    return out


def _show(path: str, ref: str, rel: str) -> str | None:
    r = subprocess.run(["git", "show", f"{ref}:{rel}"], cwd=path, capture_output=True, text=True, errors="replace")
    return r.stdout if r.returncode == 0 else None


def replaces(rid: str, task: str | None) -> list[str]:
    """The test paths or globs a task declared in the approved task graph as replaced by its work (a greenfield rewrite)."""
    if not task:
        return []
    for m in store.read_json(store.run_dir(rid) / "tasks.json").get("milestones", []):
        for t in m.get("tasks", []):
            if t["id"] == task:
                return t.get("replaces_tests", [])
    return []


def replaceable(rel: str, globs: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel, g) for g in globs)


def guard_diff(rid: str, repo_name: str, base: str, cand: str, task: str | None = None) -> list[str]:
    """Compare a candidate against its base for tampering (called before integration). Empty list means clean.
    A task's declared `replaces_tests` may be deleted or rewritten; nothing else may, and the contract's own checks still run."""
    import deps
    meta = store.load_meta(rid)
    path = meta["repos"][repo_name]["path"]
    c = store.read_json(store.run_dir(rid) / "contract.json")
    mine = [k for k in c["checks"] if k["repo"] == repo_name]
    pins = {rel for k in mine for rel in k.get("pins", {})} | set(pinned_inputs(rid, repo_name))
    swap = replaces(rid, task)
    allowed = {m["path"] for m in c.get("migrations", [])} | set(c.get("deps", {}).get(repo_name, {}).get("files", {}))
    protected = DEFAULT_PROTECTED + c.get("protected", [])
    for k in mine:  # the runner entry and the config the contract names are protected too
        if k["runner"][0] == "make":
            protected.append("Makefile")
        for tok in k["runner"][1:]:
            if contract.safe_relpath(tok) and subprocess.run(["git", "cat-file", "-e", f"{base}:{tok}"], cwd=path, capture_output=True).returncode == 0:
                protected.append(tok)
    bad = []
    for line in contract.git(path, "diff", "--name-status", f"{base}..{cand}").splitlines():
        status, _, rel = line.partition("\t")
        rel = rel.split("\t")[-1]
        if rel in allowed:
            continue
        if rel in pins:
            bad.append(f"changed pinned input {rel}")
        elif swap and TEST_PATH.search(rel) and replaceable(rel, swap):
            continue  # a declared replacement: its removed tests and assertions are expected (skips are still refused below)
        elif _protected(rel, protected):
            bad.append(f"changed protected path {rel} (test discovery, runner config or CI)")
        elif TEST_PATH.search(rel) and status.startswith("D"):
            bad.append(f"deleted test file {rel}")
        elif TEST_PATH.search(rel) and (old := _show(path, base, rel)) is not None:
            new = _show(path, cand, rel) or ""
            was, now = assertions_per_test(old), assertions_per_test(new)
            for name, n in was.items():
                if name not in now:
                    bad.append(f"removed test {name} in {rel}")
                elif now[name] < n:
                    bad.append(f"removed an assertion in {name} ({rel})")
    bad += deps.guard(rid, repo_name, base, cand)
    cur = ""
    for line in contract.git(path, "diff", "-U0", f"{base}..{cand}").splitlines():
        if line.startswith("+++ "):
            cur = line[6:] if line.startswith("+++ b/") else ""
        elif cur and cur not in allowed and TEST_PATH.search(cur) and line.startswith("+") and SKIPS.search(line):
            bad.append(f"added a skip in {cur}: {line[1:].strip()[:60]}")
    return bad
