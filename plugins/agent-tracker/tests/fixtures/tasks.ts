// Task asks for the tests: a made-up town of sessions that carry them. Every name is invented; times are relative to NOON.
import type { Ask, SessionRecord } from '../../hooks/tracker/types'
import { MILESTONE } from './band'
import { at, sess } from './pane'

export const ask = (n: number, text: string, agoMin: number, extra: Partial<Ask> = {}): Ask => ({ n, text, kind: 'task', status: 'replied', at: at(agoMin), ...extra })
const web = { repo: { path: '/work/web-app', name: 'web-app' } }

// One session of each status, plus the ones that are not on the list: a question, an ask nobody classified and a task judged done.
export const taskTown = (): SessionRecord[] => [
  // needs you: its last ask waits for the answer
  sess('need-1', 'needs-you', 4, 'web-app', 'login', { ...web, branch: 'feat/login', reason: 'question', asks: [ask(1, 'Fix the login redirect so users land back on the page they came from.', 20)] }),
  // forgotten: the session ended two hours ago, and one went quiet 45 minutes ago
  sess('lost-1', 'ended', 120, 'api', 'orders', { repo: { path: '/work/api', name: 'api' }, branch: 'feat/orders', endedAt: at(120), asks: [ask(1, 'Migrate the orders table to the new schema.', 180, { verdict: 'not-started' })] }),
  sess('lost-2', 'done', 45, 'api', 'retry', { repo: { path: '/work/api', name: 'api' }, branch: 'feat/retry', asks: [ask(1, 'Add a retry with backoff on 429.', 50, { verdict: 'partly' })] }),
  // superseded: a later ask may have replaced the first
  sess('sup-1', 'running', 2, 'web-app', 'client', { ...web, branch: 'feat/client', asks: [ask(1, 'Add retry on 401 responses in the API client.', 15, { verdict: 'replaced', replacedBy: 2 }), ask(2, 'Fix the login redirect and the 401 retry together.', 8)] }),
  // in progress: a milestone, and a session with none
  sess('prog-1', 'running', 1, 'web-app', 'tokens', { ...web, branch: 'milestone/agent-tracker-1', milestone: MILESTONE, asks: [ask(1, 'Move every colour to design tokens.', 70)] }),
  sess('prog-2', 'running', 1, 'docs-site', 'index', { repo: { path: '/work/docs-site', name: 'docs-site' }, branch: 'main', asks: [ask(1, 'Rebuild the search index on every docs deploy.', 100)] }),
  // not checked: it ended with no verdict (asked before verdicts existed), and a headless run that is nothing of the owner's
  sess('chk-1', 'ended', 300, 'api', 'old', { repo: { path: '/work/api', name: 'api' }, branch: 'main', endedAt: at(300), asks: [ask(1, 'Rename the config keys.', 400)] }),
  sess('head-1', 'ended', 100, 'api', 'reply with ok', { repo: { path: '/work/api', name: 'api' }, branch: 'main', endedAt: at(100), headless: true, asks: [ask(1, 'reply with ok', 110, { verdict: 'not-started' })] }),
  // not on the list
  sess('else-1', 'done', 3, 'web-app', 'misc', {
    ...web,
    branch: 'main',
    asks: [ask(1, 'Add search filters.', 30, { verdict: 'done' }), ask(2, 'Why is the build slow?', 10, { kind: 'question' }), ask(3, 'An ask nobody classified.', 9, { kind: 'not-classified' })],
  }),
]
