#!/usr/bin/env bash
# Usage: test-integrity.sh <repo-or-worktree> <base-ref> [plan.md [--task <id> | --milestone <id>] [--approved <sha>] [--pin <sha>] [--target <sha>] [--checked <sha>[,<sha>...]]]
# Compares <base-ref>...HEAD of <repo-or-worktree>. Prints one `INTEGRITY FAIL <reason>` per
# violation (exit 1) or `INTEGRITY OK` (exit 0). plan.md is a path inside the repo, relative to its root
# (changes/<slug>/plan.md) or an absolute path in any worktree of it, read at --approved when given
# (else from <repo-or-worktree>; without --approved a plan copy outside every worktree is read as is, for replays). With a plan a test is new when absent on --target <sha>, else on the
# plan's integration (else base) branch; --task/--milestone limit changed paths to the task(s) files,
# new tests (inside a task file's directory) and allowTestEdits; --milestone requires --approved; --pin <sha> keeps that commit's tests as is; --checked (with
# --milestone) lists the commits the per-task checks passed: every changed implementation path must
# have its HEAD blob in one of them. Plan-gap lane: `GAP-FIX <M> round=<n> files=<a,b> tests=<c,d>` lines in the plan's progress log (read at HEAD) extend
# --milestone <M> (all rounds), and are the whole scope of --task <M>-gap<n> (round n; <M>-gap is round 1), but only for paths matching the approved
# milestone's mayTouch; rounds are numbered 1..n once each (a line without round= is round 1), at most the milestone's gapRounds (default 3).
set -euo pipefail

U="usage: test-integrity.sh <repo-or-worktree> <base-ref> [plan.md [--task <id> | --milestone <id>] [--approved <sha>] [--pin <sha>] [--target <sha>] [--checked <sha>[,<sha>...]]]"
repo="${1:?$U}"
base="${2:?$U}"
plan="${3:-}"
if [ "$#" -ge 3 ]; then shift 3; else shift "$#"; fi
task="" ms="" approved="" pin="" target="" checked=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --task) task="${2:?$U}" ;;
    --milestone) ms="${2:?$U}" ;;
    --approved) approved="${2:?$U}" ;;
    --pin) pin="${2:?$U}" ;;
    --target) target="${2:?$U}" ;;
    --checked) checked="${2:?$U}" ;;
    *) echo "$U" >&2; exit 2 ;;
  esac
  shift 2
done
mode=""
[ -n "$task" ] && mode=task
[ -n "$ms" ] && mode=milestone
if [ -n "$mode" ] && [ -z "$plan" ]; then echo "$U" >&2; exit 2; fi
if [ "$mode" = milestone ] && [ -z "$approved" ]; then echo "--milestone requires --approved" >&2; echo "$U" >&2; exit 2; fi

fail=0
say() { echo "INTEGRITY FAIL $1"; fail=1; }

# The approved-content exemption and the plan scope trust --approved, so it must be history of the checked tree.
if [ -n "$approved" ]; then
  git -C "$repo" rev-parse --verify --quiet "$approved^{commit}" >/dev/null || { say "cannot resolve approved $approved in $repo"; exit 1; }
  git -C "$repo" merge-base --is-ancestor "$approved" HEAD 2>/dev/null || { say "approved $approved is not an ancestor of HEAD"; exit 1; }
fi

allow="" files="" integ="" pbase="" slug="" last=0 planfile=""
if [ -n "$plan" ]; then
  out=$(python3 -c '
import fnmatch, json, os, re, subprocess, sys
plan, repo, approved, task, ms = sys.argv[1:6]
def git(*a): return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, check=True).stdout
top = os.path.realpath(git("rev-parse", "--show-toplevel").strip())
rel = os.path.normpath(plan)  # repo-relative, the form the coordinator passes
if os.path.isabs(plan):  # a path in any worktree of this repo (the innermost one holds it)
    p = os.path.realpath(plan)
    wts = [os.path.realpath(l[9:]) for l in git("worktree", "list", "--porcelain").splitlines() if l.startswith("worktree ")]
    inside = [w for w in wts if p.startswith(w + os.sep)]
    rel = os.path.relpath(p, max(inside, key=len)) if inside else ".."
loose = os.path.isabs(plan) and rel.startswith("..") and not approved and os.path.isfile(plan)  # replays: a plan copy outside any worktree
if rel.startswith("..") and not loose: sys.exit("plan " + plan + " is not a path inside " + top)
print("PLANFILE\t" + (plan if loose else os.path.join(top, rel)))
text = git("show", approved + ":" + rel) if approved else open(plan if loose else os.path.join(top, rel)).read()
p = json.loads(re.search(r"^```json factory[ \t]*\n(.*?)^```", text, re.S | re.M).group(1))
mss = p.get("milestones", [])
print("BASE\t" + str(p.get("base", ""))); print("INTEG\t" + str(p.get("integration", ""))); print("SLUG\t" + str(p.get("change", "")))
if ms and mss and mss[-1].get("id") == ms: print("LAST\t1")
sel = None
if task: sel = [t for m in mss for t in m.get("tasks", []) if t.get("id") == task]
elif ms: sel = [t for m in mss if m.get("id") == ms for t in m.get("tasks", [])]
# plan-gap lane: the fix rounds the coordinator logs as `GAP-FIX <M> round=<n> files=<a,b> tests=<c,d>` in the progress log (read at HEAD, not at --approved);
# a legacy line without `round=` is round 1. At most the milestone gapRounds (default 3), numbered 1..n once each.
# Only paths matching the milestone mayTouch globs the owner approved count; the fix task of round n is `<M>-gap<n>` (`<M>-gap` is round 1).
gm = re.fullmatch(r"(M\d+[a-z]?)-gap([1-9]\d*)?", task)
gap = ms or (gm.group(1) if gm else "")
if gap:
    m0 = next((m for m in mss if m.get("id") == gap), {})
    may, cap = m0.get("mayTouch") or [], m0.get("gapRounds", 3)
    if not (type(cap) is int and 1 <= cap <= 5): cap = 3
    # The log is read from the committed tree: an uncommitted plan edit must not grant scope. Only a replay copy outside every worktree (loose) is read from disk.
    try: cur = open(plan).read() if loose else git("show", "HEAD:" + rel)
    except subprocess.CalledProcessError: cur = ""
    rounds = [(int(r or 1), a, b) for r, a, b in re.findall(r"^GAP-FIX " + gap + r"(?: round=(\d+))? files=(\S*)(?: tests=(\S*))?[ \t]*$", cur, re.M)]
    # `*` never crosses `/`: a glob matches a path with the same number of segments, each by fnmatchcase; a trailing `/` is a directory prefix.
    # A glob needs a static first segment and no `**`, else it matches nothing (check-plan rejects it at approval too).
    static = lambda g: g != "" and not g.startswith("/") and ".." not in g.split("/") and "**" not in g and not re.search(r"[*?\[]", g.split("/")[0])
    def ok(f):
        fs = f.split("/")
        return any(static(g) and ((g.endswith("/") and f.startswith(g)) or (not g.endswith("/") and len(g.split("/")) == len(fs)
                   and all(fnmatch.fnmatchcase(a, b) for a, b in zip(fs, g.split("/"))))) for g in may)
    if sorted(r for r, _, _ in rounds) != list(range(1, len(rounds) + 1)): print("ERR\tgap rounds for " + gap + " must be numbered 1..n, each round once")
    if len(rounds) > cap: print("ERR\tmore than " + str(cap) + " gap rounds for " + gap + " (gapRounds " + str(cap) + ")")
    want = rounds if ms else [x for x in rounds if x[0] == int(gm.group(2) or 1)]
    if want:
        extra = {"files": [f for _, a, _ in want for f in a.split(",") if f and ok(f)], "allowTestEdits": [t for _, _, b in want for t in b.split(",") if t and ok(t)]}
        if task: sel = [extra]
        else: sel.append(extra)
if sel is None: sel = [{"allowTestEdits": p.get("allowTestEdits", [])}]  # old plans: top-level list
elif not sel: print("ERR\tno task or milestone " + (task or ms) + " in the plan")
for t in sel:
    for f in t.get("files", []): print("FILE\t" + f)
    for a in t.get("allowTestEdits", []): print("ALLOW\t" + a)' "$plan" "$repo" "$approved" "$task" "$ms") || { say "cannot read plan $plan"; exit 1; }
  while IFS=$'\t' read -r k v; do
    case "$k" in
      PLANFILE) planfile="$v" ;; BASE) pbase="$v" ;; INTEG) integ="$v" ;; SLUG) slug="$v" ;; LAST) last=1 ;;
      FILE) files+="$v"$'\n' ;; ALLOW) allow+="$v"$'\n' ;;
      ERR) say "$v"; exit 1 ;;
    esac
  done <<< "$out"
fi

# A diff that cannot run must fail, never fall through to OK (process substitution hides git errors).
for ref in "$base" HEAD; do
  git -C "$repo" rev-parse --verify --quiet "$ref^{commit}" >/dev/null || { say "cannot resolve $ref in $repo"; exit 1; }
done
iref="" chk=()
if [ -n "$target" ]; then  # the recorded target SHA beats any local branch, which can lag origin
  iref=$(git -C "$repo" rev-parse --verify --quiet "$target^{commit}") || { say "cannot resolve target $target in $repo"; exit 1; }
elif [ -n "$plan" ]; then  # a test is new when absent here
  b="${integ:-$pbase}"
  for c in "refs/heads/$b" "refs/remotes/origin/$b"; do
    if [ -n "$b" ] && git -C "$repo" rev-parse --verify --quiet "$c^{commit}" >/dev/null; then iref="$c"; break; fi
  done
  [ -n "$iref" ] || { say "cannot resolve integration ref $b in $repo"; exit 1; }
fi
if [ "$mode" = milestone ] && [ -n "$checked" ]; then
  IFS=, read -ra chk <<< "$checked"
  for c in "${chk[@]}"; do
    git -C "$repo" rev-parse --verify --quiet "$c^{commit}" >/dev/null || { say "cannot resolve checked commit $c in $repo"; exit 1; }
  done
fi
names=$(git -C "$repo" diff --no-renames --name-status "$base...HEAD") || { say "git diff failed"; exit 1; }
scan=()  # test files and package.json: the only places a skip or `|| true` weakens a test
code=()  # non-test source: where a lint suppression hides a defect

is_test() {  # path segments and suffixes only, so latest.ts or inspector.ts never match
  case "/$1" in
    */test/*|*/tests/*|*/__tests__/*|*/e2e/*|*.test.*|*.spec.*|*_test.*|*/test_*.py) return 0 ;;
  esac
  return 1
}

is_new() {  # $1 status, $2 path
  if [ -n "$iref" ]; then ! git -C "$repo" cat-file -e "$iref:$2" 2>/dev/null; else case "$1" in A*) return 0 ;; *) return 1 ;; esac; fi
}

in_files() {  # exact path, directory prefix ending in /, or glob
  local g
  while IFS= read -r g; do
    [ -n "$g" ] || continue
    case "$g" in
      */) [[ "$1" == "$g"* ]] && return 0 ;;
      *) [ "$1" = "$g" ] && return 0; case "$1" in $g) return 0 ;; esac ;;
    esac
  done <<< "$files"
  return 1
}

unbuilt() {  # $1 path, implementation paths in milestone mode with --checked: its HEAD blob must be in a checked commit
  [ "${#chk[@]}" -gt 0 ] || return 1
  local h c
  h=$(git -C "$repo" rev-parse --verify --quiet "HEAD:$1" || echo gone)
  for c in "${chk[@]}"; do
    [ "$(git -C "$repo" rev-parse --verify --quiet "$c:$1" || echo gone)" = "$h" ] && return 1
  done
  say "changed after the builder check: $1"
}

in_file_dirs() {  # a directory of one of the task's files globs (its static prefix), so a new test sits beside the code it covers
  local g d
  while IFS= read -r g; do
    [ -n "$g" ] || continue
    case "$g" in */) d="${g%/}" ;; */*) d="${g%/*}" ;; *) d="" ;; esac
    case "$d" in *[*?[]*) d="${d%%[*?[]*}"; case "$d" in */) d="${d%/}" ;; */*) d="${d%/*}" ;; *) d="" ;; esac ;; esac
    if [ -z "$d" ]; then case "$1" in */*) ;; *) return 0 ;; esac
    elif [[ "$1" == "$d"/* ]]; then return 0; fi
  done <<< "$files"
  return 1
}

outside() {  # $1 status, $2 path: task and milestone modes only
  [ -n "$mode" ] || return 0
  in_files "$2" && return 0
  is_test "$2" && is_new "$1" "$2" && in_file_dirs "$2" && return 0  # a new test elsewhere is not exempt by its name
  is_test "$2" && ! is_new "$1" "$2" && ! printf '%s\n' "$allow" | grep -qxF -- "$2" && return 0  # reported as an existing test change
  printf '%s\n' "$allow" | grep -qxF -- "$2" && return 0
  if [ "$mode" = task ]; then say "outside task $task: $2"; else say "outside milestone $ms: $2"; fi
}

# Any status counts for the harness, plan, CI, baselines, specs and deltas; new test files are fine.
while IFS=$'\t' read -r status path _; do
  if [ "$mode" = milestone ]; then  # coordinator paths
    case "$path" in
      "changes/$slug/plan.md")
        if [ -n "$approved" ]; then
          cp_out=$(python3 "$(dirname "$0")/check-plan.py" "$planfile" --approved "$approved") || { echo "$cp_out"; say "plan changed: $path fails check-plan"; }
        fi
        continue ;;
      "changes/$slug/evidence/"*|"changes/$slug/kickoff-"*) continue ;;
      specs/adr/*) ;;
      specs/*) [ "$last" -eq 1 ] && continue ;;
    esac
    # approved content: milestone 1 carries the approved delta, intent, ADRs and .factory/ when there is no plan PR
    if [ -n "$approved" ] && [ "$(git -C "$repo" rev-parse --verify --quiet "HEAD:$path" || echo gone)" = \
         "$(git -C "$repo" rev-parse --verify --quiet "$approved:$path" || echo gone)" ]; then continue; fi
  fi
  case "$path" in
    .factory/*) say "harness changed: $path" ;;
    changes/*/plan.md) say "plan changed: $path" ;;
    .github/*) say "CI config changed: $path" ;;
    .fitness/*|*baseline*.json) say "baseline changed: $path" ;;
    specs/adr/*) say "ADR changed: $path" ;;
    specs/*) say "spec changed: $path" ;;
    changes/*/delta.md) say "delta changed: $path" ;;
    package.json|*/package.json)
      unbuilt "$path" && continue
      outside "$status" "$path"
      case "$status" in D*) ;; *) scan+=("$path"); code+=("$path") ;; esac ;;
    *)
      unbuilt "$path" && continue
      outside "$status" "$path"
      case "$status:$path" in D*|*:*.md) ;; *)  # every new file gets both scans, whatever is_test says
        if is_new "$status" "$path"; then scan+=("$path"); code+=("$path"); fi ;; esac
      if ! is_test "$path"; then
        case "$status:$path" in D*|*:*.md) ;; *) code+=("$path") ;; esac
        continue
      fi
      case "$status" in D*) ;; *) scan+=("$path") ;; esac
      if is_new "$status" "$path"; then continue; fi
      if ! printf '%s\n' "$allow" | grep -qxF -- "$path"; then say "existing test changed or deleted: $path"; fi ;;
  esac
done <<< "$names"

if [ -n "$pin" ]; then  # the bug flow's failing test must reach HEAD untouched
  pinned=$(git -C "$repo" diff-tree --root --no-commit-id --no-renames --name-only -r "$pin") || { say "cannot read pin $pin"; exit 1; }
  while IFS= read -r path; do
    [ -n "$path" ] && is_test "$path" || continue
    want=$(git -C "$repo" rev-parse --verify --quiet "$pin:$path" || true)
    [ -n "$want" ] || continue
    [ "$(git -C "$repo" rev-parse --verify --quiet "HEAD:$path" || true)" = "$want" ] || say "pinned regression test changed: $path"
  done <<< "$pinned"
fi

added=""
if [ "${#scan[@]}" -gt 0 ]; then
  patch=$(git -C "$repo" diff -U0 "$base...HEAD" -- "${scan[@]}") || { say "git diff failed"; exit 1; }
  added=$(printf '%s\n' "$patch" | grep -E '^\+[^+]' || true)
fi
for pat in '|| true' '.skip(' 'xit(' 'it.only(' 'test.only(' 'describe.only(' '@pytest.mark.skip'; do
  if printf '%s\n' "$added" | grep -qF -- "$pat"; then say "added line contains $pat"; fi
done

sup=""
if [ "${#code[@]}" -gt 0 ]; then
  patch=$(git -C "$repo" diff -U0 "$base...HEAD" -- "${code[@]}") || { say "git diff failed"; exit 1; }
  sup=$(printf '%s\n' "$patch" | grep -E '^\+[^+]' || true)
fi
for pat in 'biome-ignore' 'eslint-disable' 'oxlint-disable' '@ts-ignore' '@ts-expect-error' '# noqa'; do
  if printf '%s\n' "$sup" | grep -qF -- "$pat"; then say "added lint suppression $pat"; fi
done

[ "$fail" -eq 0 ] && echo "INTEGRITY OK"
exit "$fail"
