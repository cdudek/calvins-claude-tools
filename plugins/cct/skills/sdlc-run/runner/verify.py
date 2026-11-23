"""The verifier: runs approved checks in a clean checkout and writes receipts (design 3.4).

The result comes from the process this module started: its exit status and its own captured output. A results file
the candidate wrote, or anything an agent says, is never read. FAIL means the assertion ran and failed. BLOCKED means
the check could not prove anything (missing tool, zero tests, a check that passes on the base).
"""
from __future__ import annotations

import fnmatch
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
DEFAULT_PROTECTED = [".github/workflows/*", ".github/workflows/**", "pytest.ini", "tox.ini", "conftest.py", "**/conftest.py",
                     "playwright.config.*", "jest.config.*", "vitest.config.*", "**/playwright.config.*"]
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


def kill_group(pgid: int) -> None:
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            return
        t = time.time()
        while sig == signal.SIGTERM and time.time() - t < GRACE:
            try:
                os.killpg(pgid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.05)


def run_job(rid: str, label: str, argv: list[str], cwd: Path, timeout: float = JOB_DEADLINE, env: dict | None = None) -> Job:
    """Run one job in its own process group; poll for the stop marker; cancel the group on stop or deadline."""
    jobs = store.run_dir(rid) / "jobs"
    jobs.mkdir(parents=True, exist_ok=True)
    if store.is_stopped(rid):
        return Job(143, "", "stop")
    try:
        p = subprocess.Popen(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace",
                             start_new_session=True, env={**os.environ, **(env or {})})
    except (FileNotFoundError, PermissionError) as e:
        return Job(127, f"cannot start {argv[0]}: {e}")
    pidf = jobs / f"{label.replace('/', '_')}.pid"
    pidf.write_text(str(p.pid))
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
        f = src / rel
        if not f.is_file() or store.sha256(f.read_bytes()) != want:
            raise SdlcError(f"approved input {repo}/{rel} is missing or changed since approval")
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f, dest / rel)


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
        overlay(rid, chk["repo"], wt, chk.get("pins", {}))
        kind = chk["expect"]["kind"]
        if kind in ("fails_on_base", "negative_control"):
            base_rec = _prove_failing(rid, meta, chk, base_sha or repo["base_sha"], wt, key)
            if base_rec["verdict"] != "OK":
                return done("BLOCKED", base_rec["reason"], base=base_rec)
        job = run_job(rid, f"{chk['repo']}-{chk['id']}", chk["runner"], wt, env=_artifact_env(rid, chk))
        if job.exit != 0 and TRANSIENT.search(job.out) and _spend_retry(rid, f"{chk['repo']}:{chk['id']}"):
            job = run_job(rid, f"{chk['repo']}-{chk['id']}", chk["runner"], wt)
        verdict, reason, tests = classify(chk, job)
        ev = store.run_dir(rid) / "evidence" / f"{chk['repo']}--{chk['id'].replace('/', '_')}.log"
        store.atomic_write(ev, job.out[-20000:])
        return done(verdict, reason, job.exit, tests, base_rec)
    finally:
        if wt:
            _drop(repo["path"], wt)
            _drop(repo["path"], contract.wt_path(repo["path"], rid, f"verify-b-{key}"))


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
        if not argv:
            return {"verdict": "NO", "reason": "negative_control check names no control command"}
    else:
        argv, wt = chk["runner"], _checkout(rid, chk["repo"], repo["path"], base_sha, f"b-{key}")
        overlay(rid, chk["repo"], wt, chk.get("pins", {}))
    job = run_job(rid, f"{chk['repo']}-{chk['id']}-base", argv, wt)
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


def _match(path: str, globs: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, g) for g in globs)


def guard_paths(rid: str, meta: dict, chk: dict, wt: Path) -> str:
    """The candidate may not edit a pinned spec: its copy must equal the approved one, or be absent (overlaid)."""
    src = store.run_dir(rid) / "inputs" / chk["repo"]
    for rel in chk.get("pins", {}):
        f = wt / rel
        if f.is_file() and (src / rel).is_file() and f.read_bytes() != (src / rel).read_bytes():
            return f"test path: the candidate changed pinned input {rel}"
    return ""


def guard_diff(rid: str, repo_name: str, base: str, cand: str) -> list[str]:
    """Compare a candidate against its base for tampering (called before integration). Empty list means clean."""
    meta = store.load_meta(rid)
    path = meta["repos"][repo_name]["path"]
    c = store.read_json(store.run_dir(rid) / "contract.json")
    pins = {rel for chk in c["checks"] if chk["repo"] == repo_name for rel in chk.get("pins", {})}
    allowed = {m["path"] for m in c.get("migrations", [])}
    protected = DEFAULT_PROTECTED + c.get("protected", [])
    bad = []
    names = contract.git(path, "diff", "--name-status", f"{base}..{cand}").splitlines()
    for line in names:
        status, _, rel = line.partition("\t")
        rel = rel.split("\t")[-1]
        if rel in allowed:
            continue
        if rel in pins:
            bad.append(f"changed pinned input {rel}")
        elif _match(rel, protected):
            bad.append(f"changed protected path {rel} (test discovery or CI)")
        elif TEST_PATH.search(rel) and status.startswith("D"):
            bad.append(f"deleted test file {rel}")
    import deps
    bad += deps.guard(rid, repo_name, base, cand)
    allowed |= set(c.get("deps", {}).get(repo_name, {}).get("files", {}))
    diff = contract.git(path, "diff", "-U0", f"{base}..{cand}")
    cur, tally = "", {}
    for line in diff.splitlines():
        if line.startswith("+++ "):
            cur = line[6:] if line.startswith("+++ b/") else ""
        elif cur and cur not in allowed and TEST_PATH.search(cur):
            if line.startswith("+") and SKIPS.search(line):
                bad.append(f"added a skip in {cur}: {line[1:].strip()[:60]}")
            elif line[:1] in "+-" and line[:3] not in ("+++", "---") and ASSERTS.search(line):
                tally[cur] = tally.get(cur, 0) + (1 if line[0] == "+" else -1)
    bad += [f"removed an assertion in {f}" for f, n in tally.items() if n < 0]  # a reworded assertion nets to zero
    return bad
