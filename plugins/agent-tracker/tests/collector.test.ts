import { describe, expect, test } from 'claude-code/testing'

import {
  PERMISSION_WAITING_FOR,
  completeCount,
  deriveState,
  homeModel,
  isLive,
  isComplete,
  labelRepos,
  lastActivity,
  leaseState,
  mergeSessions,
  needsLines,
  parseAgents,
  parseMilestone,
  repoFromCommonDir,
  sessionModel,
} from '../hooks/tracker/core'
import type { AgentRow, AgentsFile, Lease, SessionRecord, Snapshot } from '../hooks/tracker/types'
import { AGENTS, AGENTS_JSON, ID, PID, PID_JSON, PID_ROWS, T0 } from './fixtures/agents'
import { MILESTONE_MD } from './fixtures/milestone'
import { DIR, start, world } from './fixtures/world'

const TAG = '@2026-11-13-agent-tracker'
const CHANGE = '@2026-11-14-tracker-session-cleanup'
const NOW = T0 + 3_600_000
const rows = parseAgents(AGENTS_JSON) as AgentRow[]
const row = (id: string) => rows.find(r => r.sessionId === id)!


const record = (id: string, extra: Partial<SessionRecord> = {}): SessionRecord => ({
  v: 1, sessionId: id, source: 'mod', writtenAt: NOW, kind: 'interactive', title: null, cwd: '/work/x', repo: null, branch: null,
  startedAt: T0, lastActivityAt: NOW, endedAt: null, engine: { since: NOW }, state: 'done', reason: null, unknownValue: null,
  questionFlag: null, usage: { tokensIn: 0, tokensOut: 0, toolErrors: 0, retries: 0 }, asks: [],
  runs: { goalSince: null, subagents: [], background: [] }, milestone: null, scan: null, ...extra,
})

describe('collector and states', () => {
  test(`@F1 ${TAG} lists sessions with and without the mod; the lease holder polls, the others read agents.json`, async ($, on) => {
    const w = world(on, { now: NOW, id: ID.busy, cwd: '/work/repo-4' })
    w.agents.json = AGENTS_JSON
    await start($, w)
    await w.clock.advance(5000)
    // This session took the lease and polled; the list holds sessions that run without the mod.
    expect(w.procs.some(p => p.argv.join(' ') === 'claude agents --json')).toBe(true)
    expect((w.json(`${DIR}/poller.json`) as Lease).sessionId).toBe(ID.busy)
    expect((w.json(`${DIR}/agents.json`) as AgentsFile).agents.length).toBe(5)
    const ids = (w.snapshot()).sessions.map(s => s.sessionId).sort()
    expect(ids).toEqual(AGENTS.map(a => a.sessionId).sort())
    expect((w.snapshot()).sessions.find(s => s.sessionId === ID.idle)?.source).toBe('engine')
  })

  test(`@F1 ${TAG} a session that does not hold the lease reads agents.json and runs no call`, async ($, on) => {
    const w = world(on, { now: NOW, id: ID.busy, cwd: '/work/repo-4' })
    w.put(`${DIR}/poller.json`, { v: 1, sessionId: 'someone-else', heartbeat: NOW, gen: 2 } satisfies Lease)
    w.put(`${DIR}/agents.json`, { v: 1, readAt: NOW, agents: rows } satisfies AgentsFile)
    await start($, w)
    await w.clock.advance(5000)
    expect(w.procs.filter(p => p.argv[0] === 'claude').length).toBe(0)
    expect((w.snapshot()).sessions.length).toBe(5)
  })

  test(`@F2 ${TAG} busy and working map to running`, () => {
    expect(deriveState(row(ID.busy), false).state).toBe('running')
    expect(deriveState(row(ID.working), false).state).toBe('running')
  })

  test(`@F3 ${TAG} waiting and blocked map to needs you`, () => {
    expect(deriveState(row(ID.waiting), false).state).toBe('needs-you')
    expect(deriveState(row(ID.blocked), false).state).toBe('needs-you')
  })

  test(`@F4 ${TAG} waitingFor becomes the reason, from a recorded fixture or else the default "waiting" logged to questions.md`, () => {
    // The one waiting session at build waited on a question: "input needed". No permission value was recorded.
    expect(row(ID.waiting).waitingFor).toBe('input needed')
    expect(PERMISSION_WAITING_FOR).toBeNull()
    expect(deriveState(row(ID.waiting), false).reason).toBe('waiting')
    // With a recorded permission value the mapping holds, and a question flag says "question".
    expect(deriveState(row(ID.waiting), false, 'input needed').reason).toBe('permission')
    expect(deriveState(row(ID.idle), true).reason).toBe('question')
    expect(deriveState(row(ID.blocked), false).reason).toBe('waiting')
  })

  test(`@F5 ${TAG} idle maps to done unless the question flag is set`, () => {
    expect(deriveState(row(ID.idle), false)).toMatchObject({ state: 'done', reason: null })
    expect(deriveState(row(ID.idle), true)).toMatchObject({ state: 'needs-you', reason: 'question' })
  })

  test(`@F6 ${TAG} done state or absence maps to ended`, () => {
    expect(deriveState({ kind: 'background', state: 'done' }, false).state).toBe('ended')
    const files = [record('gone'), record(ID.idle)]
    const good = mergeSessions({ files, transcripts: [], agents: rows, now: NOW, selfId: 'self' })
    expect(good.find(s => s.sessionId === 'gone')?.state).toBe('ended')
    // A failed read of the list never ends a session: the last state stays.
    const failed = mergeSessions({ files, transcripts: [], agents: null, now: NOW, selfId: 'self' })
    expect(failed.find(s => s.sessionId === 'gone')?.state).toBe('done')
  })

  test(`@F7 ${TAG} repo label from the main worktree, same folder name twice`, async ($, on) => {
    expect(repoFromCommonDir('/work/web-app/.git')).toEqual({ path: '/work/web-app', name: 'web-app' })
    const labelled = labelRepos([
      record('a', { repo: { path: '/work/web-app', name: 'web-app' } }),
      record('b', { repo: { path: '/play/web-app', name: 'web-app' } }),
      record('c', { repo: { path: '/work/other', name: 'other' } }),
    ]).map(s => s.repo?.name)
    expect(labelled).toEqual(['work/web-app', 'play/web-app', 'other'])
    // A linked worktree's session groups under its repo: the common dir is the main worktree's .git.
    const w = world(on, { now: NOW, cwd: '/work/web-app/.worktrees/fix' })
    w.git[w.cwd] = { commonDir: '/work/web-app/.git', branch: 'fix' }
    await start($, w)
    const mine = w.json(`${DIR}/sessions/${w.id}.json`) as SessionRecord
    expect(mine.repo).toEqual({ path: '/work/web-app', name: 'web-app' })
    expect(mine.branch).toBe('fix')
  })

  test(`@F8 ${TAG} one file per session, rewritten whole`, async ($, on) => {
    const w = world(on, { now: NOW })
    await start($, w)
    await w.clock.advance(5000)
    const own = `${DIR}/sessions/${w.id}.json`
    expect(w.writes.filter(p => p.includes('/sessions/')).every(p => p === own)).toBe(true)
    expect(w.json(own)).toMatchObject({ v: 1, sessionId: w.id, source: 'mod', cwd: w.cwd })
  })

  test(`@F9 ${TAG} reads a milestone.md fixture whose branch equals the session branch`, async ($, on) => {
    const w = world(on, { now: NOW })
    w.git[w.cwd] = { commonDir: `${w.cwd}/.git`, branch: 'milestone/demo-1' }
    w.put(`${w.cwd}/changes/2026-01-01-demo/milestone.md`, MILESTONE_MD)
    await start($, w)
    const mine = w.json(`${DIR}/sessions/${w.id}.json`) as SessionRecord
    expect(mine.milestone?.slug).toBe('demo-1')
    expect(mine.milestone?.sentence).toBe("Open any session and see every session's repo, work and state.")
    expect(mine.milestone?.features.map(f => [f.n, f.state])).toEqual([[0, 'done abc1234'], [1, 'done def5678'], [2, 'building'], [3, 'merged'], [4, 'blocked: waits on review']])
    expect(parseMilestone(MILESTONE_MD)?.branch).toBe('milestone/demo-1')
  })

  test(`@F10 ${TAG} changes folder without a matching milestone`, async ($, on) => {
    const w = world(on, { now: NOW })
    // A changes folder with no milestone.md, and one whose milestone.md names another branch.
    w.put(`${w.cwd}/changes/2026-01-01-other/plan.md`, '# plan')
    w.put(`${w.cwd}/changes/2026-01-01-demo/milestone.md`, MILESTONE_MD)
    await start($, w)
    expect((w.json(`${DIR}/sessions/${w.id}.json`) as SessionRecord).milestone).toBeNull()
  })

  test(`@F11 ${TAG} goal age, subagents and background sessions`, async ($, on) => {
    const w = world(on, { now: NOW, id: ID.busy, cwd: '/work/repo-4' })
    w.agents.json = JSON.stringify([...AGENTS, { kind: 'background', state: 'working', sessionId: 'bg-session', cwd: '/work/repo-4', name: 'nightly run', startedAt: NOW - 120_000 }])
    w.subagents = [{ id: 'sub-1', description: 'review the diff', type: 'general-purpose', status: 'running' } as never]
    await start($, w)
    await $.command.run({ command: 'goal', args: 'ship the band', origin: { kind: 'composer' }, presentation: {} as never })
    await w.clock.advance(5000)
    const mine = w.json(`${DIR}/sessions/${w.id}.json`) as SessionRecord
    expect(mine.runs.goalSince).toBe(NOW)
    expect(mine.runs.subagents).toEqual([{ id: 'sub-1', name: 'review the diff', status: 'running' }])
    expect(mine.runs.background).toEqual([{ id: 'bg-session', name: 'nightly run', since: NOW - 120_000 }])
  })

  test(`@F21 ${TAG} tokens, errors and retries from fixtures`, async ($, on) => {
    const w = world(on, { now: NOW })
    await start($, w)
    const usage = { input_tokens: 100, output_tokens: 40, cache_read_input_tokens: 900, cache_creation_input_tokens: 10, model: 'm' }
    await $.turn.complete({ answer: 'ok', durationMs: 1, isAborted: false, turnId: 't1', reason: 'answer', usage })
    await $.turn.complete({ answer: 'ok', durationMs: 1, isAborted: false, turnId: 't2', reason: 'answer', usage: { ...usage, output_tokens: 10 } })
    // Each call made straight after the same failed call is a retry, whether it fails again or passes.
    const results = [true, true, true, false]
    w.tool = () => ({ result: {}, isError: results.shift() })
    for (const command of ['make', 'make', 'make test', 'make test']) await $.tool.call({ tool: 'Bash', command })
    const u = (w.json(`${DIR}/sessions/${w.id}.json`) as SessionRecord).usage
    expect(u).toEqual({ tokensIn: 2020, tokensOut: 50, toolErrors: 3, retries: 2 })
  })

  test(`@F11 ${TAG} a proposed goal counts only when the call went through; a failed one is an error (R6)`, async ($, on) => {
    const w = world(on, { now: NOW })
    await start($, w)
    const own = () => w.json(`${DIR}/sessions/${w.id}.json`) as SessionRecord
    w.tool = () => ({ result: {}, isError: true })
    await $.tool.call({ tool: 'ProposeGoal', condition: 'ship it' })
    expect(own().runs.goalSince).toBeNull()
    expect(own().usage.toolErrors).toBe(1)
    w.tool = () => ({ deny: 'not now' }) as never
    await $.tool.call({ tool: 'ProposeGoal', condition: 'ship it' })
    expect(own().runs.goalSince).toBeNull()
    w.tool = () => ({ result: {}, isError: false })
    await $.tool.call({ tool: 'ProposeGoal', condition: 'ship it' })
    expect(own().runs.goalSince).toBe(NOW)
  })

  test(`@F58 ${TAG} write failure sets the status line`, async ($, on) => {
    const w = world(on, { now: NOW })
    w.failWrite = p => p.includes('/sessions/')
    await start($, w)
    expect(w.statuses.at(-1)).toBe("Tracker could not save this session's record. Asks from now on are not kept. Check that the agent-tracker folder in your Claude folder can be written.")
    w.failWrite = () => false
    await w.clock.advance(5000)
    expect(w.statuses.at(-1)).toBeUndefined()
  })

  test(`@F66 ${TAG} unknown status shows as needs you, state unknown, with the raw value`, () => {
    const r = deriveState({ kind: 'interactive', status: 'pondering' }, false)
    expect(r).toMatchObject({ state: 'needs-you', reason: 'unknown', unknownValue: 'pondering' })
    expect(deriveState({ kind: 'background', state: 'paused' }, false)).toMatchObject({ state: 'needs-you', reason: 'unknown', unknownValue: 'paused' })
  })

  test(`@F68 ${TAG} files of several sessions merge into one list`, async ($, on) => {
    const w = world(on, { now: NOW })
    w.agents.json = JSON.stringify([{ ...row(ID.idle), sessionId: 'a' }, { ...row(ID.busy), sessionId: w.id }])
    w.put(`${DIR}/sessions/a.json`, record('a', { cwd: '/work/a' }))
    w.put(`${DIR}/sessions/b.json`, record('b', { cwd: '/work/b' })) // its mod is gone and it left the list
    w.put(`${DIR}/sessions/torn.json`, '{"v":1,"sess') // a half-written file is skipped
    w.put(`${DIR}/transcripts/c.json`, record('c', { source: 'transcript' }))
    w.put(`${DIR}/transcripts/a.json`, record('a', { source: 'transcript', title: 'twin' })) // a sessions/ file wins
    await start($, w)
    await w.clock.advance(5000)
    const sessions = (w.snapshot()).sessions
    expect(sessions.map(s => s.sessionId).sort()).toEqual(['a', 'b', 'c', w.id].sort())
    expect(sessions.find(s => s.sessionId === 'a')?.source).toBe('mod')
    expect(sessions.find(s => s.sessionId === 'b')?.state).toBe('ended')
  })

  test(`@F68 ${TAG} a session only the list holds has no known wait; a transcript record the list holds is live, one it does not is not (R7, R10)`, () => {
    const list = [
      { sessionId: 'e', cwd: '/work/e', name: 'engine only', startedAt: T0, kind: 'interactive', status: 'waiting' },
      { sessionId: 't', cwd: '/work/t', name: 'from transcript', startedAt: T0, kind: 'interactive', status: 'busy' },
    ] as AgentRow[]
    const history = ['t', 'gone'].map(id => record(id, { source: 'transcript', state: 'done' }))
    const sessions = mergeSessions({ files: [], transcripts: history, agents: list, now: NOW, selfId: 'me' })
    const by = (id: string) => sessions.find(r => r.sessionId === id)!
    expect(by('e').engine.since).toBeNull()
    expect(needsLines(sessions, 'me', NOW)).toMatchObject([{ id: 'e', ms: null }])
    expect(isLive(by('t'))).toBe(true)
    expect(by('t').state).toBe('running')
    expect(by('t').engine.since).toBeNull() // no mod file saw it change: its age is not a wait
    expect(isLive(by('gone'))).toBe(false)
    const home = homeModel({ at: NOW, agentsOk: true, okAt: NOW, failedReads: 0, sessions }, 'me', NOW, { midnight: 0, clock: () => '', day: () => '', date: () => '' }, null, 80)
    const row = home.blocks.find(x => x.kind === 'row' && x.key === 'session:e')
    expect(row?.kind === 'row' && row.lines[0]!.map(x => x.text).join('')).not.toMatch(/\d+m|<1m/) // the row shows no wait
  })

  test(`@F6 ${TAG} a failed list read restores only the sessions the last good read showed (R11)`, () => {
    const files = [record('seen', { state: 'running' }), record('crashed', { state: 'running' }), record('finished', { state: 'done' })]
    const merged = mergeSessions({ files, transcripts: [], agents: null, now: NOW, selfId: 'me', seen: new Set(['seen']) })
    expect(merged.map(r => [r.sessionId, r.state])).toEqual([['seen', 'running'], ['crashed', 'ended'], ['finished', 'done']])
  })

  test(`@F71 ${TAG} done and merged count as complete`, () => {
    const features = parseMilestone(MILESTONE_MD)!.features
    expect(['done abc1234', 'done', 'merged', 'building', 'todo', 'blocked: x'].map(isComplete)).toEqual([true, true, true, false, false, false])
    expect(completeCount(features)).toBe(3)
  })

  test(`@F127 ${TAG} lease taken when none is fresh, kept while fresh, dropped when another session holds it`, async ($, on) => {
    const w = world(on, { now: NOW })
    expect(leaseState(null, 'me', NOW)).toBe('free')
    expect(leaseState({ v: 1, sessionId: 'me', heartbeat: NOW - 14_000, gen: 2 }, 'me', NOW)).toBe('mine')
    expect(leaseState({ v: 1, sessionId: 'x', heartbeat: NOW - 16_000, gen: 2 }, 'me', NOW)).toBe('free')
    // A fresh lease from an older tracker (0.1.x wrote no gen) is taken, so its old session never blocks the late check.
    expect(leaseState({ v: 1, sessionId: 'x', heartbeat: NOW - 1000 }, 'me', NOW)).toBe('free')
    expect(leaseState({ v: 1, sessionId: 'x', heartbeat: NOW - 1000, gen: 2 }, 'me', NOW)).toBe('other')
    const polls = () => w.procs.filter(p => p.argv[0] === 'claude').length
    await start($, w)
    expect((w.json(`${DIR}/poller.json`) as Lease).sessionId).toBe(w.id) // none was fresh: taken
    await w.clock.advance(5000)
    expect((w.json(`${DIR}/poller.json`) as Lease).heartbeat).toBe(NOW + 5000) // kept: heartbeat refreshed
    const before = polls()
    w.put(`${DIR}/poller.json`, { v: 1, sessionId: 'other', heartbeat: w.clock.now(), gen: 2 } satisfies Lease)
    await w.clock.advance(5000) // another session holds it now: this one stops polling
    expect(polls()).toBe(before)
    expect((w.json(`${DIR}/poller.json`) as Lease).sessionId).toBe('other')
    await w.clock.advance(20_000) // its heartbeat is stale: taken again
    expect((w.json(`${DIR}/poller.json`) as Lease).sessionId).toBe(w.id)
  })

  test(`@F128 ${TAG} the holder polls every 5 seconds, refreshes the heartbeat and writes agents.json by temp file and rename`, async ($, on) => {
    // The mod API has no rename (questions.md Q2): agents.json is written whole, and readers keep their last good copy.
    const w = world(on, { now: NOW })
    w.agents.json = AGENTS_JSON
    await start($, w)
    await w.clock.advance(25_000)
    expect(w.procs.filter(p => p.argv.join(' ') === 'claude agents --json').length).toBe(6) // at start, then every 5 s
    expect((w.json(`${DIR}/poller.json`) as Lease).heartbeat).toBe(NOW + 25_000)
    expect((w.json(`${DIR}/agents.json`) as AgentsFile).readAt).toBe(NOW + 25_000)
    expect(w.writes.filter(p => p.includes('agents.json'))).toEqual(new Array(6).fill(`${DIR}/agents.json`))
  })

  test(`@F129 ${TAG} a non-holder runs no call and reads agents.json; an old file counts as a failed read`, async ($, on) => {
    const w = world(on, { now: NOW })
    w.put(`${DIR}/poller.json`, { v: 1, sessionId: 'other', heartbeat: NOW, gen: 2 } satisfies Lease)
    w.put(`${DIR}/agents.json`, { v: 1, readAt: NOW, agents: rows } satisfies AgentsFile)
    w.put(`${DIR}/sessions/old.json`, record('old', { state: 'done' }))
    await start($, w)
    await w.clock.advance(5000)
    expect(w.procs.filter(p => p.argv[0] === 'claude').length).toBe(0)
    expect((w.snapshot()).agentsOk).toBe(true)
    // The holder keeps its heartbeat fresh, but agents.json is 21 s old: that counts as a failed read.
    w.put(`${DIR}/poller.json`, { v: 1, sessionId: 'other', heartbeat: w.clock.now(), gen: 2 } satisfies Lease)
    w.put(`${DIR}/agents.json`, { v: 1, readAt: w.clock.now() - 16_000, agents: rows } satisfies AgentsFile)
    await w.clock.advance(5000)
    const snap = w.snapshot()
    expect(snap.agentsOk).toBe(false)
    expect(snap.sessions.find(s => s.sessionId === 'old')?.state).toBe('done') // not "ended"
    expect(w.procs.filter(p => p.argv[0] === 'claude').length).toBe(0)
  })
})

// A row with no `pid` has no process: the session is ended, whatever its state says (change 2026-11-14-tracker-session-cleanup).
const pidRows = parseAgents(PID_JSON) as AgentRow[]
const withoutPid = parseAgents(JSON.stringify(PID_ROWS.map(({ pid: _pid, ...r }: Record<string, unknown>) => r))) as AgentRow[]
const merged = (agents: AgentRow[], extra: Partial<Parameters<typeof mergeSessions>[0]> = {}) =>
  mergeSessions({ files: [], transcripts: [], agents, now: NOW, selfId: PID.self, ...extra })
const stateOf = (list: SessionRecord[], id: string) => list.find(r => r.sessionId === id)?.state
const factsLine = (r: SessionRecord) => {
  const local = { midnight: NOW - 3_600_000, clock: () => '10:00', day: () => 'Mon', date: () => '14 Nov' }
  const model = sessionModel({ at: NOW, agentsOk: true, okAt: NOW, failedReads: 0, sessions: [r] }, r.sessionId, NOW, local, 80)!
  const facts = model.blocks.find(b => b.kind === 'lines' && b.key === 'facts')
  return facts?.kind === 'lines' ? facts.lines[0]!.map(s => s.text).join('') : ''
}

describe('a session with no process is ended', () => {
  test(`@F1 ${CHANGE} a row with no pid is ended, whatever its state`, async ($, on) => {
    const list = merged(pidRows)
    expect(pidRows.find(r => r.sessionId === PID.closedWaiting)).toMatchObject({ kind: 'interactive', status: 'waiting' })
    expect(pidRows.find(r => r.sessionId === PID.closedWaiting)!.pid).toBeUndefined()
    for (const id of [PID.exited, PID.deadBlocked, PID.closedWaiting, PID.closedIdle]) expect(stateOf(list, id)).toBe('ended') // background and interactive, blocked, waiting, idle, done
    expect(stateOf(list, PID.live)).toBe('running')
    // The same through the poller: this session's own row has a pid, so the rule holds for the others.
    const w = world(on, { now: NOW, id: PID.self, cwd: '/work/pid-1' })
    w.agents.json = PID_JSON
    await start($, w)
    await w.clock.advance(5000)
    expect(stateOf(w.snapshot().sessions, PID.deadBlocked)).toBe('ended')
    expect(stateOf(w.snapshot().sessions, PID.closedWaiting)).toBe('ended')
    expect(stateOf(w.snapshot().sessions, PID.liveWaiting)).toBe('needs-you')
  })

  test(`@F2 ${CHANGE} a row with a pid that is blocked or waiting needs you`, () => {
    const list = merged(pidRows)
    expect(stateOf(list, PID.liveBlocked)).toBe('needs-you') // a background row
    expect(stateOf(list, PID.liveWaiting)).toBe('needs-you') // an interactive row
    expect(isLive(list.find(r => r.sessionId === PID.liveBlocked)!)).toBe(true)
  })

  test(`@F4 ${CHANGE} a read where no row has a pid keeps the old rule and marks nothing ended`, () => {
    const list = merged(withoutPid)
    expect(stateOf(list, PID.deadBlocked)).toBe('needs-you') // the old rule: blocked waits
    expect(stateOf(list, PID.closedWaiting)).toBe('needs-you')
    expect(stateOf(list, PID.closedIdle)).toBe('done')
    expect(stateOf(list, PID.live)).toBe('running')
    expect(stateOf(list, PID.exited)).toBe('ended') // `done` ends it as before, not by the pid rule
  })

  test(`@F72 ${CHANGE} this session's own id is never ended; a background \`done\` row stays ended`, () => {
    // This session's row lost its pid: it keeps its state while the others still read ended.
    const ownNoPid = pidRows.map(r => (r.sessionId === PID.self ? { ...r, pid: undefined } : r))
    const list = merged(ownNoPid)
    expect(stateOf(list, PID.self)).toBe('running')
    expect(stateOf(list, PID.closedIdle)).toBe('ended')
    // A background row that reports done is ended with or without a pid.
    const done = (pid: number | undefined) => merged([...pidRows, { ...pidRows.find(r => r.sessionId === PID.exited)!, sessionId: 'done-pid', pid }])
    expect(stateOf(done(4242), 'done-pid')).toBe('ended')
    expect(stateOf(done(undefined), 'done-pid')).toBe('ended')
    // A read that has no row for this session marks nothing ended: the list is not trusted, the next read corrects it.
    const noSelf = merged(pidRows.filter(r => r.sessionId !== PID.self))
    expect(stateOf(noSelf, PID.closedWaiting)).toBe('needs-you')
    expect(stateOf(noSelf, PID.closedIdle)).toBe('done')
  })

  test(`@F71 ${CHANGE} last activity is the newest of prompt, turn end and transcript; unknown reads "last activity unknown"`, async ($, on) => {
    const stamp = (ms: number) => JSON.stringify({ type: 'assistant', timestamp: new Date(ms).toISOString() })
    const base = record('x', { startedAt: T0, lastActivityAt: T0, asks: [] }) // lastActivityAt is the start: not an activity
    expect(lastActivity(base)).toBeNull()
    expect(lastActivity({ ...base, asks: [{ n: 1, text: 'a', kind: 'task', status: 'replied', at: T0 + 100 }] })).toBe(T0 + 100) // a prompt
    expect(lastActivity({ ...base, lastActivityAt: T0 + 500 })).toBe(T0 + 500) // a turn end
    expect(lastActivity({ ...base, lastActivityAt: T0 + 500, asks: [{ n: 1, text: 'a', kind: 'task', status: 'replied', at: T0 + 900 }] }, T0 + 700)).toBe(T0 + 900)
    expect(lastActivity({ ...base, lastActivityAt: T0 + 500 }, T0 + 700)).toBe(T0 + 700) // the transcript's last line
    // A closed terminal that the list alone knows: its last line time is the activity; with none the page says so.
    const id = PID.closedIdle
    const known = merged(pidRows, { lastLines: { [id]: T0 + 600_000 } }).find(r => r.sessionId === id)!
    expect(known.lastActivityAt).toBe(T0 + 600_000)
    expect(factsLine(known)).toContain('last activity')
    expect(factsLine(known)).not.toContain('unknown')
    const unknown = merged(pidRows).find(r => r.sessionId === id)!
    expect(factsLine(unknown)).toContain('last activity unknown')
    // The poller reads the transcript's tail with `tail`: the time of the last line that has one (the lines before it hold the rest).
    const w = world(on, { now: NOW, id: PID.self, cwd: '/work/pid-1' })
    w.agents.json = PID_JSON
    w.put(`/u/.claude/projects/-work-pid-8/${id}.jsonl`, [stamp(T0 + 100_000), stamp(T0 + 900_000), JSON.stringify({ type: 'cost-state', totalCostUSD: 1 })].join('\n') + '\n')
    await start($, w)
    await w.clock.advance(5000)
    const tail = w.procs.find(p => p.argv[0] === 'tail')
    expect(tail?.argv.slice(0, 2)).toEqual(['tail', '-c'])
    expect(w.snapshot().sessions.find(r => r.sessionId === id)?.lastActivityAt).toBe(T0 + 900_000)
    expect(factsLine(w.snapshot().sessions.find(r => r.sessionId === PID.closedWaiting)!)).toContain('last activity unknown') // no transcript
  })
})
