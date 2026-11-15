#!/usr/bin/env python3
"""The checks and the removals of the git-cleanup-run skill. Python 3 standard library only.

  cleanup.py list            read only: print JSON, one item per ended session or linked worktree idle 30 days or more,
                             each with the result of every check and a verdict (removable, or needs-look with the
                             first failed check)
  cleanup.py act ID [ID...]  act on the ids the owner chose, and only those: each id is checked again right before
                             it is acted on; prints JSON with cleared, removed, skipped and failed

Sessions leave Claude Code's list with `claude rm <job id>`; worktrees go with `git worktree remove <path>`, run from
the main checkout. Neither forces anything, and branches are kept. The script reads `claude`, git, `gh` and the
tracker's own records (the agent-tracker folder of the Claude folder). The days are fixed; ids are never read from
`list` or from standard input.
"""
import argparse
import fnmatch
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

DAYS = 30
DAY = 86400
SECRET_NAMES = (".env*", "*.pem", "*key*", "credentials*")
OTHER_MAX = 3  # other ignored names listed before "and N more"
NAME_MAX = 30  # cells
REASON_MAX = 60  # cells, as the tracker cuts a failure reason
JOB_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")  # a job id is a plain word, as the tracker takes it
# The tracker's git flags: a repo's own config cannot start a program (fsmonitor, hooks).
GIT_FLAGS = ["-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null"]
WHY = {
    "pid_reported": "no pid reported",
    "no_process": "a process is running",
    "job_id": "no job id",
    "asks": "a task is marked partly done or not started",
    "linked": "not a linked worktree",
    "clean": "uncommitted changes",
    "pushed": "commits not pushed",
    "merged": "branch not merged",
    "unused": "a session is running in it",
}


class Unreadable(Exception):
    pass


def run(argv, cwd=None, timeout=60):
    """The one place a command runs: an argument list, no shell, no input. Every git call gets the tracker's -c flags."""
    if argv[0] == "git":
        argv = ["git", *GIT_FLAGS, *argv[1:]]
    try:
        r = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=timeout,
                           env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
    except (OSError, subprocess.SubprocessError) as e:
        return 127, "", str(e)
    return r.returncode, r.stdout, r.stderr


def under(path, base):
    return path == base or path.startswith(base.rstrip(os.sep) + os.sep)


def real(path):
    return os.path.realpath(path)


def seconds(ms):
    return ms / 1000 if isinstance(ms, (int, float)) and not isinstance(ms, bool) and ms > 0 else None


def read_rows():
    rc, out, err = run(["claude", "agents", "--json", "--all"], timeout=30)
    try:
        rows = json.loads(out) if rc == 0 else None
    except ValueError:
        rows = None
    if not isinstance(rows, list):
        raise Unreadable("Could not read Claude Code's session list" + (f": {err.strip()[:120]}" if err.strip() else "."))
    return [r for r in rows if isinstance(r, dict)]


def read_late(path):
    """The late verdicts by session id, and whether the file is unreadable. A missing file has none."""
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        return {}, False
    except (OSError, ValueError):
        return {}, True
    ok = isinstance(data, dict) and data.get("v") == 1 and isinstance(data.get("by"), dict)
    return (data["by"], False) if ok else ({}, True)


def late_verdicts(w, sid):
    """One session's late verdicts by ask number; None when the file or the session's entry is unreadable."""
    entry = w.late.get(sid)
    if w.late_torn or (entry is not None and not (isinstance(entry, dict) and isinstance(entry.get("verdicts", []), list))):
        return None
    return {v.get("n"): v.get("verdict") for v in (entry or {}).get("verdicts", []) if isinstance(v, dict) and isinstance(v.get("n"), int)}


class World:
    """One read of everything the checks need, taken at the start of a pass."""

    def __init__(self):
        self.now = time.time()
        self.refresh()
        claude = Path.home() / ".claude"
        self.records, self.torn = {}, set()
        for folder in ("sessions", "transcripts"):  # the mod's own file wins over a backfilled one
            for f in sorted((claude / "agent-tracker" / folder).glob("*.json")):
                try:
                    rec = json.loads(f.read_text())
                except (OSError, ValueError):
                    rec = None
                if isinstance(rec, dict):
                    self.records.setdefault(f.stem, rec)
                elif f.stem not in self.records or folder == "sessions":
                    self.torn.add(f.stem)
        self.late, self.late_torn = read_late(claude / "agent-tracker" / "latechecks.json")
        self.transcripts = {}  # session id -> (modified time, path)
        for d in sorted((claude / "projects").glob("*")):
            try:
                for e in os.scandir(d):
                    if e.name.endswith(".jsonl") and e.is_file():
                        self.transcripts[e.name[:-6]] = (e.stat().st_mtime, e.path)
            except OSError:
                continue
        self.last, self.cwd, self.title = {}, {}, {}
        for sid, row, rec in [(r.get("sessionId"), r, self.records.get(r.get("sessionId"))) for r in self.rows] + \
                             [(s, None, rec) for s, rec in self.records.items()]:
            if not isinstance(sid, str):
                continue
            times = [seconds((row or {}).get("startedAt")), seconds((rec or {}).get("lastActivityAt")), (self.transcripts.get(sid) or (None,))[0]]
            known = [t for t in times if t is not None]
            if known:
                self.last[sid] = max(known + [self.last.get(sid, 0)])
            self.cwd.setdefault(sid, (row or rec or {}).get("cwd"))
            self.title.setdefault(sid, (row or {}).get("name") or (rec or {}).get("title"))
        self.rcwd = {sid: real(c) for sid, c in self.cwd.items() if isinstance(c, str)}
        self.repos = self.find_repos()

    def refresh(self):
        """Read the session list again. Records, transcripts and repos stay as read: they only feed idle time and asks."""
        self.rows = read_rows()
        self.pid_seen = any(r.get("pid") for r in self.rows)
        # With no pid in the read nothing can be told apart from a live session, so every row's folder counts as in use.
        self.live = [real(r["cwd"]) for r in self.rows if (r.get("pid") or not self.pid_seen) and isinstance(r.get("cwd"), str)]

    def find_repos(self):
        """main checkout -> its worktree blocks, from the repos the tracker and the rows know. Nothing else is crawled."""
        found = {}
        paths = {(rec.get("repo") or {}).get("path") for rec in self.records.values() if isinstance(rec.get("repo"), dict)}
        paths |= {r.get("cwd") for r in self.rows}
        for p in sorted(x for x in paths if isinstance(x, str) and os.path.isdir(x)):
            rc, out, _ = run(["git", "-C", p, "worktree", "list", "--porcelain"])
            blocks = [dict(line.partition(" ")[::2] for line in b.splitlines() if line) for b in out.split("\n\n") if b.strip()] if rc == 0 else []
            if blocks and "worktree" in blocks[0]:
                found.setdefault(real(blocks[0]["worktree"]), blocks)
        return found

    def repo_name(self, cwd, rec):
        if isinstance(cwd, str):
            for main, blocks in self.repos.items():
                if any("worktree" in b and under(real(cwd), real(b["worktree"])) for b in blocks):
                    return os.path.basename(main)
        name = ((rec or {}).get("repo") or {}).get("name")
        return name or os.path.basename(str(cwd or "").rstrip(os.sep)) or "unknown"


def first_failed(checks):
    failed = next((k for k, ok in checks.items() if not ok), None)
    return ("removable", None) if failed is None else ("needs-look", failed)


def session_item(w, row):
    if row.get("pid"):
        return None  # it has a process: never collected
    sid, jid = row.get("sessionId"), row.get("id")
    last = w.last.get(sid) if isinstance(sid, str) else None
    ident = jid or sid
    if last is None or w.now - last < DAYS * DAY or not isinstance(ident, str):
        return None
    rec = w.records.get(sid)
    asks, reasons = True, {}
    late = late_verdicts(w, sid)
    if sid in w.torn or not isinstance((rec or {}).get("asks", []), list):
        asks, reasons["asks"] = False, "ask record unreadable"
    elif late is None:
        asks, reasons["asks"] = False, "late checks unreadable"
    elif any(isinstance(a, dict) and (a["verdict"] if "verdict" in a else late.get(a.get("n")) if a.get("kind") == "task" and isinstance(a.get("n"), int) else None)
             in ("partly", "not-started") for a in (rec or {}).get("asks", [])):  # a late verdict fills an ask no turn judged, as the tracker's merge does
        asks = False
    if isinstance(jid, str) and jid != "" and not JOB_ID.fullmatch(jid):
        reasons["job_id"] = "job id not plain"
    checks = {"pid_reported": w.pid_seen, "no_process": True, "job_id": isinstance(jid, str) and JOB_ID.fullmatch(jid) is not None, "asks": asks}
    verdict, failed = first_failed(checks)
    repo, title, days = w.repo_name(row.get("cwd"), rec), w.title.get(sid) or "untitled", int((w.now - last) // DAY)
    return {"type": "session", "id": ident, "act_arg": shlex.quote(ident), "label": f"{repo} · {title} · idle {days}d", "short": f"{repo} · {title}", "repo": repo,
            "title": title, "idle_days": days, "transcript": (w.transcripts.get(sid) or (None, None))[1], "checks": checks,
            "verdict": verdict, "failed": failed, "reason": (reasons.get(failed) or WHY[failed]) if failed else None}


def ignored_names(lines):
    names = sorted(n for n in lines if n)
    secret = [n for n in names if any(fnmatch.fnmatchcase(n.rstrip("/").rsplit("/", 1)[-1].lower(), p) for p in SECRET_NAMES)]
    rest = [n for n in names if n not in secret]
    ordered = [n for n in rest if not n.endswith("/")] + [n for n in rest if n.endswith("/")]  # files, then folders
    cut = lambda n: n if len(n) <= NAME_MAX else n[: NAME_MAX - 1] + "…"  # noqa: E731
    return {"secret": secret, "other": [cut(n) for n in ordered[:OTHER_MAX]], "more": max(0, len(ordered) - OTHER_MAX)}


def default_ref(main):
    rc, out, _ = run(["git", "-C", main, "symbolic-ref", "--short", "refs/remotes/origin/HEAD"])
    if rc == 0 and out.strip():
        return out.strip()
    for name in ("main", "master"):
        for ref in (f"refs/remotes/origin/{name}", f"refs/heads/{name}"):
            if run(["git", "-C", main, "rev-parse", "--verify", "--quiet", ref])[0] == 0:
                return ref
    return None


def pr_settled(main, branch):
    """True: the branch's PR is merged or closed. False: none, or one is open. None: gh gave no answer."""
    rc, out, _ = run(["gh", "pr", "list", "--head", branch, "--state", "all", "--json", "state", "--limit", "20"], cwd=main)
    try:
        states = [p.get("state") for p in json.loads(out)] if rc == 0 else None
    except (ValueError, AttributeError):
        states = None
    return None if states is None else bool(states) and "OPEN" not in states


def worktree_item(w, main, block):
    path = block.get("worktree")
    if not path or "prunable" in block or not os.path.isdir(path):
        return None
    branch = (block.get("branch") or "").removeprefix("refs/heads/") or None
    rc, out, _ = run(["git", "-C", path, "log", "-1", "--format=%ct%n%s", "HEAD"])
    commit, _, subject = out.partition("\n") if rc == 0 else ("", "", "")
    where = real(path)
    used = [t for sid, t in w.last.items() if sid in w.rcwd and under(w.rcwd[sid], where)]
    times = [t for t in (float(commit) if commit.strip().isdigit() else None, os.stat(path).st_mtime, *used) if t is not None]
    if not times or w.now - max(times) < DAYS * DAY:
        return None
    rc, out, _ = run(["git", "-C", path, "status", "--porcelain", "--ignored"])
    lines = out.splitlines() if rc == 0 else []
    clean = rc == 0 and not any(not line.startswith("!!") for line in lines)
    rc, out, _ = run(["git", "-C", path, "rev-list", "--count", "HEAD", "--not", "--remotes"])
    unpushed = int(out) if rc == 0 and out.strip().isdigit() else None
    default = default_ref(main)
    merged = default is not None and run(["git", "-C", path, "merge-base", "--is-ancestor", "HEAD", default])[0] == 0
    if not merged and branch:
        merged = pr_settled(main, branch) is True  # no gh: the branch alone decided above (F38)
    checks = {"linked": real(path) != real(main), "clean": clean, "pushed": unpushed == 0, "merged": merged,
              "unused": not any(under(c, where) for c in w.live)}
    verdict, failed = first_failed(checks)
    reason = WHY[failed] if failed else None
    if failed == "pushed" and unpushed:
        reason = f"{unpushed} commit{'' if unpushed == 1 else 's'} not pushed"
    repo, folder, days = os.path.basename(main), os.path.basename(path), int((w.now - max(times)) // DAY)
    return {"type": "worktree", "id": path, "act_arg": shlex.quote(path), "main": main, "label": f"{repo} · {folder} · idle {days}d", "short": f"{repo}/{folder}",
            "repo": repo, "branch": branch, "idle_days": days, "last_commit": subject.strip(), "checks": checks,
            "ignored": ignored_names([line[3:].strip('"') for line in lines if line.startswith("!! ")]),
            "sessions": sorted({w.title[s] for s in w.last if w.title.get(s) and s in w.rcwd and under(w.rcwd[s], where)}),
            "verdict": verdict, "failed": failed, "reason": reason}


def build(w, only=None):
    """Every candidate with its checks. `only`: ids to look at; anything else is skipped before its git calls."""
    items = []
    for row in w.rows:
        if only is None or row.get("id") in only or row.get("sessionId") in only:
            item = session_item(w, row)
            if item and (only is None or item["id"] in only):
                items.append(item)
    for main, blocks in w.repos.items():
        for block in blocks[1:]:
            if only is None or block.get("worktree") in only:
                item = worktree_item(w, main, block)
                if item:
                    items.append(item)
    return items


def cmd_list():
    w = World()
    print(json.dumps({"days": DAYS, "no_pid_reported": not w.pid_seen, "items": build(w)}, indent=1))


def cmd_act(ids):
    """@F59 @2026-11-14-tracker-session-cleanup act re-reads the session list before each id; after the first unreadable read it skips every remaining id without reading again."""
    out = {"cleared": [], "removed": [], "skipped": [], "failed": []}
    unique = list(dict.fromkeys(ids))
    w = World()  # the fresh list; each id below gets its own fresh read of the session list
    known = {i["id"]: i for i in build(w, set(unique))}

    unreadable = False

    def skip(ident, item, why=None, kind=None):
        """@F61 @2026-11-14-tracker-session-cleanup a skip caused by an unreadable session list has its own kind, not a failed check."""
        kind = kind or ("unknown" if item is None else "running" if item["failed"] == "unused" else "needs-look")
        out["skipped"].append({"id": ident, "short": item["short"] if item else ident, "kind": kind,
                               "reason": why or (item["reason"] if item else "not in a fresh list")})

    for ident in unique:
        item = known.get(ident)
        if item is None or item["verdict"] != "removable":
            skip(ident, item)
            continue
        if not unreadable:
            try:
                w.refresh()
            except Unreadable:
                unreadable = True
        if unreadable:
            skip(ident, item, "session list unreadable", "unreadable")
            continue
        again = build(w, {ident})  # the re-check right before the action
        item = next((i for i in again if i["id"] == ident), None)
        if item is None or item["verdict"] != "removable":
            skip(ident, item, None if item else "it changed since the list")
            continue
        if item["type"] == "session":
            rc, o, e = run(["claude", "rm", ident], timeout=15)
            done, bucket = rc == 0, "cleared"
        else:
            rc, o, e = run(["git", "worktree", "remove", ident], cwd=item["main"], timeout=120)  # the tracker's allowance for a removal
            done, bucket = rc == 0, "removed"
        if done:
            out[bucket].append({"id": ident, "short": item["short"]})
        else:
            reason = next((s.strip() for s in (e + "\n" + o).splitlines() if s.strip()), "no reason given")
            cut = reason if len(reason) <= REASON_MAX else reason[: REASON_MAX - 1] + "…"
            out["failed"].append({"id": ident, "short": item["short"], "reason": cut})
    print(json.dumps(out, indent=1))


def main(argv):
    p = argparse.ArgumentParser(prog="cleanup.py", allow_abbrev=False, description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", allow_abbrev=False, help="print the candidates and their checks as JSON; changes nothing")
    act = sub.add_parser("act", allow_abbrev=False, help="clear or remove the ids given, each checked again first")
    act.add_argument("ids", nargs="+", metavar="id")
    args = p.parse_args(argv)
    try:
        cmd_list() if args.cmd == "list" else cmd_act(args.ids)
    except Unreadable as e:
        print(json.dumps({"error": str(e)}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
