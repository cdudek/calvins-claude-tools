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
export PYTHONDONTWRITEBYTECODE=1 # a hook must not leave __pycache__ in a clean checkout
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


def proof(name: str):
    """What pass_proof.py defines (`proves`, `bound`, `milestone_of`), shared with sdlc_status.py."""
    try:
        return getattr(helper("pass_proof"), name)
    except Exception:  # a gate that cannot read the rule blocks
        block(
            "pass_proof.py is missing or broken beside pr-gate.sh.", "Run `sdlc-run adopt` to restore it.",
            source="pass_proof.py beside pr-gate.sh",
        )


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
        self.seen: dict[tuple, list[tuple[str, dict]]] = {}  # records() per question: one scan per command

    def is_this(self, named: str) -> bool:
        """`--repo` is empty or names this repo (any remote's OWNER/REPO, URL or HOST/OWNER/REPO)."""
        slug = lambda url: "/".join(re.split(r"[/:]", url.strip().removesuffix(".git").rstrip("/"))[-2:]).lower()  # noqa: E731
        remotes = git(self.dir, "remote", "-v").splitlines()
        return not named or slug(named) in {slug(line.split()[1]) for line in remotes if len(line.split()) > 1}

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

    def change_dirs(self) -> list[Path]:
        """The changes folders a gate may have run in: ours, and in local mode every worktree's."""
        dirs = [self.changes]
        if self.local:  # the gate ran in the milestone's worktree, the merge runs in another
            rel = self.changes.relative_to(self.top)
            listing = git(self.dir, "worktree", "list", "--porcelain")
            dirs = [Path(t) / rel for t in re.findall(r"^worktree (.+)$", listing, re.M)] or dirs
        return dirs

    def in_changes(self, name: str) -> list[Path]:
        """`name` under every supported layout: live, archive/<id> and archive/<year>/<month>/<id>
        (the Stage 7 archive move is the last commit before the push). Nothing deeper is read."""
        patterns = [f"*/{name}"] + [f"{lay.format(id='*')}/{name}" for lay in proof("LAYOUTS")[1:]]
        return [f for changes in self.change_dirs() for pat in patterns for f in changes.glob(pat)]

    def reports(self, scope: str, slug: str) -> list[Path]:
        if scope == "project":  # verify_gate.py project: one record in the common git dir
            common = git(self.dir, "rev-parse", "--path-format=absolute", "--git-common-dir")
            return [Path(common) / "sdlc" / "projects" / slug / "verify" / "report.json"] if common else []
        return self.in_changes("verify/report.json")

    def records(self, *refs: str, live: bool = True) -> list[tuple[str, dict]]:
        """(change id, decisions.json) of every change record we can see: the worktrees' folders
        (unless `live` is off) and the records committed on each of `refs` (the gated ref carries
        its own change, which the checkout receiving a merge does not hold yet). A ref's record
        wins over another worktree's copy of the same change."""
        if (ask := (refs, live)) in self.seen:
            return self.seen[ask]
        found = {}
        # the old place first, then state/intake.json (the new place of decisions.json) over it
        for path in [*self.in_changes("decisions.json"), *self.in_changes("state/intake.json")] if live else []:
            try:
                found[path.parent.parent.name if path.parent.name == "state" else path.parent.name] = json.loads(
                    path.read_text(encoding="utf-8")
                )
            except (OSError, ValueError):
                continue
        rel = self.changes.relative_to(self.top).as_posix()
        for ref in refs:
            if not ref or not self.sha(ref):
                continue
            listing = git(self.dir, "ls-tree", "-r", "--name-only", ref, "--", rel + "/")
            for name in listing.splitlines():
                depth = len(Path(name).relative_to(rel).parts)
                moved = name.endswith("/state/intake.json")
                if (name.endswith("/decisions.json") and depth in (2, 3, 5)) or (moved and depth - 1 in (2, 3, 5)):
                    try:
                        found[Path(name).parents[1 if moved else 0].name] = json.loads(git(self.dir, "show", f"{ref}:{name}"))
                    except ValueError:
                        continue
        self.seen[ask] = [(i, d) for i, d in found.items() if isinstance(d, dict)]
        return self.seen[ask]

    def matching(self, milestone: str, *refs: str, live: bool = True) -> list[tuple[str, dict]]:
        """The records whose milestone slug names this branch (milestone/<slug> or <slug>-<n>).
        Without `live` only the records committed on `refs` count, not the branch tip."""
        name = milestone.removeprefix(self.m)
        return [
            (i, d) for i, d in self.records(*([milestone] if live else []), *refs, live=live)
            if (slug := (d.get("milestone") or {}).get("slug")) and re.fullmatch(re.escape(slug) + r"(-\d+)?", name)
        ]

    def change_ids(self, milestone: str, *refs: str) -> set[str]:
        """The change(s) a milestone branch belongs to."""
        return {i for i, _ in self.matching(milestone, *refs)}

    def pass_sha(
        self, sha: str, scope: str = "milestone", slug: str = "", branch: str = "", owner: str | None = None
    ) -> str:
        """The gated commit of a PASS of this scope for the change that owns `branch` (the project
        `slug`) that still holds at `sha`, or "". A pass holds on its own commit or on a descendant
        that only records followed (pass_proof.proves). Another change's pass never counts; a
        milestone's report counts only for the number the branch is (`milestones.branchPrefix`, an
        unnumbered branch is 1: M1's pass never admits M2), and only for the `owner` (the project
        branch) it was gated for when the caller names one (pass_proof.bound)."""
        if not sha:
            return ""
        if scope == "project":
            subjects = [(slug, None)]
        else:
            subjects = [
                (i, proof("milestone_of")(branch, self.m, (d.get("milestone") or {}).get("slug", "")))
                for i, d in self.matching(branch, sha)
            ]
        rel = self.changes.relative_to(self.top).as_posix()
        for subject, number in subjects:
            if not subject:
                continue
            # the checkout reports and the gate's shared copy: the newest report of the key speaks, and
            # a newer failure or block ends the walk (pass_proof.chain), whichever copy holds it
            key = proof("pass_key")(scope, branch, number)
            files = [*self.reports(scope, slug), proof("shared")(self.dir, subject, scope, key)]
            for is_pass, data in proof("chain")(files, scope, subject, number, owner):
                if is_pass and proof("proves")(self.dir, rel, data["sha"], sha):
                    return str(data["sha"])
        return ""

    def passed(
        self, sha: str, scope: str = "milestone", slug: str = "", branch: str = "", owner: str | None = None
    ) -> bool:
        return bool(self.pass_sha(sha, scope, slug, branch, owner))

    def owners(self, milestone: str, *refs: str, live: bool = True) -> set[str]:
        """The project branch each matching change record names for this milestone branch. Read from
        the records of the gated ref (with `live` off, only those), so a checkout that does not hold
        the milestone's change yet still knows who owns it, and an edit made after the gate does not
        change whom the pass was for. A change with no project branch (one that joined the
        milestone through Stage 1 `existing`, or a milestone with no project) names no owner."""
        out = set()
        for _, found in self.matching(milestone, *refs, live=live):
            project = found.get("project")
            if isinstance(project, dict) and project.get("slug") and project.get("branch", True):
                out.add(f"{self.p}{project['slug']}")
        return out

    def project_of(self, milestone: str, *refs: str) -> str:
        """The project/<slug> a milestone branch merges into: "" when its change has no project
        branch (or the owner is not unambiguous)."""
        found = self.owners(milestone, *refs)
        return next(iter(found)) if len(found) == 1 else ""

    def excepted(self, branch: str) -> bool:
        # the pushed repo's own exceptions, and the session's: the engineer speaks in the session
        start = root / cfg.get("changesDir", "changes")
        for path in [*self.changes.glob("*/decisions.json"), *start.glob("*/decisions.json"),
                     *self.changes.glob("*/state/intake.json"), *start.glob("*/state/intake.json")]:
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


CONFLICT = (
    "Feature PRs need a published milestone branch, and local milestones never publish one. Choose one in "
    'sdlc.json: remote feature PRs (milestones.merge "pr") or local feature commits (delivery "one-go"). '
    "`preflight.py` and `adopt` refuse the same pair."
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
            if repo.feature_prs and repo.local:
                block(f"a push of {dst}: sdlc.json asks for feature PRs and for local milestones.", CONFLICT, "sdlc.json")
            if repo.local and (project := repo.project_of(dst)):
                block(f"a push of {dst} in local milestones mode.", local_merge_route(project, dst))
            if not repo.feature_prs and not repo.passed(sha, branch=dst, owner=repo.project_of(dst, sha)):
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
        sha = repo.sha(head) if repo.is_this(opts.get("repo", "")) else ""
        parent = repo.project_of(head, sha) if sha else ""
        if parent and base != parent:  # GitHub picks the default branch when --base is left out
            block(f"a PR from {head} into {base}: its project is {parent}.", f"Pass `--base {parent}`.")
        if sha and not repo.passed(sha, branch=head, owner=parent):
            block(f"a PR from {head} at {sha[:12]} without a passing milestone gate.", CLOSE, "verify/report.json")
        return
    if head.startswith(repo.p):
        if base != repo.default:
            block(f"a PR from {head} into {base}.", "A project PR goes into the default branch (Stage 6p).")
        return
    if repo.hotfix and head.startswith("hotfix/") and base == repo.default:
        return
    if base.startswith(repo.m):
        if repo.feature_prs and repo.local:
            block(f"a PR from {head} into {base}: sdlc.json asks for feature PRs and for local milestones.", CONFLICT, "sdlc.json")
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
            into = current if current.startswith(repo.p) else real
            gated = repo.pass_sha(sha, branch=ref)
            if not gated:
                block(f"a merge of {ref} into {current} without a passing milestone gate.", CLOSE, "verify/report.json")
            tip = repo.sha(into)
            if not tip:
                block(
                    f"a merge of {ref} into {into}: the project branch {into} cannot be resolved.",
                    f"Create or check out {into} first (`git switch {into}`), then merge.",
                )
            owners = repo.owners(ref, gated, live=False)  # the change record as the gate saw it
            if len(owners) > 1 or not repo.matching(ref, gated, live=False):
                block(
                    f"a merge of {ref} into {into}: its change record names no single owner.",
                    "Commit the milestone's decisions.json (milestone.slug and project.slug) on "
                    f"{ref}, one change per branch name, then merge.",
                    "decisions.json on the milestone ref",
                )
            parent = next(iter(owners), "")
            if parent != into:
                block(
                    f"a merge of {ref} into {into}: it belongs to {parent or 'no project'}.",
                    local_merge_route(parent, ref)
                    if parent else "A milestone with no project goes in its own PR into the default branch.",
                )
            if not repo.passed(sha, branch=ref, owner=into):  # the report names the project it was gated for
                block(f"a merge of {ref} into {into}: its pass was gated for another project.", CLOSE, "verify/report.json")
            if subprocess.run(
                ["git", "-C", str(repo.dir), "merge-base", "--is-ancestor", tip, sha], capture_output=True
            ).returncode:
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
