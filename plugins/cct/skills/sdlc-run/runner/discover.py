"""Discovery, capability probes and the one approval screen (design 3.1, 3.3).

Reads the repo's own instructions, manifests and CI at the starting commit; writes only into the run folder. Nothing is
added to the product repo (the one git ref, sdlc/<run-id>, is a branch name, not a file).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import contract
import store
from contract import git
from store import SdlcError

ROLE_WORDS = {"e2e": ("e2e", "test:e2e", "playwright"), "test": ("test", "tests", "check", "verify"), "lint": ("lint", "ruff", "eslint"), "typecheck": ("typecheck", "types", "tsc", "mypy"),
              "build": ("build",)}
LOCKS = {"pnpm-lock.yaml": "pnpm", "yarn.lock": "yarn", "package-lock.json": "npm", "uv.lock": "uv", "poetry.lock": "poetry",
         "Gemfile.lock": "bundler", "go.sum": "go", "Cargo.lock": "cargo"}
FENCE = re.compile(r"```(?:bash|sh|shell)?\n(.*?)```", re.S)


def _run(repo: Path, *argv: str) -> str:
    r = subprocess.run(argv, cwd=repo, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def _node_runner(repo: Path) -> list[str]:
    for lock, pm in (("pnpm-lock.yaml", ["pnpm"]), ("yarn.lock", ["yarn"])):
        if (repo / lock).exists():
            return pm
    return ["npm", "run"]


def discover(repo: Path) -> dict:
    repo = Path(repo).resolve()
    d: dict = {"repo": repo.name, "path": str(repo), "commands": {}, "sources": {}, "package_manager": None, "ci": {"jobs": []}}
    head = git(repo, "rev-parse", "HEAD")
    d["head"] = head
    d["default_branch"] = (_run(repo, "git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD").removeprefix("origin/")
                           or git(repo, "branch", "--show-current") or "main")
    d["remote"] = _run(repo, "git", "remote", "get-url", "origin")
    for lock, pm in LOCKS.items():
        if (repo / lock).exists():
            d["package_manager"] = pm
            break

    def put(role: str, argv: list[str], source: str):
        if role not in d["commands"]:
            d["commands"][role], d["sources"][role] = argv, source

    # 2. manifests
    pj = repo / "package.json"
    if pj.exists():
        scripts = json.loads(pj.read_text()).get("scripts", {})
        run = _node_runner(repo)
        for role, words in ROLE_WORDS.items():
            for w in words:
                if w in scripts:
                    put(role, run + [w], "package.json")
                    break
    mk = repo / "Makefile"
    if mk.exists():
        targets = set(re.findall(r"^([A-Za-z0-9_.-]+):", mk.read_text(), re.M))
        for role, words in ROLE_WORDS.items():
            for w in words:
                if w in targets:
                    put(role, ["make", w], "Makefile")
                    break
    py = repo / "pyproject.toml"
    if py.exists():
        text = py.read_text()
        if "[tool.pytest" in text or (repo / "tests").is_dir():
            put("test", ["uv", "run", "pytest"] if (repo / "uv.lock").exists() else ["python3", "-m", "pytest"], "pyproject.toml")
        if "[tool.ruff" in text:
            put("lint", ["uv", "run", "ruff", "check", "."] if (repo / "uv.lock").exists() else ["ruff", "check", "."], "pyproject.toml")
        if "[tool.mypy" in text:
            put("typecheck", ["uv", "run", "mypy", "."] if (repo / "uv.lock").exists() else ["mypy", "."], "pyproject.toml")
    # 1. the repo's own instructions: fenced commands in CLAUDE.md / AGENTS.md / README.md
    for doc in ("CLAUDE.md", "AGENTS.md", "README.md"):
        p = repo / doc
        if p.exists():
            for block in FENCE.findall(p.read_text(errors="replace")):
                for line in block.splitlines():
                    line = line.split("#")[0].strip()
                    for role, words in ROLE_WORDS.items():
                        if line and re.search(r"\b(" + "|".join(map(re.escape, words)) + r")\b", line) and not line.startswith(("cd ", "git ")):
                            put(role, ["bash", "-c", line], f"{doc}")
    # 3. existing CI: workflow files and their jobs (a contract may name one as the source of a result)
    wf = repo / ".github" / "workflows"
    for f in sorted(wf.glob("*.y*ml")) if wf.is_dir() else []:
        text = f.read_text(errors="replace")
        name = (re.search(r"^name:\s*(.+)$", text, re.M) or [None, f.stem])[1].strip()
        in_jobs = False
        for line in text.splitlines():
            if line.startswith("jobs:"):
                in_jobs = True
            elif in_jobs and (m := re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)):
                d["ci"]["jobs"].append({"file": f.name, "workflow": name, "job": m[1]})
    return d


def full_gate(d: dict) -> list[str] | None:
    """The repo's full local gate: lint, types and tests in one command, from what discovery found."""
    parts = [" ".join(map(_q, d["commands"][r])) for r in ("lint", "typecheck", "test") if r in d["commands"]]
    return ["bash", "-c", " && ".join(parts)] if parts else None


def _q(s: str) -> str:
    return s if re.fullmatch(r"[\w./:=@+-]+", s) else "'" + s.replace("'", "'\\''") + "'"


def probe(d: dict, contract_doc: dict | None = None) -> dict:
    """Capabilities, not values: which tools exist, whether credentials work, whether a browser can start."""
    tools = {}
    wanted = {a[0] for a in d["commands"].values()} | {"git"}
    for argv in d["commands"].values():
        if argv[0] == "bash":
            wanted |= {w for w in re.findall(r"(?:^|&&\s*|;\s*)([\w.-]+)", argv[2])}
    for c in (contract_doc or {}).get("checks", []):
        wanted.add(c["runner"][0])
        wanted |= {p["tool"] for p in c.get("prereqs", []) if "tool" in p}
    for t in sorted(wanted - {"bash", "cd"}):
        tools[t] = shutil.which(t)
    gh = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True) if shutil.which("gh") else None
    from board import browser_available
    ok, why = browser_available()
    return {"tools": tools, "missing_tools": [t for t, p in tools.items() if not p],
            "credentials": {"github": bool(gh and gh.returncode == 0), "git_remote": bool(d["remote"])},
            "browser": {"available": ok, "why": "" if ok else why}, "ci_jobs": [j["job"] for j in d["ci"]["jobs"]]}


def blockers(probe_doc: dict, contract_doc: dict) -> list[str]:
    out = []
    for c in contract_doc.get("checks", []):
        if c["runner"][0] in probe_doc["missing_tools"]:
            out.append(f"{c['repo']}:{c['id']} needs {c['runner'][0]}, which is not installed")
        for p in c.get("prereqs", []):
            if "browser" in p and not probe_doc["browser"]["available"]:
                out.append(f"{c['repo']}:{c['id']} needs a browser ({probe_doc['browser']['why']})")
            if "tool" in p and p["tool"] in probe_doc["missing_tools"]:
                out.append(f"{c['repo']}:{c['id']} needs {p['tool']}, which is not installed")
    return sorted(set(out))


# ---- plan: one run, one branch per repo -----------------------------------------------------------

def fresh_base(p: Path, d: dict) -> str:
    """Branch from a fresh origin/<default>, never from a stale local branch; no remote means the local default."""
    br = d["default_branch"]
    if d["remote"]:
        r = subprocess.run(["git", "fetch", "-q", "origin", br], cwd=p, capture_output=True, text=True)
        if r.returncode:
            raise SdlcError(f"BLOCKED env cannot fetch origin/{br} for {p.name}: {r.stderr.strip()[:120]}")
        return git(p, "rev-parse", f"origin/{br}")
    return git(p, "rev-parse", br if _run(p, "git", "rev-parse", "--verify", "-q", br) else "HEAD")


def plan(repos: list[str], slug: str, title: str | None = None) -> str:
    paths = [Path(r).resolve() for r in repos]
    discs = [discover(p) for p in paths]
    rid = store.make_run_id(paths[0].name, slug)
    meta_repos = {}
    for p, d in zip(paths, discs, strict=True):
        branch = f"sdlc/{rid}"
        base = fresh_base(p, d)
        meta_repos[p.name] = {"path": str(p), "base_sha": base, "branch": branch, "default_branch": d["default_branch"], "remote": d["remote"]}
    d0 = store.init_run(rid, {"title": title or slug, "slug": slug, "repos": {}})
    for p in paths:
        r = meta_repos[p.name]
        git(p, "branch", r["branch"], r["base_sha"])  # a ref, not a file: the repo's tree and status stay as they were
    m = store.load_meta(rid)
    m["repos"] = meta_repos
    store.save_meta(rid, m)
    checks = []
    for d in discs:
        g = full_gate(d)
        if g:
            checks.append({"id": f"full:{d['repo']}", "repo": d["repo"], "milestone": None, "due": "each", "runner": g,
                           "expect": {"kind": "pass"}, "count": False, "source": "discovered: " + ", ".join(sorted(set(d["sources"].values())))})
    store.write_json(d0 / "discovery.json", discs)
    pr = [probe(d) for d in discs]
    store.write_json(d0 / "probe.json", pr)
    store.write_json(d0 / "contract.json", {"version": 1, "checks": checks, "limits": {"builders": 8, "deadline_hours": 24}})
    store.write_json(d0 / "tasks.json", {"milestones": []})
    store.atomic_write(d0 / "plan.md", f"# {title or slug}\n\n## Outcome\n\n(the planner fills this in)\n")
    return rid


def pin_bases(rid: str, c: dict, meta: dict) -> None:
    """Resolve each `repos.<repo>.base` to a full SHA (fetched from origin), write it into the contract (so it is in the bundle digest)
    and cut the run branch from it. Only before any work: a branch that already moved cannot change base."""
    for name, spec in (c.get("repos") or {}).items():
        if name not in meta["repos"]:
            raise SdlcError(f"contract repos.{name} is not a repo of this run")
        spec.pop("base_sha", None)
        r = meta["repos"][name]
        if not spec.get("base"):
            if r.get("base_ref"):
                raise SdlcError(f"{name}: the run branch was cut from {r['base_ref']}; start a new run to build on the default branch")
            continue
        sha = contract.resolve_base(r, spec["base"])
        tip = git(r["path"], "rev-parse", r["branch"])
        if tip not in (r["base_sha"], sha):
            raise SdlcError(f"{name}: the run branch already has commits; start a new run for a new base")
        if tip != sha:
            git(r["path"], "branch", "-f", r["branch"], sha)
        spec["base_sha"], r["base_sha"], r["base_ref"] = sha, sha, spec["base"]
    store.save_meta(rid, meta)


def draft(rid: str, plan_file: str | None, contract_file: str | None, tasks_file: str | None,
          inputs: list[str], deps: list[str]) -> list[str]:
    """Ingest the planner's files (written outside the run folder) before approval. Returns blockers still open."""
    import engine
    d = store.run_dir(rid)
    if (d / "approval.json").exists():
        raise SdlcError("the bundle is approved and frozen; start a new run for a changed plan")
    meta = store.load_meta(rid)
    for kind, specs in (("inputs", inputs), ("deps", deps)):
        for spec in specs:  # repo:relative/path=local/file
            key, _, src = spec.partition("=")
            repo, _, rel = key.partition(":")
            if repo not in meta["repos"] or not contract.safe_relpath(rel):
                raise SdlcError(f"--{'input' if kind == 'inputs' else 'dep'} {key}: needs a repo of this run and a relative path inside it")
            if not Path(src).is_file():
                raise SdlcError(f"--{'input' if kind == 'inputs' else 'dep'} {key}: {src} is not a file")
            dst = d / kind / repo / rel
            if not dst.resolve().is_relative_to((d / kind / repo).resolve()):
                raise SdlcError(f"{key} resolves outside its folder")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
    if plan_file:
        shutil.copyfile(plan_file, d / "plan.md")
    if tasks_file:
        store.write_json(d / "tasks.json", store.read_json(Path(tasks_file)))
    if contract_file:
        c = store.read_json(Path(contract_file))
        for chk in c.get("checks", []):  # a list of paths becomes path -> digest of the approved copy
            pins = chk.get("pins", {})
            if isinstance(pins, list):
                chk["pins"] = {}
                for rel in pins:
                    f = d / "inputs" / chk["repo"] / rel
                    if not f.is_file():
                        raise SdlcError(f"check {chk['id']} pins {rel}, but no --input {chk['repo']}:{rel}=<file> was given")
                    chk["pins"][rel] = store.sha256(f.read_bytes())
        have = {k["id"] for k in c.get("checks", [])}
        for disc in store.read_json(d / "discovery.json"):  # the discovered full gate stays unless the plan waives it by name
            g = full_gate(disc)
            if g and f"full:{disc['repo']}" not in have and disc["repo"] not in c.get("waive_full", []):
                c.setdefault("checks", []).append({"id": f"full:{disc['repo']}", "repo": disc["repo"], "milestone": None, "due": "each",
                                                   "runner": g, "expect": {"kind": "pass"}, "count": False, "source": "discovered"})
        contract.validate_contract(c)
        for chk in c["checks"]:
            if chk["repo"] not in meta["repos"]:
                raise SdlcError(f"check {chk['id']} names unknown repo {chk['repo']}")
        for repo in {p.parent.name for p in (d / "deps").glob("*/*")} if (d / "deps").exists() else []:
            c.setdefault("deps", {}).setdefault(repo, {})["files"] = {
                f.relative_to(d / "deps" / repo).as_posix(): store.sha256(f.read_bytes())
                for f in (d / "deps" / repo).rglob("*") if f.is_file()}
        pin_bases(rid, c, meta)
        store.write_json(d / "contract.json", c)
    engine.validate_plan(rid)  # a cycle is a planning error
    cdoc = store.read_json(d / "contract.json")
    fresh = [probe(x, cdoc) for x in store.read_json(d / "discovery.json")]
    store.write_json(d / "probe.json", fresh)
    merged = {"missing_tools": sorted({t for p in fresh for t in p["missing_tools"] if t not in {k for q in fresh for k, v in q["tools"].items() if v}}),
              "browser": fresh[0]["browser"]}
    return blockers(merged, cdoc)


CAP_LINES, CAP_CHARS = 200, 160


def _one(x, cap: int = CAP_CHARS) -> str:
    """An untrusted string as one short line: control characters and newlines become spaces, and it is cut at `cap` characters."""
    t = " ".join(re.sub(r"[\x00-\x1f\x7f]", " ", str(x)).split())
    return t if len(t) <= cap else f"{t[:cap]}... (truncated, {len(t) - cap} more characters)"


def _code(x) -> str:
    """An untrusted string as an inline code span its own content cannot close: the delimiter is longer than any backtick run inside."""
    t = _one(x)
    n = max((len(m) for m in re.findall(r"`+", t)), default=0) + 1
    pad = " " if t.startswith("`") or t.endswith("`") else ""
    return f"{'`' * n}{pad}{t}{pad}{'`' * n}"


def _fence(text: str, lang: str = "") -> str:
    """A fenced block an untrusted text cannot break out of (the fence is longer than any backtick run inside), cut at a fixed line cap."""
    lines = text.splitlines()
    body = "\n".join(lines[:CAP_LINES])[:20000]
    if len(lines) > CAP_LINES or len(body) >= 20000:
        body += f"\n(truncated, {max(len(lines) - CAP_LINES, 0) or 'more'} more lines)"
    n = max((len(m) for m in re.findall(r"`+", body)), default=0) + 1
    f = "`" * max(n, 3)
    return f"{f}{lang}\n{body}\n{f}"


def _pinned_rows(rid: str, c: dict, meta: dict) -> list[tuple[str, str, str, bool]]:
    """(repo, path, diff against the base, sensitive) for every pinned input: written by the runner, so the owner must see it."""
    import difflib

    import verify
    d, out = store.run_dir(rid), []
    for repo, rels in contract.pinned_map(c).items():
        for rel in rels:
            try:
                old = contract.git(meta["repos"][repo]["path"], "show", f"{meta['repos'][repo]['base_sha']}:{rel}").splitlines(True)
            except (store.SdlcError, KeyError):
                old = []
            f = d / "inputs" / repo / rel
            new = f.read_text(errors="replace").splitlines(True) if f.is_file() else []
            diff = "".join(difflib.unified_diff(old, new, f"a/{_one(rel)}", f"b/{_one(rel)}")) or "(no change)\n"
            hot = verify._protected(rel, verify.DEFAULT_PROTECTED + c.get("protected", [])) or rel.startswith(".github/") or rel.rsplit("/", 1)[-1] == ".npmrc"
            out.append((repo, rel, diff, hot))
    return out


def _replaces_rows(tasks: dict, meta: dict) -> list[str]:
    """One line per replaces_tests glob: its task, its owned paths and how many files of the base it matches."""
    import fnmatch
    out, listed = [], {}
    for m in tasks.get("milestones", []):
        for t in m.get("tasks", []):
            for g in t.get("replaces_tests", []):
                r = meta["repos"][m["repo"]]
                if m["repo"] not in listed:
                    listed[m["repo"]] = contract.git(r["path"], "ls-tree", "-r", "--name-only", r["base_sha"]).splitlines()
                n = sum(fnmatch.fnmatch(f, g) for f in listed[m["repo"]])
                out.append(f"- {_code(t['id'])} ({_one(m['repo'])}): {_code(g)} matches {n} files at the base; the task owns {', '.join(_code(p) for p in t.get('paths', [])) or 'nothing'}")
    return out


def _base_lines(c: dict, meta: dict) -> list[str]:
    """One line per repo that builds on an approved base ref instead of its default branch."""
    out = []
    for n, s in (c.get("repos") or {}).items():
        if s.get("base") and n in meta["repos"]:
            r = meta["repos"][n]
            out.append(f"- **base:** {_code(n)}: {_code(s['base'])} @ `{s.get('base_sha', 'unresolved')}` "
                       f"({contract.base_ahead(r, s['base_sha']) if s.get('base_sha') else '?'} commits not on {r['default_branch']}); "
                       f"`sdlc pr` still targets {r['default_branch']}, so the PR also carries these base commits")
    return ["", "## Base", ""] + out if out else []


def _spec_lines(c: dict) -> list[str]:
    """Spec id, its checks and task in one table, uncovered and waived items first, then the waivers with their reasons."""
    rows = contract.spec_rows(c)
    if not rows:
        return []
    cell = lambda x: _one(x, 90).replace("|", "\\|")  # noqa: E731
    out = ["", "## Spec coverage", "", "| Spec | Text | Checks | Task | State |", "|---|---|---|---|---|"]
    for r in rows:
        state = "WAIVED" if r["waiver"] and not r["checks"] else "covered" if r["checks"] else "UNCOVERED"
        out.append(f"| {cell(r['id'])} | {cell(r['text'])} | {cell(', '.join(r['checks']) or '-')} | {cell(', '.join(r['tasks']) or '-')} | {state} |")
    waived = [r for r in rows if r["waiver"]]
    return out + ["", "## Waived spec items", ""] + (
        [f"- **{_code(r['id'])}:** {_one(r['waiver'])}" for r in waived] or ["- none"])


def screen(rid: str) -> Path:
    """The single approval screen: plan, the actual checks with expected values, dependency diff, destinations, caps."""
    d = store.run_dir(rid)
    c = store.read_json(d / "contract.json")
    meta = store.load_meta(rid)
    pr = store.read_json(d / "probe.json", [{"missing_tools": [], "browser": {"available": True, "why": ""}, "credentials": {"github": False}}])
    miss = sorted({t for p in pr for t in p["missing_tools"]})
    rows = ["| Check | Repo | Command | Expect | Where | Pinned | Env passed |", "|---|---|---|---|---|---|---|"]
    for k in c["checks"]:
        cell = lambda x: _one(x, 90).replace("|", "\\|")  # noqa: E731 - one table cell, no pipes, one line
        shown = f"board check {k['board']['spec']} ({k['board']['expected_rows']} rows)" if k.get("kind") == "board" else " ".join(k["runner"])
        if k.get("kind") == "board":
            shown += "".join(f"; {w}: {' '.join(k['board'][w])}" for w in ("build", "start") if k["board"].get(w))
        rows.append(f"| {cell(k['id'])} | {cell(k['repo'])} | {cell(shown)} | {cell(k['expect']['kind'])}"
                    f"{cell('; ' + json.dumps(k['expect'].get('value'))) if 'value' in k['expect'] else ''} | {cell(k.get('site', 'local'))} | {cell(', '.join(k.get('pins', {})) or '-')} | {cell(', '.join(k.get('env', [])) or '-')} |")
    import deps as deps_mod
    ui = [k for k in c["checks"] if k.get("design")]
    deps = c.get("deps", {})
    lim = c.get("limits", {})
    tasks = store.read_json(d / "tasks.json")
    pinned = _pinned_rows(rid, c, meta)
    hot = [f"- **PROTECTED — sensitive:** {_code(f'{r}:{p}')} is a protected path (test or CI config, workflow or registry settings) that the runner will write" for r, p, _, x in pinned if x]
    repl = _replaces_rows(tasks, meta)
    lines = [f"# Approve run {rid}", "", f"**Bundle digest:** `{contract.bundle_digest(rid)[:16]}`", ""] + (hot + [""] if hot else []) + [
             store.read_json(d / 'run.json')['title'], "",
             "## Plan", "", (d / "plan.md").read_text(), "",
             "## Repos", ""] + [f"- {_code(n)}: base `{r['base_sha'][:9]}`, branch {_code(r['branch'])}" for n, r in meta["repos"].items()] + _base_lines(c, meta) + [
             "", "## Milestones", ""] + [f"- {_code(m['id'])} ({_one(m['repo'])}): {len(m.get('tasks', []))} tasks, needs {_one(m.get('needs') or 'nothing')}" for m in tasks.get("milestones", [])] + [
             "", "## Paths each task owns", ""] + [f"- {_code(t['id'])} ({_one(m['repo'])}): {', '.join(_code(p) for p in t.get('paths', [])) or 'everything (no paths declared)'}"
                                                   for m in tasks.get("milestones", []) for t in m.get("tasks", [])] + [
             "", "## Pinned inputs (written by the runner before any task)", ""] + (
        [f"- {'**PROTECTED — sensitive:** ' if x else ''}{_code(f'{r}:{p}')}\n\n{_fence(df, 'diff')}" for r, p, df, x in pinned] or ["- none"]) + [
             "", "## Tests a task may delete or rewrite", ""] + (repl or ["- none"]) + [
             ] + _spec_lines(c) + [
             "", "## Checks that decide the result", ""] + rows + [
             "", "## Dependency and lockfile changes", ""] + (
        [f"- {_code(r)}: applied by the runner, then a frozen install with install scripts and source builds off; a manager with no such flag is not run\n\n{_fence(deps_mod.diff_text(rid, r), 'diff')}" for r in deps]
        or ["- none"]) + [
             "", "## Limits", "",
             f"- **Builders:** up to {lim.get('builders', 8)}, fewer when the graph allows less",
             f"- **Dispatch cap:** {lim.get('max_dispatches', 'not set: kickoff must set one')}",
             f"- **Run deadline:** {lim.get('deadline_hours', 24)} hours; job deadline 30 minutes; one build plus two fixes per feature",
             "", "## Release and destinations", ""] + (
        [f"- **{e['producer']} then {e['consumer']}:** {e.get('release', {}).get('kind', 'none')}"
         + (f"; packages {', '.join(e['packages'])}" if e.get("packages") else "")
         + (f"; tarballs vendored into `{e['pin']['dir']}`, package.json and lockfile rewritten by the runner (npm, scripts off, offline)"
            if e.get("release", {}).get("kind") == "vendored-tarball" else "") for e in c.get("edges", [])] or ["- one PR per repo: project branch into the default branch"]) + [
             "", "## Probes", "",
             f"- **Missing tools:** {', '.join(miss) or 'none'}",
             f"- **Browser:** {'available' if pr[0]['browser']['available'] else 'unavailable: ' + pr[0]['browser']['why']}",
             f"- **GitHub credentials:** {'ok' if pr[0]['credentials']['github'] else 'not signed in'}"] + (
        ["", "## UI rows and what cannot be measured", ""] + [f"- **{k['id']}:** {json.dumps(k['design'])[:120]}" for k in ui] if ui else [])
    p = d / "approval.md"
    store.atomic_write(p, "\n".join(lines) + "\n")
    return p


def gate_decision(out: str) -> str | None:
    """The `decision` of the JSON object `plannotator annotate --gate --json` prints (recorded values: approved, annotated,
    dismissed). Only an explicit "approved" counts; a missing or unparsable result is no approval."""
    for line in reversed(out.strip().splitlines()):
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("decision"), str):
            return obj["decision"]
    return None


KNOWN_PLANNOTATOR = (".local/bin/plannotator", ".plannotator/bin/plannotator", ".bun/bin/plannotator",
                     "/opt/homebrew/bin/plannotator", "/usr/local/bin/plannotator", "/usr/bin/plannotator")
SAFE_PATH = "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"
KEEP_ENV = ("USER", "LOGNAME", "TERM", "LANG", "DISPLAY", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR", "TMPDIR")


def _passwd_home() -> str:
    import pwd
    return os.path.realpath(pwd.getpwuid(os.getuid()).pw_dir)


def _temp_dirs() -> list[str]:
    import tempfile
    return [os.path.realpath(p) for p in ("/tmp", "/var/tmp", "/var/folders", tempfile.gettempdir(), os.environ.get("TMPDIR") or "/tmp")]


def environment_problem(env=None) -> str:
    """Why the gate refuses to run: HOME, PATH or PYTHON* changed from what a normal login has. Plannotator is found by
    absolute path and runs in a scrubbed environment, so these cannot swap it; refusing makes an attempt visible."""
    env = os.environ if env is None else env
    if (h := env.get("HOME")) and os.path.realpath(h) != _passwd_home():
        return "HOME is not the account's home folder"
    if bad := sorted(k for k in env if k.startswith("PYTHON")):
        return f"{bad[0]} is set"
    temps = _temp_dirs()
    for part in (env.get("PATH") or SAFE_PATH).split(":"):
        if not part or not os.path.isabs(part):
            return "PATH has an empty or relative entry"
        real = os.path.realpath(part)
        if any(real == t or real.startswith(t + os.sep) for t in temps):
            return f"PATH has a temporary folder ({part})"
    return ""


def plannotator_path() -> str | None:
    """The one plannotator program: an executable file at a known install location, never found through PATH."""
    home = _passwd_home()
    temps = _temp_dirs()
    for cand in KNOWN_PLANNOTATOR:
        p = cand if os.path.isabs(cand) else os.path.join(home, cand)
        real = os.path.realpath(p)
        if os.path.isfile(real) and os.access(real, os.X_OK) and not any(real.startswith(t + os.sep) for t in temps):
            return real
    return None


def _plannotator(cmd: list[str]) -> tuple[int, str]:
    env = {"HOME": _passwd_home(), "PATH": SAFE_PATH, **{k: os.environ[k] for k in KEEP_ENV if k in os.environ}}
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return r.returncode, r.stdout + r.stderr


GATE_RUN = _plannotator  # tests replace this function; nothing in the environment can


def gate(rid: str, purpose: str = "approve", by: str = "") -> bool:
    """The owner's gate and the decision in ONE process: show the screen in Plannotator and, only if it comes back approved,
    approve (or restart) right here. No marker file is written, so nothing another process writes can stand in for it."""
    if purpose == "approve" and not by.strip():
        raise SdlcError("`sdlc gate` needs --by NAME: who approves")
    if why := environment_problem():
        raise SdlcError(f"BLOCKED gate refused: {why}; run it from a normal shell, not with HOME, PATH or PYTHON* changed")
    exe = plannotator_path()
    if not exe:
        raise SdlcError("BLOCKED gate refused: plannotator is not installed at a known location")
    d = store.run_dir(rid)
    if purpose == "approve":
        doc = screen(rid)
    else:
        doc = d / f"gate-{purpose}.md"
        store.atomic_write(doc, f"# Restart run {rid}\n\nThe run was stopped or blocked. Approve to continue within the original caps and deadline.\n")
    rc, said = GATE_RUN([exe, "annotate", str(doc), "--gate", "--json"])  # a fixed command: no environment variable swaps it
    ok = rc == 0 and gate_decision(said) == "approved"
    store.log(rid, f"gate {purpose}: {'approved' if ok else 'not approved'}")
    if ok:
        contract.grant(purpose, rid)
        if purpose == "approve":
            contract.approve(rid, by)
        else:
            import engine
            engine.restart(rid)
    return ok
