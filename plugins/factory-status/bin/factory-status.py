#!/usr/bin/env python3
"""Usage: factory-status.py --json [--roots DIR ...]
       factory-status.py --repo DIR --line
The one reader of factory state. It stores nothing (only a 60 s `gh` cache in ~/.factory/cache/) and derives everything from what the factory writes:
the `json factory` block and the progress log in changes/<slug>/plan.md, <worktree>/.factory/state/<M>.json, `git worktree list`, and `gh pr list`.
Needs python3 and git; `gh` is optional (without it `prs` is empty and a waiting release PR is not seen). Env FACTORY_HOME overrides ~/.factory.

--json   every git repo under the roots (default ~/projects, depth 3, dot folders, node_modules and .worktrees skipped) that has a factory change under changes/ (a plan with a `json factory` block, or an intent.md with outcome-<n> ids):
  {"generated": iso, "warnings": [str], "projects": [{"repo", "name", "changes": [{"slug", "title", "column", "approved": bool,
     "milestones": [{"id", "state", "tasks": [{"id", "state"}], "gapRound", "gapRounds"}],
     "current": {"milestone", "milestoneIndex", "milestoneCount", "task", "taskIndex", "taskCount", "gapRound", "gapRounds", "since"} | null,
     "needs": {"kind", "text", "where"} | null, "prs": [{"number", "url", "title", "state"}]}]}]}
  column: needs-you | building | ready | backlog | done. needs.kind: approve-plan | blocked | hold-review | gallery | release-pr.
  milestone state: pending | building | incomplete | blocked | hold | merged | shipped. task state: pending | building | done. pr state: open | draft.
--line   one line for the run active in the repo DIR (a worktree is fine): `M3a (4/20) · T2/6 building · gap 0/3 · 38m`; nothing, exit 0, when nothing runs.

How state is read (the log is free text, so these are the rules, most conservative reading wins):
- approved: the plan's progress log has `approved: <sha>`. No such line, no approval.
- A progress entry starts at a heading or a dated line (else at each paragraph). Its first milestone id (M<n>[letter], the heading's first) is its subject. Its state is the
  last SHIPPED / HOLD / BLOCKED / INCOMPLETE in its heading line or at the start of a later line (`BLOCKED: ...`, `State: HOLD`); `HOLD pending` does not count; `HOLD-MERGED <M>` marks it merged. The last entry for a milestone wins.
  The freshest copy of plan.md (main checkout or a milestone worktree) wins, older copies fill the gaps.
- building: the milestone's state file changed in the last 15 minutes, or an unmerged task worktree (branch <slug>-<M>-<T>) of the current milestone exists.
  A task is done when the state file records it merged (or empty) or its `factory-merge: <branch>` commit is on the milestone branch. `since` is when the state file was created (else last changed).
- gap rounds: the highest `GAP-FIX <M> round=<n>` line; the cap is the milestone's gapRounds (default 3).
- Not read: whether an approved revision still matches the files (that needs check-plan.py --approved), a PR's merged state, deploy state.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BLOCK = re.compile(r"^```json c?factory[ \t]*\n(.*?)^```", re.S | re.M)  # check-plan.py's fence, plus the old plugin name `cfactory`; no import, this file runs from ~/.factory/bin too
ACTIVE_SECS = 15 * 60
CACHE_SECS = 60
MS = r"M\d+[a-z]?"
STATE_RE = re.compile(r"\b(SHIPPED|BLOCKED|INCOMPLETE|HOLD)\b(?!-)(?!\s+pending)")  # "(HOLD pending)" says a hold is coming, not that it is here
LINE_STATE = re.compile(r"^\s*(?:[-*]\s*)?(?:state|status)?\s*:?\s*(SHIPPED|BLOCKED|INCOMPLETE|HOLD)\b(?!-)(?!\s+pending)", re.I)
MERGED_RE = re.compile(r"\bHOLD-MERGED\s+(" + MS + r")\b")
STATE_NAME = {"SHIPPED": "shipped", "BLOCKED": "blocked", "INCOMPLETE": "incomplete", "HOLD": "hold"}
DONE = ("shipped", "merged")
SKIP_DIRS = {".worktrees", "node_modules", ".git"}


def home():
    return Path(os.environ.get("FACTORY_HOME") or Path.home() / ".factory")


def read(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def run(cmd, cwd, timeout=10):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return p.stdout if p.returncode == 0 else None


def as_int(v, default):
    """Plan files are untrusted: a count is an int or the default, never a string that could carry markup."""
    return v if isinstance(v, int) and not isinstance(v, bool) else default


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def find_repos(roots, depth=3):
    found = []
    for root in roots:
        root = Path(root).expanduser()
        base = len(root.parts)
        for d, dirs, _ in os.walk(root):
            if (Path(d) / ".git").is_dir():  # a main checkout; a linked worktree has a .git file and is reached through its repo
                if (Path(d) / "changes").is_dir() or any(Path(d).glob(".worktrees/*/changes")):
                    found.append(Path(d))
                dirs[:] = []
            elif len(Path(d).parts) - base >= depth:
                dirs[:] = []
            else:
                dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith(".")]
    return sorted(set(found))


def worktrees(repo):
    """[(path, branch)] from `git worktree list`, the main checkout included; branch is '' when detached."""
    out = run(["git", "-C", str(repo), "worktree", "list", "--porcelain"], None) or ""
    res = []
    for block in out.split("\n\n"):
        path = branch = ""
        for line in block.splitlines():
            if line.startswith("worktree "):
                path = line[9:]
            elif line.startswith("branch refs/heads/"):
                branch = line[18:]
        if path:
            res.append((Path(path), branch))
    return res or [(Path(repo), "")]


def open_prs(repo):
    """Open PRs of the repo from `gh` (cached 60 s); [] when gh is missing, fails or is slow."""
    cache = home() / "cache" / f"gh-{hashlib.sha1(str(repo).encode()).hexdigest()[:12]}.json"
    try:
        if time.time() - cache.stat().st_mtime < CACHE_SECS:
            return json.loads(cache.read_text())
    except (OSError, ValueError):
        pass
    out = run(["gh", "pr", "list", "--state", "open", "--limit", "100", "--json", "number,title,url,headRefName,isDraft,reviewDecision"], str(repo))
    try:
        prs = json.loads(out) if out else []
    except ValueError:
        prs = []
    if out is not None and isinstance(prs, list):
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(prs))
        except OSError:
            pass
    return prs if isinstance(prs, list) else []


def log_events(log, ids):
    """([(milestone, state, note)] in log order, {milestone: highest GAP-FIX round}) from the free-text progress log."""
    log = re.sub(r"<!--.*?-->", "", log, flags=re.S)
    lines = log.splitlines()
    marked = any(re.match(r"#{1,6}\s|\s*(?:[-*]\s+)?\W*\d{4}-\d{2}-\d{2}", ln) for ln in lines)
    entries, prev_blank = [], True
    for ln in lines:
        starts = re.match(r"#{1,6}\s|\s*(?:[-*]\s+)?\W*\d{4}-\d{2}-\d{2}", ln) if marked else (prev_blank and ln.strip())
        if starts or not entries:
            entries.append([])
        entries[-1].append(ln)
        prev_blank = not ln.strip()
    events = []
    for e in entries:
        text = "\n".join(e)
        head = re.sub(r"[*_`]", "", e[0])
        cand = [(i, STATE_RE.findall(head)[-1]) for i in [0] if STATE_RE.search(head)]  # the entry's heading names its state anywhere in the line
        for i, ln in enumerate(e[1:], 1):  # a later line only when it starts with the state word ("BLOCKED: ...", "State: HOLD")
            lm = LINE_STATE.match(re.sub(r"[*_`]", "", ln))
            if lm and lm.group(1) == lm.group(1).upper():
                cand.append((i, lm.group(1)))
        found = [m for m in re.findall(r"\b(" + MS + r")\b", head) if m in ids] or [m for m in re.findall(r"\b(" + MS + r")\b", text) if m in ids]
        if found and cand:
            i, st = cand[-1]
            events.append((found[0], STATE_NAME[st], re.sub(r"[*_`#>]+", "", e[i]).strip()[:200]))
        events += [(m, "merged", "") for m in MERGED_RE.findall(text) if m in ids]
    gaps = {}
    for m, r in re.findall(r"^GAP-FIX (" + MS + r")(?: round=(\d+))?", log, re.M):
        gaps[m] = max(gaps.get(m, 0), int(r or 1))
    return events, gaps


def fmt_age(secs):
    m = max(int(secs // 60), 0)
    return f"{m}m" if m < 60 else f"{m // 60}h{m % 60:02d}m"


def _after_block(text):
    m = BLOCK.search(text or "")
    return text[m.end():] if m else ""


def analyze(repo, slug, wts, now, warns, prs_fn):
    """One change (a slug found in the main checkout or any worktree) -> its card, or None when it is not a factory change.
    The freshest copy of its folder (newest plan.md) supplies title, plan block and intent."""
    where = f"{repo.name}/changes/{slug}"
    card = {"slug": slug, "title": slug, "column": "backlog", "approved": False, "milestones": [], "current": None, "needs": None, "prs": []}
    dirs = [Path(w) / "changes" / slug for w, _ in wts if (Path(w) / "changes" / slug).is_dir()]
    stamp = lambda d: max([(d / n).stat().st_mtime for n in ("plan.md", "intent.md") if (d / n).is_file()] or [0])  # noqa: E731
    dirs.sort(key=stamp)
    cdir = dirs[-1]
    for n in ("plan.md", "intent.md"):
        t = read(cdir / n)
        h = t and re.search(r"^#\s+(.+)$", t, re.M)
        if h:
            card["title"] = h.group(1).strip()
            break
    copies = [d / "plan.md" for d in dirs if (d / "plan.md").is_file()]
    text = next((t for t in (read(p) for p in reversed(copies)) if BLOCK.search(t or "")), None)
    m = BLOCK.search(text or "")
    if not m:
        # no plan block: a draft is backlog, but only when intent.md has factory ids; other tools' changes/ folders are not ours
        return card if any(re.search(r"^\s*-\s*(?:outcome|constraint)-\d+\s*:", read(d / "intent.md") or "", re.M) for d in dirs) else None
    try:
        plan = json.loads(m.group(1))
        mss = [x for x in plan["milestones"] if isinstance(x, dict) and re.fullmatch(MS, str(x.get("id")))]
        if not isinstance(plan, dict) or not mss:
            raise ValueError("no milestones")
    except (ValueError, KeyError, TypeError) as e:
        warns.append(f"{where}: plan block unreadable ({e})")
        return card
    log = "\n".join(_after_block(read(p)) for p in copies)
    ids = [x["id"] for x in mss]
    events, gaps = log_events(log, set(ids))
    logstate = {}
    for mid, st, note in events:
        logstate[mid] = (st, note)
    card["approved"] = bool(re.search(r"\bapproved:\s*`?[0-9a-f]{7,40}", log, re.I))
    change = str(plan.get("change") or slug)
    # state files and task worktrees
    sfiles, building = {}, {}
    for path, branch in wts:
        sm = re.fullmatch(re.escape("milestone/" + change) + "-(" + MS + ")", branch)
        if sm:
            f = Path(path) / ".factory" / "state" / f"{sm.group(1)}.json"
            try:
                st = json.loads(f.read_text())
                s = f.stat()
                sfiles[sm.group(1)] = (st if isinstance(st, dict) else {}, s.st_mtime, getattr(s, "st_birthtime", s.st_mtime))
            except OSError:
                pass
            except ValueError:
                warns.append(f"{where}: state file {f.name} is not valid JSON")
        tm = re.fullmatch(re.escape(change) + "-(" + MS + ")-(T\\d+|gap\\d*)", branch)
        if tm:
            building.setdefault(tm.group(1), []).append(tm.group(2) if tm.group(2).startswith("T") else f"{tm.group(1)}-{tm.group(2)}")
    rows = []
    open_ms = next((ms["id"] for ms in mss if (logstate.get(ms["id"]) or ("",))[0] not in ("shipped", "merged", "hold")), None)  # the current milestone
    subjects = {}
    for ms in mss:
        mid = ms["id"]
        sf = sfiles.get(mid)
        tasks = [t["id"] for t in ms.get("tasks", []) if isinstance(t, dict) and "id" in t]
        done = {t for t, v in ((sf or ({},))[0].get("tasks") or {}).items() if isinstance(v, dict) and (v.get("merged") or v.get("empty"))}
        ls = logstate.get(mid)
        finished = bool(ls) and ls[0] in ("shipped", "merged", "hold")
        live = []
        if mid == open_ms and building.get(mid):  # a leftover worktree of a merged task is not work: only an unmerged one of the current milestone is
            if mid not in subjects:
                subjects[mid] = set((run(["git", "-C", str(repo), "log", "--first-parent", "--format=%s", f"refs/heads/milestone/{change}-{mid}"], None) or "").splitlines())
            for t in building[mid]:
                name = f"{change}-{mid}-{t}" if t.startswith("T") else f"{change}-{t}"
                if f"factory-merge: {name}" in subjects[mid]:
                    done.add(t)
                else:
                    live.append(t)
        active = not finished and (bool(live) or (sf is not None and now - sf[1] < ACTIVE_SECS))
        if finished and ls[0] in DONE:
            state, done = ls[0], set(tasks)
        elif finished:
            state, done = "hold", set(tasks)
        elif active:
            state = "building"
        elif ls:
            state = ls[0]
        else:
            state = "incomplete" if done else "pending"
        tstate = [{"id": t, "state": "done" if t in done else "building" if t in live else "pending"} for t in tasks]
        rows.append({"id": mid, "state": state, "tasks": tstate, "gapRound": gaps.get(mid, 0), "gapRounds": as_int(ms.get("gapRounds"), 3),
                     "_live": live, "_since": (sf[2] if sf else None), "_note": (ls[1] if ls else "")})
    card["milestones"] = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    states = [r["state"] for r in rows]
    cur = next((r for r in rows if r["state"] == "building"), None) or next((r for r in rows if r["state"] in ("blocked", "hold")), None)
    if "building" in states:
        card["column"] = "building"
    elif not card["approved"]:
        card["column"] = "needs-you"
        card["needs"] = {"kind": "approve-plan", "text": "The plan is written and waits for your approval.", "where": f"In {repo}, run /factory:run {slug} and approve."}
    else:
        card["column"] = "ready"
    prs = []
    if card["approved"] or card["column"] == "building":
        prs = [p for p in prs_fn() if isinstance(p, dict) and _mine(str(p.get("headRefName", "")), change, plan)]
        card["prs"] = [{"number": p.get("number"), "url": p.get("url"), "title": p.get("title"), "state": "draft" if p.get("isDraft") else "open"} for p in prs]
    if card["column"] != "building" and card["approved"]:
        again = f"In {repo}, fix the cause, then run /factory:run {slug}."
        if "blocked" in states:
            card["column"], card["needs"] = "needs-you", {"kind": "blocked", "text": next(r["_note"] for r in rows if r["state"] == "blocked") or "The run stopped on a decision only you can make.", "where": again}
        elif "hold" in states:
            card["column"], card["needs"] = "needs-you", {"kind": "hold-review", "text": next(r["_note"] for r in rows if r["state"] == "hold") or "A held milestone is pushed and waits for you.",
                                                          "where": f"Review the pushed branch in {repo}, then run /factory:run {slug}."}
        elif (release := _release(prs, plan, mss)) is not None:
            gal = any(g.is_file() for w, _ in wts for g in (Path(w) / "changes" / slug / "evidence").glob("*/gallery.md"))
            card["column"] = "needs-you"
            card["needs"] = {"kind": "gallery" if gal else "release-pr", "text": (f"Review the gallery, then merge release PR #{release['number']}." if gal else f"Release PR #{release['number']} waits for your merge."),
                             "where": f"Open {release['url']}"}
        elif all(s in DONE for s in states):
            card["column"] = "done"
    if card["column"] in ("building", "needs-you") and cur is not None:
        card["current"] = _current(cur, rows, mss)
    return card


def _mine(head, change, plan):
    return head.startswith(f"milestone/{change}-") or head == f"plan/{change}" or (bool(plan.get("integration")) and head == plan["integration"])


def _release(prs, plan, mss):
    """The open, non-draft PR a human must merge: the release PR (with `integration`) or the milestone PR, when the plan says the owner merges."""
    owner = plan.get("merge") == "owner" or plan.get("deployOnMerge") is True or any(m.get("risky") for m in mss)
    pick = [p for p in prs if not p.get("isDraft") and (p.get("headRefName") == plan["integration"] if plan.get("integration") else True)]
    return pick[0] if owner and pick else None


def _current(cur, rows, mss):
    ms = next(m for m in mss if m["id"] == cur["id"])
    tasks = [t["id"] for t in ms.get("tasks", []) if isinstance(t, dict) and "id" in t]
    live = cur["_live"]
    task = live[0] if live else next((t["id"] for t in cur["tasks"] if t["state"] != "done"), None)
    idx = tasks.index(task) + 1 if task in tasks else None
    since = cur["_since"]
    return {"milestone": cur["id"], "milestoneIndex": [r["id"] for r in rows].index(cur["id"]) + 1, "milestoneCount": len(rows),
            "task": task, "taskIndex": idx, "taskCount": len(tasks), "gapRound": cur["gapRound"], "gapRounds": cur["gapRounds"],
            "since": iso(since) if since else None}


def project(repo, now=None, warns=None, with_prs=True):
    """{"repo", "name", "changes"} for one main checkout, or None when it holds no change folder."""
    now, warns = now or time.time(), warns if warns is not None else []
    wts = worktrees(repo)
    if not any(Path(w) == Path(repo) for w, _ in wts):
        wts.append((Path(repo), ""))
    memo = []

    def prs_fn():
        if not memo:
            memo.append(open_prs(repo) if with_prs else [])
        return memo[0]

    changes = []
    slugs = sorted({p.name for w, _ in wts if (Path(w) / "changes").is_dir() for p in (Path(w) / "changes").iterdir() if p.is_dir()})
    for slug in slugs:
        try:
            card = analyze(Path(repo), slug, wts, now, warns, prs_fn)
        except Exception as e:  # one broken folder must not hide the others
            warns.append(f"{repo.name}/changes/{slug}: {type(e).__name__}: {e}")
            continue
        if card:
            changes.append(card)
    return {"repo": str(repo), "name": Path(repo).name, "changes": changes} if changes else None


def status(roots):
    warns, projects, now = [], [], time.time()
    for repo in find_repos(roots):
        p = project(repo, now, warns)
        if p:
            projects.append(p)
    return {"generated": iso(now), "warnings": warns, "projects": projects}


def line(repo_arg):
    p = run(["git", "-C", repo_arg, "rev-parse", "--path-format=absolute", "--git-common-dir"], None)
    repo = Path(p.strip()).parent if p else Path(repo_arg)
    proj = project(repo, with_prs=False)
    for c in (proj or {}).get("changes", []):
        cur = c["current"]
        if c["column"] == "building" and cur:
            parts = [f"{cur['milestone']} ({cur['milestoneIndex']}/{cur['milestoneCount']})"]
            if cur["task"]:
                # a gap task is not one of the milestone's planned tasks, so it has no n/total
                parts.append("gap fix building" if "gap" in cur["task"] else f"{cur['task']}/{cur['taskCount']} building")
            parts.append(f"gap {cur['gapRound']}/{cur['gapRounds']}")
            if cur["since"]:
                parts.append(fmt_age(time.time() - datetime.strptime(cur["since"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()))
            return " · ".join(parts)
    return ""


def main(argv=None):
    ap = argparse.ArgumentParser(description="Reads factory state; see the file header.")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--line", action="store_true")
    ap.add_argument("--repo")
    ap.add_argument("--roots", nargs="+")
    a = ap.parse_args(argv)
    if a.line:
        try:
            out = line(a.repo or os.getcwd())
        except Exception:  # a status line must never break its host
            out = ""
        if out:
            print(out)
        return 0
    if a.json:
        print(json.dumps(status(a.roots or [Path.home() / "projects"]), indent=1))
        return 0
    ap.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
