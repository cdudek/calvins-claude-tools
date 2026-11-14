import { describe, expect, mock, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'

import { MODEL, bandData, isLive, taskLists } from '../hooks/tracker/core'
import * as agentsFixture from './fixtures/agents'
import * as bandFixture from './fixtures/band'
import * as milestoneFixture from './fixtures/milestone'
import * as scansFixture from './fixtures/scans'
import * as transcriptFixture from './fixtures/transcript'
import { DIR, start, world } from './fixtures/world'
import type { World } from './fixtures/world'

declare function setTimeout(run: () => void, ms: number): unknown // the runtime has it; the plugin's type set does not

const TAG = '@2026-11-13-agent-tracker'
const NOW = 1_700_003_600_000
const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

// Reads only: git to read a repo, gh to read PRs, `claude agents --json`, grep to search a transcript.
const GIT_READS = ['rev-parse', 'worktree', 'status', 'log', 'diff', 'show', 'ls-files']
export const isRead = (argv: readonly string[]) => {
  const [cmd, ...args] = argv
  while (args[0] === '-c') args.splice(0, 2) // git's leading `-c key=value` pairs
  const [sub, ...rest] = args
  if (cmd === 'claude') return sub === 'agents' && rest.join(' ') === '--json'
  if (cmd === 'gh') return sub === 'pr' && (rest[0] === 'list' || rest[0] === 'view')
  if (cmd === 'grep') return true
  if (cmd !== 'git') return false
  if (sub === 'remote') return rest.join(' ') === 'get-url origin'
  if (sub === 'branch') return rest.join(' ') === '--show-current'
  return GIT_READS.includes(sub ?? '') && !(sub === 'worktree' && rest[0] !== 'list')
}

// One scripted session: a start, two prompts (one turn asks a question), a failing tool call, a goal, half a
// minute of polling and the end. Whatever the mod calls while it runs is recorded in the world.
const runSession = async ($: Engine, w: World, isHolder: boolean) => {
  w.classify = (_, labels) => (labels.includes('task') ? 'task' : 'asks-owner')
  w.agents.json = JSON.stringify([{ kind: 'interactive', status: 'idle', sessionId: w.id, cwd: w.cwd, name: 'this one', startedAt: NOW }])
  // Another session holds the lease and keeps it fresh.
  const other = () => {
    w.put(`${DIR}/poller.json`, { v: 1, sessionId: 'someone-else', heartbeat: w.clock.now() })
    w.put(`${DIR}/agents.json`, { v: 1, readAt: w.clock.now(), agents: [] })
  }
  if (!isHolder) other()
  let raised = { tools: 0, commands: 0 }
  await start($, w)
  const prompt = (text: string) => $.prompt.submit({ text, wait: false, origin: { kind: 'composer' } })
  const turn = () => $.turn.complete({ answer: 'x', durationMs: 1, isAborted: false, turnId: 't', reason: 'answer' })
  await prompt('first ask')
  w.messages = [{ role: 'assistant', text: 'Done.\n\nWhich branch should I use?', toolUses: [] }]
  await turn()
  await prompt('second ask')
  w.messages = [{ role: 'assistant', text: 'All done.', toolUses: [] }]
  await turn()
  // A turn whose last message is 200 characters or more: one more call, the notes read, pinned to the same model.
  await prompt('third ask')
  w.completeReply = () => JSON.stringify({ know: ['A step was skipped'], decided: ['A default was taken'], verdicts: [{ n: 1, verdict: 'done' }] })
  w.messages = [{ role: 'assistant', text: `Finished the work. ${'I skipped a step and took a default. '.repeat(8)}`, toolUses: [] }]
  await turn()
  await new Promise<void>(done => setTimeout(done, 0)) // the notes call runs after the turn went on
  w.tool = () => ({ result: {}, isError: true })
  await $.tool.call({ tool: 'Bash', command: 'make' })
  raised.tools += 1
  await $.command.run({ command: 'goal', args: 'ship it', origin: { kind: 'composer' }, presentation: {} as never })
  raised.commands += 1
  for (let i = 0; i < 6; i++) {
    if (!isHolder) other()
    await w.clock.advance(5000)
  }
  await $.session.end({ reason: 'other', sessionId: w.id, resume: {} as never })
  return raised
}

describe('headless sessions', () => {
  const NOTE_LONG = `Finished. ${'I skipped a step and took a default. '.repeat(8)}\n\nWhich branch should I use?`
  const drive = async ($: Engine, w: World) => {
    const prompt = (text: string) => $.prompt.submit({ text, wait: false, origin: { kind: 'composer' } })
    await prompt('reply with ok')
    w.completeReply = () => JSON.stringify({ know: ['x'], decided: [], verdicts: [{ n: 1, verdict: 'not-started' }] })
    w.messages = [{ role: 'assistant', text: NOTE_LONG, toolUses: [] }]
    await $.turn.complete({ answer: 'x', durationMs: 1, isAborted: false, turnId: 't', reason: 'answer' })
    await new Promise<void>(done => setTimeout(done, 0))
  }
  const record = (w: World) => w.json(`${DIR}/sessions/${w.id}.json`) as { headless?: boolean; asks: { kind: string; verdict?: string }[]; notes?: unknown[] }

  test(`${TAG} a -p run (session.start says it is not interactive) makes no model call at all, and is on no list or count`, async ($, on) => {
    const w = world(on, { now: NOW })
    await $.session.start({ cwd: w.cwd, surface: undefined as never, isInteractive: false })
    await new Promise<void>(done => setTimeout(done, 0))
    await drive($, w)
    expect(w.models).toEqual([]) // no classification, no notes or verdict call, no question check
    expect(record(w)).toMatchObject({ headless: true })
    expect(record(w).asks.every(a => a.kind === 'not-classified' && a.verdict === undefined)).toBe(true)
    expect(record(w).notes).toBeUndefined()
    const snap = w.snapshot()
    const mine = snap.sessions.find(r => r.sessionId === w.id)!
    expect(isLive(mine)).toBe(false) // not running, not needs-you, in no band count
    expect(taskLists({ ...snap, sessions: [{ ...mine, state: 'ended', endedAt: NOW }] }, NOW + 3 * 3600_000).tasks).toEqual([])
    expect(bandData(snap, 'other', NOW).live).toBe(0)
  })

  test(`${TAG} with no session.start (after /clear) a session that draws nowhere is headless; one that draws is not`, async ($, on) => {
    const w = world(on, { now: NOW })
    on('session.surfaces', () => ({ value: [] }) as never)
    await $.prompt.submit({ text: 'reply with ok', wait: false, origin: { kind: 'composer' } })
    await new Promise<void>(done => setTimeout(done, 0))
    expect(record(w).headless).toBe(true)
    expect(w.models).toEqual([])
  })

  test(`${TAG} an interactive session is not headless and still makes its calls`, async ($, on) => {
    const w = world(on, { now: NOW })
    await start($, w)
    await drive($, w)
    expect(record(w).headless).toBeUndefined()
    expect(w.models.length).toBeGreaterThan(0)
    expect(record(w).asks[0]).toMatchObject({ kind: 'task', verdict: 'not-started' })
  })
})

describe('safety', () => {
  test(`@F60 ${TAG} every model call passes the MODEL constant`, async ($, on) => {
    const w = world(on, { now: NOW })
    await runSession($, w, true)
    expect(MODEL).toBe('haiku')
    expect(w.models.length).toBeGreaterThan(0)
    expect(w.models.every(m => (m.op === 'classify' || m.op === 'complete') && m.model === MODEL)).toBe(true) // classify and complete, never fork
    expect(w.models.some(m => m.op === 'complete')).toBe(true) // the notes call is among them
  })

  test(`@F61 ${TAG} call counts for one ask and one turn, none for a turn without a question mark`, async ($, on) => {
    const w = world(on, { now: NOW })
    await runSession($, w, true)
    const asks = w.models.filter(m => m.labels?.includes('task'))
    const checks = w.models.filter(m => m.labels?.includes('asks-owner'))
    expect(asks.map(m => m.text)).toEqual(['first ask', 'second ask', 'third ask']) // one classification per ask
    const notes = w.models.filter(m => m.op === 'complete')
    expect(notes.length).toBe(1) // one notes call, for the one turn of 200 characters or more: it also judges the open tasks, with no call of its own
    expect(notes[0]!.text).toContain('verdicts')
    expect(notes[0]!.text).toContain('1: first ask')
    expect(checks.length).toBe(1) // one check, for the turn whose final paragraph holds a "?"; none for the other
    expect(checks[0]!.text).toContain('Which branch should I use?')
  })

  test(`@F62 ${TAG} no write call reaches a session`, async ($, on) => {
    const session = mock.session(on)
    const w = world(on, { now: NOW })
    const raised = await runSession($, w, true)
    expect(session.appended().length).toBe(0) // no hidden note
    expect(w.origins.every(o => o === 'composer')).toBe(true) // no prompt of its own: no automatic continue, no queued answer
    expect(w.toolCalls).toBe(raised.tools) // no tool call, no agent, no command of its own
    expect(w.commandRuns).toBe(raised.commands)
    expect(w.procs.length).toBeGreaterThan(0)
    expect(w.procs.filter(p => !isRead(p.argv)).map(p => p.argv.join(' '))).toEqual([]) // git, gh and bd are read, never written
    expect(w.procs.some(p => p.argv[0] === 'bd')).toBe(false)
    expect(isRead(['git', 'push'])).toBe(false)
    expect(isRead(['git', 'worktree', 'remove', 'x'])).toBe(false)
    expect(isRead(['git', 'remote', 'add', 'x', 'y'])).toBe(false)
    expect(isRead(['git', '-c', 'core.hooksPath=/dev/null', 'remote', 'get-url', 'origin'])).toBe(true)
    expect(isRead(['gh', 'pr', 'merge'])).toBe(false)
    expect(isRead(['bd', 'close', 'x'])).toBe(false)
  })

  test(`@F63 ${TAG} every fs write path is under the folder`, async ($, on) => {
    const w = world(on, { now: NOW })
    await runSession($, w, true)
    expect(w.writes.length).toBeGreaterThan(0)
    expect(w.writes.filter(p => !p.startsWith(`${DIR}/`))).toEqual([])
  })

  test(`@F130 ${TAG} every write path is the session's own file, a lease file while held, a transcripts file or settings.json`, async ($, on) => {
    const allowed = new RegExp(`^${esc(DIR)}/(sessions/${esc('self-0000')}\\.json|settings\\.json|poller\\.json|agents\\.json|transcripts/[^/]+\\.json)$`)
    const holder = world(on, { now: NOW })
    await runSession($, holder, true)
    expect(holder.writes.filter(p => !allowed.test(p))).toEqual([])
    expect(holder.writes.some(p => p.endsWith('/poller.json'))).toBe(true) // held: both lease files are written
    expect(holder.writes.some(p => p.endsWith('/agents.json'))).toBe(true)
  })

  test(`@F130 ${TAG} a session that does not hold the lease writes no lease file`, async ($, on) => {
    const w = world(on, { now: NOW })
    await runSession($, w, false)
    expect(w.writes.length).toBeGreaterThan(0)
    expect(w.writes.every(p => p === `${DIR}/sessions/${w.id}.json`)).toBe(true)
  })

  test(`@F64 ${TAG} the committed fixtures hold no names, paths or addresses`, () => {
    const leak = /\/Users\/|\/home\/|[\w.+-]+@[\w-]+\.[\w.-]+/
    for (const [name, fixture] of Object.entries({ agentsFixture, bandFixture, milestoneFixture, scansFixture, transcriptFixture })) expect([name, leak.test(JSON.stringify(fixture))]).toEqual([name, false])
    // The scan itself catches each kind.
    expect(['/Users/someone/repo', '/home/someone', 'someone@example.com'].every(s => leak.test(s))).toBe(true)
  })

  test(`@F65 ${TAG} no listener: no server, no port, no spawned process, no network call`, async ($, on) => {
    const w = world(on, { now: NOW })
    await runSession($, w, true)
    expect(w.net).toEqual([])
    expect(w.procs.filter(p => !isRead(p.argv))).toEqual([])
  })
})
