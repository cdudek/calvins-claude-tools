// A made-up town of sessions for the band tests: every repo, title and folder is invented.
import type { Pr, SessionRecord, Snapshot } from '../../hooks/tracker/types'
import { T0 } from './agents'

export const NOW = T0 + 3_600_000
export const MIN = 60_000
export const SELF = 'self-0000'

export const rec = (id: string, extra: Partial<SessionRecord> = {}): SessionRecord => ({
  v: 1, sessionId: id, source: 'mod', writtenAt: NOW, kind: 'interactive', title: null, cwd: `/work/${id}`, repo: null, branch: null,
  startedAt: T0, lastActivityAt: NOW, endedAt: null, engine: { since: NOW }, state: 'running', reason: null, unknownValue: null,
  questionFlag: null, usage: { tokensIn: 0, tokensOut: 0, toolErrors: 0, retries: 0 }, asks: [],
  runs: { goalSince: null, subagents: [], background: [] }, milestone: null, scan: null, ...extra,
})

const repo = (name: string) => ({ path: `/work/${name}`, name })
// A session that has been in `state` for `ago` minutes.
export const inState = (id: string, state: SessionRecord['state'], ago: number, name: string, title: string, extra: Partial<SessionRecord> = {}) =>
  rec(id, { state, engine: { since: NOW - ago * MIN }, repo: repo(name), cwd: `/work/${name}`, title, ...extra })

export const pr = (number: number, extra: Partial<Pr> = {}): Pr => ({
  number, title: `PR ${number}`, url: `https://example.test/pr/${number}`, branch: `feat/b${number}`, createdAt: '2026-11-10T08:00:00Z',
  checks: 'pass', review: 'none', mergeable: 'unknown', ...extra,
})

// 4 open PRs, 1 failing, 2 mergeable.
export const PRS: Pr[] = [pr(1, { mergeable: 'mergeable', review: 'approved' }), pr(2, { checks: 'failing', mergeable: 'conflicts' }), pr(3, { mergeable: 'mergeable' }), pr(4, { checks: 'running' })]
export const scan = (prs: Pr[], ghOk = true, at = NOW - 30_000) => ({ at, ghOk, worktrees: [], prs })

// This session works on milestone agent-tracker-1, 2 of 4 features complete, with a goal 14 minutes old.
export const MILESTONE = {
  slug: 'agent-tracker-1',
  sentence: 'Open any session and see every session.',
  features: [
    { n: 1, name: 'collector', state: 'done abc1234' },
    { n: 2, name: 'backfill', state: 'merged' },
    { n: 3, name: 'band', state: 'building' },
    { n: 4, name: 'pane', state: 'todo' },
  ],
}

// The town: this session runs, two wait (web-app 6m, docs-site 2m), two more run, two are done.
export const town = (): SessionRecord[] => [
  inState(SELF, 'running', 20, 'platform-tools-suite', 'build the band', { milestone: MILESTONE, branch: 'milestone/agent-tracker-1', runs: { goalSince: NOW - 14 * MIN, subagents: [], background: [] } }),
  inState('web-1', 'needs-you', 6, 'web-app', 'fix login', { reason: 'waiting' }),
  inState('docs-1', 'needs-you', 2, 'docs-site', 'edit pages', { reason: 'waiting' }),
  inState('api-1', 'running', 22, 'api', 'migrate users', { scan: scan(PRS) }),
  inState('api-2', 'running', 5, 'api', 'seed data'),
  inState('docs-2', 'done', 3, 'docs-site', 'rename skills'),
  inState('web-2', 'done', 9, 'web-app', 'dark mode'),
]

export const snap = (sessions: SessionRecord[], extra: Partial<Snapshot> = {}): Snapshot => ({ at: NOW, agentsOk: true, okAt: NOW, failedReads: 0, sessions, ...extra })

// The same town with this session waiting for 1 minute and web-app for 6: two need you (docs-site now runs).
export const townSelfWaiting = (): SessionRecord[] =>
  town().map(r =>
    r.sessionId === SELF
      ? { ...r, state: 'needs-you' as const, reason: 'waiting' as const, engine: { since: NOW - MIN } }
      : r.sessionId === 'docs-1'
        ? { ...r, state: 'running' as const, reason: null }
        : r,
  )
