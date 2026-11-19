#!/usr/bin/env python3
"""spec.py: the living spec (one file per rule) and the checks of a three-document change.

    spec.py find <words...> [--paths a,b] [--limit 10] [--prs]   rules for a request, ranked
    spec.py show <capability>                                    one capability, rule by rule
    spec.py new <capability> <summary...> [--proof test|manual|check:<name>]
    spec.py next                                                 the next free rule number
    spec.py last-id --write                                      record the highest id in .sdlc/last-rule-id
    spec.py renumber [--base REF] [--dry-run]                    move this branch's colliding rule ids
    spec.py index [--force]                                      rebuild the local index (never committed)
    spec.py capabilities [--write|--check]                       the generated specs/CAPABILITIES.md
    spec.py check [--base REF] [--json]                          the drift check (exit 1 on a problem)
    spec.py eval <fixture.json> [--k 10] [--fail-under 0.8]      recall@k of `find` against a grep
    spec.py qa <change-dir>                                      build QA applies? exit 0 yes, 3 skip, 2 unrecorded
    spec.py consistency <change-dir> [--phase draft|approve] [--base REF]
    spec.py outcome write|record|due ...                         the success measure after the folder is gone

Layout, from the repo root (`livingSpecs` in sdlc.json renames `specs`):

    specs/CAPABILITIES.md                      generated, one line per capability
    specs/<capability>/manifest.yaml           purpose, aliases, owner, code, tests, related
    specs/<capability>/rules/R123.md           one requirement: frontmatter + one EARS sentence

A rule id is `R` and a number with no fixed width. It is never reused: the next one is the highest
ever used plus one. Tests carry it as `@R123`. A rule keeps its id when it moves to another
capability (a file move); the capability is the folder, never part of the file. The PR's git diff
of `specs/` is the delta: there is no delta format and nothing to apply.

Importable by the gate with no side effects: `check`, `check_report`, `consistency`, `applies`,
`layout`, `changed_rules`, `change_rules`, `qa_applicability`, `outcome_write`. Stdlib only; runs in
CI without the plugin. Nothing here touches the network except `find --prs`, and that stays quiet
when `gh` is missing or offline.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

RULE_FILE = re.compile(r"^R(\d+)\.md$")
TAG = re.compile(r"(?<![\w@])@R(\d+)\b")
STATUSES = ("live", "planned")
# shortcut: a skip marker on the tag's line or the two lines above it. Misses a skip set far
# from the tag (a file-level skip); upgrade to per-framework collection when that bites.
SKIP = re.compile(
    r"\.skip\(|\bxit\(|\bxdescribe\(|\bxtest\(|pytest\.mark\.skip|pytest\.skip\(|unittest\.skip"
    r"|test\.fixme|\.fixme\(|\bfixme\b|skipIf|skipUnless|@Ignore"
)
TEST_DIRS = {"tests", "test", "__tests__", "e2e", "spec"}
SKIP_DIRS = {".git", "node_modules", ".worktrees", ".venv", "venv", "__pycache__", "dist", "build"}
STOP = {"the", "and", "for", "with", "that", "this", "when", "shall", "system", "from", "into"}


class SpecError(Exception):
    pass


# ---------------------------------------------------------------- small parsers


def parse_flat(text: str) -> dict:
    """The YAML subset the manifests and rule files use: `key: value`, `key: [a, b]`, and a key
    followed by `- item` lines. Anything else raises, so a typo is loud and no parser is needed."""
    out: dict = {}
    key = None
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.match(r"^\s*-\s+(.*)$", line)
        if item and key is not None and isinstance(out.get(key), list):
            out[key].append(_scalar(item.group(1)))
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not m:
            raise SpecError(f"line {n}: not `key: value`: {raw!r}")
        key, val = m.group(1), m.group(2).strip()
        if val == "":
            out[key] = []
        elif val.startswith("[") and val.endswith("]"):
            out[key] = [_scalar(v) for v in val[1:-1].split(",") if v.strip()]
        else:
            out[key] = _scalar(val)
    return out


def _scalar(v: str):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return {"null": None, "true": True, "false": False}.get(v, v)


def split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text
    return parse_flat(text[4:end]), text[end + 4 :].lstrip("\n")


_STRICT = (
    False  # set by check_report in CI or with an explicit --base: a failed git call is an error
)


def git(root: Path, *args: str, probe: bool = False) -> str | None:
    try:
        r = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True, timeout=60
        )
        ok = r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        ok = False
    if not ok and _STRICT and not probe:
        raise SpecError(f"git {' '.join(args[:2])} failed")
    return r.stdout if ok else None


def _inside(root: Path, p: Path) -> bool:
    try:
        p.resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def _config(root: Path) -> dict:
    try:
        return json.loads((Path(root) / "sdlc.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def specs_declared(root: Path) -> bool:
    return bool(_config(root).get("livingSpecs"))


def specs_name(root: Path) -> str:
    """The living-spec folder: `specs`, or sdlc.json `livingSpecs`, which must be one plain name
    that stays inside the repo (it becomes a path and a git pathspec)."""
    name = _config(root).get("livingSpecs")
    if not name:
        return "specs"
    if (
        not isinstance(name, str)
        or not re.fullmatch(r"[A-Za-z0-9._-]+", name)
        or name in (".", "..")
        or not _inside(root, Path(root) / name)
    ):
        raise SpecError(f"sdlc.json livingSpecs {name!r} must be one folder name inside the repo")
    return name


# ---------------------------------------------------------------- loading


@dataclass
class Rule:
    num: int
    cap: str
    path: str
    summary: str = ""
    status: str = "live"
    proof: str = "test"
    since: str = ""
    evidence: str = ""
    body: str = ""
    problems: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return f"R{self.num}"


def _rule_path_re(specs: str) -> re.Pattern:
    return re.compile(rf"^{re.escape(specs)}/([^/]+)/rules/R(\d+)\.md$")


def _parse_rule(cap: str, num: int, path: str, text: str) -> Rule:
    rule = Rule(num=num, cap=cap, path=path)
    try:
        meta, body = split_frontmatter(text)
    except SpecError as e:
        rule.problems.append(f"{path}: frontmatter: {e}")
        return rule
    rule.body = body.strip()
    if str(meta.get("id", "")) != rule.id:
        rule.problems.append(f"{path}: frontmatter id {meta.get('id')!r} must be {rule.id}")
    first = re.split(r"(?<=[.!?])\s", rule.body, maxsplit=1)[0] if rule.body else ""
    rule.summary = str(meta.get("summary") or first)[:120]
    rule.status = str(meta.get("status") or "live")
    rule.proof = str(meta.get("proof") or "test")
    rule.since = str(meta.get("since") or "")
    rule.evidence = str(meta.get("evidence") or "")
    if not rule.body:
        rule.problems.append(f"{path}: no requirement sentence")
    if rule.status not in STATUSES:
        rule.problems.append(f"{path}: status {rule.status!r} is not one of {STATUSES}")
    if not (rule.proof in ("test", "manual") or rule.proof.startswith("check:")):
        rule.problems.append(f"{path}: proof {rule.proof!r} must be test, manual or check:<name>")
    if rule.proof == "manual" and not rule.evidence:
        rule.problems.append(f"{path}: proof manual needs `evidence:` (who checks, and how)")
    return rule


def load_rules(root: Path, rev: str | None = None):
    """(rules, manifests {cap: dict}, problems). `rev` reads a past revision from git."""
    root = Path(root)
    specs = specs_name(root)
    pat = _rule_path_re(specs)
    rules: list[Rule] = []
    manifests: dict[str, dict] = {}
    problems: list[str] = []
    if rev:
        names = (git(root, "ls-tree", "-r", "--name-only", rev, "--", specs) or "").splitlines()

        def read(p: str) -> str:
            return git(root, "show", f"{rev}:{p}") or ""
    else:
        base = root / specs
        names = (
            sorted(str(p.relative_to(root)) for p in base.rglob("*") if p.is_file())
            if base.is_dir()
            else []
        )

        def read(p: str) -> str:
            return (root / p).read_text(encoding="utf-8")

    for p in names:
        parts = p.split("/")
        if len(parts) >= 3 and parts[2] == "rules" and p.endswith(".md"):
            m = pat.match(p)
            if not m:
                problems.append(f"{p}: a rule file is named R<number>.md")
                continue
            r = _parse_rule(m.group(1), int(m.group(2)), p, read(p))
            rules.append(r)
            problems += r.problems
        elif len(parts) == 3 and parts[2] == "manifest.yaml":
            try:
                manifests[parts[1]] = parse_flat(read(p))
            except SpecError as e:
                problems.append(f"{p}: {e}")
    rules.sort(key=lambda r: r.num)
    return rules, manifests, problems


# ---------------------------------------------------------------- ids


def history_ids(root: Path, ref: str = "--all") -> set[int]:
    """Every rule number that was ever added on `ref`. --no-renames: a move hides no add."""
    specs = specs_name(root)
    out = git(
        root, "log", ref, "--no-renames", "--diff-filter=A", "--name-only", "--format=",
        "--", f"{specs}/*/rules/R*.md",
    )  # fmt: skip
    ids = set()
    for line in (out or "").splitlines():
        m = _rule_path_re(specs).match(line.strip())
        if m:
            ids.add(int(m.group(2)))
    return ids


def last_id_file(root: Path) -> int:
    try:
        return int((root / ".sdlc" / "last-rule-id").read_text().strip())
    except (OSError, ValueError):
        return 0


def highest_id(root: Path) -> int:
    rules, _, _ = load_rules(root)
    return max(
        [r.num for r in rules] + [last_id_file(root)] + sorted(history_ids(root))[-1:], default=0
    )


def next_id(root: Path) -> int:
    return highest_id(root) + 1


# ---------------------------------------------------------------- tags


def test_files(root: Path, manifests: dict) -> list[Path]:
    """Files that may carry @R tags: the manifests' test roots, else the usual test places."""
    roots = [
        r
        for m in manifests.values()
        for t in _as_list(m.get("tests"))
        if (r := _safe_root(root, str(t))) is not None
    ]
    found: list[Path] = []
    specs = specs_name(root)
    if roots:
        for r in roots:
            found += [r] if r.is_file() else [p for p in r.rglob("*") if p.is_file()]
    else:
        for dirpath, dirs, files in os.walk(root):
            rel = Path(dirpath).relative_to(root)
            dirs[:] = [
                d for d in dirs if d not in SKIP_DIRS and str(rel / d) not in (specs, "changes")
            ]
            in_tests = bool(TEST_DIRS & set(rel.parts))
            for f in files:
                if in_tests or re.match(r"(test_.*\.py|.*_test\.py|.*\.(test|spec)\.\w+)$", f):
                    found.append(Path(dirpath) / f)
    return [p for p in found if _inside(root, p) and p.stat().st_size < 1_000_000]


def _safe_root(root: Path, rel: str) -> Path | None:
    """A manifest test root: relative, no `..`, and (links followed) inside the repo."""
    p = Path(rel)
    if p.is_absolute() or ".." in p.parts or not _inside(root, root / p):
        return None
    return root / p


def _as_list(v) -> list:
    return v if isinstance(v, list) else ([v] if v else [])


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _block(lines: list[str], j: int) -> range:
    """Line j and what is nested under it (deeper indentation, then a closing `})` line)."""
    base, k = _indent(lines[j]), j + 1
    while k < len(lines) and (
        not lines[k].strip()
        or _indent(lines[k]) > base
        or (_indent(lines[k]) == base and lines[k].lstrip().startswith(("}", ")")))
    ):
        k += 1
    return range(j, k)


MODULE_SKIP = re.compile(r"^pytestmark\s*=.*\bskip")
DESCRIBE_SKIP = re.compile(r"\b(describe|context|suite)\.skip\b")
BARE_SKIP = re.compile(r"\b(test|it)\.skip\(\s*(?![\"'`])")
CLASS_SKIP = re.compile(r"^\s*@(pytest\.mark\.skip|unittest\.skip)")


def skipped_lines(lines: list[str]) -> set[int]:
    """Lines a file-, describe- or class-level skip covers. Text-based: no runner is called.
    shortcut: indentation finds the block, so a skip inside one-line or oddly formatted code is
    missed; upgrade to a real parser if that bites."""
    out: set[int] = set()
    for i, line in enumerate(lines):
        if MODULE_SKIP.match(line):
            return set(range(len(lines)))
        if DESCRIBE_SKIP.search(line):
            out |= set(_block(lines, i))
        elif BARE_SKIP.search(line):
            if _indent(line) == 0:
                return set(range(len(lines)))
            # a bare skip inside a describe skips the whole enclosing block
            j = next(
                (
                    k
                    for k in range(i - 1, -1, -1)
                    if lines[k].strip() and _indent(lines[k]) < _indent(line)
                ),
                None,
            )
            if j is not None:
                out |= set(_block(lines, j))
        elif CLASS_SKIP.match(line):
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or lines[j].lstrip().startswith("@")):
                j += 1
            if j < len(lines) and lines[j].lstrip().startswith("class "):
                out |= set(_block(lines, j))
    return out


def scan_tags(files: list[Path], root: Path) -> dict[int, list[tuple[str, int, bool]]]:
    """number -> [(path, line, skipped)]."""
    out: dict[int, list] = {}
    for p in files:
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        covered = skipped_lines(lines) if any(TAG.search(ln) for ln in lines) else set()
        for i, line in enumerate(lines):
            for m in TAG.finditer(line):
                near = "\n".join(lines[max(0, i - 2) : i + 1])
                out.setdefault(int(m.group(1)), []).append(
                    (str(p.relative_to(root)), i + 1, i in covered or bool(SKIP.search(near)))
                )
    return out


# ---------------------------------------------------------------- git diff of the branch


def tip_ref(root: Path, base: str | None) -> str | None:
    default = _config(root).get("defaultBranch")
    names = (
        [default, "main", "master"] if isinstance(default, str) and default else ["main", "master"]
    )
    for cand in [base, *[f"origin/{n}" for n in names], *names]:
        if cand and git(root, "rev-parse", "--verify", "-q", cand + "^{commit}", probe=True):
            return cand
    return None


def resolve_base(root: Path, base: str | None) -> str | None:
    cand = tip_ref(root, base)
    return ((git(root, "merge-base", cand, "HEAD") or "").strip() or None) if cand else None


def changed_files(root: Path, mb: str) -> list[tuple[str, str, str | None]]:
    """(status, path, old path) of the working tree against the merge base, untracked included."""
    out = []
    for line in (git(root, "diff", "-M", "--name-status", mb) or "").splitlines():
        f = line.split("\t")
        s = f[0]
        out.append((s[0] if s[0] != "R" else s, f[-1], f[1] if s[0] == "R" else None))
    for p in (git(root, "ls-files", "--others", "--exclude-standard") or "").splitlines():
        out.append(("A", p, None))
    return out


def changed_rules(root: Path, base: str | None = None) -> dict[str, list[int]]:
    """The PR's delta, read from git: {"added", "changed", "removed", "moved"} -> rule numbers."""
    root = Path(root)
    mb = resolve_base(root, base)
    res: dict[str, list[int]] = {"added": [], "changed": [], "removed": [], "moved": []}
    if not mb:
        return res
    pat = _rule_path_re(specs_name(root))
    entries = changed_files(root, mb)
    deleted = {int(m.group(2)) for s, p, _ in entries if s == "D" and (m := pat.match(p))}
    for s, p, _old in entries:
        m = pat.match(p)
        if not m:
            continue
        n = int(m.group(2))
        if s == "A":
            res["moved" if n in deleted else "added"].append(n)
        elif s == "M":
            res["changed"].append(n)
        elif s == "D":
            if not any(
                t == "A" and (q := pat.match(p2)) and int(q.group(2)) == n for t, p2, _ in entries
            ):
                res["removed"].append(n)
        elif s.startswith("R"):
            res["moved" if s == "R100" else "changed"].append(n)
    return {k: sorted(set(v)) for k, v in res.items()}


# ---------------------------------------------------------------- check


def check_report(root: Path, base: str | None = None) -> dict[str, list[str]]:
    """The drift check. `problems` fail it; `warnings` are for people. A repo with no specs
    folder and no `livingSpecs` key is a legacy repo: nothing to check, never blocked. Anything
    that cannot be checked in CI, or with an explicit `base`, is a problem and never a silent skip."""
    global _STRICT
    strict = bool(base) or bool(os.environ.get("CI"))
    _STRICT = strict
    try:
        return _check_report(Path(root), base, strict)
    except SpecError as e:
        return {"problems": [str(e)], "warnings": []}
    finally:
        _STRICT = False


def _check_report(root: Path, base: str | None, strict: bool) -> dict[str, list[str]]:
    specs = specs_name(root)
    if not (root / specs).is_dir():
        if specs_declared(root):
            return {
                "problems": [f"sdlc.json names livingSpecs {specs!r} but the folder is missing"],
                "warnings": [],
            }
        return {"problems": [], "warnings": []}
    rules, manifests, problems = load_rules(root)
    warnings: list[str] = []
    seen: dict[int, str] = {}
    for r in rules:
        if r.num in seen:
            problems.append(
                f"{r.id} is in two places: {seen[r.num]} and {r.path} (run `spec renumber`)"
            )
        seen[r.num] = r.path
    caps = {r.cap for r in rules} | set(manifests)
    for cap in sorted(caps):
        m = manifests.get(cap)
        if m is None:
            problems.append(f"{specs_name(root)}/{cap}/manifest.yaml is missing")
        elif not m.get("purpose"):
            problems.append(f"{specs_name(root)}/{cap}/manifest.yaml has no purpose")
        elif m.get("coverage") == "partial":
            warnings.append(f"capability {cap} is only partly catalogued (coverage: partial)")
    for cap, m in sorted(manifests.items()):
        for tr in _as_list(m.get("tests")):
            if _safe_root(root, str(tr)) is None:
                problems.append(f"{specs}/{cap}/manifest.yaml: tests {tr!r} is outside the repo")
    tags = scan_tags(test_files(root, manifests), root)
    for n, hits in sorted(tags.items()):
        if n not in seen:
            problems.append(f"@R{n} in {hits[0][0]}:{hits[0][1]} names no rule")
    for r in rules:
        if r.status != "live" or r.proof != "test":
            continue
        hits = tags.get(r.num, [])
        if not hits:
            problems.append(f"{r.id} ({r.path}) has no test tagged @{r.id}")
        elif all(h[2] for h in hits):
            problems.append(f"{r.id} is tagged only in skipped tests ({hits[0][0]}:{hits[0][1]})")
    mb = resolve_base(root, base)
    if mb:
        problems += _diff_problems(root, mb, base, rules, tags)
    elif strict:
        problems.append(
            f"cannot resolve the base branch ({base or 'origin/main'}): the diff checks cannot run"
        )
    return {"problems": problems, "warnings": warnings}


def check(root: Path, base: str | None = None) -> list[str]:
    return check_report(root, base)["problems"]


def _diff_problems(root, mb, base, rules, tags) -> list[str]:
    out: list[str] = []
    delta = changed_rules(root, base)
    by_num = {r.num: r for r in rules}
    tip = tip_ref(root, base)
    tip_ids = _ids_at(root, tip) if tip else set()
    hist = history_ids(root, tip) if tip else set()
    for n in delta["added"]:
        if n in tip_ids:
            out.append(f"R{n} is already taken on {tip} by another change (run `spec renumber`)")
        elif n in hist:
            out.append(
                f"R{n} was used and removed before; ids are never reused (run `spec renumber`)"
            )
    changed_paths = {p for s, p, _ in changed_files(root, mb) if s != "D"}
    for n in delta["changed"]:
        r = by_num.get(n)
        if r is None or r.proof != "test" or r.status != "live":
            continue
        touched = [h for h in tags.get(n, []) if h[0] in changed_paths and not h[2]]
        if not touched:
            out.append(f"R{n} changed but no test tagged @R{n} changed with it")
    return out


def _ids_at(root: Path, ref: str) -> set[int]:
    specs = specs_name(root)
    out = git(root, "ls-tree", "-r", "--name-only", ref, "--", specs) or ""
    pat = _rule_path_re(specs)
    return {int(m.group(2)) for line in out.splitlines() if (m := pat.match(line))}


# ---------------------------------------------------------------- renumber


def renumber(root: Path, base: str | None = None, dry_run: bool = False) -> dict[str, str]:
    """Give this branch's colliding rule ids the next free numbers. Only what the branch added
    changes: its rule files, and the `@R` tags and `R<n>` words on lines the branch added."""
    root = Path(root)
    specs = specs_name(root)
    mb = resolve_base(root, base)
    if not mb:
        raise SpecError("no base branch found; pass --base")
    tip = tip_ref(root, base)
    delta = changed_rules(root, base)
    tip_ids = _ids_at(root, tip) if tip else set()
    clash = [
        n for n in delta["added"] if n in tip_ids or n in (history_ids(root, tip) if tip else set())
    ]
    if not clash:
        return {}
    rules, _, _ = load_rules(root)
    top = max(
        [r.num for r in rules]
        + list(tip_ids)
        + [last_id_file(root)]
        + sorted(history_ids(root, tip or "--all"))
    )
    mapping = {}
    for n in clash:
        top += 1
        mapping[f"R{n}"] = f"R{top}"
    if dry_run:
        return mapping
    pat = _rule_path_re(specs)
    for r in rules:
        if r.id in mapping and pat.match(r.path):
            new = mapping[r.id]
            dest = str(Path(r.path).with_name(f"{new}.md"))
            text = (root / r.path).read_text(encoding="utf-8")
            text = re.sub(rf"^id:\s*{r.id}\s*$", f"id: {new}", text, count=1, flags=re.M)
            if git(root, "mv", r.path, dest) is None:
                (root / r.path).rename(root / dest)
            (root / dest).write_text(text, encoding="utf-8")
    _retag_added_lines(root, mb, mapping)
    if (root / ".sdlc" / "last-rule-id").exists():
        (root / ".sdlc" / "last-rule-id").write_text(f"{top}\n")
    return mapping


def _retag_added_lines(root: Path, mb: str, mapping: dict[str, str]) -> None:
    pat = re.compile(r"(?<![\w@])(@?)(" + "|".join(map(re.escape, mapping)) + r")\b")
    specs = specs_name(root)
    diff = git(root, "diff", "-U0", mb, "--") or ""
    path, added = None, {}
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
        elif line.startswith("@@") and path:
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            start, n = int(m.group(1)), int(m.group(2) or 1)  # type: ignore[union-attr]
            added.setdefault(path, set()).update(range(start, start + n))
    for p in (git(root, "ls-files", "--others", "--exclude-standard") or "").splitlines():
        added[p] = None  # untracked: every line is the branch's
    for p, lines in added.items():
        if p.startswith(f"{specs}/") and "/rules/" in p:
            continue
        f = root / p
        try:
            text = f.read_text(encoding="utf-8").split("\n")
        except (OSError, UnicodeDecodeError):
            continue
        changed = False
        for i, line in enumerate(text):
            if lines is None or (i + 1) in lines:
                new = pat.sub(lambda m: m.group(1) + mapping[m.group(2)], line)
                if new != line:
                    text[i], changed = new, True
        if changed:
            f.write_text("\n".join(text), encoding="utf-8")


# ---------------------------------------------------------------- new, show


def new_rule(root: Path, cap: str, summary: str, proof: str = "test", since: str = "") -> Path:
    root = Path(root)
    specs = specs_name(root)
    n = next_id(root)
    d = root / specs / cap
    (d / "rules").mkdir(parents=True, exist_ok=True)
    if not (d / "manifest.yaml").exists():
        (d / "manifest.yaml").write_text(
            f"purpose: {summary}\naliases: []\nowner: \ncode: []\ntests: []\nrelated: []\n"
        )
    extra = "evidence: who checks this, and how\n" if proof == "manual" else ""
    p = d / "rules" / f"R{n}.md"
    p.write_text(
        f"---\nid: R{n}\nsummary: {summary}\nstatus: live\nproof: {proof}\n"
        f"since: {since}\n{extra}---\nWhen <trigger>, the system shall <response>.\n"
    )
    return p


def show(root: Path, cap: str) -> str:
    rules, manifests, _ = load_rules(root)
    m = manifests.get(cap, {})
    out = [f"# {cap}: {m.get('purpose', '')}"]
    for r in rules:
        if r.cap == cap:
            out.append(f"\n{r.id} [{r.status}, proof {r.proof}]\n{r.body}")
    return "\n".join(out)


# ---------------------------------------------------------------- capabilities


def render_capabilities(root: Path) -> str:
    """One line per capability and no rule counts, so two PRs rarely touch the same line."""
    _, manifests, _ = load_rules(root)
    lines = ["<!-- generated by spec.py capabilities; do not edit -->", "# Capabilities", ""]
    for cap in sorted(manifests):
        m = manifests[cap]
        extra = []
        if m.get("aliases"):
            extra.append("also: " + ", ".join(map(str, _as_list(m["aliases"]))))
        if m.get("owner"):
            extra.append(f"owner: {m['owner']}")
        if m.get("coverage") == "partial":
            extra.append("partly catalogued")
        tail = f" ({'; '.join(extra)})" if extra else ""
        lines.append(f"- **{cap}**: {m.get('purpose', '')}{tail}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- index and find


def _fingerprint(root: Path) -> str:
    h = hashlib.sha1()
    base = root / specs_name(root)
    if base.is_dir():
        for p in sorted(base.rglob("*")):
            if p.is_file() and (p.name == "manifest.yaml" or p.parent.name == "rules"):
                st = p.stat()
                h.update(f"{p.relative_to(root)}{st.st_mtime_ns}{st.st_size}".encode())
    return h.hexdigest()


def _index_path(root: Path) -> Path | None:
    out = git(root, "rev-parse", "--git-path", "spec-index.json")
    return (root / out.strip()) if out else None  # inside .git: never committed, one per worktree


def load_index(root: Path, force: bool = False) -> list[dict]:
    """The local index: id, cap, summary, status. Rebuilt when any rule or manifest changed."""
    root = Path(root)
    path, fp = _index_path(root), _fingerprint(root)
    if path and path.exists() and not force:
        try:
            data = json.loads(path.read_text())
            if data.get("fp") == fp:
                return data["rules"]
        except (OSError, ValueError, KeyError):
            pass
    rules, _, _ = load_rules(root)
    rows = [{"id": r.id, "cap": r.cap, "summary": r.summary, "status": r.status} for r in rules]
    if path:
        try:
            path.write_text(json.dumps({"fp": fp, "rules": rows}))
        except OSError:
            pass
    return rows


def stem(w: str) -> str:
    w = w.lower()
    if w.endswith("ies") and len(w) > 5:
        return w[:-3] + "y"
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def tokens(text: str) -> list[str]:
    return [
        stem(t) for t in re.findall(r"[A-Za-z0-9]+", text) if t.lower() not in STOP and len(t) > 1
    ]


def rank(rows: list[dict], manifests: dict, query: str, paths: list[str] | None = None):
    """Score rows by id, summary, capability name, aliases and purpose; [(score, row, matched)]."""
    q = list(dict.fromkeys(tokens(query)))
    raw = {t.lower() for t in re.findall(r"[A-Za-z0-9]+", query)}
    scored = []
    for row in rows:
        m = manifests.get(row["cap"], {})
        score, hit = 0.0, []
        if row["id"].lower() in raw:
            score += 100
            hit.append(row["id"])
        summ = set(tokens(row["summary"]))
        cap_t = set(tokens(row["cap"].replace("-", " ").replace("_", " ")))
        for a in _as_list(m.get("aliases")):
            cap_t |= set(tokens(str(a)))
        purpose = set(tokens(str(m.get("purpose", ""))))
        for t in q:
            if t in summ:
                score, hit = score + 2, hit + [t]
            if t in cap_t:
                score, hit = score + 3, hit + [t]
            elif t in purpose:
                score += 1
        for p in paths or []:
            if any(p.startswith(str(c).rstrip("/")) for c in _as_list(m.get("code")) if c):
                score += 2
        if score:
            scored.append((score, row, list(dict.fromkeys(hit))))
    # related capabilities: the rules next door to the best hits, below every direct hit
    direct = {r["id"] for _, r, _ in scored}
    best = sorted(
        {row["cap"]: s for s, row, _ in sorted(scored, key=lambda x: x[0])}.items(),
        key=lambda kv: -kv[1],
    )[:3]
    near = {rel: cap for cap, _ in best for rel in _as_list(manifests.get(cap, {}).get("related"))}
    for row in rows:
        if row["id"] not in direct and row["cap"] in near:
            scored.append((0.5, row, [f"via {near[row['cap']]}"]))
    return scored


def _rule_ts(root: Path, path: str) -> int:
    out = git(root, "log", "-1", "--format=%ct", "--", path)
    return int(out.strip()) if out and out.strip() else int(dt.datetime.now().timestamp())


def _stale(root: Path, row: dict, manifest: dict, path: str) -> bool:
    code = [str(c) for c in _as_list(manifest.get("code")) if c]
    out = (
        git(root, "log", f"--since=@{_rule_ts(root, path)}", "--format=%h", "--", *code)
        if code
        else ""
    )
    return len((out or "").split()) >= 3  # three code commits since the rule last changed


def open_pr_files(root: Path) -> list[tuple[int, list[str]]]:
    try:
        r = subprocess.run(
            ["gh", "pr", "list", "--state", "open", "--limit", "100", "--json", "number,files"],
            capture_output=True, text=True, timeout=20, cwd=root,
        )  # fmt: skip
        return (
            [(p["number"], [f["path"] for f in p["files"]]) for p in json.loads(r.stdout)]
            if r.returncode == 0
            else []
        )
    except (OSError, ValueError, subprocess.TimeoutExpired, KeyError):
        return []


def find(root: Path, query: str, paths=None, limit: int = 10, prs: bool = False) -> list[str]:
    root = Path(root)
    rows = load_index(root)
    _, manifests, _ = (
        load_rules(root) if rows or (root / specs_name(root)).is_dir() else ([], {}, [])
    )
    scored = rank(rows, manifests, query, paths)
    scored.sort(key=lambda s: -s[0])
    top = scored[:30]
    specs = specs_name(root)
    # git dates break ties: a long-lived rule outranks yesterday's copy edit
    top.sort(key=lambda s: (-s[0], -_rule_ts(root, f"{specs}/{s[1]['cap']}/rules/{s[1]['id']}.md")))
    top = top[:limit]
    open_prs = open_pr_files(root) if prs else []
    out = []
    for _, row, hit in top:
        path = f"{specs}/{row['cap']}/rules/{row['id']}.md"
        flags = ""
        if _stale(root, row, manifests.get(row["cap"], {}), path):
            flags += "  stale?"
        flags += "".join(f"  ! open PR #{n} edits it" for n, fs in open_prs if path in fs)
        out.append(
            f"{row['id']}  {row['cap']}  {row['status']}  {row['summary']}  {path}  [{', '.join(hit)}]{flags}"
        )
    if not out:
        out.append("no rule matched")
        q = set(tokens(query))
        for cap, m in sorted(manifests.items()):
            words = set(tokens(cap.replace("-", " "))) | set(tokens(str(m.get("purpose", ""))))
            words |= {t for a in _as_list(m.get("aliases")) for t in tokens(str(a))}
            if q & words or m.get("coverage") == "partial":
                part = (
                    "  (partly catalogued: absence is not proof)"
                    if m.get("coverage") == "partial"
                    else ""
                )
                out.append(
                    f"capability {cap}: code {_as_list(m.get('code'))} tests {_as_list(m.get('tests'))}{part}"
                )
    return out


# ---------------------------------------------------------------- eval


def grep_baseline(rules: list[Rule], query: str, k: int) -> list[str]:
    """What `rg -c -i` over the rule files ranks: the files with the most query-word hits."""
    words = [w for w in re.findall(r"[A-Za-z0-9]+", query) if w.lower() not in STOP and len(w) > 1]
    hits = []
    for r in rules:
        text = f"{r.summary}\n{r.body}".lower()
        n = sum(text.count(w.lower()) for w in words)
        if n:
            hits.append((-n, r.num, r.id))
    return [h[2] for h in sorted(hits)[:k]]


def evaluate(root: Path, fixture: list[dict], k: int = 10) -> dict:
    """recall@k of `find` and of the grep baseline over the fixture's past changes. A case lists
    the request `query`, the `paths` known at intake, the pre-existing rule ids that mattered
    (`relevant`) and optionally `rev`, the parent revision to replay at. Cases with no relevant
    rule are new features: counted apart."""
    root = Path(root)
    res = {"cases": 0, "no_prior": 0, "find": 0.0, "grep": 0.0, "misses": []}
    for case in fixture:
        rel = set(case.get("relevant", []))
        if not rel:
            res["no_prior"] += 1
            continue
        rules, manifests, _ = load_rules(root, case.get("rev"))
        rows = [{"id": r.id, "cap": r.cap, "summary": r.summary, "status": r.status} for r in rules]
        got = [
            row["id"]
            for s, row, _ in sorted(
                rank(rows, manifests, case["query"], case.get("paths")), key=lambda x: -x[0]
            )[:k]
        ]
        base = grep_baseline(rules, case["query"], k)
        a, b = len(rel & set(got)) / len(rel), len(rel & set(base)) / len(rel)
        res["cases"] += 1
        res["find"] += a
        res["grep"] += b
        if a < 1:
            res["misses"].append(
                {"case": case.get("id", case["query"]), "missing": sorted(rel - set(got))}
            )
    for key in ("find", "grep"):
        res[key] = round(res[key] / res["cases"], 3) if res["cases"] else 0.0
    res["k"] = k
    return res


# ---------------------------------------------------------------- the three-document change

CHANGE_ID = re.compile(r"^\d{4}-\d{2}-\d{2}")


def layout(change: Path) -> str:
    """'v4' for a change pinned to the three-document layout, 'legacy' for intent/facts/plan,
    'none' for an empty folder. The pin is `layout: 4` in decisions.json; a folder that has a
    spec.md and no facts.md counts too."""
    change = Path(change)
    try:
        if json.loads((change / "decisions.json").read_text()).get("layout") == 4:
            return "v4"
    except (OSError, ValueError):
        pass
    if (change / "spec.md").exists() and not (change / "facts.md").exists():
        return "v4"
    return "legacy" if (change / "facts.md").exists() or (change / "intent.md").exists() else "none"


# family letter -> (what it is, where it is defined). The letter R is one id family with two
# meanings, pinned by layout: a review finding before layout 4, a rule from layout 4 on, where a
# review finding is V. F, N, X and H (facts, analysis, challenge) do not exist in layout 4.
FAMILIES_LEGACY = {
    "A": ("ask", "intent.md"),
    "J": ("job story", "intent.md"),
    "F": ("fact", "facts.md"),
    "N": ("non-functional fact", "facts.md"),
    "X": ("analysis finding", "analyze.md"),
    "H": ("challenge finding", "challenge.md"),
    "Q": ("question asked during the build", "questions.md"),
    "R": ("review finding", "findings.md"),
    "B": ("numbered item", ""),
}
FAMILIES_V4 = {
    "A": ("ask", "spec.md"),
    "J": ("job story", "spec.md"),
    "R": ("rule", "specs/<capability>/rules/R<n>.md"),
    "V": ("review finding", "findings.md"),
    "Q": ("question asked during the build", "questions.md"),
    "B": ("numbered item", ""),
}


def id_families(change: Path | None) -> dict[str, tuple[str, str]]:
    return FAMILIES_V4 if change is not None and applies(Path(change)) else FAMILIES_LEGACY


def applies(change: Path) -> bool:
    return layout(change) == "v4"


def documents(change: Path) -> list[str]:
    """The files a person reads, by layout: what a lint or a lock covers."""
    change = Path(change)
    if applies(change):
        return [f for f in ("spec.md", "design.md", "tasks.md") if (change / f).exists()]
    return [f for f in ("intent.md", "facts.md", "plan.md") if (change / f).exists()]


def section(text: str, name: str) -> str:
    m = re.search(rf"^(#{{2,4}})\s+{re.escape(name)}\b.*$", text, re.M | re.I)
    if not m:
        return ""
    rest = text[m.end() :]
    stop = re.search(rf"^#{{2,{len(m.group(1))}}}\s", rest, re.M)
    return rest[: stop.start()] if stop else rest


def table(text: str, name: str) -> list[dict[str, str]]:
    rows = [
        [c.strip() for c in ln.strip().strip("|").split("|")]
        for ln in section(text, name).splitlines()
        if ln.strip().startswith("|")
    ]
    rows = [r for r in rows if not all(re.fullmatch(r":?-{2,}:?", c) for c in r)]
    if len(rows) < 2:
        return []
    head = [h.lower() for h in rows[0]]
    return [dict(zip(head, r)) for r in rows[1:]]


def _cell(row: dict, *names: str) -> str:
    for n in names:
        for k, v in row.items():
            if k.startswith(n):
                return v
    return ""


def change_rules(change: Path) -> dict[int, dict]:
    """Rule number -> {change, capability, asks} from the spec's Requirements table."""
    text = (Path(change) / "spec.md").read_text(encoding="utf-8")
    out = {}
    for row in table(text, "Requirements"):
        m = re.fullmatch(r"R(\d+)", _cell(row, "rule", "#").strip("*` "))
        if m:
            out[int(m.group(1))] = {
                "change": _cell(row, "change").lower(),
                "capability": _cell(row, "capab").strip("` "),
                "asks": re.findall(r"A\d+", _cell(row, "ask")),
            }
    return out


def qa_applicability(change: Path) -> tuple[bool | None, str]:
    """Decide first whether build QA applies, before any readiness file is asked for (S1).
    True runs it, False skips it with the reason, None means Stage 2 recorded nothing: the
    caller stops and asks, it never treats a missing record as a skip."""
    fm, _ = split_frontmatter((Path(change) / "spec.md").read_text(encoding="utf-8"))
    if "ux" not in fm:
        return None, "spec.md has no `ux` field: Stage 2 must record it"
    if str(fm["ux"]) in ("none", "off"):
        return False, "no interface change (ux: none)"
    if str(fm.get("prototype", "")) == "none":
        return False, "prototype: none, recorded at Stage 2"
    if str(fm.get("prototype", "")) == "required":
        return True, "prototype: required"
    return None, "prototype is not recorded: Stage 2 must write required or none"


def task_states(change: Path) -> list[tuple[str, str, str]]:
    """(task id, state, milestone) from tasks.md, for the status script."""
    f = Path(change) / "tasks.md"
    if not f.exists():
        return []
    rows = table(f.read_text(encoding="utf-8"), "Tasks")
    return [(r.get("#", ""), _cell(r, "state"), _cell(r, "milestone")) for r in rows if r.get("#")]


def lock_inputs(change: Path) -> dict[str, str]:
    """What the approval lock hashes, by file: all of spec.md and design.md, the task rows of
    tasks.md without the State column, and each approved rule file by id (`rules/R<n>.md`). A
    tick or a handover edit never moves the hash."""
    change = Path(change)
    out = {}
    for name in ("spec.md", "design.md"):
        if (change / name).exists():
            out[name] = (change / name).read_text(encoding="utf-8")
    f = change / "tasks.md"
    if f.exists():
        text = f.read_text(encoding="utf-8")
        keep = []
        for sec in ("Tasks", "Milestones"):
            for r in table(text, sec):
                keep.append("|".join(v for k, v in r.items() if k != "state"))
        out["tasks.md"] = "\n".join(keep)
    root = change.parent.parent
    by_num = {r.num: r.path for r in load_rules(root)[0]}
    for n, r in sorted(change_rules(change).items()):
        if r["change"] != "removed" and n in by_num:
            # keyed by id, not path: a move to another capability keeps the hash. The `status:`
            # line is left out: planned to live is the build's own step, not an edit of the rule.
            text = (root / by_num[n]).read_text(encoding="utf-8")
            out[f"rules/R{n}.md"] = re.sub(r"^status:.*\n", "", text, count=1, flags=re.M)
    return out


def consistency(
    change: Path, phase: str = "approve", root: Path | None = None, base: str | None = None
) -> list[str]:
    """The cross-document check a script does faster than a model. `draft` (before the UX
    validation and the joint gate) lets an ask be `pending`; `approve` does not (D1)."""
    change = Path(change)
    root = Path(root) if root else change.parent.parent
    errs: list[str] = []
    try:
        text = (change / "spec.md").read_text(encoding="utf-8")
        fm, _ = split_frontmatter(text)
    except (OSError, SpecError) as e:
        return [f"spec.md: {e}"]
    scope = str(fm.get("scope", ""))
    if scope not in ("S", "M", "L"):
        errs.append("spec.md: scope must be S, M or L (chosen by risk, not by UX size)")
    if "ux" not in fm:
        errs.append("spec.md: no `ux` field (none, S, M or L)")
    ux = str(fm.get("ux", "none"))
    if ux not in ("none", "off") and str(fm.get("prototype", "")) not in ("required", "none"):
        errs.append(
            "spec.md: ux is not none, so record `prototype: required` or `prototype: none` at Stage 2"
        )
    reqs = change_rules(change)
    asks = {r["#"]: r for r in table(text, "Asks") if re.fullmatch(r"A\d+", r.get("#", ""))}
    if not asks:
        errs.append("spec.md: no asks found in the Asks table")
    for aid, row in asks.items():
        ans = _cell(row, "answered").strip("` ")
        if not ans:
            errs.append(f"ask {aid} has no `Answered by` cell")
            continue
        for part in [p.strip() for p in re.split(r"[,;]", ans) if p.strip()]:
            low = part.lower()
            if low == "pending":
                if phase != "draft":
                    errs.append(
                        f"ask {aid} is still pending: map it to a rule or out of scope before the gate"
                    )
            elif low != "out of scope" and not (
                re.fullmatch(r"R\d+", part) and int(part[1:]) in reqs
            ):
                errs.append(
                    f"ask {aid} is answered by {part}, which is not in the Requirements table"
                )
    if phase == "draft":
        return errs
    for n, r in sorted(reqs.items()):
        if r["change"] not in ("new", "changed", "removed"):
            errs.append(f"R{n}: Change must be new, changed or removed")
        if not r["asks"] or any(a not in asks for a in r["asks"]):
            errs.append(f"R{n}: cites no ask, or an ask that does not exist")
    errs += _rule_file_errors(root, reqs, base)
    tasks = (
        table((change / "tasks.md").read_text(encoding="utf-8"), "Tasks")
        if (change / "tasks.md").exists()
        else []
    )
    if scope in ("M", "L"):
        errs += _task_errors(tasks, reqs)
    if scope == "L":
        errs += _design_errors(change, reqs)
    return errs


def _rule_file_errors(root: Path, reqs: dict, base: str | None) -> list[str]:
    errs = []
    rules, _, _ = load_rules(root)
    by_num = {r.num: r for r in rules}
    for n, r in sorted(reqs.items()):
        have = by_num.get(n)
        if r["change"] in ("new", "changed") and have is None:
            errs.append(f"R{n} is listed as {r['change']} but has no rule file")
        elif r["change"] in ("new", "changed") and r["capability"] and have.cap != r["capability"]:  # type: ignore[union-attr]
            errs.append(f"R{n} is in {have.cap}, the spec says {r['capability']}")  # type: ignore[union-attr]
        elif r["change"] == "removed" and have is not None:
            errs.append(f"R{n} is listed as removed but its rule file still exists")
    if base and not resolve_base(root, base):
        errs.append(f"cannot resolve the base branch {base!r}: the diff comparison cannot run")
    elif resolve_base(root, base):
        delta = changed_rules(root, base)
        touched = set(delta["added"] + delta["changed"] + delta["removed"])
        if touched != set(reqs):
            diff = sorted(touched ^ set(reqs))
            errs.append(
                "the Requirements table and the git diff of the rules disagree on "
                + ", ".join(f"R{n}" for n in diff)
            )
    return errs


def _task_errors(tasks: list[dict], reqs: dict) -> list[str]:
    errs = []
    if not tasks:
        return ["tasks.md: no tasks in the Tasks table"]
    ids = {t.get("#") or _cell(t, "task") for t in tasks}
    covered: set[int] = set()
    graph = {}
    for t in tasks:
        tid = t.get("#") or _cell(t, "task")
        cited = {int(x) for x in re.findall(r"R(\d+)", _cell(t, "rules", "satisf"))}
        covered |= cited
        for n in cited - set(reqs):
            errs.append(f"task {tid} cites R{n}, which is not in the Requirements table")
        if not _cell(t, "test").strip(" -"):
            errs.append(f"task {tid} names no test")
        graph[tid] = [d for d in re.findall(r"T\d+", _cell(t, "needs"))]
        for d in graph[tid]:
            if d not in ids:
                errs.append(f"task {tid} needs {d}, which does not exist")
    for n, r in sorted(reqs.items()):
        if r["change"] in ("new", "changed") and n not in covered:
            errs.append(f"R{n} has no task")
    state: dict[str, int] = {}

    def visit(t: str) -> bool:
        if state.get(t) == 1:
            return True
        if state.get(t) == 2:
            return False
        state[t] = 1
        if any(visit(d) for d in graph.get(t, []) if d in graph):
            return True
        state[t] = 2
        return False

    if any(visit(t) for t in graph):
        errs.append("tasks.md: the `needs` column has a cycle")
    return errs


def _design_errors(change: Path, reqs: dict) -> list[str]:
    errs = []
    if not (change / "design.md").exists():
        return ["scope L needs design.md"]
    text = (change / "design.md").read_text(encoding="utf-8")
    strategy = {
        int(m)
        for row in table(text, "Test strategy")
        for m in re.findall(r"R(\d+)", _cell(row, "rule"))
    }
    for n, r in sorted(reqs.items()):
        if r["change"] in ("new", "changed") and n not in strategy:
            errs.append(f"R{n} has no line in design.md Test strategy")
    for row in table(text, "Risks"):
        if not _cell(row, "proof").strip(" -"):
            errs.append(
                f"risk {_cell(row, 'risk')[:40]!r} has no `Proof before build` (a command, or `known`)"
            )
    return errs


# ---------------------------------------------------------------- outcome (S3)


def outcome_write(root: Path, change: Path, due: str | None = None) -> Path:
    """Copy the success measure out of the change folder before the folder is removed, to
    `.sdlc/outcomes/<id>.json`. It survives the folder, needs no tracker and no later PR."""
    root, change = Path(root), Path(change)
    text = (change / "spec.md").read_text(encoding="utf-8")
    fm, _ = split_frontmatter(text)
    measure = " ".join(section(text, "Success measure").split())
    due = due or (dt.date.today() + dt.timedelta(days=14)).isoformat()
    rec = {
        "change": change.name,
        "capabilities": _as_list(fm.get("capabilities")),
        "rules": [f"R{n}" for n in sorted(change_rules(change))],
        "measure": measure,
        "due": due,
        "observed": None,
        "observed_at": None,
        "met": None,
    }
    p = root / ".sdlc" / "outcomes" / f"{change.name}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rec, indent=2) + "\n")
    return p


def outcome_record(
    root: Path, change_id: str, observed: str, met: bool, on: str | None = None
) -> dict:
    p = Path(root) / ".sdlc" / "outcomes" / f"{change_id}.json"
    rec = json.loads(p.read_text())
    rec.update(observed=observed, observed_at=on or dt.date.today().isoformat(), met=met)
    p.write_text(json.dumps(rec, indent=2) + "\n")
    return rec


def outcome_due(root: Path, today: str | None = None) -> list[str]:
    today = today or dt.date.today().isoformat()
    out = []
    for p in sorted((Path(root) / ".sdlc" / "outcomes").glob("*.json")):
        rec = json.loads(p.read_text())
        if rec.get("observed") is None and rec.get("due", "9999") <= today:
            out.append(rec["change"])
    return out


# ---------------------------------------------------------------- cli


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="spec.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("find")
    f.add_argument("words", nargs="+")
    f.add_argument("--paths", default="")
    f.add_argument("--limit", type=int, default=10)
    f.add_argument("--prs", action="store_true")
    sub.add_parser("show").add_argument("cap")
    n = sub.add_parser("new")
    n.add_argument("cap")
    n.add_argument("summary", nargs="+")
    n.add_argument("--proof", default="test")
    n.add_argument("--since", default="")
    sub.add_parser("next")
    sub.add_parser("last-id").add_argument("--write", action="store_true")
    r = sub.add_parser("renumber")
    r.add_argument("--base")
    r.add_argument("--dry-run", action="store_true")
    sub.add_parser("index").add_argument("--force", action="store_true")
    c = sub.add_parser("capabilities")
    c.add_argument("--write", action="store_true")
    c.add_argument("--check", action="store_true")
    k = sub.add_parser("check")
    k.add_argument("--base")
    k.add_argument("--json", action="store_true")
    e = sub.add_parser("eval")
    e.add_argument("fixture")
    e.add_argument("--k", type=int, default=10)
    e.add_argument("--fail-under", type=float, default=0.0)
    e.add_argument("--root", help="evaluate against this repo root instead of the current one")
    sub.add_parser("qa").add_argument("change")
    s = sub.add_parser("consistency")
    s.add_argument("change")
    s.add_argument("--phase", default="approve", choices=("draft", "approve"))
    s.add_argument("--base")
    o = sub.add_parser("outcome")
    o.add_argument("action", choices=("write", "record", "due"))
    o.add_argument("target", nargs="?")
    o.add_argument("--due")
    o.add_argument("--observed")
    o.add_argument("--met", choices=("yes", "no"))
    a = ap.parse_args(argv)
    here = Path.cwd()
    top = git(here, "rev-parse", "--show-toplevel")
    root = here if (here / "sdlc.json").exists() or not top else Path(top.strip())
    try:
        if a.cmd == "find":
            print(
                "\n".join(
                    find(
                        root,
                        " ".join(a.words),
                        [p for p in a.paths.split(",") if p],
                        a.limit,
                        a.prs,
                    )
                )
            )
        elif a.cmd == "show":
            print(show(root, a.cap))
        elif a.cmd == "new":
            print(new_rule(root, a.cap, " ".join(a.summary), a.proof, a.since).relative_to(root))
        elif a.cmd == "next":
            print(f"R{next_id(root)}")
        elif a.cmd == "last-id":
            hi = highest_id(root)
            if a.write:
                (root / ".sdlc").mkdir(exist_ok=True)
                (root / ".sdlc" / "last-rule-id").write_text(f"{hi}\n")
            print(hi)
        elif a.cmd == "renumber":
            m = renumber(root, a.base, a.dry_run)
            print("\n".join(f"{x} -> {y}" for x, y in m.items()) or "no collision")
        elif a.cmd == "index":
            print(f"{len(load_index(root, a.force))} rules indexed")
        elif a.cmd == "capabilities":
            text = render_capabilities(root)
            target = root / specs_name(root) / "CAPABILITIES.md"
            if a.write:
                target.write_text(text)
            elif a.check:
                if not target.exists() or target.read_text() != text:
                    print("CAPABILITIES.md is stale: run spec.py capabilities --write")
                    return 1
            else:
                print(text, end="")
        elif a.cmd == "check":
            rep = check_report(root, a.base)
            if a.json:
                print(json.dumps(rep, indent=2))
            else:
                for w in rep["warnings"]:
                    print(f"warn  {w}")
                for p in rep["problems"]:
                    print(f"FAIL  {p}")
                print("SPEC PASS" if not rep["problems"] else f"SPEC FAIL ({len(rep['problems'])})")
            return 1 if rep["problems"] else 0
        elif a.cmd == "eval":
            res = evaluate(
                Path(a.root) if a.root else root, json.loads(Path(a.fixture).read_text()), a.k
            )
            print(json.dumps(res, indent=2))
            return 1 if res["find"] < a.fail_under else 0
        elif a.cmd == "qa":
            ok, why = qa_applicability(Path(a.change))
            print(
                ("QA RUNS: " if ok else "QA SKIPPED: " if ok is False else "QA UNRECORDED: ") + why
            )
            return 0 if ok else 3 if ok is False else 2
        elif a.cmd == "consistency":
            errs = consistency(Path(a.change), a.phase, root, a.base)
            print("\n".join(errs) or f"CONSISTENT ({a.phase})")
            return 1 if errs else 0
        elif a.cmd == "outcome":
            if a.action == "write":
                print(outcome_write(root, Path(a.target), a.due).relative_to(root))
            elif a.action == "record":
                print(json.dumps(outcome_record(root, a.target, a.observed or "", a.met == "yes")))
            else:
                print("\n".join(outcome_due(root)) or "none due")
    except SpecError as e:
        print(f"spec.py: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
