#!/usr/bin/env python3
"""Usage: check-plan.py <plan.md> [--all] [--approved <sha>]
With --all every milestone must have tasks and the plan must have no `hold` (what goal-brief.py --all needs).
With --approved plan.md through its json block, delta.md and intent.md must equal revision <sha> (only the text after the block may differ).
Validates the first fenced block with info string `json factory`, delta.md and intent.md next to it
(intent ids are list items `- outcome-1: ...` / `- constraint-1: ...`; every delta requirement line `- req-<n>: ...` cites one as `[outcome-1]`).
Old ids (`I1`, `C1`, `<spec>/R<n>`) fail with a one-line rewrite hint. In the plan (through its json block) and in intent.md,
an id written in prose must sit in parentheses after at least two words: `guests see their items (req-12)` (the 8-word cap in SKILL.md is guidance, not checked).
A task's prose bullet that names an effort or model must match the task's json. A milestone's optional `mayTouch` is a non-empty list of narrow relative path globs.
Prints `PLAN OK <n> milestones <m> tasks` (exit 0) or one `PLAN FAIL <reason>` per problem (exit 1).
"""
import json
import os
import re
import subprocess
import sys

LAYERS = ["components", "layouts", "backend", "screens", "rest"]
SLUG = r"\d{4}-\d{2}-\d{2}-[a-z0-9]+(-[a-z0-9]+)*"
REQ_ID = r"req-\d+"
OLD_REQ = r"[a-z0-9]+(-[a-z0-9]+)*/R\d+"
OLD_CITE = r"\[[IC]\d+\]"
MIGRATE = "rewrite it as req-<n>, outcome-<n> or constraint-<n> by hand"
ID_WORD = r"\b(?:req|adr|outcome|constraint|scenario|journey|board|deferred|finding)-\d+\b"


def read_next(plan_path, name):
    """Text of <name> next to the plan, or None when it does not exist."""
    path = os.path.join(os.path.dirname(os.path.abspath(plan_path)), name)
    return open(path, encoding="utf-8").read() if os.path.exists(path) else None


def delta_entries(delta):
    """[(requirement id, line)] listed under an ADDED, MODIFIED or REMOVED heading (any level) or its deeper sub-headings;
    a heading at the same or a higher level closes the section."""
    out, listed, level = [], False, 0
    for line in delta.splitlines():
        h = re.match(r"(#+)\s*(\w*)", line)
        if h and not (listed and len(h.group(1)) > level):
            listed, level = h.group(2) in ("ADDED", "MODIFIED", "REMOVED"), len(h.group(1))
        m = re.match(r"\s*-\s*(" + REQ_ID + "|" + OLD_REQ + r")\s*:", line)
        if m and listed:
            out.append((m.group(1), line))
    return out


def intent_ids(intent):
    """Ids intent.md defines, as list items `- outcome-1: ...` or `- constraint-1: ...`."""
    return set(re.findall(r"^\s*-\s*((?:outcome|constraint)-\d+)\s*:", intent, re.M))


def prose_errs(text, name):
    """Every id in prose sits in parentheses after at least two words. Exempt: fenced code, headings, citation brackets, list items that define the id."""
    errs, fenced = [], False
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced or line.startswith("#") or re.match(r"\s*-\s*" + ID_WORD + r"\s*:", line):
            continue
        line = re.sub(r"\[(?:outcome|constraint)-\d+\]", "", line)
        for m in re.finditer(ID_WORD, line):
            depth, start = 0, None
            for i in range(m.start() - 1, -1, -1):  # the nearest unclosed "(" before the id
                if line[i] == ")":
                    depth += 1
                elif line[i] == "(":
                    if depth == 0:
                        start = i
                        break
                    depth -= 1
            if start is None or len(re.findall(r"[^\s()]+", line[:start])) < 2:
                errs.append(f"{name}:{n} bare id {m.group(0)}: say what it does first, then the id in parentheses, like `guests see their items ({m.group(0)})`")
    return errs


def task_prose_errs(text, plan):
    """A task's prose bullet (starts with its id, like `**T3 ... (high effort).**`) must not name another effort or model than the task's json (no json effort counts as medium, no json model as sonnet)."""
    errs = []
    for m in plan.get("milestones", []):
        for t in m.get("tasks", []):
            tid = str(t.get("id"))
            for line in text.splitlines():
                if not re.match(r"\s*[-*]\s*\**" + re.escape(tid) + r"\b", line):
                    continue
                for word, found, want in (("effort", re.findall(r"\b(low|medium|high) effort\b", line), t.get("effort", "medium")),
                                          ("model", re.findall(r"\b(haiku|sonnet|opus)\b", line), t.get("model", "sonnet"))):
                    if found and found[0] != want:
                        errs.append(f"{m.get('id')}/{tid} prose says {word} {found[0]} but the json block says {want}: make them agree")
    return errs


def intent_errs(plan_path, delta_lines_by_id):
    """intent.md must exist; every delta requirement cites an intent id it defines; no open question anywhere."""
    intent, delta = read_next(plan_path, "intent.md"), read_next(plan_path, "delta.md")
    errs = []
    if intent is None:
        errs.append("missing intent.md next to the plan")
    known = intent_ids(intent or "")
    if intent is not None and not known:
        old = re.search(r"^\s*-\s*[IC]\d+\s*:", intent, re.M)
        errs.append("intent.md defines no ids: list them as `- outcome-1: ...` and `- constraint-1: ...`"
                    + (f" (old `- I1:` form found: {MIGRATE})" if old else ""))
    for rid, line in sorted(delta_lines_by_id.items()):
        cited = re.findall(r"\[((?:outcome|constraint)-\d+)\]", line)
        if not re.fullmatch(REQ_ID, rid):
            errs.append(f"delta requirement {rid} uses the old <spec>/R<n> id: {MIGRATE}")
        if re.search(OLD_CITE, line):
            errs.append(f"requirement {rid} in delta.md cites an old [I<n>] or [C<n>] id: {MIGRATE}")
        elif not cited:
            errs.append(f"requirement {rid} in delta.md cites no [outcome-<n>] or [constraint-<n>] from intent.md")
        elif intent is not None:
            errs += [f"requirement {rid} in delta.md cites {c}, which intent.md does not define" for c in cited if c not in known]
    if intent is not None:
        errs += prose_errs(intent, "intent.md")
    for name, text in (("intent.md", intent), ("delta.md", delta)):
        if text and "[NEEDS CLARIFICATION" in text:
            errs.append(f"{name} still has [NEEDS CLARIFICATION: ...]: resolve it before approval")
    return errs


BLOCK = re.compile(r"^```json factory[ \t]*\n(.*?)^```", re.S | re.M)


def block_match(text):
    m = BLOCK.search(text)
    if not m:
        raise ValueError("no json factory block")
    return m


def block_text(text):
    return block_match(text).group(1)


def load(path):
    return json.loads(block_text(open(path, encoding="utf-8").read()))


def at_sha(path, sha):
    """File content at <sha> (None when the file does not exist there), read through git next to the file."""
    d, name = os.path.split(os.path.abspath(path))
    pre = subprocess.run(["git", "-C", d, "rev-parse", "--show-prefix"], capture_output=True, text=True)
    if pre.returncode:
        raise ValueError(f"{d} is not in a git repo, cannot read {name} at {sha}")
    ref = f"{sha}:{pre.stdout.strip()}{name}"
    if subprocess.run(["git", "-C", d, "cat-file", "-e", ref], capture_output=True).returncode:
        return None
    return subprocess.run(["git", "-C", d, "show", ref], capture_output=True, text=True, check=True).stdout


def approved_errs(plan_path, sha):
    """plan.md from its start through the json block, delta.md and intent.md must equal the approved revision; only the text after the block may differ."""
    d = os.path.dirname(os.path.abspath(plan_path))
    ok = subprocess.run(["git", "-C", d, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}"], capture_output=True)
    if ok.returncode:
        return [f"approved {sha} is not a commit in this repo"]
    errs = []
    for name in (os.path.basename(plan_path), "delta.md", "intent.md"):
        path = os.path.join(d, name)
        then = at_sha(path, sha)
        now = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if name == os.path.basename(plan_path):
            try:
                then = then[:block_match(then).end()] if then is not None else None
                now = now[:block_match(now).end()] if now is not None else None
            except ValueError:
                pass
        if then != now:
            errs.append(f"{name} changed since approved {sha}: owner approves a new revision")
    return errs


def ready_errs(plan):
    """What `--all` needs on top: every milestone detailed, and no hold (a held milestone is not merged)."""
    ms = plan.get("milestones", [])
    errs = [f"{m.get('id')} has no tasks: detail it in plan.md and get the plan revision approved first" for m in ms if not m.get("tasks")]
    if plan.get("hold") and ms:
        errs.append(f"--all cannot run with a hold: {ms[0].get('id')} stops at the hold and is not merged, so the next milestone has nothing to build on")
    return errs


def validate(plan_path, approved=None, every=False):
    """One entry point: load the block, check it, require delta.md, compare with the approved revision.
    every=True (`--all`) also requires every milestone to have tasks and the plan to have no hold."""
    try:
        text = open(plan_path, encoding="utf-8").read()
        plan = json.loads(block_text(text))
    except (OSError, ValueError) as e:  # json errors are ValueError
        return [str(e)], 0, 0, []
    errs, notes = id_errs(plan), []
    if errs:
        return errs, 0, 0, notes
    errs, nm, nt = check(plan)
    errs += guards_errs(plan, plan_path, notes)
    head = text[:block_match(text).end()]  # the log after the block stays free text
    errs += prose_errs(head, os.path.basename(plan_path)) + task_prose_errs(head, plan)
    if every:
        errs += ready_errs(plan)
    delta = read_next(plan_path, "delta.md")
    entries = delta_entries(delta or "")
    lines = dict(entries)
    if delta is None:
        errs.append("missing delta.md next to the plan")
    else:  # the plan may only build what the approved delta lists
        known, reqs = set(lines), set(map(str, plan.get("requirements", [])))
        ids = [r for r, _ in entries]
        errs += [f"delta requirement {r} is listed more than once in delta.md: requirement numbers are unique in the repo" for r in sorted({r for r in ids if ids.count(r) > 1})]
        errs += [f"requirement {r} is not ADDED, MODIFIED or REMOVED in delta.md" for r in sorted(reqs - known)]
        errs += [f"delta requirement {r} is in no plan requirement" for r in sorted(known - reqs)]
    errs += intent_errs(plan_path, lines)
    if approved:
        try:
            errs += approved_errs(plan_path, approved)
        except ValueError as e:
            errs.append(str(e))
    return errs, nm, nt, notes


def is_strs(v):
    return isinstance(v, list) and all(isinstance(x, str) for x in v)


def filled(v):
    return isinstance(v, str) and bool(v.strip())


TEST_DIR = re.compile(r"(tests?|__tests__|e2e)/")
TEST_FILE = re.compile(r"[^/]*\.(test|spec)\.[^/]*")
MS_ID, TASK_ID = r"M\d+", r"T\d+"


def is_test_path(f):
    """A test file: its basename is *.test.* or *.spec.*, or it sits under a top-level test/, tests/, __tests__/ or e2e/ folder.
    A source file in src/lib/tests-helpers/ is not a test."""
    return bool(TEST_FILE.fullmatch(f.rsplit("/", 1)[-1]) or TEST_DIR.match(f))


def id_errs(plan):
    """Milestone and task ids go into every message, so they must look like M<n> and T<n> before anything else runs.
    A bad id is shown escaped and cut, never raw."""
    errs = []
    for m in plan.get("milestones", []):
        if not isinstance(m, dict):
            continue
        if not re.fullmatch(MS_ID, str(m.get("id", ""))):
            errs.append(f"milestone id {ascii(m.get('id'))[:40]} must look like M<n>")
        for t in m.get("tasks", []) if isinstance(m.get("tasks", []), list) else []:
            if isinstance(t, dict) and not re.fullmatch(TASK_ID, str(t.get("id", ""))):
                errs.append(f"task id {ascii(t.get('id'))[:40]} must look like T<n>")
    return errs


def covers(declared, f):
    """Exact path, or a declared path ending in / that is a prefix of it."""
    return any(f == o or (o.endswith("/") and f.startswith(o)) for o in declared)


def guards_errs(plan, plan_path, notes):
    """A milestone's `guards` are regexes for how the guarded data is read, e.g. `(from|join)\\(comments\\b`.
    One `git grep -l -P` per guard (PCRE, so `\\b` works on macOS and Linux) (tracked and untracked, gitignore respected, minus the change folder and
    `.factory/`). A source file it finds must be a task `files` or `allowTestEdits` path of this or an earlier
    milestone, a surface `exposure`, or a deferred `item`. A test file nobody owns is appended to `notes`, which never fail the check."""
    ms = [m for m in plan.get("milestones", []) if m.get("guards") is not None]
    if not ms:
        return []
    errs = []
    for m in ms:
        gs = m["guards"]
        if not (is_strs(gs) and gs and all(g.strip() for g in gs)):
            errs.append(f"{m.get('id', '?')} guards must be a non-empty list of patterns")
            continue
        for g in gs:
            try:
                re.compile(g)
            except re.error as e:
                errs.append(f"{m.get('id', '?')} guard {g} is not a valid pattern: {e}")
    if errs:
        return errs
    d = os.path.dirname(os.path.abspath(plan_path))
    top = subprocess.run(["git", "-C", d, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if top.returncode:
        return ["guards need the plan inside a git repo: the check runs git grep"]
    root = top.stdout.strip()
    folder = os.path.relpath(os.path.realpath(d), os.path.realpath(root))
    if folder.startswith(".."):
        return [f"guards: the plan folder {folder} is outside the repo"]
    skip = [":(exclude).factory", f":(exclude){folder}"]
    owned, declared = set(), set()
    for m in plan["milestones"]:
        for t in m.get("tasks", []):
            owned |= set(t.get("files", [])) | set(t.get("allowTestEdits", []))
        for s in m.get("surface") or []:
            if isinstance(s, dict) and filled(s.get("exposure")):
                declared.add(s["exposure"].strip())
        for x in m.get("deferred") or []:
            if isinstance(x, dict) and filled(x.get("item")) and filled(x.get("probe")):
                declared.add(x["item"].strip())
        for g in m.get("guards") or []:
            p = subprocess.run(["git", "-C", root, "grep", "-l", "-P", "--untracked", "-e", g, "--", ".", *skip], capture_output=True, text=True)
            if p.returncode not in (0, 1):
                errs.append(f"guard {g}: git grep failed: {p.stderr.strip()}")
                continue
            for f in p.stdout.split("\n"):
                if not f or covers(owned, f):
                    continue
                if is_test_path(f):
                    notes.append(f"{m['id']} guard {g}: {f} reads it; if it asserts the old behaviour, add it to allowTestEdits")
                elif not covers(declared, f):
                    errs.append(f"{m['id']} guard {g}: {f} reads it but no task of {m['id']} or earlier owns it, no surface exposure names it and no deferred item with a probe lists it")
    return errs


def may_touch_errs(m, mid):
    """`mayTouch`: path globs the owner approves with the plan, for the one plan-gap fix round. Narrow, relative, no spaces or commas (the log line is comma-separated)."""
    if "mayTouch" not in m:
        return []
    g = m["mayTouch"]
    if not (is_strs(g) and g):
        return [f"{mid} mayTouch must be a non-empty list of path globs"]
    def bad(x):  # `*` stays inside one path segment; the first segment is static; a trailing `/` is a plain directory prefix; no `**`
        segs = x.split("/")
        return (not x or x.startswith("/") or ".." in segs or "**" in x or re.search(r"[\s,]", x) is not None or re.search(r"[*?\[]", segs[0]) is not None
                or (x.endswith("/") and re.search(r"[*?\[]", x) is not None))
    return [f"{mid} mayTouch {x!r} must be a relative path under a static directory (`src/api/*`, `tests/api/`): `*` stays in one path segment, no `**`, no spaces or commas" for x in g if bad(x)]


def surface_errs(m, mid):
    """A risky milestone with tasks lists every exposure with a scenario, or a deferral with its reason and probe."""
    surface = m.get("surface")
    if not surface:
        return [f"{mid} surface is required on a risky milestone: list each exposure with a scenario or a deferral"] if m.get("risky") and m.get("tasks") else []
    if not isinstance(surface, list):
        return [f"{mid} surface must be a list"]
    errs = []
    for i, s in enumerate(surface):
        s = s if isinstance(s, dict) else {}
        at = f"{mid} surface[{i}]"
        if not filled(s.get("exposure")):
            errs.append(f"{at} needs a non-empty exposure")
        if not filled(s.get("requirement")):
            errs.append(f"{at} needs a non-empty requirement")
        elif s["requirement"] not in m.get("covers", []):
            errs.append(f"{at} requirement {s['requirement']} is not in {mid} covers")
        d = s.get("deferred")
        if d is None:
            if not filled(s.get("scenario")):
                errs.append(f"{at} needs a non-empty scenario, or deferred {{reason, probe}}")
        elif not (isinstance(d, dict) and filled(d.get("reason")) and filled(d.get("probe"))):
            errs.append(f"{at} deferred needs a non-empty reason and probe")
    return errs


def deferred_errs(m, mid):
    """What a milestone leaves for later: each with the reason and the probe that showed it."""
    d = m.get("deferred")
    if d is None:
        return []
    if not isinstance(d, list):
        return [f"{mid} deferred must be a list"]
    return [f"{mid} deferred[{i}] needs a non-empty item, reason and probe"
            for i, x in enumerate(d) if not (isinstance(x, dict) and all(filled(x.get(k)) for k in ("item", "reason", "probe")))]


def keys_errs(plan):
    errs = []
    if "allowTestEdits" in plan:
        errs.append("move allowTestEdits into the task that edits them")
    for k in ("hold", "setup"):
        if k in plan and (not isinstance(plan[k], str) or not plan[k].strip()):
            errs.append(f"{k} must be a non-empty string")
    if "preflight" in plan and not (is_strs(plan["preflight"]) and all(x.strip() for x in plan["preflight"])):
        errs.append("preflight must be a list of non-empty strings")
    if "deployOnMerge" in plan and not isinstance(plan["deployOnMerge"], bool):
        errs.append("deployOnMerge must be true or false")
    if "kind" in plan:
        ms = plan.get("milestones", [])
        if plan["kind"] not in ("bug", "feature"):
            errs.append('kind must be "bug" or "feature"')
        elif len(ms) != 1 or len(ms[0].get("tasks", [])) != 1 or len(plan.get("requirements", [])) > 3:
            errs.append(f"kind {plan['kind']} needs exactly one milestone with one task and at most 3 requirements")
    return errs


def check(plan):
    errs = []
    if not re.fullmatch(SLUG, str(plan.get("change", ""))):
        errs.append("change must be the dated slug, like 2026-11-24-search")
    if not str(plan.get("base", "")).strip():
        errs.append("missing base")
    if plan.get("merge", "auto") not in ("auto", "owner"):
        errs.append('merge must be "auto" or "owner"')
    if "integration" in plan:
        integ = plan["integration"]
        if not isinstance(integ, str) or not re.fullmatch(r"[A-Za-z0-9._/-]+", integ) or integ == plan.get("base"):
            errs.append("integration must be a branch name different from base")
    if not isinstance(plan.get("goalTurns"), int) or plan["goalTurns"] <= 0:
        errs.append("goalTurns must be a positive whole number")
    errs += keys_errs(plan)
    reqs = set(plan.get("requirements", []))
    if not reqs:
        errs.append("plan has no requirements: list at least one, each ADDED, MODIFIED or REMOVED in delta.md")
    errs += [f"requirement id {r} must look like req-<n>" + (f" (old form: {MIGRATE})" if re.fullmatch(OLD_REQ, r) else "")
             for r in sorted(map(str, reqs)) if not re.fullmatch(REQ_ID, r)]
    ms = plan.get("milestones", [])
    covered, seen_tasks, earlier, last, seen_ms = set(), set(), set(), -1, set()
    for m in ms:
        mid = m.get("id", "?")
        if mid in seen_ms:
            errs.append(f"milestone id {mid} is not unique")
        seen_ms.add(mid)
        if "needs" in m:
            errs.append(f"{mid} needs is not allowed on a milestone: array order is the only milestone dependency")
        layer = m.get("layer")
        if layer not in LAYERS:
            errs.append(f"{mid} unknown layer {layer!r}")
        elif LAYERS.index(layer) < last:
            errs.append(f"{mid} layer {layer} goes backwards")
        else:
            last = LAYERS.index(layer)
        v = m.get("verifier", {})
        if not isinstance(v, dict) or v.get("model", "opus") not in ("sonnet", "opus") or v.get("effort", "high") not in ("medium", "high"):
            errs.append(f"{mid} verifier must be {{model: sonnet or opus, effort: medium or high}}")
        errs += surface_errs(m, mid) + deferred_errs(m, mid) + may_touch_errs(m, mid)
        mc = set(m.get("covers", []))
        covered |= mc
        errs += [f"{mid} covers unknown requirement {r}" for r in sorted(mc - reqs)]
        owner, union, ids = {}, set(), set()
        for t in m.get("tasks", []):
            tid = t.get("id", "?")
            if tid in seen_tasks | ids:
                errs.append(f"task id {tid} is not unique")
            ids.add(tid)
            union |= set(t.get("covers", []))
            if "kind" in plan and not t.get("covers"):  # a bug or small feature task must prove a requirement
                errs.append(f"{mid}/{tid} covers no requirement")
            if not str(t.get("check", "")).strip():
                errs.append(f"{mid}/{tid} has an empty check")
            if t.get("effort", "medium") not in ("low", "medium", "high"):
                errs.append(f"{mid}/{tid} effort must be low, medium or high")
            if t.get("model", "sonnet") not in ("haiku", "sonnet", "opus"):
                errs.append(f"{mid}/{tid} model must be haiku, sonnet or opus")
            if not isinstance(t.get("needs", []), list):
                errs.append(f"{mid}/{tid} needs must be a list")
            else:
                errs += [f"{mid}/{tid} needs {n}, not a task of an earlier milestone" for n in t.get("needs", []) if n not in earlier]
            if not is_strs(t.get("allowTestEdits", [])):
                errs.append(f"{mid}/{tid} allowTestEdits must be a list of strings")
            for f in t.get("files", []):
                if f in owner and owner[f] != tid:
                    errs.append(f"{mid} tasks {owner[f]} and {tid} both own {f}")
                owner[f] = tid
        if m.get("tasks") and union != mc:
            errs.append(f"{mid} task coverage {sorted(union)} differs from milestone covers {sorted(mc)}")
        seen_tasks |= ids
        earlier |= ids  # only tasks of finished milestones are visible to the next one
    errs += [f"requirement {r} is covered by no milestone" for r in sorted(reqs - covered)]
    return errs, len(ms), len(seen_tasks)


def main():
    args = sys.argv[1:]
    every = "--all" in args
    args = [a for a in args if a != "--all"]
    approved = None
    if "--approved" in args and args.index("--approved") == len(args) - 2:
        args, approved = args[:-2], args[-1]
    if len(args) != 1:
        print("usage: check-plan.py <plan.md> [--all] [--approved <sha>]", file=sys.stderr)
        return 2
    errs, nm, nt, notes = validate(args[0], approved, every)
    for n in notes:
        print(f"PLAN NOTE {n}")
    for e in errs:
        print(f"PLAN FAIL {e}")
    if not errs:
        print(f"PLAN OK {nm} milestones {nt} tasks")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
