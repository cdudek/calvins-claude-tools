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
# An exception exists only in the engineer's words: decisions.json
# `prExceptions: [{"branch": "<head>", "words": "<what the engineer said>"}]`.
# Tags and branch deletions pass. A repo without sdlc.json gets no opinion.
set -uo pipefail
. "$(dirname "$0")/sdlc-config.sh"

payload=$(cat)
[ -f "$SDLC_JSON" ] || exit 0
case "$payload" in *push*|*"pr create"*) ;; *) exit 0 ;; esac

PAYLOAD="$payload" python3 - "$SDLC_ROOT" "$SDLC_JSON" <<'PY'
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


def block(why: str, route: str) -> None:
    print(f"BLOCKED: {why}\n{route}\n({docs}, \"One milestone, one PR\")", file=sys.stderr)
    sys.exit(2)


def git(where: Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(where), *args], capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else ""


def goal_active() -> bool:
    """Same reading as chain-gate.sh: the last goal_status entry of the transcript says met: false."""
    try:
        lines = Path(transcript).read_text(encoding="utf-8").splitlines()
    except (OSError, ValueError):
        return False
    last = None
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        att = entry.get("attachment") if isinstance(entry, dict) else None
        if isinstance(att, dict) and att.get("type") == "goal_status":
            last = att
    return last is not None and last.get("met") is False


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
        self.hotfix = bool(self.cfg.get("hotfix", True))
        self.changes = self.top / self.cfg.get("changesDir", "changes")

    def branch(self) -> str:
        return git(self.dir, "rev-parse", "--abbrev-ref", "HEAD")

    def sha(self, ref: str) -> str:
        return git(self.dir, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")

    def passed(self, sha: str) -> bool:
        """A milestone PASS on this commit, or on an ancestor that only records followed:
        writing the gate line into milestone.md must not need a second full gate."""
        if not sha:
            return False
        rel = self.changes.relative_to(self.top).as_posix() + "/"
        # archive/ too: the Stage 7 archive move is the last commit before the push (3.7.0)
        found = [*self.changes.glob("*/verify/report.json"), *self.changes.glob("archive/*/verify/report.json")]
        for report in found:
            try:
                data = json.loads(report.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            gated = data.get("sha") or ""
            if not gated or not str(data.get("result", "")).startswith("VERIFY PASS milestone"):
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

    def excepted(self, branch: str) -> bool:
        for path in self.changes.glob("*/decisions.json"):
            try:
                rows = json.loads(path.read_text(encoding="utf-8")).get("prExceptions") or []
            except (OSError, ValueError, AttributeError):
                continue
            if any(r.get("branch") == branch and str(r.get("words", "")).strip() for r in rows):
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
            if not repo.feature_prs and not repo.passed(sha):
                block(f"a push of {dst} at {sha[:12] or src} without a passing milestone gate.", CLOSE)
            continue
        if dst.startswith(repo.p):
            if sha and sha == repo.sha(f"origin/{repo.default}"):
                continue  # creating the project branch from the trunk (Stage 1.2)
            block(f"a push to {dst}.", "A project branch moves only through milestone PRs. " + RIDE)
        if repo.feature_prs:
            continue
        if goal_active():
            block(f"a push of {dst} inside a /goal run.", RIDE)


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
        if not (base.startswith(repo.p) or base == repo.default):
            block(f"a PR from {head} into {base}.", "A milestone PR goes into its parent: project/* or the default branch.")
        sha = repo.sha(head) if "repo" not in opts else ""
        if sha and not repo.passed(sha):
            block(f"a PR from {head} at {sha[:12]} without a passing milestone gate.", CLOSE)
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
    if goal_active():
        block(f"a PR from {head} inside a /goal run: only milestone and project PRs open there.", RIDE)


def segments(text: str) -> list[list[str]]:
    lex = shlex.shlex(text, posix=True, punctuation_chars=";&|")
    lex.whitespace_split = True
    out: list[list[str]] = [[]]
    for tok in lex:
        if tok and set(tok) <= set(";&|"):
            out.append([])
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
                here = (where / os.path.expanduser(rest[1])).resolve()
            rest = rest[2:]
        if rest and rest[0] == "push":
            check_push(Repo(here), rest[1:])
    elif seg[0] == "gh" and seg[1:3] == ["pr", "create"]:
        check_pr(Repo(where), seg[3:])
sys.exit(0)
PY
