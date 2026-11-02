"""Builds the cct plugin (Calvin's Claude Tools): copies every skill, agent, command and hook it needs into one
self-contained plugin, renames on collision, and rewrites `plugin:name` references to `cct:<new>`, then keeps only what sdlc-run reaches."""
import json, os, re, shutil, subprocess, sys
from pathlib import Path

import tempfile

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "plugins/cct"
TMP = Path(tempfile.mkdtemp())
# The OMR AI Kit at its latest master, not whatever the local checkout has
KIT_REPO = Path.home() / "projects/omr/omr-ai-kit"
subprocess.run(["git", "-C", str(KIT_REPO), "fetch", "-q", "origin"], check=True)
subprocess.run(f"git -C {KIT_REPO} archive origin/master plugins | tar -x -C {TMP}", shell=True, check=True)
KIT = TMP / "plugins"
C = Path.home() / ".claude/plugins/cache"
HOME = Path.home()
HD = HOME / "projects/heydiff"
SNAP = HOME / "projects/ai-feedback-editor"  # Snapmark, cdudek/snapmark-mac: its own product, not HeyDiff
P = "cct"

shutil.rmtree(OUT, ignore_errors=True)
OUT.mkdir(parents=True)

# (origin, kind, name) -> new name; first come keeps the plain name
names = {}
taken = {"skill": set(), "agent": set(), "command": set()}
renames = []


def claim(origin, kind, name, want=None):
    new = want or name
    if new in taken[kind]:
        new = f"{origin}-{name}"
        renames.append(f"{kind} {origin}:{name} -> {new}")
    assert new not in taken[kind], (kind, new)
    taken[kind].add(new)
    names[(origin, kind, name)] = new
    return new


def copy_skill(origin, src, want=None):
    src = Path(src)
    new = claim(origin, "skill", src.name, want)
    shutil.copytree(src, OUT / "skills" / new, symlinks=False, dirs_exist_ok=False)
    md = OUT / "skills" / new / "SKILL.md"
    if md.exists() and new != src.name:
        t = md.read_text()
        md.write_text(re.sub(r"^name:\s*.*$", f"name: {new}", t, count=1, flags=re.M))


def copy_agent(origin, src):
    src = Path(src)
    new = claim(origin, "agent", src.stem)
    (OUT / "agents").mkdir(exist_ok=True)
    t = src.read_text()
    if new != src.stem:
        t = re.sub(r"^name:\s*.*$", f"name: {new}", t, count=1, flags=re.M)
    (OUT / "agents" / f"{new}.md").write_text(t)


def copy_command(origin, src):
    src = Path(src)
    new = claim(origin, "command", src.stem)
    (OUT / "commands").mkdir(exist_ok=True)
    shutil.copy2(src, OUT / "commands" / f"{new}{src.suffix}")


def dirs(p):
    p = Path(p)
    return sorted(d for d in p.iterdir() if d.is_dir() and not d.name.startswith(".")) if p.exists() else []


def files(p, ext=".md"):
    p = Path(p)
    return sorted(f for f in p.iterdir() if f.is_file() and f.suffix == ext) if p.exists() else []


licenses = OUT / "licenses"


def keep_license(origin, root):
    for f in ("LICENSE", "LICENSE.md", "LICENSE.txt"):
        if (Path(root) / f).exists():
            (licenses / origin).mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(root) / f, licenses / origin / f)


# ── OMR AI Kit: the SDLC itself ──────────────────────────────────────────────
# OMR-internal systems (Toggl, Billwerk, OMR's secret registry, OMR's warehouse, Jev, reviews-agents traces)
OMR_ONLY = {"time-log", "secret-set", "engineering-metrics-track", "jev-integrate", "billing-manage", "langsmith-analyze"}
for d in dirs(KIT / "omr-dev/skills"):
    if d.name not in OMR_ONLY:
        copy_skill("omr-dev", d)
for d in dirs(KIT / "omr-ux/skills"):
    copy_skill("omr-ux", d, "ux-" + d.name)
# Product: the whole of omr-pm. Every skill is a job Calvin does on his own products; none touches an OMR system
PM = [d.name for d in dirs(KIT / "omr-pm/skills")]
for n in PM:
    copy_skill("omr-pm", KIT / "omr-pm/skills" / n)
# Data: the method half of omr-data. The warehouse half (query-run, ask, dbt, Airflow, the semantic layer) is OMR's
# BigQuery. chart-create and report-create (and omr-core's pdf-create and presentation-create) ship OMR Sans and the
# OMR logo as files: they come in once a style layer reads the product's tokens.json instead.
DATA = ["analyze", "model-train", "network-analyze"]
for n in DATA:
    copy_skill("omr-data", KIT / "omr-data/skills" / n)
CORE = ["transcripts-fix"]
for n in ("brand", "tone-of-voice", "copy-write", *CORE):
    copy_skill("omr-core", KIT / "omr-core/skills" / n)
for f in files(KIT / "omr-dev/agents"):
    copy_agent("omr-dev", f)
for f in files(KIT / "omr-ux/agents"):
    copy_agent("omr-ux", f)
shutil.copytree(KIT / "omr-dev/references", OUT / "references")
shutil.copytree(KIT / "omr-ux/references", OUT / "references", dirs_exist_ok=True)
shutil.copytree(KIT / "omr-dev/hooks", OUT / "hooks")
(OUT / "docs").mkdir()
shutil.copy2(KIT / "omr-dev/skills/CLAUDE.md", OUT / "docs/omr-dev-guide.md")

# ── Public plugins ───────────────────────────────────────────────────────────
SP = C / "claude-plugins-official/superpowers/7.0.0"
for d in dirs(SP / "skills"):
    copy_skill("superpowers", d)
for f in files(SP / "agents"):
    copy_agent("superpowers", f)
for f in files(SP / "commands"):
    copy_command("superpowers", f)
shutil.copytree(SP / "hooks", OUT / "hooks/superpowers")
keep_license("superpowers", SP)

PT = C / "ponytail/ponytail/5.3.3"
for d in dirs(PT / "skills"):
    copy_skill("ponytail", d)
keep_license("ponytail", PT)

for d in sorted((HOME / ".claude/skills").glob("plannotator-*")):
    copy_skill("plannotator", d.resolve())

for origin, path in [
    ("pr-review-toolkit", "claude-plugins-official/pr-review-toolkit/1.0.1"),
    ("code-review", "claude-plugins-official/code-review/1.0.1"),
    ("feature-dev", "claude-plugins-official/feature-dev/1.0.1"),
    ("code-simplifier", "claude-plugins-official/code-simplifier/1.0.0"),
    ("frontend-design", "claude-plugins-official/frontend-design/1.1.1"),
    ("impeccable", "impeccable/impeccable/4.8.0"),
    ("show-me", "show-me/show-me/1.1.0"),
    ("calvin", "calvin-kit/calvin/0.1.0"),
]:
    root = C / path
    for d in dirs(root / "skills"):
        copy_skill(origin, d)
    for f in files(root / "agents"):
        copy_agent(origin, f)
    for f in files(root / "commands"):
        copy_command(origin, f)
    keep_license(origin, root)

SG = C / "claude-plugins-official/security-guidance/2.0.17"
shutil.copytree(SG / "hooks", OUT / "hooks/security-guidance", ignore=shutil.ignore_patterns("__pycache__"))
keep_license("security-guidance", SG)
shutil.copy2(C / "claude-plugins-official/playwright/a7ba5b93db0c/.mcp.json", OUT / ".mcp.json")

UX = C / "ui-ux-pro-max-skill/ui-ux-pro-max/2.15.0"
for d in dirs(UX / ".claude/skills"):
    copy_skill("ui-ux-pro-max", d.resolve())
keep_license("ui-ux-pro-max", UX)

for plug in sorted((C / "designer-skills").iterdir()):
    root = sorted(plug.iterdir())[-1]
    for d in dirs(root / "skills"):
        copy_skill(plug.name, d)
    for f in files(root / "commands"):
        copy_command(plug.name, f)

for n in ("ux-patterns", "sign-macos-app"):
    copy_skill("user", HOME / ".claude/skills" / n)
for n in ("ux-heuristics", "next-best-practices", "next-cache-components", "next-upgrade"):
    copy_skill("user", (HOME / ".agents/skills" / n).resolve())

# ── Hooks: one hooks.json ────────────────────────────────────────────────────
hooks = json.loads((KIT / "omr-dev/hooks/hooks.json").read_text())["hooks"]


def add(src_hooks, subdir=None):
    for ev, groups in src_hooks.items():
        for g in groups:
            for h in g["hooks"]:
                if subdir:
                    h["command"] = h["command"].replace("${CLAUDE_PLUGIN_ROOT}/hooks/", f"${{CLAUDE_PLUGIN_ROOT}}/hooks/{subdir}/")
            hooks.setdefault(ev, []).append(g)


add(json.loads((SP / "hooks/hooks.json").read_text())["hooks"], "superpowers")
add(json.loads((C / "impeccable/impeccable/4.8.0/hooks.json").read_text())["hooks"]
    if (C / "impeccable/impeccable/4.8.0/hooks.json").exists()
    else json.loads((C / "impeccable/impeccable/4.8.0/hooks/hooks.json").read_text())["hooks"])
add(json.loads((C / "plannotator/plannotator/0.28.42/hooks/hooks.json").read_text())["hooks"])
add(json.loads((SG / "hooks/hooks.json").read_text())["hooks"], "security-guidance")
for stale in ("hooks.json", "superpowers/hooks.json", "superpowers/hooks-cursor.json", "security-guidance/hooks.json"):
    (OUT / "hooks" / stale).unlink(missing_ok=True)
(OUT / "hooks/hooks.json").write_text(json.dumps({"hooks": hooks}, indent=2) + "\n")

# The user's own worktree hooks win over the kit's copy (global CLAUDE.md: settings.json's copy is the rule)
for n in ("worktree-create.sh", "worktree-remove.sh"):
    shutil.copy2(HOME / ".claude/hooks" / n, OUT / "hooks" / n)

# ── Rewrite references: plugin:name → cct:new, plugin paths → cct ──
by_origin = {}
for (origin, kind, name), new in names.items():
    by_origin.setdefault(origin, {})[name] = new
ref = re.compile(r"(?<![\w-])(" + "|".join(sorted(map(re.escape, by_origin), key=len, reverse=True)) + r"):([a-z0-9][a-z0-9-]*)")


def sub_ref(m):
    new = by_origin[m.group(1)].get(m.group(2))
    return f"{P}:{new}" if new else m.group(0)


ux_skill = re.compile(r"plugins/omr-ux/skills/([a-z0-9-]+)")
TEXT = {".md", ".sh", ".py", ".json", ".js", ".mjs", ".cjs", ".ts", ".yml", ".yaml", ".txt", ".cmd", ".toml", ".html", ""}
changed = 0
for f in OUT.rglob("*"):
    if not f.is_file() or f.is_symlink() or f.suffix not in TEXT or "licenses" in f.parts:
        continue
    try:
        t = f.read_text()
    except (UnicodeDecodeError, OSError):
        continue
    n = ref.sub(sub_ref, t)
    n = ux_skill.sub(lambda m: f"plugins/{P}/skills/ux-{m.group(1)}", n)
    n = re.sub(r"plugins/omr-(dev|ux|pm|core)/", f"plugins/{P}/", n)
    if n != t:
        f.write_text(n)
        changed += 1

print(f"skills {len(taken['skill'])}  agents {len(taken['agent'])}  commands {len(taken['command'])}  rewritten files {changed}")
print("\n".join(renames))


# ── Blueprint and examples, straight from the HeyDiff repos' main branches ─────
def git_files(repo, ref, paths, dest):
    for p in paths:
        out = subprocess.run(["git", "-C", str(repo), "ls-tree", "-r", "--name-only", ref, "--", p],
                             capture_output=True, text=True, check=True).stdout.split()
        for f in out:
            target = dest / f
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(subprocess.run(["git", "-C", str(repo), "show", f"{ref}:{f}"],
                                              capture_output=True, check=True).stdout)


BP = OUT / "blueprint"
git_files(HD / "heydiff-web", "origin/main", [
    "Dockerfile", ".dockerignore", ".github", "docs/deploy.md", "docs/sdlc.md", "Makefile", "sdlc.json",
    ".releaserc.json", ".nvmrc", "tsconfig.json", "package.json", "AGENTS.md", "CLAUDE.md", "REVIEW.md",
    "scripts/docker-smoke.sh", "scripts/image-tags.sh", "scripts/dev-db.sh", "scripts/sdlc_status.py",
    "scripts/verify_gate.py", "scripts/marks.py", "scripts/design_index.py",
], BP / "web-nextjs-cloud-run")
git_files(SNAP, "origin/main", [
    ".github", ".releaserc.json", "snapmark-app/scripts/electron-builder.sh", "snapmark-app/package.json",
    "snapmark-app/tsconfig.json", "sdlc.json",
], BP / "desktop-electron")
git_files(HD / "heydiff-chrome", "origin/main", [
    "package.json", "wxt.config.ts", "tsconfig.json", "sdlc.json", ".github", "CLAUDE.md",
], BP / "chrome-extension-wxt")
git_files(HD / "heydiff-kit", "origin/main", [
    "package.json", "packages/ui/package.json", "packages/tokens/package.json", ".github", "sdlc.json",
], BP / "design-system-kit-heroui")

EX = OUT / "examples/heydiff"
git_files(HD / "heydiff-context", "origin/main", [
    "CLAUDE.md", "design-system.md", "audience", "strategy/roadmap.md",
    "brand/v4/README.md", "brand/v4/heydiff-brand-guide-v4/README.md", "brand/v4/heydiff-brand-guide-v4/brand-guide.md",
    "brand/v4/heydiff-brand-guide-v4/decisions.md", "brand/v4/heydiff-brand-guide-v4/implementation-brief.md",
    "brand/v4/heydiff-brand-guide-v4/llms.txt", "brand/v4/heydiff-brand-guide-v4/manifest.json",
    "brand/v4/heydiff-brand-guide-v4/tokens",
], EX / "context")
git_files(HD / "heydiff-web", "origin/main", ["docs/ux"], EX / "web")
git_files(SNAP, "origin/main", [
    "docs/ux/setup.md", "docs/ux/interaction-guidelines.md", "docs/ux/glossary-proposal.md", "docs/ux/owner-words.md",
    "docs/ux/sitemap.md", "docs/ux/decisions.md", ".impeccable/config.json",
], OUT / "examples/snapmark")
shutil.copy2(HOME / "Downloads/HeyDiff Brand Guide-selection.pdf", EX / "heydiff-brand-guide-selection.pdf")
print("blueprint + examples copied")


# Calvin's changes to the kit's SDLC. Each old text must still be there, so a kit rewording fails the build.
SEC = "when auth, money or consent is touched"
PATCHES = [
    # security-review runs once, at the very end of a goal or project, never per milestone
    ("skills/sdlc-run/SKILL.md",
     f"the `verifier` and `ac-auditor` agents for jobs and facts, `security-review` {SEC}. One findings list",
     f"the `verifier` and `ac-auditor` agents for jobs and facts. **Last milestone of the goal only:** "
     f"`security-review` on the whole goal diff {SEC} anywhere in it (in a project it waits for 6p). One findings list"),
    ("skills/sdlc-run/SKILL.md",
     "re-run `checks.milestone` on the whole project diff",
     f"re-run `checks.milestone` on the whole project diff, plus `security-review` on it {SEC}"),
    ("skills/sdlc-run/references/stages.md",
     f"`cct:verifier` and `cct:ac-auditor` agents for job\n   stories and facts, `cct:security-review` {SEC}.",
     "`cct:verifier` and `cct:ac-auditor` agents for job\n   stories and facts. `cct:security-review` runs only on the goal's last milestone, on the whole\n"
     "   goal diff (`git diff origin/<defaultBranch>...milestone/<slug>-<last>`), and only when auth, money or\n"
     "   consent is touched anywhere in it; in a project it waits for Stage 6p. Never on earlier milestones."),
    ("skills/sdlc-run/references/stages.md",
     "anything looks at the seams between them.",
     f"anything looks at the seams between them. Run `cct:security-review` on the same diff {SEC};\n"
     "   it is the project's only security review."),
]
# Agents run on the model their definition names. A general-purpose agent inherits the session's model (often
# Opus), which burned a whole milestone's tokens on 2026-10-31; the chain has to say so where it dispatches.
AGENTS_RULE = (
    "Agents: every build, fix, test, capture, restack or records agent is `cct:builder` (Sonnet); review and checks use "
    "their typed agents (`cct:code-reviewer`, `cct:verifier`, `cct:ac-auditor`, `cct:ux-reviewer`, `cct:validate-finding`). "
    "Never launch general-purpose for this work: it inherits the session's model. Any other subagent gets `model: sonnet` "
    "explicitly. The session's own model is only for the gate's visual judgement and for decisions. Dispatch builders "
    "yourself, never through a closer agent that spawns its own."
)
PATCHES.append(("skills/sdlc-run/SKILL.md",
                "Every step, input, output, skip and failure mode: `references/stages.md`.",
                f"## Agents and models\n\n{AGENTS_RULE}\n\nEvery step, input, output, skip and failure mode: `references/stages.md`."))
# Ship/Show/Ask is still asked on every adopt, but cct recommends and defaults to no: one owner.
# Owner decision 2026-10-31 (kit #490): keep this even if a kit rebuild seems to make it moot.
PATCHES.append(("skills/sdlc-run/scripts/adopt.py", "TIERS_DEFAULT = True", "TIERS_DEFAULT = False"))
for goal in ("run", "milestone", "feature"):
    PATCHES.append((f"skills/sdlc-run/templates/goal/{goal}.txt", "Stop after <TURNS> turns and report.",
                    f"{AGENTS_RULE} Stop after <TURNS> turns and report."))
for rel, old, new in PATCHES:
    f = OUT / rel
    t = f.read_text()
    assert t.count(old) == 1, f"patch no longer matches {rel}: {old[:60]}"
    f.write_text(t.replace(old, new))

# Bare agent names that now resolve to omr-dev's code-reviewer point back at their own renamed agent
for cmd, agent in (("review-pr", "pr-review-toolkit-code-reviewer"), ("feature-dev", "feature-dev-code-reviewer")):
    f = OUT / "commands" / f"{cmd}.md"
    f.write_text(re.sub(r"(?<![\w:-])code-reviewer\b", agent, f.read_text()))

# ── Hand-written files, the skill map, the README ────────────────────────────
assert not (OUT / "skills/project-kickoff").exists()
shutil.copytree(REPO / "overlay", OUT, dirs_exist_ok=True)
shutil.copy2(REPO / "README.md", OUT / "README.md")
# ── Keep only what the SDLC reaches: sdlc-run and project-kickoff, followed through every reference ──
DROP = {"brand", "tone-of-voice", "vue-code-write"}  # OMR's own brand and voice; Vue is not in the stack
have_s = {d.name for d in (OUT / "skills").iterdir()}
have_a = {f.stem for f in (OUT / "agents").iterdir()}
# Every skill Calvin calls directly. The prune keeps these and everything they reach; the rest of the kit stays out,
# so a new kit skill enters cct only when one of these starts calling it or it is added here.
ROOTS = [
    "sdlc-run", "project-kickoff",
    "aws-manage", "cloudflare-manage",  # overlay skills: without a root the prune deleted them (PR #12)
    "ux-run", "ux-laws-apply",  # design: ux-run was the one omr-ux skill nothing reached
    *PM,
    # Engineering Calvin runs by hand, outside the SDLC chain. Left out on purpose: posthog-*, sentry-issues-fix (no
    # product uses PostHog or Sentry, checked 2026-11-02), payments-integrate, vectorstore-scaffold, gsap-animate,
    # scroll-animate (take when a product needs one), the AWS, Cloudflare and Fastly CDNs beyond the overlay, OMR's
    # on-call and cluster skills, and the pattern catalogues nobody asks for by name.
    "release-cut", "codex-run", "github-manage", "dependency-review", "api-design", "data-model-create",
    "docs-audit", "dockerfile-review", "queries-optimize", "tracking-apply",
    *DATA, *CORE,
]
missing = sorted(set(ROOTS) - have_s)
assert not missing, f"roots not in the build: {missing}"
keep, queue = set(), [("skill", r) for r in ROOTS]
while queue:
    kind, n = queue.pop()
    if (kind, n) in keep or n in DROP:
        continue
    keep.add((kind, n))
    paths = list((OUT / "skills" / n).rglob("*")) if kind == "skill" else [OUT / "agents" / f"{n}.md"]
    for f in paths:
        try:
            t = f.read_text()
        except (UnicodeDecodeError, OSError, IsADirectoryError):
            continue
        for m in re.findall(rf"{P}:([a-z0-9][a-z0-9-]*)", t) + re.findall(r"skills/([a-z0-9][a-z0-9-]*)/", t):
            if m in have_s:
                queue.append(("skill", m))
            elif m in have_a:
                queue.append(("agent", m))
        for a in have_a:  # agents are dispatched by their bare, hyphenated names too
            if "-" in a and re.search(rf"(?<![\w-]){re.escape(a)}(?![\w-])", t):
                queue.append(("agent", a))
for d in (OUT / "skills").iterdir():
    if ("skill", d.name) not in keep:
        shutil.rmtree(d)
for f in (OUT / "agents").iterdir():
    if ("agent", f.stem) not in keep:
        f.unlink()
shutil.rmtree(OUT / "commands")
for extra in ("hooks/superpowers", "hooks/security-guidance"):
    shutil.rmtree(OUT / extra)
(OUT / ".mcp.json").unlink()
shutil.rmtree(OUT / "references/claude-setup")  # only the dropped claude-setup skills read it
(OUT / "hooks/hooks.json").write_text((KIT / "omr-dev/hooks/hooks.json").read_text())
kept_origins = {o for (o, k, n), new in names.items() if (k, new) in keep}
for d in licenses.iterdir():
    if d.name not in kept_origins:
        shutil.rmtree(d)
names = {key: new for key, new in names.items() if (key[1], new) in keep}

# ── No call into a plugin cct does not carry ─────────────────────────────────
# The rewrite turned every carried `omr-x:name` into `cct:name`. What is left calls a skill that is not here and would
# resolve to nothing at runtime. Each one is named below with its reason and rewritten to say so; an unnamed one fails
# the build, so the decision is made here and not when a skill silently calls nothing.
NOT_CARRIED = {
    "query-run": "OMR's BigQuery", "ask": "OMR's BigQuery", "bq-access-grant": "OMR's BigQuery IAM",
    "model-scaffold": "OMR's dbt repo", "dag-scaffold": "OMR's Airflow repo", "model-diff": "OMR's dbt repo",
    "semantic-model-create": "OMR's semantic layer", "semantic-layer-audit": "OMR's semantic layer",
    "chart-create": "OMR branding baked in", "report-create": "OMR branding baked in",
    "pdf-create": "OMR branding baked in", "presentation-create": "OMR branding baked in",
    "pitch-create": "OMR branding baked in", "template-apply": "OMR templates",
    "brand": "OMR's brand", "tone-of-voice": "OMR's voice", "copy-write": "OMR's voice",
    "docs-search": "OMR's Outline", "mcp-and-artifacts": "OMR AI OS", "skill-names-fix": "OMR kit renames",
    "omr-context": "OMR's GTM knowledge", "time-log": "OMR's Toggl", "secret-set": "OMR's secret registry",
    "engineering-metrics-track": "OMR's warehouse", "jev-integrate": "OMR's Jev", "billing-manage": "OMR's Billwerk",
    "langsmith-analyze": "OMR's reviews-agents traces", "overview": "OMR AI OS",
    "posthog-*": "no product uses PostHog", "review-design": "the old name of ux-audit",
    "vue-code-write": "Vue is not in the stack",
}
PLUGINS = r"omr-(?:dev|ux|pm|core|data|content|gtm|reviews|context|ai-os|cs)"
kit_ref = re.compile(rf"`?{PLUGINS}:([a-z0-9][a-z0-9-]*\*?)`?")
kept_files = [p for d in ("skills", "agents", "references", "hooks") for p in (OUT / d).rglob("*") if p.is_file()]
unknown = {}
for f in kept_files:
    try:
        t = f.read_text()
    except (UnicodeDecodeError, OSError):
        continue
    n = re.sub(rf"{PLUGINS}:(\.\./)", r"\1", t)  # `omr-data:../model-train/...` is a sibling path, not a call
    for m in kit_ref.finditer(n):
        if m.group(1) not in NOT_CARRIED:
            unknown.setdefault(m.group(1), set()).add(str(f.relative_to(OUT)))
    n = kit_ref.sub(lambda m: f"`{m.group(1)}` (OMR AI Kit only, {NOT_CARRIED.get(m.group(1), '?')}; not in cct)", n)
    # The same for a `cct:` call whose target the prune or DROP removed
    for m in re.finditer(rf"`?{P}:([a-z0-9][a-z0-9-]*)`?", n):
        if ("skill", m.group(1)) not in keep and ("agent", m.group(1)) not in keep and m.group(1) not in NOT_CARRIED:
            unknown.setdefault(m.group(1), set()).add(str(f.relative_to(OUT)))
    n = re.sub(rf"`?{P}:([a-z0-9][a-z0-9-]*)`?",
               lambda m: m.group(0) if ("skill", m.group(1)) in keep or ("agent", m.group(1)) in keep
               else f"`{m.group(1)}` (OMR AI Kit only, {NOT_CARRIED.get(m.group(1), '?')}; not in cct)", n)
    if n != t:
        f.write_text(n)
assert not unknown, "calls into skills cct does not carry, decide each in NOT_CARRIED or ROOTS:\n" + "\n".join(
    f"  {k}: {', '.join(sorted(v))}" for k, v in sorted(unknown.items()))

# ── Mirror pairs: two copies that must stay identical from the first rule down (the kit's own check) ──
for canon, mirror in (
    ("skills/linear-manage/references/prd-template.md", "skills/develop-prd/template.md"),
    ("skills/ai-ready-issues/references/requirements-grammar.md", "skills/sdlc-run/references/requirements-grammar.md"),
):
    a, b = ((OUT / p).read_text() for p in (canon, mirror))
    assert a[a.find("\n---\n"):] == b[b.find("\n---\n"):], f"{mirror} no longer matches {canon}"


# ── Description budget: every description is read on every prompt ──
def description(md):
    fm = md.read_text().split("---", 2)[1]
    out, on = [], False
    for line in fm.splitlines():
        if line.startswith("description:"):
            on, rest = True, line[len("description:"):].strip()
            if rest not in (">-", ">", "|", "|-"):
                out.append(rest.strip("\"'"))
        elif on and line.startswith((" ", "\t")):
            out.append(line.strip())
        elif on:
            break
    return " ".join(out)


lengths = {d.name: len(description(d / "SKILL.md")) for d in (OUT / "skills").iterdir()}
over = {k: v for k, v in lengths.items() if v > 1024}
assert not over, f"descriptions over 1024 characters are dropped silently: {over}"
budget = sum(lengths.values())
renames = []
print(f"kept: {sum(k == 'skill' for k, _ in keep)} skills, {sum(k == 'agent' for k, _ in keep)} agents")

n_skills = sum(1 for d in (OUT / "skills").iterdir())
print(f"description budget: {n_skills} skills, {budget:,} characters")
rows = ["# Skill map", "", "Where every skill, agent and command in this plugin came from. Call each one as `cct:<name>`.", "",
        f"Description budget: {n_skills} skills, {budget:,} characters of descriptions, read on every prompt.", ""]
if renames:
    rows += ["Renamed because two sources used the same name:", ""] + [f"- {r}" for r in renames] + [""]
rows += ["| Name | Kind | Source |", "| --- | --- | --- |"]
for (origin, kind, name), new in sorted(names.items(), key=lambda kv: (kv[0][1], kv[1])):
    rows.append(f"| `{new}` | {kind} | {origin}:{name} |")
rows.append("| `project-kickoff` | skill | cct |")
(OUT / "docs/skill-map.md").write_text("\n".join(rows) + "\n")
shutil.rmtree(TMP)
print("overlay applied:", OUT)
