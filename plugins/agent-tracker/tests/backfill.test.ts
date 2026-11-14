import { describe, expect, test } from 'claude-code/testing'

import type { SessionRecord } from '../hooks/tracker/types'
import { ASKS_MAX, ASK_TEXT_MAX, WEEK_MS } from '../hooks/tracker/core'
import { ASK_TEXTS, EXPECTED, PROJECT_DIR, TRANSCRIPT_CWD, TRANSCRIPT_ID, TRANSCRIPT_TEXT } from './fixtures/transcript'
import { DIR, HOME, start, world } from './fixtures/world'
import type { World } from './fixtures/world'

const TAG = '@2026-11-13-agent-tracker'
const NOW = Date.parse('2026-11-11T00:00:00Z')
const PATH = `${HOME}/.claude/projects/${PROJECT_DIR}/${TRANSCRIPT_ID}.jsonl`
const STORED = `${DIR}/transcripts/${TRANSCRIPT_ID}.json`
const BIG = 5 * 1024 * 1024
const MINUTE = 60_000

// A session of this mod, in a world that holds one transcript of another session, then one backfill pass.
const run = async ($: Parameters<typeof start>[0], w: World, agents: object[] = []) => {
  w.git[TRANSCRIPT_CWD] = { commonDir: `${TRANSCRIPT_CWD}/.git`, branch: 'main' }
  w.agents.json = JSON.stringify(agents)
  await start($, w)
  await w.clock.advance(5000)
}
const stored = (w: World) => w.json(STORED) as SessionRecord

describe('backfill from transcripts', () => {
  test(`@F12 ${TAG} fixture transcript fields, live and ended`, async ($, on) => {
    const w = world(on, { now: NOW })
    w.put(PATH, TRANSCRIPT_TEXT)
    await run($, w)
    const r = stored(w)
    expect(r).toMatchObject({
      v: 1,
      sessionId: TRANSCRIPT_ID,
      source: 'transcript',
      cwd: EXPECTED.cwd,
      branch: EXPECTED.branch,
      title: EXPECTED.title,
      repo: { path: TRANSCRIPT_CWD, name: 'repo-7' },
      startedAt: EXPECTED.startedAt,
      lastActivityAt: EXPECTED.lastActivityAt,
      endedAt: null,
      usage: { tokensIn: EXPECTED.tokensIn, tokensOut: EXPECTED.tokensOut, toolErrors: EXPECTED.toolErrors, retries: 0 },
    })
    expect(r.asks.length).toBe(3)
    expect(r.asks.every(a => a.kind === 'not-classified')).toBe(true)
    expect(w.models.length).toBe(0) // the backfill makes no model call
    expect(w.procs.some(p => p.argv[0] === 'grep')).toBe(false) // a small file is read whole
    // Ended: absent from a good list.
    expect(w.snapshot().sessions.find(s => s.sessionId === TRANSCRIPT_ID)).toMatchObject({ source: 'transcript', state: 'ended' })
  })

  test(`@F12 ${TAG} a transcript of a session the list shows reads as live`, async ($, on) => {
    const w = world(on, { now: NOW })
    w.put(PATH, TRANSCRIPT_TEXT)
    await run($, w, [{ kind: 'interactive', status: 'busy', sessionId: TRANSCRIPT_ID, cwd: TRANSCRIPT_CWD, name: 'login work', startedAt: NOW }])
    expect(w.snapshot().sessions.find(s => s.sessionId === TRANSCRIPT_ID)).toMatchObject({ source: 'transcript', state: 'running', asks: expect.any(Array) })
  })

  test(`@F12 ${TAG} only sessions with no file, active in the last 7 days, and never its own`, async ($, on) => {
    const w = world(on, { now: NOW })
    const other = (id: string) => `${HOME}/.claude/projects/${PROJECT_DIR}/${id}.jsonl`
    w.put(PATH, TRANSCRIPT_TEXT)
    w.put(other('has-file'), TRANSCRIPT_TEXT)
    w.put(`${DIR}/sessions/has-file.json`, { v: 1, sessionId: 'has-file' })
    w.put(other(w.id), TRANSCRIPT_TEXT) // this session's own transcript: it has its own file
    w.put(`${HOME}/.claude/projects/${PROJECT_DIR}/notes.txt`, 'not a transcript')
    w.put(other('old'), TRANSCRIPT_TEXT) // a transcript, but older than 7 days
    w.mtimes.set(other('old'), NOW - WEEK_MS - 1)
    await run($, w)
    expect(w.writes.filter(p => p.includes('/transcripts/')).sort()).toEqual([STORED])
  })

  test(`@F13 ${TAG} transcript over 4 MiB read by search`, async ($, on) => {
    const w = world(on, { now: NOW })
    w.put(PATH, TRANSCRIPT_TEXT)
    w.sizes.set(PATH, BIG) // the engine reports 5 MiB; a whole read of it rejects
    await run($, w)
    const greps = w.procs.filter(p => p.argv[0] === 'grep')
    expect(greps.length).toBe(1)
    expect(greps[0]!.argv.at(-1)).toBe(PATH)
    expect(greps[0]!.argv).toContain('-o') // only the matching parts come back, never the lines
    // The search finds the prompt, usage and tool-error lines, and returns the fields of F12.
    const r = stored(w)
    expect(r).toMatchObject({
      cwd: EXPECTED.cwd,
      branch: EXPECTED.branch,
      title: EXPECTED.title,
      startedAt: EXPECTED.startedAt,
      lastActivityAt: EXPECTED.lastActivityAt,
      usage: { tokensIn: EXPECTED.tokensIn, tokensOut: EXPECTED.tokensOut, toolErrors: EXPECTED.toolErrors },
    })
    expect(r.asks.map(a => a.text)).toEqual(ASK_TEXTS)
  })

  test(`@F70 ${TAG} asks skip tool results, slash commands and system notes`, async ($, on) => {
    const w = world(on, { now: NOW })
    w.put(PATH, TRANSCRIPT_TEXT)
    await run($, w)
    const asks = stored(w).asks
    // Every prompt the owner typed, in order: the typed one, the image one (its text part), the queued one.
    expect(asks.map(a => a.text)).toEqual(ASK_TEXTS)
    expect(asks.map(a => a.n)).toEqual([1, 2, 3])
    expect(asks.map(a => a.at)).toEqual([Date.parse('2026-11-10T09:00:00.000Z'), Date.parse('2026-11-10T09:12:00.000Z'), Date.parse('2026-11-10T09:15:00.000Z')])
    // Not asks: tool results, /clear and its expansion, shell input and output, the interrupt note, the peer note,
    // the meta line, the task notification and the subagent's prompt.
    const text = asks.map(a => a.text).join('\n')
    for (const skipped of ['tool_result', '/clear', 'bash-', 'Request interrupted', 'Another session', 'Caveat', 'task-notification', 'subagent task']) {
      expect(text.includes(skipped)).toBe(false)
    }
  })

  test(`@F70 ${TAG} the list keeps the last 200 asks, each text cut at 2,000 characters`, async ($, on) => {
    const w = world(on, { now: NOW })
    const prompt = (i: number, text: string) =>
      JSON.stringify({ isSidechain: false, type: 'user', message: { role: 'user', content: text }, timestamp: '2026-11-10T09:00:00.000Z', promptSource: 'typed', i })
    const lines = Array.from({ length: ASKS_MAX + 5 }, (_, i) => prompt(i, i === ASKS_MAX + 4 ? 'x'.repeat(ASK_TEXT_MAX + 50) : `ask ${i}`))
    w.put(PATH, lines.join('\n') + '\n')
    await run($, w)
    const asks = stored(w).asks
    expect(asks.length).toBe(ASKS_MAX)
    expect(asks[0]!.n).toBe(6)
    expect(asks.at(-1)!.text.length).toBe(ASK_TEXT_MAX)
  })

  test(`@F55 ${TAG} unreadable transcript`, async ($, on) => {
    const w = world(on, { now: NOW })
    w.put(PATH, TRANSCRIPT_TEXT)
    w.unreadable.add(PATH)
    await run($, w)
    // The session shows, without its asks and numbers.
    expect(stored(w)).toMatchObject({ sessionId: TRANSCRIPT_ID, source: 'transcript', asks: [], usage: { tokensIn: 0, tokensOut: 0, toolErrors: 0, retries: 0 } })
    expect(w.snapshot().sessions.some(s => s.sessionId === TRANSCRIPT_ID)).toBe(true)
    // It is not tried again until the transcript changes.
    await w.clock.advance(2 * MINUTE)
    expect(w.writes.filter(p => p === STORED).length).toBe(1)
    // Read again on the next change.
    w.unreadable.delete(PATH)
    w.put(PATH, TRANSCRIPT_TEXT)
    await w.clock.advance(MINUTE)
    expect(stored(w).asks.length).toBe(3)
    expect(stored(w).usage.tokensIn).toBe(EXPECTED.tokensIn)
  })
})
