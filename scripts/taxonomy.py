"""The cct naming rules (docs/adr/0001-skill-taxonomy.md) and the checks that validate plugins/cct against them:
name pattern, approved verbs, frontmatter, trigger-phrase uniqueness and references that must resolve.

Imported by tests/test_plugin.py. Importing it has no side effects."""

import re
from pathlib import Path

import yaml

# ── The rules ────────────────────────────────────────────────────────────────
FAMILIES = ("sdlc", "project", "product", "ux", "design", "arch", "db", "review", "test", "git", "data", "tracking", "docs")
VENDORS = ("aws", "cloudflare", "github", "linear", "posthog", "codex")
PREFIXES = (*FAMILIES, *VENDORS, "browser", "role")
NAME_RE = re.compile(r"^(?=.{1,64}$)(?:" + "|".join(PREFIXES) + r")-[a-z0-9]+(?:-[a-z0-9]+)*$")
AGENT_RE = re.compile(r"^(?=.{1,64}$)(?:" + "|".join(FAMILIES) + r")-[a-z0-9]+(?:-[a-z0-9]+)*$")

# The closed verb list. The last segment of an action is its verb.
VERBS = {
    "create": "a finished artifact that is not language: a diagram, a map, mockups",
    "scaffold": "boilerplate meant to be filled in",
    "write": "prose, copy, code, specs: anything authored in a language",
    "audit": "an artifact against a standard or checklist",
    "review": "a change under someone's authorship, with feedback to them",
    "analyze": "data in, insight out; writes nothing back",
    "validate": "a binary verdict against rules",
    "consult": "advice in dialogue, no artifact",
    "fix": "a defect, back to intended behaviour",
    "optimize": "already correct, now better on a measured axis",
    "apply": "an existing standard, system or patch onto a target",
    "enrich": "add data to records that already exist",
    "integrate": "wire two systems together",
    "migrate": "move something between two homes",
    "read": "fetch a known artifact by identity",
    "query": "ask a datastore a question in its own language",
    "search": "find candidates by relevance",
    "explore": "open-ended, no known target",
    "ask": "natural-language question over a corpus",
    "run": "execute a defined process end to end",
    "setup": "configure one named thing, once",
    "init": "first-time scaffolding of a whole repo or workspace",
    "manage": "ongoing CRUD against an external system",
    "track": "observe over time",
    "log": "record an entry",
    "set": "write one value",
    "grant": "give access",
    "respond": "act on an incoming event",
    "cut": "produce a release",
    "squash": "collapse commits",
    "diff": "compare two states",
    "automate": "drive a UI or tool programmatically",
    "train": "fit a model",
    "transcribe": "speech to text",
    "animate": "motion",
    "design": "produce a design for something that will then be built",
}
# Words people reach for instead of an approved verb, with the verb to use. Rejected by name.
SYNONYMS = {
    "author": "write", "compose": "write", "draft": "write", "edit": "write", "define": "write",
    "generate": "create", "make": "create", "build": "create", "produce": "create",
    "fetch": "read", "get": "read", "load": "read",
    "execute": "run", "launch": "run", "start": "run",
    "check": "validate", "verify": "validate", "test": "validate",
    "evaluate": "audit", "inspect": "audit", "assess": "audit",
    "improve": "optimize", "tune": "optimize",
    "fit": "apply", "configure": "setup", "install": "setup",
}
# Knowledge skills end in a noun on purpose. Each needs a reason: "it is a noun" is not one.
NOUN_TAILS = {
    "test-e2e-policy": "E2E strategy, locator, waiting and test-integrity rules that generators and healers read; it runs nothing",
    "ux-ai-heuristics": "AI-specific usability criteria supplied to the usability auditor; it judges nothing itself",
    "product-playbook": "the index of product methods and their shared guidance; it authors nothing",
    "data-classification-metrics": "the reference for confusion matrices and classification metrics; it trains nothing",
}
# Agents are roles, so their names end in a noun. An agent name ends in one of these.
AGENT_NOUNS = {
    "auditor", "runner", "writer", "builder", "reviewer", "selector", "generator", "healer", "planner",
    "triager", "implementer", "validator", "verifier",
}
BROWSER_ADAPTER = "browser-automate"
# Names written in skills that cct does not carry, each with its reason.
EXTERNAL = {
    "c4-context": "optional agent of the c4-architecture plugin, not part of cct",
    "c4-container": "optional agent of the c4-architecture plugin, not part of cct",
    "c4-component": "optional agent of the c4-architecture plugin, not part of cct",
    "c4-code": "optional agent of the c4-architecture plugin, not part of cct",
    "differential-review": "a third-party Trail of Bits skill named as a method, not a cct dependency",
    "design-review": "gstack's skill, cited as a source in a bibliography",
    "test-set": "a test-set bisection technique, not a skill",
}
TEXT_SUFFIX = {".py", ".sh", ".js", ".mjs", ".ts", ".json", ".yml", ".yaml", ".toml", ".md", ".txt", ".html", ".cmd", ".cjs", ""}
# A skill or agent word near a bare name marks it as a reference rather than plain English
CONTEXT = re.compile(r"\b(skill|agent|subagent|subagent_type|dispatch|cct:|command|/)\b|/", re.I)

# ── The plugin's classes, read from its folder names ────────────────────────
def classes(out: Path) -> dict[str, str]:
    """Skill name -> class: R role-, K listed in NOUN_TAILS, A everything else."""
    return {d.name: "R" if d.name.startswith("role-") else "K" if d.name in NOUN_TAILS else "A"
            for d in sorted((out / "skills").iterdir()) if d.is_dir()}


# ── Frontmatter ──────────────────────────────────────────────────────────────
FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def parse(text: str) -> tuple[dict, str]:
    m = FM.match(text)
    if not m:
        return {}, text
    return (yaml.safe_load(m.group(1)) or {}), text[m.end():]


# ── The checks ───────────────────────────────────────────────────────────────
def triggers(description: str) -> set[str]:
    """Quoted phrases in a description are its trigger phrases."""
    out = set()
    for m in re.findall(r"\"([^\"]{3,70})\"|'([^']{3,70})'", description):
        p = (m[0] or m[1]).strip().lower().rstrip(".,;")
        if re.search(r"[`*=:/<>(){}\[\]]|^-", p):
            continue
        out.add(re.sub(r"\s+", " ", p))
    return out


def _tail_problem(name: str, cls: str, errors: list[str]):
    parts = name.split("-")
    tail = parts[-1]
    if name.startswith("role-"):
        if cls != "R":
            errors.append(f"{name}: role- prefix on a {cls} skill")
        return
    if cls == "R":
        errors.append(f"{name}: class R must start with role-")
    if name in NOUN_TAILS:
        if cls != "K":
            errors.append(f"{name}: listed in NOUN_TAILS but classed {cls}")
        return
    if cls == "K":
        errors.append(f"{name}: knowledge skill needs a NOUN_TAILS entry with its reason")
        return
    if parts[0] in VENDORS:
        if len(parts) != 2 or tail not in VERBS:
            errors.append(f"{name}: a vendor adapter is exactly <vendor>-<approved verb>")
        return
    if name == BROWSER_ADAPTER:
        return
    if tail in SYNONYMS:
        errors.append(f"{name}: '{tail}' is a synonym; use '{SYNONYMS[tail]}'")
    elif tail not in VERBS:
        errors.append(f"{name}: '{tail}' is not an approved verb (add it to VERBS with its distinction, or to NOUN_TAILS with a reason)")
    if cls == "P" and tail != "run":
        errors.append(f"{name}: a process ends in run")


def check_names(skill_names: dict[str, str], agent_names: set[str]) -> list[str]:
    """Pure name rules. skill_names maps a name to its class."""
    e: list[str] = []
    for n, cls in sorted(skill_names.items()):
        if not NAME_RE.match(n):
            e.append(f"{n}: does not match the name pattern (family or vendor prefix, kebab-case, <= 64 characters)")
        p = n.split("-")
        if len(p) != len(set(p)):
            e.append(f"{n}: repeats a word")
        _tail_problem(n, cls, e)
    for n in sorted(agent_names):
        if not AGENT_RE.match(n):
            e.append(f"agent {n}: must start with a discipline family ({', '.join(FAMILIES)})")
        p = n.split("-")
        if len(p) != len(set(p)):
            e.append(f"agent {n}: repeats a word")
        if p[-1] not in AGENT_NOUNS:
            e.append(f"agent {n}: '{p[-1]}' is not a registered agent noun (AGENT_NOUNS)")
    for n in sorted(set(skill_names) & agent_names):
        e.append(f"{n}: is both a skill and an agent")
    for n in sorted(set(NOUN_TAILS) - set(skill_names)):
        e.append(f"{n}: in NOUN_TAILS but no such skill exists; remove the entry")
    return e


def check_plugin(out: Path, external: dict[str, str] = EXTERNAL) -> list[str]:
    """Every rule that needs the built files. `external` are names cct does not carry, each with its reason."""
    e: list[str] = []
    skills = {d.name: d for d in (out / "skills").iterdir() if d.is_dir()}
    agents = {f.stem: f for f in (out / "agents").glob("*.md")}
    cls = classes(out)
    e += check_names(cls, set(agents))
    descs: dict[str, str] = {}
    trig: dict[str, list[str]] = {}
    for n, d in sorted(skills.items()):
        md = d / "SKILL.md"
        if not md.exists():
            e.append(f"{n}: no SKILL.md")
            continue
        try:
            fm, _ = parse(md.read_text())
        except yaml.YAMLError as x:
            e.append(f"{n}: frontmatter is not valid YAML ({x})")
            continue
        if fm.get("name") != n:
            e.append(f"{n}: folder and frontmatter name differ ({fm.get('name')!r})")
        ui = fm.get("user_invocable")
        if not isinstance(ui, bool):
            e.append(f"{n}: user_invocable must be an explicit boolean, got {ui!r}")
        elif ui == n.startswith("role-"):
            e.append(f"{n}: user_invocable must be {str(not n.startswith('role-')).lower()} ({'role-' if n.startswith('role-') else 'non-role'} skill)")
        desc = str(fm.get("description", "")).strip()
        descs[n] = desc
        if not desc:
            e.append(f"{n}: no description")
        elif len(desc) > 1024:
            e.append(f"{n}: description is {len(desc)} characters, the limit is 1024")
        for t in triggers(desc):
            trig.setdefault(t, []).append(n)
    for n, f in sorted(agents.items()):
        fm, _ = parse(f.read_text())
        if fm.get("name") != n:
            e.append(f"agent {n}: file and frontmatter name differ ({fm.get('name')!r})")
    for t, ns in sorted(trig.items()):
        if len(ns) > 1:
            e.append(f"trigger phrase {t!r} is in the descriptions of {', '.join(sorted(ns))}")
    e += check_references(out, set(skills), set(agents), external)
    return e


FAMILY_SLUG = re.compile(r"(?<![\w/:.@$-])`((?:" + "|".join(PREFIXES) + r")-[a-z0-9]+(?:-[a-z0-9]+)*)`")


def check_references(out: Path, skills: set[str], agents: set[str], external: dict[str, str]) -> list[str]:
    e: list[str] = []
    have = skills | agents
    skip = {"licenses"}
    for f in sorted(out.rglob("*")):
        if not f.is_file() or f.is_symlink() or skip & set(f.parts) or f.suffix not in TEXT_SUFFIX:
            continue
        try:
            t = f.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        rel = f.relative_to(out).as_posix()
        if rel.startswith(("blueprint/", "examples/")):
            continue
        for m in re.finditer(r"(?<![\w-])cct:([a-z0-9][a-z0-9-]*)", t):
            n = m.group(1)
            if n not in have and n not in external:
                e.append(f"{rel}: cct:{n} does not resolve")
        for m in re.finditer(r"\$\{CLAUDE_PLUGIN_ROOT\}/(skills/[\w./-]*[\w-]\.(?:sh|py|md|json|ts|js|mjs))", t):
            if not (out / m.group(1)).exists():
                e.append(f"{rel}: {m.group(1)} does not exist")
        for m in re.finditer(r"\$\{CLAUDE_SKILL_DIR\}/(\.\./[\w./-]*[\w-]\.(?:sh|py|md|json|ts|js|mjs))", t):
            base = out / "skills" / "_loader"  # shared files are read by whichever skill loads them
            if rel.startswith("skills/"):
                base = out / "skills" / rel.split("/")[1]
            if not (base / m.group(1)).resolve().exists():
                e.append(f"{rel}: {m.group(1)} does not exist")
        for m in re.finditer(r"(?:skills/|\.\./)([a-z0-9][a-z0-9-]*)/", t):
            n = m.group(1)
            if "-" in n and n.split("-")[-1] in VERBS and n not in have and n not in external:
                if (f.parent / m.group(0)).exists() or (out / "skills" / n).exists():
                    continue
                e.append(f"{rel}: path segment {m.group(0)} does not resolve")
        for m in re.finditer(r"(?m)^\s+-\s+(?:cct:)?([a-z0-9][a-z0-9-]*)\s*$", t):
            if f.suffix == ".md" and rel.startswith("agents/") and t.startswith("---") and "skills:" in t.split("\n---", 1)[0]:
                n = m.group(1)
                if n not in have and n not in external:
                    e.append(f"{rel}: preloads {n}, which does not resolve")
        for m in FAMILY_SLUG.finditer(t):
            n = m.group(1)
            if n.split("-")[-1] not in VERBS or n.startswith(("re-", "self-")):
                continue
            if n not in have and n not in external:
                e.append(f"{rel}: `{n}` looks like a skill name and does not resolve (carry it, or declare it in NOT_CARRIED with a reason)")
    return e