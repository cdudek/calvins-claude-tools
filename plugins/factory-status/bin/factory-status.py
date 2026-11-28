#!/usr/bin/env python3
"""Usage: factory-status.py --json [--roots DIR ...]
       factory-status.py --repo DIR --line
The one reader of factory state. It stores nothing (only a 60 s `gh` cache in ~/.factory/cache/) and derives everything from what the factory writes:
the `json factory` block and the progress log in changes/<slug>/plan.md, <worktree>/.factory/state/<M>.json, `git worktree list`, and `gh pr list`.
Needs python3 and git; `gh` is optional (without it `prs` is empty and a waiting release PR is not seen). Env FACTORY_HOME overrides ~/.factory.

--json   every git repo under the roots (default ~/projects, depth 3, dot folders, node_modules and .worktrees skipped) that has a factory change under changes/ (a plan with a `json factory` block, or an intent.md with outcome-<n> ids):
  {"generated": iso, "warnings": [str], "projects": [{"repo", "name", "changes": [{"slug", "title", "column", "stage", "approved": bool, "approvedSha", "approvedAt", "integration", "doneAt",
     "outcomes": [{"id", "text"}], "requirementCount", "milestones": [{"id", "title", "layer", "risky", "requirements", "branch", "state", "tasks": [{"id", "state", "title", "model", "effort"}],
     "gapRound", "gapRounds", "verifier": {"result", "sha", "reqs"}}], "current": {...} | null, "needs": need | null, "needsAll": [need],
     "questions": [{"id", "milestone", "text", "source", "open", "at"}], "failures": [{"milestone", "text", "sha", "at", "kind", "reqs"}],
     "run": {"state", "lastActivity", "lastEndState", "worktree", "logLines"}, "prs": [{"number", "url", "title", "state"}]}]}]}
  need = {"kind", "text", "cmd", "where", "since", "milestone"}. Full contract: references/board.md.
  column: needs-you | building | ready | backlog | done. stage: intent | plan | ready | building | done. need kind: approve-plan | blocked | hold-review | gallery | release-pr | question.
  milestone state: pending | building | incomplete | blocked | hold | merged | shipped. task state: pending | building | done | failed. pr state: open | draft. Unknown values are null, never invented.
--line   one line for the run active in the repo DIR (a worktree is fine): `M3a (4/20) · T2/6 building · gap 0/3 · 38m`; nothing, exit 0, when nothing runs.

How state is read (the log is free text, so these are the rules, most conservative reading wins):
- approved: the plan's progress log has `approved: <sha>`. No such line, no approval.
- A progress entry starts at a heading or a dated line (else at each paragraph). Its first milestone id (M<n>[letter], the heading's first) is its subject. Its state is the
  last SHIPPED / HOLD / BLOCKED / INCOMPLETE in its heading line or at the start of a later line (`BLOCKED: ...`, `State: HOLD`); `HOLD pending` does not count; `HOLD-MERGED <M>` marks it merged. The last entry for a milestone wins.
  The freshest copy of plan.md (main checkout or a milestone worktree) wins, older copies fill the gaps.
- building: the milestone's state file changed in the last 15 minutes, or an unmerged task worktree (branch <slug>-<M>-<T>) of the current milestone exists.
  A task is done when the state file records it merged (or empty) or its `factory-merge: <branch>` commit is on the milestone branch. `since` is when the state file was created (else last changed).
- board lines (QUESTION, ANSWERED, VERIFY, ERROR) are read one per line, each once; `[NEEDS CLARIFICATION: ...]` in delta.md is an open question.
- gap rounds: the highest `GAP-FIX <M> round=<n>` line; the cap is the milestone's gapRounds (default 3).
- Not read: whether an approved revision still matches the files (that needs check-plan.py --approved), a PR's merged state, deploy state.
"""
import argparse
import hashlib
import json
import os
import re
import shlex
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


ENTRY_START = r"#{1,6}\s|\s*(?:[-*]\s+)?\W*\d{4}-\d{2}-\d{2}"
TS_RE = re.compile(r"(\d{4}-\d{2}-\d{2})(?:[ T,]+(\d{1,2}:\d{2}))?")
HM_RE = re.compile(r"^\W*(\d{1,2}:\d{2})\b")
LEAD_TS = re.compile(r"^(?:\d{4}-\d{2}-\d{2}[ T,]*)?(?:\d{1,2}:\d{2}\s*[-:,]?\s*)?")
REQS = r"(req-\d+(?:[ ,]+req-\d+)*)"
LINE_KINDS = (
    ("question", re.compile(r"QUESTION (" + MS + r") (q\d+):\s*(.+)")),
    ("answered", re.compile(r"ANSWERED (" + MS + r") (q\d+):\s*(.+)")),
    ("verify-pass", re.compile(r"VERIFY (" + MS + r") PASS ([0-9a-f]{7,40})\b")),
    ("verify-fail", re.compile(r"VERIFY (" + MS + r") FAIL ([0-9a-f]{7,40}) " + REQS + r":\s*(.+)")),
    ("error", re.compile(r"ERROR (" + MS + r"):\s*(.+)")),
)


def to_iso(date, hm=None):
    """Log times carry no zone: a date with a time is read as this machine's local time and written as UTC; a bare date stays `YYYY-MM-DD`."""
    if not hm:
        return date
    try:
        return datetime.strptime(f"{date} {hm}", "%Y-%m-%d %H:%M").astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return date


def stamp_of(line, head_ts):
    """The line's own time when it carries one (`2026-11-28 10:05` or `19:44` after the entry's date), else the entry heading's, else None."""
    m = TS_RE.search(line[:40])
    if m:
        return to_iso(m.group(1), m.group(2))
    h = HM_RE.match(line)
    if h and head_ts:
        return to_iso(head_ts[0], h.group(1))
    return head_ts and to_iso(*head_ts)


def log_entries(log):
    """The progress log as entries (lists of lines): each starts at a heading or dated line, else at each paragraph."""
    log = re.sub(r"<!--.*?-->", "", log, flags=re.S)
    lines = log.splitlines()
    marked = any(re.match(ENTRY_START, ln) for ln in lines)
    entries, prev_blank = [], True
    for ln in lines:
        starts = re.match(ENTRY_START, ln) if marked else (prev_blank and ln.strip())
        if starts or not entries:
            entries.append([])
        entries[-1].append(ln)
        prev_blank = not ln.strip()
    return entries


def log_events(log, ids):
    """([(milestone, state, note, at)] in log order, {milestone: highest GAP-FIX round}) from the free-text progress log."""
    entries = log_entries(log)
    events = []
    for e in entries:
        text = "\n".join(e)
        head = re.sub(r"[*_`]", "", e[0])
        hm = TS_RE.search(head)
        head_ts = (hm.group(1), hm.group(2)) if hm else None
        at = head_ts and to_iso(*head_ts)
        cand = [(i, STATE_RE.findall(head)[-1]) for i in [0] if STATE_RE.search(head)]  # the entry's heading names its state anywhere in the line
        for i, ln in enumerate(e[1:], 1):  # a later line only when it starts with the state word ("BLOCKED: ...", "State: HOLD")
            lm = LINE_STATE.match(re.sub(r"[*_`]", "", ln))
            if lm and lm.group(1) == lm.group(1).upper():
                cand.append((i, lm.group(1)))
        found = [m for m in re.findall(r"\b(" + MS + r")\b", head) if m in ids] or [m for m in re.findall(r"\b(" + MS + r")\b", text) if m in ids]
        if found and cand:
            i, st = cand[-1]
            events.append((found[0], STATE_NAME[st], re.sub(r"[*_`#>]+", "", e[i]).strip()[:200], stamp_of(re.sub(r"[*_`#>]+", "", e[i]).strip(), head_ts) if i else at))
        events += [(m, "merged", "", at) for m in MERGED_RE.findall(text) if m in ids]
    gaps = {}
    gap_files = {}
    for m, r, f in re.findall(r"^GAP-FIX (" + MS + r")(?: round=(\d+))?(?: files=(\S*))?", re.sub(r"<!--.*?-->", "", log, flags=re.S), re.M):
        gaps[m] = max(gaps.get(m, 0), int(r or 1))
        gap_files[(m, int(r or 1))] = f
    return events, gaps, gap_files


def log_records(log, ids):
    """The board's fixed one-line formats, in log order, each once (plan.md copies repeat the log):
    {"questions": [{id, milestone, text, at}], "answered": {(milestone, id): text}, "verifies": [{milestone, result, sha, reqs, text, at}], "errors": [{milestone, text, at}]}."""
    out = {"questions": [], "answered": {}, "verifies": [], "errors": []}
    seen = set()
    for e in log_entries(log):
        hm = TS_RE.search(re.sub(r"[*_`]", "", e[0]))
        head_ts = (hm.group(1), hm.group(2)) if hm else None
        for ln in e:
            plain = re.sub(r"[*_`]", "", ln).strip()
            plain = re.sub(r"^[-*]\s+", "", plain)
            body = plain[LEAD_TS.match(plain).end():]
            for kind, rx in LINE_KINDS:
                m = rx.match(body)
                if not m or m.group(1) not in ids:
                    continue
                key = (kind,) + m.groups()
                if key in seen:
                    break
                seen.add(key)
                n = len(seen)
                at = stamp_of(plain, head_ts)
                g = m.groups()
                if kind == "question":
                    out["questions"].append({"id": g[1], "milestone": g[0], "text": g[2].strip()[:300], "at": at, "n": n})
                elif kind == "answered":
                    out["answered"][(g[0], g[1])] = g[2].strip()[:300]
                elif kind == "verify-pass":
                    out["verifies"].append({"milestone": g[0], "result": "PASS", "sha": g[1], "reqs": [], "text": f"Verifier PASS on {g[1][:7]}.", "at": at, "n": n})
                elif kind == "verify-fail":
                    reqs = re.findall(r"req-\d+", g[2])
                    out["verifies"].append({"milestone": g[0], "result": "FAIL", "sha": g[1], "reqs": reqs, "text": f"Verifier FAIL {', '.join(reqs)}: {g[3].strip()[:300]}", "at": at, "n": n})
                else:
                    out["errors"].append({"milestone": g[0], "text": g[1].strip()[:300], "at": at, "n": n})
                break
    return out


def fmt_age(secs):
    m = max(int(secs // 60), 0)
    return f"{m}m" if m < 60 else f"{m // 60}h{m % 60:02d}m"


def _after_block(text):
    m = BLOCK.search(text or "")
    return text[m.end():] if m else ""


def _blank(slug):
    return {"slug": slug, "title": slug, "column": "backlog", "stage": "intent", "approved": False, "approvedSha": None, "approvedAt": None,
            "integration": None, "doneAt": None, "outcomes": [], "requirementCount": 0, "milestones": [], "current": None,
            "needs": None, "needsAll": [], "questions": [], "failures": [],
            "run": {"state": "idle", "lastActivity": None, "lastEndState": None, "worktree": None, "logLines": []}, "prs": []}


def _short(text, n):
    text = re.sub(r"[*_`]", "", text or "").strip()
    return text[:n].rstrip() or None


def prose_titles(text):
    """({milestone: title}, {task: title}) from the plan's prose (before the json block): `### M1 layer: Title` headings and `- **T1:** Title. ...` bullets. Absent -> missing, never invented."""
    ms, ts = {}, {}
    for ln in (text or "").splitlines():
        m = re.match(r"#{2,5}\s+(?:Milestone\s+)?(" + MS + r")\b[\s:—–-]*(.*)$", ln)
        if m and _short(m.group(2), 120):
            ms.setdefault(m.group(1), _short(m.group(2), 120))
        t = re.match(r"\s*[-*]\s+\*\*(T\d+)\b[^*]*\*\*\s*(.*)$", ln)
        if t:
            first = re.split(r"\.\s|\sCovers\b|\sOwns\b", t.group(2), maxsplit=1)[0].rstrip(".")
            if _short(first, 100):
                ts.setdefault(t.group(1), _short(first, 100))
    return ms, ts


def intent_outcomes(text):
    return [{"id": i, "text": _short(t, 300) or ""} for i, t in re.findall(r"^\s*-\s*(outcome-\d+)\s*:\s*(.+)$", text or "", re.M)]


def _has_github(repo):
    return "github.com" in (run(["git", "-C", str(repo), "remote", "get-url", "origin"], None) or "")


def _need(kind, text, cmd, where, since=None, milestone=None):
    return {"kind": kind, "text": text, "cmd": cmd, "where": where, "since": since, "milestone": milestone}


def analyze(repo, slug, wts, now, warns, prs_fn):
    """One change (a slug found in the main checkout or any worktree) -> its card, or None when it is not a factory change.
    The freshest copy of its folder (newest plan.md) supplies title, plan block and intent."""
    where = f"{repo.name}/changes/{slug}"
    card = _blank(slug)
    dirs = [Path(w) / "changes" / slug for w, _ in wts if (Path(w) / "changes" / slug).is_dir()]
    stamp = lambda d: max([(d / n).stat().st_mtime for n in ("plan.md", "intent.md") if (d / n).is_file()] or [0])  # noqa: E731
    dirs.sort(key=stamp)
    cdir = dirs[-1]
    for n in ("plan.md", "intent.md"):
        t = read(cdir / n)
        h = t and re.search(r"^#\s+(.+)$", t, re.M)
        if h:
            card["title"] = re.sub(r"^Plan:\s*", "", h.group(1).strip()) or h.group(1).strip()
            break
    intents = [d / "intent.md" for d in dirs if (d / "intent.md").is_file()]
    card["outcomes"] = intent_outcomes(read(intents[-1])) if intents else []
    deltas = [d / "delta.md" for d in dirs if (d / "delta.md").is_file()]
    delta_qs = [{"id": f"d{i}", "milestone": None, "text": _short(t, 300), "source": "delta.md", "open": True, "at": None}
                for i, t in enumerate(re.findall(r"\[NEEDS CLARIFICATION:\s*(.{1,400}?)\]", read(deltas[-1]) or "", re.S), 1) if _short(t, 300)] if deltas else []
    run_cmd = f"/factory:run {shlex.quote(slug)}"
    in_repo = f"Paste it in a new Claude session in {repo.name}."
    copies = [d / "plan.md" for d in dirs if (d / "plan.md").is_file()]
    text = next((t for t in (read(p) for p in reversed(copies)) if BLOCK.search(t or "")), None)
    m = BLOCK.search(text or "")
    if not m:
        # no plan block: a draft is backlog, but only when intent.md has factory ids; other tools' changes/ folders are not ours
        if not any(re.search(r"^\s*-\s*(?:outcome|constraint)-\d+\s*:", read(d / "intent.md") or "", re.M) for d in dirs):
            return None
        _intent_needs(card, delta_qs, run_cmd, repo)
        return card
    try:
        plan = json.loads(m.group(1))
        mss = [x for x in plan["milestones"] if isinstance(x, dict) and re.fullmatch(MS, str(x.get("id")))]
        if not isinstance(plan, dict) or not mss:
            raise ValueError("no milestones")
    except (ValueError, KeyError, TypeError) as e:
        warns.append(f"{where}: plan block unreadable ({e})")
        _intent_needs(card, delta_qs, run_cmd, repo)
        return card
    log = "\n".join(_after_block(read(p)) for p in copies)
    ids = [x["id"] for x in mss]
    events, gaps, gap_files = log_events(log, set(ids))
    recs = log_records(log, set(ids))
    ms_titles, task_titles = prose_titles(text[:m.start()])
    logstate = {}
    for mid, st, note, at in events:
        logstate[mid] = (st, note, at)
    am = re.search(r"\bapproved:\s*`?([0-9a-f]{7,40})", log, re.I)
    card["approved"] = bool(am)
    if am:
        card["approvedSha"] = am.group(1)[:7]
        for e in log_entries(log):
            if re.search(r"\bapproved:\s*`?[0-9a-f]{7,40}", "\n".join(e), re.I):
                hm = TS_RE.search(re.sub(r"[*_`]", "", e[0]))
                card["approvedAt"] = to_iso(hm.group(1), hm.group(2)) if hm else None
                break
    change = str(plan.get("change") or slug)
    card["integration"] = plan["integration"] if isinstance(plan.get("integration"), str) and plan["integration"] else None
    card["requirementCount"] = len([r for r in plan.get("requirements", []) if isinstance(r, str)]) if isinstance(plan.get("requirements"), list) else 0
    # state files and task worktrees
    sfiles, building, wt_of = {}, {}, {}
    for path, branch in wts:
        sm = re.fullmatch(re.escape("milestone/" + change) + "-(" + MS + ")", branch)
        if sm:
            wt_of[sm.group(1)] = Path(path)
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
            name = tm.group(2)
            if name.startswith("gap"):
                name = f"{tm.group(1)}-gap{name[3:] or 1}"
            building.setdefault(tm.group(1), []).append(name)
    rows = []
    open_ms = next((ms["id"] for ms in mss if (logstate.get(ms["id"]) or ("",))[0] not in ("shipped", "merged", "hold")), None)  # the current milestone
    subjects = {}
    last_verify = {}
    for v in recs["verifies"]:
        last_verify[v["milestone"]] = v
    any_active = False
    for ms in mss:
        mid = ms["id"]
        sf = sfiles.get(mid)
        ptasks = [t for t in ms.get("tasks", []) if isinstance(t, dict) and "id" in t]
        tasks = [t["id"] for t in ptasks]
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
        any_active = any_active or active
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
        for t, ts in zip(ptasks, tstate):
            ts["title"] = task_titles.get(t["id"])
            ts["model"] = t["model"] if t.get("model") in ("haiku", "sonnet", "opus") else None
            ts["effort"] = t["effort"] if t.get("effort") in ("low", "medium", "high") else None
        gr = gaps.get(mid, 0)
        v = last_verify.get(mid)
        gtasks = []
        for n in range(1, gr + 1):
            gid = f"{mid}-gap{n}"
            files = gap_files.get((mid, n)) or ""
            gst = "building" if gid in live else "failed" if (n == gr and v and v["result"] == "FAIL") else "done"
            gtasks.append({"id": gid, "state": gst, "title": f"Fix round {n}" + (f": {', '.join(files.split(',')[:2])}" + (f" (+{len(files.split(',')) - 2} more)" if len(files.split(',')) > 2 else "") if files else ""), "model": None, "effort": None})
        layer = ms.get("layer") if ms.get("layer") in ("components", "layouts", "backend", "screens", "rest") else None
        rows.append({"id": mid, "title": ms_titles.get(mid) or (_short(ms["title"], 120) if isinstance(ms.get("title"), str) else None), "layer": layer,
                     "risky": ms.get("risky") is True, "requirements": [r for r in ms.get("covers", []) if isinstance(r, str) and re.fullmatch(r"req-\d+", r)],
                     "branch": f"milestone/{change}-{mid}", "state": state, "tasks": tstate, "gapRound": gr, "gapRounds": as_int(ms.get("gapRounds"), 3),
                     "verifier": {"result": v["result"] if v else None, "sha": v["sha"] if v else None, "reqs": v["reqs"] if v else []},
                     "_live": live, "_since": (sf[2] if sf else None), "_note": (ls[1] if ls else ""), "_at": (ls[2] if ls else None), "_gtasks": gtasks})
    card["milestones"] = [{**{k: v for k, v in r.items() if not k.startswith("_")}, "tasks": r["tasks"] + r["_gtasks"]} for r in rows]
    states = [r["state"] for r in rows]
    cur = next((r for r in rows if r["state"] == "building"), None) or next((r for r in rows if r["state"] in ("blocked", "hold")), None)
    needs = []
    if "building" in states:
        card["column"] = "building"
    elif not card["approved"]:
        card["column"] = "needs-you"
        try:
            since = iso(max((p.stat().st_mtime for p in copies)))
        except (OSError, ValueError):
            since = None
        needs.append(_need("approve-plan", "The plan is written and waits for your approval.", run_cmd, f"{in_repo} It shows the plan and asks for approval.", since))
    else:
        card["column"] = "ready"
    prs = []
    if card["approved"] or card["column"] == "building":
        prs = [p for p in prs_fn() if isinstance(p, dict) and _mine(str(p.get("headRefName", "")), change, plan)]
        card["prs"] = [{"number": p.get("number"), "url": p.get("url"), "title": p.get("title"), "state": "draft" if p.get("isDraft") else "open"} for p in prs]
    if card["column"] != "building" and card["approved"]:
        blocked = [r for r in rows if r["state"] == "blocked"]
        held = [r for r in rows if r["state"] == "hold"]
        if blocked or held:
            card["column"] = "needs-you"
        for r in blocked:
            needs.append(_need("blocked", r["_note"] or "The run stopped on a decision only you can make.", run_cmd, f"{in_repo} Fix the cause first, it resumes the run.", r["_at"], r["id"]))
        for r in held:
            sha = (re.findall(r"\b[0-9a-f]{7,40}\b", r["_note"]) or [None])[0] or (run(["git", "-C", str(repo), "rev-parse", "--short", f"refs/heads/{r['branch']}"], None) or "").strip() or None
            cmd = f"gh browse --branch {shlex.quote(r['branch'])}" if _has_github(repo) else f"git log -1 {shlex.quote(sha or r['branch'])}"
            needs.append(_need("hold-review", r["_note"] or "A held milestone is pushed and waits for you.", cmd,
                               f"Paste it in a terminal in {repo.name}. " + ("It opens the branch on GitHub." if cmd.startswith("gh ") else "It prints the held commit."), r["_at"], r["id"]))
        if not blocked and not held and (release := _release(prs, plan, mss)) is not None:
            gal = any(g.is_file() for w, _ in wts for g in (Path(w) / "changes" / slug / "evidence").glob("*/gallery.md"))
            url = str(release.get("url") or "")
            ref = url if url.startswith("https://") else str(release.get("number"))
            card["column"] = "needs-you"
            needs.append(_need("gallery" if gal else "release-pr", (f"Review the gallery, then merge release PR #{release['number']}." if gal else f"Release PR #{release['number']} waits for your merge."),
                               f"gh pr view {shlex.quote(ref)} --web", f"Paste it in a terminal in {repo.name}. It opens the pull request in your browser."))
        elif not blocked and not held and all(s in DONE for s in states):
            card["column"] = "done"
    if card["column"] == "done":
        card["doneAt"] = next((at for _, st, _, at in reversed(events) if st in DONE), None)
    shipped = {r["id"] for r in rows if r["state"] in DONE}
    _questions(card, delta_qs, recs["questions"], recs["answered"], {r["id"]: r["state"] for r in rows}, shipped, run_cmd, f"Answer it in a new Claude session in {repo.name}.", needs)
    _set_needs(card, needs)
    # failures, newest (last in the log) first
    fails = [{"milestone": v["milestone"], "text": v["text"], "sha": v["sha"], "at": v["at"], "kind": "verify", "reqs": v["reqs"], "n": v["n"]} for v in recs["verifies"] if v["result"] == "FAIL"]
    fails += [{"milestone": e["milestone"], "text": e["text"], "sha": None, "at": e["at"], "kind": "error", "reqs": [], "n": e["n"]} for e in recs["errors"]]
    card["failures"] = sorted(fails, key=lambda f: -f.pop("n"))
    # run, stage, current
    acts = [iso(sf[1]) for sf in sfiles.values()] + [x["at"] for x in recs["verifies"] + recs["errors"] + recs["questions"] if x["at"]] + [at for _, _, _, at in events if at]
    endmap = {"shipped": "SHIPPED", "merged": "HOLD", "hold": "HOLD", "blocked": "BLOCKED", "incomplete": "INCOMPLETE"}
    wt = wt_of.get((cur or {}).get("id") or open_ms or "")
    try:
        rel = wt.relative_to(repo).as_posix() if wt else None
    except ValueError:
        rel = None
    plain = [re.sub(r"^[-*]\s+", "", re.sub(r"[*_`]", "", ln).strip()) for ln in log.splitlines()]
    seen_ll, lines = set(), []
    for ln in plain:
        if re.match(r"(?:GAP-FIX|VERIFY|QUESTION|ANSWERED|ERROR|HOLD-MERGED|approved:)", ln) and ln not in seen_ll:
            seen_ll.add(ln)
            lines.append(ln[:300])
    card["run"] = {"state": "running" if any_active else "stopped" if card["approved"] and card["column"] != "done" and any(s != "pending" for s in states) else "idle",
                   "lastActivity": max(acts) if acts else None, "lastEndState": endmap.get(events[-1][1]) if events else None, "worktree": rel, "logLines": lines[-12:]}
    card["stage"] = "done" if card["column"] == "done" else "plan" if not card["approved"] else "building" if (card["column"] == "building" or any(s != "pending" for s in states)) else "ready"
    if card["column"] in ("building", "needs-you") and cur is not None:
        card["current"] = _current(cur, rows, mss)
    return card


def _set_needs(card, needs):
    if card["column"] in ("ready", "backlog") and any(n["kind"] == "question" for n in needs):
        card["column"] = "needs-you"
    card["needsAll"] = needs
    card["needs"] = needs[0] if needs else None


def _intent_needs(card, delta_qs, run_cmd, repo):
    needs = []
    _questions(card, delta_qs, [], {}, {}, set(), run_cmd, f"Answer it in a new Claude session in {repo.name}.", needs)
    _set_needs(card, needs)


def _questions(card, delta_qs, log_qs, answered, mstate, shipped, run_cmd, where, needs=None):
    """card["questions"] (every question, open or answered) and, in `needs`, one question need per milestone with an open one on a milestone that is not shipped."""
    qs = [{"id": q["id"], "milestone": q["milestone"], "text": q["text"], "source": "log", "open": (q["milestone"], q["id"]) not in answered, "at": q["at"]} for q in log_qs] + delta_qs
    card["questions"] = qs
    if needs is None or card["column"] == "done":
        return
    groups = {}
    for q in qs:
        if q["open"] and q["milestone"] not in shipped:
            groups.setdefault(q["milestone"], []).append(q)
    for mid, g in groups.items():
        more = f" (+{len(g) - 1} more)" if len(g) > 1 else ""
        needs.append(_need("question", f"Question: {g[0]['text']}{more}", run_cmd, where, g[0]["at"], mid))


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
