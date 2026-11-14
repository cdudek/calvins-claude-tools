// A `claude agents --json` list recorded on Claude Code 2.1.323, scrubbed: every id, name, path and pid is made up.
// Shapes kept: a blocked background session, a background session that carries both `status` and `state`, and
// interactive sessions that are idle, busy and waiting. The waiting row is a session that waited on a question
// (`AskUserQuestion`): its `waitingFor` is "input needed". No permission prompt was waiting at build.
export const T0 = 1_700_000_000_000

export const AGENTS = [
  { kind: 'background', state: 'blocked', sessionId: '00000000-0000-4000-8000-000000000001', cwd: '/work/repo-1', name: 'session 1', startedAt: T0 + 60_000, id: 'bg-1' },
  { kind: 'background', status: 'busy', state: 'working', sessionId: '00000000-0000-4000-8000-000000000002', cwd: '/work/repo-2', name: 'session 2', startedAt: T0 + 120_000, pid: 1002, id: 'bg-2' },
  { kind: 'interactive', status: 'idle', sessionId: '00000000-0000-4000-8000-000000000003', cwd: '/work/repo-3', name: 'session 3', startedAt: T0 + 180_000, pid: 1003 },
  { kind: 'interactive', status: 'busy', sessionId: '00000000-0000-4000-8000-000000000004', cwd: '/work/repo-4', name: 'session 4', startedAt: T0 + 240_000, pid: 1004 },
  { kind: 'interactive', status: 'waiting', waitingFor: 'input needed', sessionId: '00000000-0000-4000-8000-000000000005', cwd: '/work/repo-5', name: 'session 5', startedAt: T0 + 300_000, pid: 1005 },
] as const

export const AGENTS_JSON = JSON.stringify(AGENTS)

export const ID = {
  blocked: AGENTS[0].sessionId,
  working: AGENTS[1].sessionId,
  idle: AGENTS[2].sessionId,
  busy: AGENTS[3].sessionId,
  waiting: AGENTS[4].sessionId,
}
