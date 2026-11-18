#!/usr/bin/env bash
# PreToolUse hook on Bash: one PR per milestone, one push per milestone close.
#
# "Records and fixes ride along" was a sentence until 2026-11-01, and one change still opened
# 30 interior PRs: records/*, fix/*, chore/merge-main-into-*, each a full CI run. This hook
# refuses them before they cost anything:
#
#   gh pr create
#     head milestone/*        -> base is project/* or the default branch, and the head carries
#                                `VERIFY PASS milestone <id> <sha>` with <sha> = the head
#     head project/*          -> base is the default branch (Stage 6p)
#     head hotfix/*           -> base is the default branch (sdlc.json hotfix)
#     base project/*          -> refused for any other head: commit it on the open milestone
#     base milestone/*        -> refused unless sdlc.json delivery is "feature-prs"
#     anything else           -> refused inside an active /goal; outside one it is the
#                                engineer's own ask and passes
#   git push
#     milestone/*             -> only a commit that carries `VERIFY PASS milestone`
#                                (feature-prs: also its sync, since feature PRs merge into it)
#     project/*               -> only its creation from origin/<default>; after that it moves
#                                through milestone PRs alone
#     the default branch      -> never
#     anything else           -> refused inside an active /goal (feature-prs: allowed)
#
# sdlc.json `milestones.merge: "local"` (default "pr", which changes nothing above) keeps milestones
# and the project branch on this machine; only the PR into the default branch goes online:
#   git push milestone/*    -> refused when its change has a project branch (merge it locally)
#   gh pr create            -> refused for head milestone/* into base project/*
#   git push project/*      -> only a head that carries `VERIFY PASS project` (verify_gate.py project)
#   git merge (on project/*) -> refused for a milestone/* ref without `VERIFY PASS milestone`
#
# An exception exists only in the engineer's words: decisions.json
# `prExceptions: [{"branch": "<head>", "words": "<what the engineer said>"}]`.
# Tags and branch deletions pass. A repo without sdlc.json gets no opinion.
set -uo pipefail
. "$(dirname "$0")/sdlc-config.sh"

payload=$(cat)
[ -f "$SDLC_JSON" ] || exit 0
case "$payload" in *push*|*"pr create"*|*merge*) ;; *) exit 0 ;; esac

PAYLOAD="$payload" SDLC_HOOK_DIR="$(cd "$(dirname "$0")" && pwd)" python3 - "$SDLC_ROOT" "$SDLC_JSON" <<'PY'
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
cfg = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
payload = json.loads(os.environ["PAYLOAD"])
cmd = (payload.get("tool_input") or {}).get("command") or ""
cwd = Path(payload.get("cwd") or root)
transcript = payload.get("transcript_path") or ""
docs = cfg.get("docs", "docs/sdlc.md")
WRAPPERS = {"rtk", "command", "env", "time", "nohup", "proxy"}


GOAL_SOURCE = f"the transcript's goal entry in {transcript}"
GOAL_ACTION = "type `/goal clear` (only the owner can)"


def helper(name: str):
    """A sibling helper by its exact path: never found on sys.path, where the working directory
    could shadow it. Raises when it is missing or broken."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, os.path.join(os.environ["SDLC_HOOK_DIR"], f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def block(why: str, route: str, source: str = "sdlc.json", action: str = "") -> None:
    """Block. `source` is what the gate read, `action` what the owner does (default: the route);
    a repeat of the same block says both (block_state.py), and without it the text is plain."""
    text = f"BLOCKED: {why}\n{route}\n({docs}, \"One milestone, one PR\")"
    try:
        text = helper("block_state").rewrite("pr-gate.sh", text, source, action or route, payload)
    except Exception:  # block state never changes the verdict
        pass
    print(text, file=sys.stderr)
    sys.exit(2)


def git(where: Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(where), *args], capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else ""


def goal_active() -> bool:
    """The goal reading is goal_active.py's; an unreadable transcript reads as no goal."""
    try:
        read = helper("goal_active").goal_active
    except Exception:  # missing, or any error while importing it: a gate that cannot read the goal blocks
        block(
            "goal_active.py is missing or broken beside pr-gate.sh.", "Run `sdlc-run adopt` to restore it.",
            source="goal_active.py beside pr-gate.sh",
        )
    return bool(read(transcript))


class Repo:
    """The repo a command acts on: its own sdlc.json when it has one, else the session's."""

    def __init__(self, where: Path) -> None:
        self.dir = where
        top = git(where, "rev-parse", "--show-toplevel")
        self.top = Path(top) if top else where
        own = self.top / "sdlc.json"
        self.cfg = json.loads(own.read_text(encoding="utf-8")) if own.exists() else cfg
        self.default = self.cfg.get("defaultBranch") or "main"
        self.m = (self.cfg.get("milestones") or {}).get("branchPrefix", "milestone/")
        self.p = (self.cfg.get("projects") or {}).get("branchPrefix", "project/")
        self.feature_prs = self.cfg.get("delivery") == "feature-prs"
        self.local = (self.cfg.get("milestones") or {}).get("merge") == "local"
        self.hotfix = bool(self.cfg.get("hotfix", True))
        self.changes = self.top / self.cfg.get("changesDir", "changes")

    def in_session(self) -> bool:
        """The goal binds the session's start repo, and any worktree of it; another repo is its own."""
        mine, start = (
            git(w, "rev-parse", "--path-format=absolute", "--git-common-dir") for w in (self.dir, root)
        )
        return not (mine and start) or Path(mine).resolve() == Path(start).resolve()

    def branch(self) -> str:
        return git(self.dir, "rev-parse", "--abbrev-ref", "HEAD")

    def sha(self, ref: str) -> str:
        return git(self.dir, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")

    def reports(self, scope: str, slug: str) -> list[Path]:
        if scope == "project":  # verify_gate.py project: one record in the common git dir
            common = git(self.dir, "rev-parse", "--path-format=absolute", "--git-common-dir")
            return [Path(common) / "sdlc" / "projects" / slug / "verify" / "report.json"] if common else []
        dirs = [self.changes]
        if self.local:  # the gate ran in the milestone's worktree, the merge runs in another
            rel = self.changes.relative_to(self.top)
            listing = git(self.dir, "worktree", "list", "--porcelain")
            dirs = [Path(t) / rel for t in re.findall(r"^worktree (.+)$", listing, re.M)] or dirs
        found: list[Path] = []
        for changes in dirs:
            # archive/ too: the Stage 7 archive move is the last commit before the push (3.7.0)
            found += [*changes.glob("*/verify/report.json"), *changes.glob("archive/**/verify/report.json")]
        return found

    def passed(self, sha: str, scope: str = "milestone", slug: str = "") -> bool:
        """A PASS of this scope on this commit, or on an ancestor that only records followed:
        writing the gate line into milestone.md must not need a second full gate."""
        if not sha:
            return False
        rel = self.changes.relative_to(self.top).as_posix() + "/"
        for report in self.reports(scope, slug):
            try:
                data = json.loads(report.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            gated = data.get("sha") or ""
            if not gated or not str(data.get("result", "")).startswith(f"VERIFY PASS {scope}"):
                continue
            if gated == sha:
                return True
            ancestor = subprocess.run(
                ["git", "-C", str(self.dir), "merge-base", "--is-ancestor", gated, sha]
            ).returncode == 0
            changed = git(self.dir, "diff", "--name-only", gated, sha).splitlines()
            if ancestor and all(p.startswith(rel) for p in changed):
                return True
        return False

    def project_of(self, milestone: str) -> str:
        """The project/<slug> a milestone branch merges into: "" when its change has no project
        branch. The branch is milestone/<slug> or milestone/<slug>-<n>."""
        name = milestone.removeprefix(self.m)
        for path in self.changes.glob("*/decisions.json"):
            try:
                found = json.loads(path.read_text(encoding="utf-8"))
                slug, project = (found.get("milestone") or {}).get("slug"), found.get("project")
            except (OSError, ValueError, AttributeError):
                continue
            if slug and re.fullmatch(re.escape(slug) + r"(-\d+)?", name):
                if isinstance(project, dict) and project.get("slug") and project.get("branch", True):
                    return f"{self.p}{project['slug']}"
        return ""

    def excepted(self, branch: str) -> bool:
        # the pushed repo's own exceptions, and the session's: the engineer speaks in the session
        start = root / cfg.get("changesDir", "changes")
        for path in [*self.changes.glob("*/decisions.json"), *start.glob("*/decisions.json")]:
            try:
                rows = json.loads(path.read_text(encoding="utf-8")).get("prExceptions") or []
            except (OSError, ValueError, AttributeError):
                continue
            if any(
                isinstance(r, dict) and r.get("branch") == branch
                and isinstance(r.get("words"), str) and r["words"].strip()
                for r in rows
            ):
                return True
        return False


CLOSE = (
    "Run `python3 scripts/verify_gate.py milestone <id>` on this exact head first (it also "
    "checks the parent is merged in). One push and one PR per milestone close."
)
RIDE = (
    "Commit it on the open milestone branch; it ships in that milestone's PR. With no milestone "
    "open in that repo, it goes into the next one. A merge from the default branch is a local "
    "`git merge origin/<parent>` on the next milestone branch, never a PR."
)


def local_merge_route(project: str, milestone: str) -> str:
    return (
        "Local milestones (sdlc.json milestones.merge): a milestone merges on this machine, after "
        f"`VERIFY PASS milestone` on its head: `git switch {project} && git merge --no-ff {milestone}`. "
        "Only the PR into the default branch goes online."
    )


def check_push(repo: Repo, args: list[str]) -> None:
    positional, delete, tags = [], False, False
    takes_value = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}
    i = 0
    while i < len(args):
        a = args[i]
        if a in takes_value:
            i += 2
            continue
        if a in ("-d", "--delete"):
            delete = True
        elif a in ("--tags", "--follow-tags"):
            tags = True
        elif not a.startswith("-"):
            positional.append(a)
        i += 1
    if delete:
        return
    refspecs = positional[1:]
    if not refspecs:
        if tags and positional:
            return
        refspecs = ["HEAD"]
    for spec in refspecs:
        spec = spec.lstrip("+")
        src, _, dst = spec.partition(":")
        if not src or src.startswith("refs/tags/"):
            continue  # `:branch` deletes; tags are not branches
        dst = dst or (repo.branch() if src == "HEAD" else src)
        dst = dst.removeprefix("refs/heads/")
        if dst.startswith("refs/tags/"):
            continue
        sha = repo.sha(src)
        if repo.excepted(dst):
            continue
        if dst == repo.default:
            block(f"a push to {dst}.", "The default branch moves only through a merged PR.")
        if dst.startswith(repo.m):
            if repo.local and (project := repo.project_of(dst)):
                block(f"a push of {dst} in local milestones mode.", local_merge_route(project, dst))
            if not repo.feature_prs and not repo.passed(sha):
                block(f"a push of {dst} at {sha[:12] or src} without a passing milestone gate.", CLOSE, "verify/report.json")
            continue
        if dst.startswith(repo.p):
            if repo.local:  # one push, at the project close, of a head that passed the project gate
                if not repo.passed(sha, "project", dst.removeprefix(repo.p)):
                    block(
                        f"a push of {dst} at {sha[:12] or src} without `VERIFY PASS project`.",
                        f"Local milestones: run `python3 scripts/verify_gate.py project {dst.removeprefix(repo.p)}` "
                        f"on {dst} merged with origin/{repo.default}, then push it once (Stage 6p).",
                    )
                continue
            if sha and sha == repo.sha(f"origin/{repo.default}"):
                continue  # creating the project branch from the trunk (Stage 1.2)
            block(f"a push to {dst}.", "A project branch moves only through milestone PRs. " + RIDE)
        if repo.feature_prs:
            continue
        if repo.in_session() and goal_active():
            block(f"a push of {dst} inside a /goal run.", RIDE, GOAL_SOURCE, GOAL_ACTION)


def check_pr(repo: Repo, args: list[str]) -> None:
    opts: dict[str, str] = {}
    names = {"-B": "base", "--base": "base", "-H": "head", "--head": "head", "-R": "repo", "--repo": "repo"}
    i = 0
    while i < len(args):
        a = args[i]
        key, _, inline = a.partition("=")
        if key in names:
            if inline:
                opts[names[key]] = inline
            elif i + 1 < len(args):
                opts[names[key]] = args[i + 1]
                i += 1
        i += 1
    head = opts.get("head", "").split(":")[-1] or repo.branch()
    base = opts.get("base") or repo.default
    if repo.excepted(head):
        return
    if head.startswith(repo.m):
        if repo.local and base.startswith(repo.p):
            block(f"a PR from {head} into {base} in local milestones mode.", local_merge_route(base, head))
        if not (base.startswith(repo.p) or base == repo.default):
            block(f"a PR from {head} into {base}.", "A milestone PR goes into its parent: project/* or the default branch.")
        sha = repo.sha(head) if "repo" not in opts else ""
        if sha and not repo.passed(sha):
            block(f"a PR from {head} at {sha[:12]} without a passing milestone gate.", CLOSE, "verify/report.json")
        return
    if head.startswith(repo.p):
        if base != repo.default:
            block(f"a PR from {head} into {base}.", "A project PR goes into the default branch (Stage 6p).")
        return
    if repo.hotfix and head.startswith("hotfix/") and base == repo.default:
        return
    if base.startswith(repo.m):
        if repo.feature_prs:
            return
        block(f"a PR from {head} into {base}.", RIDE)
    if base.startswith(repo.p):
        block(f"a PR from {head} into {base}: only milestone branches merge into a project.", RIDE)
    if repo.in_session() and goal_active():
        block(f"a PR from {head} inside a /goal run: only milestone and project PRs open there.", RIDE, GOAL_SOURCE, GOAL_ACTION)


def switched_to(args: list[str]) -> str:
    """The branch a `git switch|checkout` argument list moves to; "" for `--` paths and none."""
    if "--" in args:
        return ""
    creates = {"-c", "-C", "--create", "--force-create", "-b", "-B"}
    for i, a in enumerate(args):
        if a in creates and i + 1 < len(args):
            return args[i + 1]
        if not a.startswith("-"):
            return a
    return ""


def check_merge(repo: Repo, args: list[str], current: str = "") -> None:
    """Local mode: on project/*, a milestone/* ref merges only with `VERIFY PASS milestone` on it.
    `current` is the branch an earlier `git switch|checkout` of the same command moved to."""
    real = repo.branch()
    current = current or real
    # Either branch gates: a failed or misread switch can only make the check stricter.
    if not (repo.local and (current.startswith(repo.p) or real.startswith(repo.p))):
        return
    takes_value = {"-m", "--message", "-F", "--file", "-s", "--strategy", "-X", "--strategy-option"}
    i = 0
    while i < len(args):
        a = args[i]
        if a in takes_value:
            i += 2
            continue
        ref = a.removeprefix("refs/heads/")
        if not a.startswith("-") and ref.startswith(repo.m):
            sha = repo.sha(ref)
            if not repo.passed(sha):
                block(f"a merge of {ref} into {current} without a passing milestone gate.", CLOSE, "verify/report.json")
            into = current if current.startswith(repo.p) else real
            parent = repo.project_of(ref)
            if parent and parent != into:
                block(f"a merge of {ref} into {into}: it belongs to {parent}.", local_merge_route(parent, ref))
            tip = repo.sha(into)
            if tip and subprocess.run(["git", "-C", str(repo.dir), "merge-base", "--is-ancestor", tip, sha]).returncode:
                block(
                    f"a merge of {ref} into {into} on a gate that ran against an older {into}.",
                    f"`git merge {into}` on {ref}, then run `python3 scripts/verify_gate.py milestone <id>` again.",
                    "verify/report.json",
                )
        i += 1


def segments(text: str) -> list[list[str]]:
    lex = shlex.shlex(text, posix=True, punctuation_chars=";&|")
    lex.whitespace_split = True
    out: list[list[str]] = [[]]
    target = False  # the token after a bare `>` or `2>>` is a file, not an argument
    toks = list(lex)
    for i, tok in enumerate(toks):
        if tok == "&" and (target or toks[i + 1 : i + 2] and toks[i + 1].startswith(">")):
            continue  # `2>&1` and `&>file`: the lexer split a redirect at the `&`
        if tok and set(tok) <= set(";&|"):
            out.append([])
        elif target:
            target = False
        elif m := re.fullmatch(r"\d*>>?(.*)", tok):
            target = not m.group(1)
        else:
            out[-1].append(tok)
    return [s for s in out if s]


try:
    parts = segments(cmd.replace("\n", " ; "))
except ValueError:
    # Unbalanced quotes, usually a heredoc body: refuse only a real push or PR at a line start.
    if re.search(r"(^|[;&|]\s*)(rtk\s+)?(git(\s+-C\s+\S+)?\s+push|gh\s+pr\s+create)\b", cmd, re.M):
        block("a command the PR gate cannot parse.", "Write the PR body to a file and pass --body-file; keep the push on its own line.")
    sys.exit(0)

where = cwd
moved = ""  # branch an earlier `git switch|checkout` in this command moves to
for seg in parts:
    while seg and ("=" in seg[0] and not seg[0].startswith("-") or seg[0] in WRAPPERS):
        seg = seg[1:]
    if not seg:
        continue
    if seg[0] == "cd" and len(seg) > 1:
        where = (where / os.path.expanduser(seg[1])).resolve()
        continue
    if seg[0] == "git":
        rest, here = seg[1:], where
        while rest and rest[0] in ("-C", "-c"):
            if rest[0] == "-C" and len(rest) > 1:
                here = (here / os.path.expanduser(rest[1])).resolve()
            rest = rest[2:]
        if rest and rest[0] == "push":
            check_push(Repo(here), rest[1:])
        elif rest and rest[0] in ("switch", "checkout"):
            moved = switched_to(rest[1:])
        elif rest and rest[0] == "merge":
            check_merge(Repo(here), rest[1:], moved)
    elif seg[0] == "gh" and seg[1:3] == ["pr", "create"]:
        check_pr(Repo(where), seg[3:])
sys.exit(0)
PY
