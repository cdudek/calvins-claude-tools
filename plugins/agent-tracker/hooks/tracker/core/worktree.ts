// The worktree a session ran in, as plain data: the five conditions that make it removable (F35), the first one that fails (F37),
// the ignored files the offer lists (F41) and the one label both the Session and the Repo page show. Pure: what git and `gh` said
// comes in as `Facts`. The script `cleanup.py` of the skill git-cleanup-run holds the same five conditions in Python; both test
// files use the case names linked, clean, pushed, merged and unused, so a drift shows.
import type { Listing } from '../types'
import { cut } from './format'
import { WORKTREE_WORDS } from './words'

// What git and `gh` said about the folder the session ran in. `pr`: the state of the branch's pull requests, null when `gh` gave
// no answer. `live`: the folders of the rows that have a process, null when the list could not be read.
export type PrState = 'merged' | 'closed' | 'open' | 'none'
export type Facts = {
  path: string // the worktree folder: the entry of `git worktree list` that holds the session's folder
  main: string // the first entry of that list, the main checkout
  linked: boolean
  branch: string | null
  status: string[] // `git status --porcelain --ignored`, one line each
  unpushed: number | null // commits on no remote; null: not read
  inDefault: boolean // HEAD is in the default branch
  pr: PrState | null
  live: string[] | null
}

export const CONDITIONS = ['linked', 'clean', 'pushed', 'merged', 'unused'] as const
export type Condition = (typeof CONDITIONS)[number]

const trim = (path: string) => path.replace(/\/+$/, '')
// `path` is `base` or a folder under it; a sibling that only shares the first letters is not.
export const under = (path: string, base: string) => trim(path) === trim(base) || path.startsWith(`${trim(base)}/`)

export const conditions = (f: Facts): Record<Condition, boolean> => ({
  linked: f.linked,
  clean: !f.status.some(l => !l.startsWith('!!')),
  pushed: f.unpushed === 0,
  merged: f.inDefault || f.pr === 'merged' || f.pr === 'closed',
  unused: f.live !== null && !f.live.some(c => under(c, f.path)),
})
export const failedOf = (f: Facts): Condition | null => {
  const c = conditions(f)
  return CONDITIONS.find(k => !c[k]) ?? null
}

// The folders with a live session. A row is live when it has a process; in a read where no row has one, nothing can be told apart
// from a live session, so every listed row counts (the script does the same). null: no read yet.
export const liveFolders = (sessions: { sessionId: string; cwd: string }[], listing: Listing | undefined): string[] | null => {
  if (listing === undefined) return null
  const pids = Object.values(listing).some(r => r.pid !== undefined)
  return sessions.filter(r => listing[r.sessionId] !== undefined && (listing[r.sessionId]!.pid !== undefined || !pids)).map(r => r.cwd)
}

// The folder label of a worktree: inside the repo's folder with a leading `.worktrees/` removed, else its folder name.
export const worktreeLabel = (path: string, repoPath: string): string =>
  path === repoPath ? 'main checkout' : path.startsWith(`${repoPath}/`) ? path.slice(repoPath.length + 1).replace(/^\.worktrees\//, '') : (path.split('/').pop() ?? path)

// ---- the ignored files ----

// `secret` and `other` are what the offer names; `more` counts the others it does not; `all` is every name, to see whether the
// list changed between the offer and the press.
export type Ignored = { secret: string[]; other: string[]; more: number; all: string[] }
const NAME_MAX = 30
const OTHER_MAX = 3
const SECRET = [/^\.env/, /\.pem$/, /key/, /^credentials/]
const secret = (name: string) => {
  const last = (name.replace(/\/+$/, '').split('/').pop() ?? '').toLowerCase()
  return SECRET.some(re => re.test(last))
}

// The `!!` lines of `git status --ignored --porcelain`. Secret-looking names (`.env*`, `*.pem`, `*key*`, `credentials*`) come first
// and are all listed, never cut and never in "and N more". The others: files, then folders (a folder ends in "/"), each group
// A to Z, the first three, each cut at 30 cells.
export const ignoredOf = (status: string[]): Ignored => {
  const all = status.filter(l => l.startsWith('!! ')).map(l => l.slice(3).trim().replace(/^"|"$/g, '')).filter(n => n !== '').sort()
  const secrets = all.filter(secret)
  const rest = all.filter(n => !secret(n))
  const ordered = [...rest.filter(n => !n.endsWith('/')), ...rest.filter(n => n.endsWith('/'))]
  return { secret: secrets, other: ordered.slice(0, OTHER_MAX).map(n => cut(n, NAME_MAX)), more: Math.max(0, ordered.length - OTHER_MAX), all }
}
export const ignoredWords = (i: Ignored): string | null => {
  const names = [...i.secret, ...i.other].join(', ')
  return names === '' ? null : `${names}${i.more > 0 ? ` ${WORKTREE_WORDS.more(i.more)}` : ''}`
}

// ---- what the page knows ----

// How condition 4 held: the branch is in the default branch, or its pull request is merged or closed.
export type Merged = 'branch' | 'merged-pr' | 'closed-pr'
// The worktree of a session, judged. `failed`: the first condition that does not hold; the worktree is removable when none fails.
export type WorktreeFact = { label: string; branch: string | null; removable: boolean; failed: Condition | null; how: Merged | null; ignored: Ignored }

// null: the folder is no linked worktree, so the page draws nothing about one.
export const judge = (f: Facts | null, label: string): WorktreeFact | null => {
  if (f === null || !f.linked) return null
  const failed = failedOf(f)
  const how = f.inDefault ? 'branch' : f.pr === 'merged' ? 'merged-pr' : f.pr === 'closed' ? 'closed-pr' : null
  return { label, branch: f.branch, removable: failed === null, failed, how, ignored: ignoredOf(f.status) }
}

// Why a worktree stays, or why a press found it changed: the first failed condition's reason (clean, pushed, merged, unused).
export const whyOf = (c: Exclude<Condition, 'linked'>) => WORKTREE_WORDS.why[c]
export const staysLine = (w: WorktreeFact): string | null =>
  w.failed === null || w.failed === 'linked' ? null : WORKTREE_WORDS.stays(w.label, whyOf(w.failed), w.failed === 'clean' ? WORKTREE_WORDS.commit : '')

// The offer, as lines: why removal is safe, the ignored files when there are any, the question.
export const offerLines = (w: WorktreeFact): string[] => {
  const names = ignoredWords(w.ignored)
  return [WORKTREE_WORDS.safe(w.label, w.how ?? 'branch'), ...(names === null ? [] : [WORKTREE_WORDS.ignored(names)]), WORKTREE_WORDS.ask(w.branch)]
}
