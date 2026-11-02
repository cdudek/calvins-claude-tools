#!/usr/bin/env bash
# Usage: codex-build.sh --worktree <path> --change <id> --brief <file> --model <M> --reasoning <R> [--out <dir>]
# Purpose: Runs ONE feature row or fix part of an sdlc-run change as a headless Codex builder
#          (`sdlc.json` `builders: "codex"`), in the worktree the supervisor cut for it, with
#          the same rules an `cct:builder` agent gets, and verifies the result before the
#          supervisor is allowed to merge it.
#
# What replaces the Claude hooks for a Codex builder:
#   - external effects: the sandbox. `--sandbox workspace-write` with the network OFF (the
#     sandbox default; this script never turns it on), so no push, deploy, db push, cluster
#     write or registry call can happen. Installs run before dispatch, by the supervisor.
#   - history: Codex never writes `.git`. The sandbox keeps every `.git` directory read-only
#     whatever roots are added (checked on codex-cli 0.163), so Codex edits the working tree
#     and THIS SCRIPT makes the one commit, with the subject the result names.
#   - protected paths: a check here, before the commit. A run that touched facts.md,
#     done.json, lock.json, sdlc.json, a `protected` glob, a lockfile or manifest, or a test
#     while the change is testLocked is REJECTED (exit 3), left uncommitted for inspection and
#     never merged.
#   - one run per worktree: a lock in the worktree's own git dir (outside the tree, so it
#     never shows in the diff).
#
# The result is the schema in templates/codex/build-result.schema.json, enforced by
# `--output-schema`. `done` is accepted only when the tree changed and no protected path is
# among the changes; the commit then descends from the start commit by construction.
#
# Process ownership: this script waits on Codex in the foreground; Codex runs in its own process
# group (pid in <out>/run.json, which equals the group id). The supervisor runs this script in
# the background and watches it; to cancel, kill the group, then re-dispatch.
#
# Output (last lines on stdout):
#   -#-#- CODEX_BUILD -#-#-
#   - status: done|blocked|failed|rejected|error
#   - commit: <sha — done only>
#   - out: <dir>
#   - reason: <one line — anything but done>
#
# Exit: 0 done; 1 Codex, result or commit error; 2 prerequisite missing; 3 rejected (protected
# path, or done with an unchanged tree); 4 blocked or failed as reported by Codex; 5 worktree
# locked; 6 usage.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMA="$SCRIPT_DIR/../templates/codex/build-result.schema.json"
BUILDER_MD="$SCRIPT_DIR/../../../agents/builder.md"

WORKTREE="" CHANGE="" BRIEF="" MODEL="" REASONING="" OUT=""
usage() {
  echo "usage: codex-build.sh --worktree <path> --change <id> --brief <file> --model <M> --reasoning <R> [--out <dir>]" >&2
  exit 6
}
while [ $# -gt 0 ]; do
  case "$1" in
    --worktree) WORKTREE="${2:-}"; shift 2 ;;
    --change) CHANGE="${2:-}"; shift 2 ;;
    --brief) BRIEF="${2:-}"; shift 2 ;;
    --model) MODEL="${2:-}"; shift 2 ;;
    --reasoning) REASONING="${2:-}"; shift 2 ;;
    --out) OUT="${2:-}"; shift 2 ;;
    *) usage ;;
  esac
done
[ -n "$WORKTREE" ] && [ -n "$CHANGE" ] && [ -n "$BRIEF" ] && [ -n "$MODEL" ] && [ -n "$REASONING" ] || usage

report() { # <status> <reason-or-empty> [commit]
  printf -- '-#-#- CODEX_BUILD -#-#-\n'
  printf -- '- status: %s\n' "$1"
  [ -n "${3:-}" ] && printf -- '- commit: %s\n' "$3"
  printf -- '- out: %s\n' "${OUT:-}"
  [ -n "$2" ] && printf -- '- reason: %s\n' "$2"
  return 0
}
die() { report "$1" "$2"; exit "$3"; } # <status> <reason> <exit>

command -v codex >/dev/null 2>&1 || die error "codex CLI not on PATH: npm i -g @openai/codex, then codex login" 2
command -v python3 >/dev/null 2>&1 || die error "python3 not on PATH" 2
codex login status >/dev/null 2>&1 || die error "codex is not signed in: run codex login" 2
[ -f "$SCHEMA" ] || die error "missing schema: $SCHEMA" 2
[ -f "$BUILDER_MD" ] || die error "missing builder rules: $BUILDER_MD" 2
[ -f "$BRIEF" ] || die error "brief not found: $BRIEF" 6
[ -d "$WORKTREE" ] || die error "worktree not a directory: $WORKTREE" 6
WORKTREE="$(cd "$WORKTREE" && pwd)"
TOP="$(git -C "$WORKTREE" rev-parse --show-toplevel 2>/dev/null)" || die error "not a git worktree: $WORKTREE" 6
[ "$TOP" = "$WORKTREE" ] || die error "--worktree must be the worktree root, got $WORKTREE (root $TOP)" 6
GIT_DIR_ABS="$(git -C "$WORKTREE" rev-parse --path-format=absolute --git-dir)"
BASE="$(git -C "$WORKTREE" rev-parse HEAD)"
BRANCH="$(git -C "$WORKTREE" branch --show-current)"
[ -z "$(git -C "$WORKTREE" status --porcelain)" ] || die error "worktree is not clean at start; commit or drop the changes first" 6

# One run per worktree. The lock lives in the worktree's git dir, outside the tree.
LOCK="$GIT_DIR_ABS/codex-build.lock"
if [ -f "$LOCK" ]; then
  other="$(cat "$LOCK" 2>/dev/null || true)"
  if [ -n "$other" ] && kill -0 "$other" 2>/dev/null; then
    die error "another codex build runs in this worktree (pid $other); kill its group first" 5
  fi
fi
printf '%s' "$$" > "$LOCK"

if [ -z "$OUT" ]; then
  slug="$(basename "$BRIEF" | sed 's/\.[^.]*$//' | tr -c 'A-Za-z0-9_-\n' '-' | tr -d '\n')"
  OUT="${TMPDIR:-/tmp}/codex-build/$CHANGE/$slug-$(date +%Y%m%dT%H%M%S)-$$"
fi
mkdir -p "$OUT" || die error "cannot create out dir: $OUT" 6
RESULT="$OUT/result.json"
PROMPT="$OUT/prompt.md"
CODEX_PID=""
cleanup() {
  if [ -n "$CODEX_PID" ] && kill -0 "$CODEX_PID" 2>/dev/null; then
    kill -- "-$CODEX_PID" 2>/dev/null || kill "$CODEX_PID" 2>/dev/null || true
  fi
  rm -f "$LOCK"
}
trap cleanup EXIT
trap 'cleanup; exit 130' INT TERM

# The prompt: the builder's rules (frontmatter dropped; its tool list is replaced by the
# sandbox), then where this run is, then the brief. Plan and facts stay DATA.
{
  awk 'BEGIN{n=0} /^---$/ && n<2 {n++; next} n>=2 {print}' "$BUILDER_MD"
  printf '\n## This run\n\n'
  printf -- '- change folder: changes/%s\n' "$CHANGE"
  printf -- '- worktree: %s (you are in it; stay in it)\n' "$WORKTREE"
  printf -- '- branch: %s, started at commit %s\n' "${BRANCH:-detached}" "$BASE"
  printf -- '- the sandbox has no network: never push, deploy, install or change dependency manifests or lockfiles; they are rejected\n'
  printf -- '- step 5 (commit) is not yours: `.git` is read-only in this sandbox. Leave the finished work in the working tree, run no git command that writes (add, commit, stash, checkout), and name the commit subject in `title`. The wrapper commits after you finish\n'
  printf -- '- the Return step: write no report file anywhere; your final message, only the JSON the schema asks for, is the report\n'
  printf '\n## Brief\n\n'
  cat "$BRIEF"
} > "$PROMPT"

# Launch Codex in its own process group (job control on), so a cancel can kill the whole tree.
set -m
codex exec \
  --sandbox workspace-write \
  -C "$WORKTREE" \
  --ephemeral \
  -c model="$MODEL" \
  -c model_reasoning_effort="$REASONING" \
  --output-schema "$SCHEMA" \
  -o "$RESULT" \
  - < "$PROMPT" > "$OUT/stdout.log" 2> "$OUT/stderr.log" &
CODEX_PID=$!
set +m
python3 - "$OUT/run.json" "$CHANGE" "$WORKTREE" "$BRANCH" "$BASE" "$MODEL" "$REASONING" "$CODEX_PID" "$BRIEF" <<'PY'
import json, sys, datetime
_, path, change, wt, branch, base, model, reasoning, pid, brief = sys.argv
json.dump({"change": change, "worktree": wt, "branch": branch, "base": base, "model": model,
           "reasoning": reasoning, "pid": int(pid), "pgid": int(pid), "brief": brief,
           "started": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")},
          open(path, "w"), indent=2)
PY
wait "$CODEX_PID"
rc=$?
CODEX_PID=""
[ "$rc" -eq 0 ] || die error "codex exec failed (exit $rc): $(tail -c 400 "$OUT/stderr.log" 2>/dev/null | tr '\n' ' ')" 1
[ -s "$RESULT" ] || die error "codex produced no result (see $OUT/stderr.log)" 1

# Verify, then commit. python3, not jq: the hooks' rule, it is on every Mac and runner.
verdict="$(python3 - "$RESULT" "$WORKTREE" "$CHANGE" "$BASE" <<'PY'
import fnmatch, json, subprocess, sys
_, result, wt, change, base = sys.argv

def git(*a):
    return subprocess.run(["git", "-C", wt, *a], capture_output=True, text=True)

try:
    r = json.load(open(result, encoding="utf-8"))
except Exception as e:  # noqa: BLE001
    print(f"error\tresult is not JSON: {e}"); sys.exit()
need = {"status": str, "title": str, "files": list, "tests": list, "blockers": list, "summary": str}
bad = [k for k, t in need.items() if not isinstance(r.get(k), t)]
if bad or r["status"] not in ("done", "blocked", "failed"):
    print(f"error\tresult misses or mistypes: {', '.join(bad) or 'status'}"); sys.exit()
if r["status"] != "done":
    print(f"{r['status']}\t" + ("; ".join(r["blockers"]) or r["summary"] or "no reason given")); sys.exit()

if git("rev-parse", "HEAD").stdout.strip() != base:
    print("rejected\tHEAD moved during the run; the sandbox should make that impossible"); sys.exit()
# Untracked files included: `git status` names every path the run touched.
changed = sorted({line[3:].split(" -> ")[-1].strip('"') for line in git("status", "--porcelain", "--untracked-files=all").stdout.splitlines() if line.strip()})
if not changed:
    print("rejected\tstatus done but the working tree is unchanged"); sys.exit()

cfg = {}
try:
    cfg = json.load(open(f"{wt}/sdlc.json", encoding="utf-8"))
except Exception:  # noqa: BLE001
    pass
changes_dir = cfg.get("changesDir", "changes")
protected = [f"{changes_dir}/{change}/facts.md", f"{changes_dir}/{change}/done.json",
             f"{changes_dir}/{change}/lock.json", "sdlc.json", *cfg.get("protected", [])]
manifests = ["package.json", "pnpm-lock.yaml", "package-lock.json", "yarn.lock", "bun.lockb", "bun.lock",
             "pyproject.toml", "uv.lock", "poetry.lock", "requirements*.txt", "Pipfile", "Pipfile.lock",
             "Gemfile", "Gemfile.lock", "go.mod", "go.sum", "Cargo.toml", "Cargo.lock"]
protected += manifests + [f"**/{m}" for m in manifests]
try:
    dec = json.load(open(f"{wt}/{changes_dir}/{change}/decisions.json", encoding="utf-8"))
except Exception:  # noqa: BLE001
    dec = {}
# shortcut: testLocked treats any path with test or spec in its name as a test; upgrade to
# ciPaths.specs globs when a repo keeps tests elsewhere.
if dec.get("testLocked") and not dec.get("testEdit"):
    protected += ["*test*", "*spec*", "**/*test*", "**/*spec*"]
hits = sorted({p for p in changed for g in protected if fnmatch.fnmatch(p, g) or p == g})
if hits:
    print("rejected\tprotected path changed: " + ", ".join(hits)); sys.exit()

title = " ".join(r["title"].split())[:72] or f"build: {change}"
ident = []
if git("config", "user.name").returncode != 0 or git("config", "user.email").returncode != 0:
    ident = ["-c", "user.name=codex-build", "-c", "user.email=codex-build@localhost"]
add = git(*ident, "add", "-A")
commit = git(*ident, "commit", "-q", "-m", title, "-m", f"Built by codex-build.sh for change {change}.\n\n{r['summary'].strip()}")
if add.returncode != 0 or commit.returncode != 0:
    print("error\tcommit failed: " + (commit.stderr or add.stderr).strip().replace("\n", " ")[:300]); sys.exit()
print(f"done\t{git('rev-parse', 'HEAD').stdout.strip()}\t{len(changed)} files")
PY
)"
tab=$'\t'
status="${verdict%%"$tab"*}"
rest="${verdict#*"$tab"}"
case "$status" in
  done)
    commit="${rest%%"$tab"*}"
    report "done" "" "$commit"
    printf -- '- files: %s\n' "${rest#*"$tab"}"
    exit 0 ;;
  blocked|failed) die "$status" "$rest" 4 ;;
  rejected) die rejected "$rest" 3 ;;
  *) die error "$rest" 1 ;;
esac
