import { describe, expect, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'

import { MODEL, bandData, homeModel, isNeedsYou, taskItems, taskLists } from '../hooks/tracker/core'
import { boardData } from '../hooks/tracker/core/board-html'
import type { Ask, Entrypoints, LateChecks, SessionRecord } from '../hooks/tracker/types'
import { NOW, MIN, SELF, inState, rec } from './fixtures/band'
import { NOON, aloneTown, at, sess, snapAt } from './fixtures/pane'
import { ask, taskTown } from './fixtures/tasks'
import { DIR, settle, start, world } from './fixtures/world'
import type { World } from './fixtures/world'

const TAG = '@2026-11-13-agent-tracker'
const PROJECTS = '/u/.claude/projects/-work-x'
const iso = (ms: number) => new Date(ms).toISOString()

// A transcript as Claude Code writes it, as far as these tests read it: every line says how the session was started.
const transcript = (entrypoint: string, lines: { role: 'user' | 'assistant'; at: number; text: string }[]) =>
  lines
    .map(l => JSON.stringify({ type: l.role, timestamp: iso(l.at), entrypoint, message: { role: l.role, content: l.role === 'user' ? l.text : [{ type: 'text', text: l.text }] } }))
    .join('\n')

const askAt = (n: number, text: string, atMs: number, extra: Partial<Ask> = {}): Ask => ({ n, text, kind: 'task', status: 'replied', at: atMs, ...extra })
// A session of another mod: it ended (the list does not show it), with task asks and no verdict.
const ended = (id: string, asks: Ask[], extra: Partial<SessionRecord> = {}) =>
  inState(id, 'done', 10, 'web-app', id, { branch: 'feat/x', startedAt: NOW - 3 * 3600_000, lastActivityAt: NOW - 2 * 3600_000, asks, ...extra })

const world1 = (on: Parameters<typeof world>[0], sessions: SessionRecord[], transcripts: Record<string, string>) => {
  const w = world(on, { now: NOW })
  for (const r of sessions) w.put(`${DIR}/sessions/${r.sessionId}.json`, r)
  for (const [id, text] of Object.entries(transcripts)) w.put(`${PROJECTS}/${id}.jsonl`, text)
  return w
}
const completes = (w: World) => w.models.filter(m => m.op === 'complete')
const checks = (w: World) => w.json(`${DIR}/latechecks.json`) as LateChecks | null
const entrypoints = (w: World) => (w.json(`${DIR}/entrypoints.json`) as Entrypoints | null)?.by
const tick = async (w: World, ms = 5000) => {
  await w.clock.advance(ms)
  await settle()
}

describe('automated sessions: the entrypoint', () => {
  test(`${TAG} an sdk-* transcript is read once from its head, and the session leaves every list and count; cli, claude-desktop and unknown stay`, async ($, on) => {
    const text = (id: string) => transcript('x', [{ role: 'user', at: NOW - 3 * 3600_000, text: id }])
    const w = world1(
      on,
      ['sdk-a', 'sdk-b', 'cli-a', 'desk-a', 'none-a'].map(id => ended(id, [askAt(1, `${id} ask`, NOW - 3 * 3600_000, { verdict: 'partly' })])),
      { 'sdk-a': transcript('sdk-ts', [{ role: 'user', at: NOW - 3 * 3600_000, text: 'x' }]), 'sdk-b': transcript('sdk-cli', [{ role: 'user', at: NOW - 3 * 3600_000, text: 'x' }]), 'cli-a': transcript('cli', [{ role: 'user', at: NOW - 3 * 3600_000, text: 'x' }]), 'desk-a': transcript('claude-desktop', [{ role: 'user', at: NOW - 3 * 3600_000, text: 'x' }]), 'none-a': text('none-a').replace('"entrypoint":"x",', '') },
    )
    await start($, w)
    await tick(w)
    expect(entrypoints(w)).toEqual({ 'sdk-a': 'sdk-ts', 'sdk-b': 'sdk-cli', 'cli-a': 'cli', 'desk-a': 'claude-desktop', 'none-a': '' }) // empty: it says nothing, and is not looked up again
    const ids = w.snapshot().sessions.map(r => r.sessionId)
    expect(ids).toEqual(expect.arrayContaining(['cli-a', 'desk-a', 'none-a']))
    expect(ids).not.toContain('sdk-a')
    expect(ids).not.toContain('sdk-b')
    expect(taskLists(w.snapshot(), NOW).tasks.map(t => t.sessionId).sort()).toEqual(['cli-a', 'desk-a', 'none-a'])
    // Once: the next passes look at no transcript again.
    const looked = () => w.procs.filter(p => p.argv[0] === 'grep').length
    const before = looked()
    await tick(w, 120_000)
    expect(looked()).toBe(before)
    expect(w.writes.filter(p => p === `${DIR}/entrypoints.json`).length).toBe(1)
  })

  test(`${TAG} the newest transcripts are looked up first, 60 a pass, so today's sessions are known before older ones`, async ($, on) => {
    const ids = Array.from({ length: 61 }, (_, i) => `t-${String(i).padStart(2, '0')}`)
    const w = world1(on, [], Object.fromEntries(ids.map(id => [id, transcript('cli', [{ role: 'user', at: NOW - 3600_000, text: id }])])))
    ids.forEach((id, i) => w.mtimes.set(`${PROJECTS}/${id}.jsonl`, NOW - (61 - i) * 60_000)) // listed oldest first: t-00 oldest, t-60 newest
    await start($, w)
    await tick(w)
    const known = Object.keys(entrypoints(w) ?? {})
    expect(known.length).toBe(60)
    expect(known).toContain('t-60')
    expect(known).not.toContain('t-00')
  })

  test(`${TAG} a record kept before isInteractive existed is covered: its transcript says sdk, and it makes no band count, no running and no needs-you`, async ($, on) => {
    const old = inState('old-sdk', 'needs-you', 5, 'web-app', 'automated', { reason: 'waiting' }) // a file with no headless field
    const w = world1(on, [old], { 'old-sdk': transcript('sdk-py', [{ role: 'user', at: NOW - 3600_000, text: 'Review the supplied diff once' }]) })
    w.agents.json = JSON.stringify([{ kind: 'interactive', status: 'waiting', sessionId: 'old-sdk', cwd: '/work/web-app', name: 'automated', startedAt: NOW - 3600_000 }]) // the list still shows it
    await start($, w)
    await tick(w)
    const snap = w.snapshot()
    expect(snap.sessions.some(r => r.sessionId === 'old-sdk')).toBe(false)
    const data = bandData(snap, SELF, NOW)
    expect(data.needs.some(l => l.id === 'old-sdk')).toBe(false)
    expect([...data.running, ...data.needs].some(l => l.id === 'old-sdk')).toBe(false)
    expect(boardData(snap, [], NOW).counts.needsYou).toBe(0)
  })
})

describe('needs you is one set', () => {
  // Every kind of waiting session of a person, and the ones that are not: headless, ended, running.
  const town = (): SessionRecord[] => [
    sess('w-task', 'needs-you', 4, 'web-app', 'task', { repo: { path: '/work/web-app', name: 'web-app' }, reason: 'permission', asks: [ask(1, 'Fix the login redirect.', 10)] }),
    sess('w-question', 'needs-you', 3, 'web-app', 'question', { repo: { path: '/work/web-app', name: 'web-app' }, reason: 'question', asks: [ask(1, 'Why is it slow?', 8, { kind: 'question' })] }),
    sess('w-none', 'needs-you', 2, 'api', 'no ask', { repo: { path: '/work/api', name: 'api' }, reason: 'waiting', asks: [] }),
    sess('w-head', 'needs-you', 2, 'api', 'headless', { repo: { path: '/work/api', name: 'api' }, reason: 'waiting', headless: true }),
    sess('w-ended', 'ended', 90, 'api', 'ended', { repo: { path: '/work/api', name: 'api' }, endedAt: at(90) }),
    sess('w-run', 'running', 1, 'api', 'running', { repo: { path: '/work/api', name: 'api' } }),
    ...aloneTown('running').map(r => ({ ...r, sessionId: 'self-x' })),
  ]

  test(`${TAG} every person-session that waits is at the top of the list, with its reason and its ask when there is one`, () => {
    const rows = taskItems(snapAt(town()), NOON).filter(t => t.status === 'needs-you')
    expect(rows.map(t => t.sessionId).sort()).toEqual(['w-none', 'w-question', 'w-task'])
    const by = (id: string) => rows.find(t => t.sessionId === id)!
    expect(by('w-task')).toMatchObject({ text: 'Fix the login redirect.', detail: 'asks permission for 4m' })
    expect(by('w-question')).toMatchObject({ text: 'Why is it slow?', detail: 'waiting for your answer for 3m' }) // a question, not a task
    expect(by('w-none')).toMatchObject({ text: 'No ask is recorded for this session.', detail: 'waiting for your answer for 2m' })
    expect(taskItems(snapAt(town()), NOON).slice(0, 3).every(t => t.status === 'needs-you')).toBe(true) // on top
  })

  test(`${TAG} the band, the pane, the Board and the list count the same sessions`, () => {
    const snap = snapAt(town())
    const expected = snap.sessions.filter(isNeedsYou).length
    expect(expected).toBe(3)
    const tasks = taskItems(snap, NOON)
    const local = { midnight: NOON - 12 * 3600_000, clock: (ms: number) => String(ms), day: () => 'Mon' }
    const home = homeModel(snap, 'self-x', NOON, local, null, 80, [], tasks)
    const needRows = home.blocks.filter(b => b.kind === 'row' && b.key.startsWith('session:'))
    expect(bandData(snap, 'self-x', NOON, [], tasks).needs.length).toBe(expected)
    expect(needRows.length).toBe(expected) // the pane's Needs you section
    expect(boardData(snap, [], NOON).counts.needsYou).toBe(expected) // the Board's "M needs you now"
    expect(tasks.filter(t => t.status === 'needs-you').length).toBe(expected) // the rows on top of the list
    expect(bandData(snap, 'self-x', NOON, [], tasks).tasks.needsYou).toBe(expected)
  })
})

describe('the header never claims more than it knows', () => {
  test(`${TAG} nothing open and something unchecked: the data says unchecked, and the page says so instead of "every task is done"`, () => {
    const old = sess('u-1', 'ended', 300, 'api', 'old', { repo: { path: '/work/api', name: 'api' }, endedAt: at(300), asks: [ask(1, 'Rename the config keys.', 400)] })
    const d = boardData(snapAt([old]), [], NOON)
    expect(d.tasks).toEqual([])
    expect(d.unchecked.length).toBe(1)
    const none = boardData(snapAt(aloneTown()), [], NOON)
    expect(none.tasks.length + none.unchecked.length).toBe(0) // only here may the page claim every task is done
  })
})

describe('the late check of "Not checked"', () => {
  const ASKED = NOW - 3 * 3600_000
  const person = (id: string, n = 1) => ended(id, [askAt(n, `${id} ask one`, ASKED)])
  const text = (id: string, entry = 'cli') =>
    transcript(entry, [{ role: 'assistant', at: ASKED - 60_000, text: `BEFORE-${id}` }, { role: 'user', at: ASKED, text: `${id} ask one` }, { role: 'assistant', at: ASKED + MIN, text: `DONE-${id}: the work is in` }])
  const reply = JSON.stringify({ verdicts: [{ n: 1, verdict: 'partly' }] })

  test(`${TAG} one haiku call per session, never per ask, on the asks and what the agent wrote after the first; pinned to the model; verdicts are late`, async ($, on) => {
    const w = world1(on, [ended('two', [askAt(1, 'two ask one', ASKED), askAt(2, 'two ask two', ASKED + 5 * MIN)])], { two: text('two') })
    w.completeReply = () => JSON.stringify({ verdicts: [{ n: 1, verdict: 'partly' }, { n: 2, verdict: 'done' }] })
    await start($, w)
    await tick(w)
    expect(completes(w).length).toBe(1) // two unchecked asks, one call
    expect(completes(w)[0]!.model).toBe(MODEL)
    const prompt = (JSON.parse(completes(w)[0]!.text) as { prompt: string }).prompt
    expect(prompt).toContain('1: two ask one')
    expect(prompt).toContain('2: two ask two')
    expect(prompt).toContain('DONE-two: the work is in')
    expect(prompt).not.toContain('BEFORE-two') // only what came after the first unchecked ask
    expect(checks(w)!.by.two).toMatchObject({ verdicts: [{ n: 1, verdict: 'partly' }, { n: 2, verdict: 'done' }] })
    // The verdicts reach the asks as late ones; the list follows them.
    const two = w.snapshot().sessions.find(r => r.sessionId === 'two')!
    expect(two.asks.map(a => [a.n, a.verdict, a.source])).toEqual([[1, 'partly', 'late'], [2, 'done', 'late']])
    expect(taskLists(w.snapshot(), NOW).tasks.map(t => [t.key, t.status])).toEqual([['two:1', 'forgotten']])
  })

  test(`${TAG} it never runs again for a session, whether the call answered or not; a failed call is marked too`, async ($, on) => {
    const w = world1(on, [person('ok'), person('bad')], { ok: text('ok'), bad: text('bad') })
    w.completeReply = req => (req.prompt.includes('bad ask one') ? new Error('model down') : reply)
    await start($, w)
    await tick(w)
    expect(completes(w).length).toBe(2)
    expect(Object.keys(checks(w)!.by).sort()).toEqual(['bad', 'ok'])
    expect(checks(w)!.by.bad!.verdicts).toEqual([]) // marked, with nothing
    await tick(w, 60_000)
    await tick(w, 60_000)
    expect(completes(w).length).toBe(2) // a failed call is not repeated
  })

  test(`${TAG} at most 5 sessions a pass, from the session that holds the lease`, async ($, on) => {
    const ids = ['a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7']
    const w = world1(on, ids.map(id => person(id)), Object.fromEntries(ids.map(id => [id, text(id)])))
    w.completeReply = () => reply
    await start($, w)
    await tick(w)
    expect(completes(w).length).toBe(5)
    await tick(w, 60_000)
    expect(completes(w).length).toBe(7) // the rest wait for the next pass
    await tick(w, 60_000)
    expect(completes(w).length).toBe(7)
  })

  test(`${TAG} a session that does not hold the lease makes no late call`, async ($, on) => {
    const other = world1(on, [person('b1')], { b1: text('b1') })
    other.put(`${DIR}/poller.json`, { v: 1, sessionId: 'someone-else', heartbeat: other.clock.now() })
    other.put(`${DIR}/agents.json`, { v: 1, readAt: other.clock.now(), agents: [] })
    other.completeReply = () => reply
    await start($, other)
    await tick(other)
    expect(completes(other).length).toBe(0)
    expect(checks(other)).toBeNull()
  })

  test(`${TAG} not for an automated session, not before its entrypoint is known, and not when a turn already judged the ask`, async ($, on) => {
    const w = world1(
      on,
      [person('sdk'), person('judged'), ended('mixed', [askAt(1, 'mixed ask one', ASKED, { verdict: 'done' })]), person('fine')],
      { sdk: text('sdk', 'sdk-ts'), judged: text('judged'), mixed: text('mixed'), fine: text('fine') },
    )
    w.put(`${DIR}/sessions/judged.json`, ended('judged', [askAt(1, 'judged ask one', ASKED, { verdict: 'not-started' })]))
    w.completeReply = () => reply
    await start($, w)
    await tick(w)
    const asked = completes(w).map(m => (JSON.parse(m.text) as { prompt: string }).prompt)
    expect(asked.length).toBe(1)
    expect(asked[0]).toContain('fine ask one')
    expect(Object.keys(checks(w)!.by)).toEqual(['fine'])
  })
})

