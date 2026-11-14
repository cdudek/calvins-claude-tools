// A `claude agents --json` list recorded on Claude Code 2.1.323, scrubbed: every id, name, path and pid is made up.
// Shapes kept: a blocked background session, a background session that carries both `status` and `state`, and
// interactive sessions that are idle, busy and waiting. The waiting row is a session that waited on a question
// (`AskUserQuestion`): its `waitingFor` is "input needed". No permission prompt was waiting at build.
export const T0 = 1_700_000_000_000

export const AGENTS = [
  { kind: 'background', state: 'blocked', sessionId: '00000000-0000-4000-8000-000000000001', cwd: '/work/repo-1', name: 'session 1', startedAt: T0 + 60_000, pid: 1001, id: 'bg-1' },
  { kind: 'background', status: 'busy', state: 'working', sessionId: '00000000-0000-4000-8000-000000000002', cwd: '/work/repo-2', name: 'session 2', startedAt: T0 + 120_000, pid: 1002, id: 'bg-2' },
  { kind: 'interactive', status: 'idle', sessionId: '00000000-0000-4000-8000-000000000003', cwd: '/work/repo-3', name: 'session 3', startedAt: T0 + 180_000, pid: 1003 },
  { kind: 'interactive', status: 'busy', sessionId: '00000000-0000-4000-8000-000000000004', cwd: '/work/repo-4', name: 'session 4', startedAt: T0 + 240_000, pid: 1004 },
  { kind: 'interactive', status: 'waiting', waitingFor: 'input needed', sessionId: '00000000-0000-4000-8000-000000000005', cwd: '/work/repo-5', name: 'session 5', startedAt: T0 + 300_000, pid: 1005 },
] as const

export const AGENTS_JSON = JSON.stringify(AGENTS)

// A scrubbed `claude agents --json` of rows that carry `pid` and rows that do not (Claude Code 2.1.323). A live background
// row has `pid`; an exited one has none (state `done`, or even `blocked` when it died waiting). An interactive row has
// `sessionId` and no job `id`; the two of them with no `pid` here are the interactive rows the assumption of F1 covers.
// Every id, name and pid is made up.
const sid = (n: number) => `00000000-0000-4000-8000-0000000001${String(n).padStart(2, '0')}`
export const PID_ROWS = [
  { kind: 'interactive', status: 'busy', sessionId: sid(1), cwd: '/work/pid-1', name: 'this session', startedAt: T0 + 10_000, pid: 2001 },
  { kind: 'background', status: 'busy', state: 'working', sessionId: sid(2), cwd: '/work/pid-2', name: 'live job', startedAt: T0 + 20_000, pid: 2002, id: 'bg-live' },
  { kind: 'background', state: 'done', sessionId: sid(3), cwd: '/work/pid-3', name: 'exited job', startedAt: T0 + 30_000, id: 'bg-done' },
  { kind: 'background', state: 'blocked', sessionId: sid(4), cwd: '/work/pid-4', name: 'dead job that was blocked', startedAt: T0 + 40_000, id: 'bg-dead' },
  { kind: 'background', state: 'blocked', sessionId: sid(5), cwd: '/work/pid-5', name: 'live job that is blocked', startedAt: T0 + 50_000, pid: 2005, id: 'bg-blocked' },
  { kind: 'interactive', status: 'waiting', waitingFor: 'input needed', sessionId: sid(6), cwd: '/work/pid-6', name: 'live terminal that waits', startedAt: T0 + 60_000, pid: 2006 },
  { kind: 'interactive', status: 'waiting', waitingFor: 'input needed', sessionId: sid(7), cwd: '/work/pid-7', name: 'closed terminal that waited', startedAt: T0 + 70_000 },
  { kind: 'interactive', status: 'idle', sessionId: sid(8), cwd: '/work/pid-8', name: 'closed terminal that was idle', startedAt: T0 + 80_000 },
] as const

export const PID_JSON = JSON.stringify(PID_ROWS)

export const PID = {
  self: sid(1),
  live: sid(2),
  exited: sid(3),
  deadBlocked: sid(4),
  liveBlocked: sid(5),
  liveWaiting: sid(6),
  closedWaiting: sid(7),
  closedIdle: sid(8),
}

export const ID = {
  blocked: AGENTS[0].sessionId,
  working: AGENTS[1].sessionId,
  idle: AGENTS[2].sessionId,
  busy: AGENTS[3].sessionId,
  waiting: AGENTS[4].sessionId,
}
