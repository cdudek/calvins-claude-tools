// A made-up town for the pane tests: every repo, title and folder is invented. Times are relative to NOON, a local
// time, so "since midnight" and "started 10:42" read the same in every time zone.
import type { Pr, SessionRecord, Snapshot } from '../../hooks/tracker/types'
import { MILESTONE, MIN, SELF, inState, pr, rec, scan } from './band'

export { MIN, SELF }
export const NOON = new Date(2026, 10, 14, 12, 0).getTime()
export const HOUR = 60 * MIN
export const at = (agoMin: number) => NOON - agoMin * MIN

export const use = (tokensIn: number, tokensOut: number, toolErrors = 0, retries = 0) => ({ tokensIn, tokensOut, toolErrors, retries })

// A session that has been in `state` for `ago` minutes.
export const sess = (id: string, state: SessionRecord['state'], ago: number, name: string, title: string | null, extra: Partial<SessionRecord> = {}): SessionRecord => ({
  ...inState(id, state, 0, name, title ?? '', extra),
  title,
  engine: { since: at(ago) },
  writtenAt: NOON,
  lastActivityAt: at(ago),
  ...extra,
})

export const WEB_PRS: Pr[] = [
  pr(41, { title: 'old cleanup', branch: 'feat/old', createdAt: '2026-11-01T08:00:00Z', checks: 'pass', review: 'approved', mergeable: 'mergeable' }),
  pr(42, { title: 'fix login redirect', branch: 'feat/login', createdAt: '2026-11-10T08:00:00Z', checks: 'failing', review: 'requested', mergeable: 'conflicts' }),
  pr(43, { title: 'dark mode', branch: 'feat/dark', createdAt: '2026-11-12T08:00:00Z', checks: 'running', review: 'changes', mergeable: 'unknown' }),
  pr(44, { title: 'newest broken', branch: 'feat/new', createdAt: '2026-11-13T08:00:00Z', checks: 'failing', review: 'none', mergeable: 'mergeable' }),
]
const WEB_SCAN = { ...scan(WEB_PRS, true, at(1)), worktrees: [{ path: '/work/web-app', branch: 'main' }, { path: '/work/web-app/.worktrees/login', branch: 'feat/login' }] }

// Home's town: this session runs (the Running section lists it), web-app has one waiting (6m, permission) and docs-site
// one (2m, a question); api runs two; web-app and docs-site are done; one ended today and one yesterday.
export const paneTown = (): SessionRecord[] => [
  sess(SELF, 'running', 20, 'platform-tools-suite', 'build the band', { branch: 'milestone/agent-tracker-1', usage: use(30000, 11000), milestone: MILESTONE, runs: { goalSince: at(14), subagents: [], background: [] } }),
  sess('web-1', 'needs-you', 6, 'web-app', 'fix login redirect', { reason: 'permission', branch: 'feat/login', usage: use(1000, 500, 2, 1), scan: WEB_SCAN, source: 'mod' }),
  sess('docs-1', 'needs-you', 2, 'docs-site', 'edit pages', { reason: 'question', branch: 'main', usage: use(500, 100) }),
  sess('api-1', 'running', 22, 'api', 'migrate users', { branch: 'feat/users', usage: use(36000, 5000, 2, 1), scan: scan([], true, at(1)) }),
  sess('api-2', 'running', 5, 'api', 'seed data', { branch: 'main', usage: use(900, 0) }),
  sess('docs-2', 'done', 3, 'docs-site', 'rename skills', { branch: 'main', usage: use(10000, 2000) }),
  sess('web-2', 'done', 9, 'web-app', 'dark mode', { branch: 'feat/dark', usage: use(3000, 1000, 1, 0) }),
  sess('web-3', 'ended', 120, 'web-app', 'fix typo', { branch: 'main', usage: use(3000, 1000), endedAt: at(120) }),
  sess('web-4', 'ended', 13 * 60, 'web-app', 'old work', { branch: 'main', usage: use(100, 0), endedAt: at(13 * 60) }),
]

export const snapAt = (sessions: SessionRecord[], extra: Partial<Snapshot> = {}): Snapshot => ({ at: NOON, agentsOk: true, okAt: NOON, failedReads: 0, sessions, ...extra })

// Only this session is live.
export const aloneTown = (state: SessionRecord['state'] = 'running'): SessionRecord[] => [
  sess(SELF, state, 4, 'platform-tools-suite', 'build the band', { branch: 'main', reason: state === 'needs-you' ? 'waiting' : null }),
]

export { rec }
