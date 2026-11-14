import type { Pr, SessionRecord } from '../types'
import { clean, duration } from './format'

type Scan = NonNullable<SessionRecord['scan']>

// `git worktree list --porcelain`: blocks split by a blank line, each `worktree <path>` then `branch refs/heads/<name>`
// or `detached` (F14).
export const parseWorktrees = (text: string): Scan['worktrees'] =>
  text
    .split(/\n\s*\n/)
    .map(block => block.split('\n'))
    .filter(lines => lines.some(l => l.startsWith('worktree ')))
    .map(lines => ({
      path: lines.find(l => l.startsWith('worktree '))!.slice('worktree '.length),
      branch: lines.find(l => l.startsWith('branch '))?.slice('branch '.length).replace(/^refs\/heads\//, '') ?? null,
    }))

const TITLE_MAX = 200
const URL_MAX = 500

// Every git call the mod makes: a repo's own config cannot start a program (fsmonitor, hooks) (S2).
export const gitArgv = (...args: string[]): string[] => ['git', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null', ...args]

// gh runs only for a remote on github.com: `https://github.com/o/r`, `git@github.com:o/r`, `ssh://git@github.com/o/r` (S2).
export const isGithubRemote = (url: string): boolean => /^(?:(?:https?|ssh|git):\/\/)?(?:[^/@:]+@)?github\.com[/:]/.test(url.trim())

type Check = { status?: string; conclusion?: string; state?: string }
const FAILED = new Set(['FAILURE', 'ERROR', 'TIMED_OUT', 'CANCELLED', 'STARTUP_FAILURE', 'ACTION_REQUIRED'])

// One check is a CheckRun (`status`, `conclusion`) or a StatusContext (`state`). Failing wins over running.
const checksOf = (rollup: Check[]): Pr['checks'] => {
  const failed = rollup.some(c => FAILED.has(c.conclusion ?? '') || FAILED.has(c.state ?? ''))
  const running = rollup.some(c => (c.status !== undefined && c.status !== 'COMPLETED') || c.state === 'PENDING' || c.state === 'EXPECTED')
  return failed ? 'failing' : running ? 'running' : 'pass'
}
const REVIEW: Record<string, Pr['review']> = { APPROVED: 'approved', CHANGES_REQUESTED: 'changes', REVIEW_REQUIRED: 'requested' }
const MERGEABLE: Record<string, Pr['mergeable']> = { MERGEABLE: 'mergeable', CONFLICTING: 'conflicts' }

// `gh pr list --json number,title,url,headRefName,createdAt,statusCheckRollup,reviewDecision,mergeable`. null: not a list.
export const GH_FIELDS = 'number,title,url,headRefName,createdAt,statusCheckRollup,reviewDecision,mergeable'
export const parsePrs = (json: string): Pr[] | null => {
  let list: unknown
  try {
    list = JSON.parse(json)
  } catch {
    return null
  }
  if (!Array.isArray(list)) return null
  return (list as Record<string, unknown>[])
    .filter(p => typeof p?.number === 'number')
    .map(p => ({
      number: p.number as number,
      title: clean(p.title, TITLE_MAX),
      url: String(p.url ?? '').startsWith('https://') ? clean(p.url, URL_MAX) : '', // anything else is not a link
      branch: clean(p.headRefName, TITLE_MAX),
      createdAt: String(p.createdAt ?? ''),
      checks: checksOf(Array.isArray(p.statusCheckRollup) ? (p.statusCheckRollup as Check[]) : []),
      review: REVIEW[String(p.reviewDecision ?? '')] ?? 'none',
      mergeable: MERGEABLE[String(p.mergeable ?? '')] ?? 'unknown',
    }))
}

export type RepoPrs = { prs: Pr[]; at: number; ghOk: boolean; ageMs: number; hasLive: boolean }

// A repo's PR state is the scan with the latest time among its sessions (F69, F78). A live session is a mod
// session that has not ended: while there is none, the state is the last stored one and the pane says so.
export const repoPrs = (sessions: SessionRecord[], repoPath: string, now: number): RepoPrs | null => {
  const inRepo = sessions.filter(s => s.repo?.path === repoPath)
  const latest = inRepo.reduce<Scan | null>((best, s) => (s.scan && (best === null || s.scan.at > best.at) ? s.scan : best), null)
  if (latest === null) return null
  const hasLive = inRepo.some(s => s.source === 'mod' && s.state !== 'ended')
  return { prs: latest.prs, at: latest.at, ghOk: latest.ghOk, ageMs: Math.max(0, now - latest.at), hasLive }
}

// The line above stored PRs; none while a session of the mod keeps them current.
export const prsLine = (r: RepoPrs): string | null => (r.hasLive ? null : `PRs as of ${duration(r.ageMs)} ago: no live session in this repo`)
