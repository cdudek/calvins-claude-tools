import { describe, expect, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'

import { MODEL, NOTES_MAX, addNotes, parseNotes, parseRevisions } from '../hooks/tracker/core'
import type { Note, SessionRecord } from '../hooks/tracker/types'
import { T0 } from './fixtures/agents'
import { DIR, settle, start, world } from './fixtures/world'
import type { World } from './fixtures/world'

const TAG = '@2026-11-13-agent-tracker'
const NOW = T0 + 3_600_000

// A last message long enough to be read (200 characters and more).
const LONG = `I moved the retry into the client. ${'The tests hit the real payment sandbox. '.repeat(6)}I skipped the browser step.`
const REPLY = JSON.stringify({ know: ['Tests hit the real payment sandbox, not a mock', 'Skipped the browser step'], decided: ['Used the existing retry helper'] })

const complete = ($: Engine) => $.turn.complete({ answer: 'ok', durationMs: 1, isAborted: false, turnId: 't1', reason: 'answer' })
const mine = (w: World) => w.json(`${DIR}/sessions/${w.id}.json`) as SessionRecord
const say = (w: World, text: string) => {
  w.messages = [{ role: 'user', text: 'go', toolUses: [] }, { role: 'assistant', text, toolUses: [] }]
}
const finish = async ($: Engine, w: World, text: string, reply: string | Error | null = REPLY) => {
  w.completeReply = () => reply ?? undefined // null: the call is refused
  say(w, text)
  await complete($)
  await settle() // the notes call runs after the turn went on
}
const completes = (w: World) => w.models.filter(m => m.op === 'complete')
const prompt = ($: Engine, text: string) => $.prompt.submit({ text, wait: false, origin: { kind: 'composer' } })
const promptOf = (w: World, i: number) => (JSON.parse(completes(w)[i]!.text) as { prompt: string }).prompt

describe('you should know, decided without you: the notes of a turn', () => {
  test(`${TAG} items are parsed from the last message and stored on the session record, unseen`, async ($, on) => {
    const w = world(on, { now: NOW })
    await start($, w)
    await finish($, w, LONG)
    expect(mine(w).notes).toEqual([
      { id: 'n1', kind: 'know', text: 'Tests hit the real payment sandbox, not a mock', at: NOW, seen: false },
      { id: 'n2', kind: 'know', text: 'Skipped the browser step', at: NOW, seen: false },
      { id: 'n3', kind: 'decided', text: 'Used the existing retry helper', at: NOW, seen: false },
    ])
    expect(completes(w).length).toBe(1)
    // The prompt carries the turn's last assistant message, read from the session's transcript.
    expect(completes(w)[0]!.text).toContain('I skipped the browser step.')
    // A second turn adds to them; ids go on counting.
    await finish($, w, `${LONG} Again.`, JSON.stringify({ know: [], decided: ['Took the default port'] }))
    expect(mine(w).notes!.map(n => [n.id, n.kind])).toEqual([['n1', 'know'], ['n2', 'know'], ['n3', 'decided'], ['n4', 'decided']])
  })

  test(`${TAG} a message under 200 characters is skipped: no model call, nothing stored`, async ($, on) => {
    const w = world(on, { now: NOW })
    await start($, w)
    await finish($, w, 'x'.repeat(199))
    expect(completes(w).length).toBe(0)
    expect(mine(w).notes).toBeUndefined()
    await finish($, w, 'x'.repeat(200)) // the gate is 200 and over
    expect(completes(w).length).toBe(1)
  })

  test(`${TAG} the call pins haiku, the one MODEL constant, and asks for JSON of two lists`, async ($, on) => {
    const w = world(on, { now: NOW })
    await start($, w)
    await finish($, w, LONG)
    expect(MODEL).toBe('haiku')
    const call = JSON.parse(completes(w)[0]!.text) as { model: string; prompt: string }
    expect(call.model).toBe('haiku')
    expect(completes(w)[0]!.model).toBe('haiku')
    expect(call.prompt).toContain('{"know":')
    expect(call.prompt).toContain('"decided"')
    expect(call.prompt).toContain('At most 3 per list')
  })

  test(`${TAG} a reply that is not the JSON asked for stores nothing; so does a refused call`, async ($, on) => {
    const w = world(on, { now: NOW })
    await start($, w)
    for (const bad of ['sorry, no', '{"know": "a string"}', '{"know": [1, 2]}', '[]', '{"other": []}', '{"know": ["a"', new Error('model down'), null]) {
      await finish($, w, LONG, bad)
      expect([bad, mine(w).notes]).toEqual([bad, undefined])
    }
    // The turn itself still ended: the session is not left running.
    expect(mine(w).asks).toEqual([])
    // Empty lists are a good answer with nothing in it.
    await finish($, w, LONG, '{"know":[],"decided":[]}')
    expect(mine(w).notes).toBeUndefined()
  })

  test(`${TAG} a subagent's turn and an aborted turn read no notes`, async ($, on) => {
    const w = world(on, { now: NOW })
    await start($, w)
    w.completeReply = () => REPLY
    say(w, LONG)
    await $.turn.complete({ answer: 'x', durationMs: 1, isAborted: false, turnId: 't2', reason: 'answer', agentId: 'sub-1' })
    await $.turn.complete({ answer: 'x', durationMs: 1, isAborted: true, turnId: 't3', reason: 'aborted' })
    await settle()
    expect(completes(w).length).toBe(0)
  })

  test(`${TAG} the notes of a turn are written to the session's own file only`, async ($, on) => {
    const w = world(on, { now: NOW })
    await start($, w)
    await finish($, w, LONG)
    expect(w.writes.every(p => p === `${DIR}/sessions/${w.id}.json` || p === `${DIR}/poller.json` || p === `${DIR}/agents.json`)).toBe(true)
    expect(w.procs.every(p => ['claude', 'git', 'gh'].includes(p.argv[0]!))).toBe(true)
  })
})

describe('how each open task stands: the same call, one per turn', () => {
  const VERDICTS = JSON.stringify({ know: [], decided: [], verdicts: [{ n: 1, verdict: 'replaced', by: 2 }, { n: 2, verdict: 'done' }, { n: 3, verdict: 'done' }] })

  test(`${TAG} the one notes call also judges every open task ask; the verdicts are stored on the asks, a question gets none`, async ($, on) => {
    const w = world(on, { now: NOW })
    w.classify = text => (text.startsWith('Why') ? 'question' : 'task')
    await start($, w)
    for (const text of ['Add retry on 401 responses', 'Fix the login redirect', 'Why is it slow?']) await prompt($, text)
    await settle()
    await finish($, w, LONG, VERDICTS)
    expect(completes(w).length).toBe(1) // still one call for the turn
    expect(promptOf(w, 0)).toContain('1: Add retry on 401 responses')
    expect(promptOf(w, 0)).toContain('2: Fix the login redirect')
    expect(promptOf(w, 0)).not.toContain('Why is it slow') // a question is not a task
    expect(mine(w).asks.map(a => [a.n, a.kind, a.verdict, a.replacedBy])).toEqual([[1, 'task', 'replaced', 2], [2, 'task', 'done', undefined], [3, 'question', undefined, undefined]])
    expect(mine(w).notes).toBeUndefined() // no lines in the reply: no notes
    // The next turn asks about the tasks not judged done, and takes a new verdict over the old one.
    await finish($, w, `${LONG} Again.`, JSON.stringify({ verdicts: [{ n: 1, verdict: 'partly' }] }))
    expect(completes(w).length).toBe(2)
    expect(promptOf(w, 1)).toContain('1: Add retry')
    expect(promptOf(w, 1)).not.toContain('2: Fix the login') // judged done: not asked again
    expect(mine(w).asks[0]).toMatchObject({ n: 1, verdict: 'partly' })
    expect(mine(w).asks[0]!.replacedBy).toBeUndefined()
  })

  test(`${TAG} a verdict that names a task nobody asked about is dropped; the notes of the same reply stay; a short turn makes no call`, async ($, on) => {
    const w = world(on, { now: NOW })
    await start($, w)
    await prompt($, 'Do the thing')
    await settle()
    await finish($, w, LONG, JSON.stringify({ know: ['A step was skipped'], decided: [], verdicts: [{ n: 9, verdict: 'done' }, { n: 1, verdict: 'replaced', by: 1 }] }))
    expect(mine(w).asks[0]!.verdict).toBeUndefined()
    expect(mine(w).notes!.map(n => n.text)).toEqual(['A step was skipped'])
    await finish($, w, 'x'.repeat(199), JSON.stringify({ verdicts: [{ n: 1, verdict: 'done' }] }))
    expect(completes(w).length).toBe(1) // the skip rule holds: nothing is judged
    expect(mine(w).asks[0]!.verdict).toBeUndefined()
  })

  test(`${TAG} with no task open the prompt is the notes prompt alone: no verdicts asked`, async ($, on) => {
    const w = world(on, { now: NOW })
    w.classify = () => 'question'
    await start($, w)
    await prompt($, 'Why?')
    await settle()
    await finish($, w, LONG)
    expect(completes(w).length).toBe(1)
    expect(promptOf(w, 0)).not.toContain('verdicts')
  })
})

describe('the notes as data', () => {
  test(`${TAG} parseNotes takes fences and words around the JSON, cleans each line and keeps 3 of each kind`, () => {
    expect(parseNotes('```json\n{"know":["a"],"decided":["b"]}\n```')).toEqual({ know: ['a'], decided: ['b'] })
    expect(parseNotes('Here you go: {"know":["a","b","c","d"],"decided":[]} done')).toEqual({ know: ['a', 'b', 'c'], decided: [] })
    expect(parseNotes('{"know":["  two\\nlines \\u001b[31mred "]}')).toEqual({ know: ['two lines [31mred'], decided: [] }) // control characters are gone
    expect(parseNotes('{"know":["x".repeat(500)]}')).toBeNull()
    const long = parseNotes(JSON.stringify({ know: ['y'.repeat(500)] }))!
    expect([...long.know[0]!].length).toBe(160)
  })

  test(`${TAG} at most 50 notes per session, the newest kept`, () => {
    let notes: Note[] | undefined
    for (let i = 0; i < 30; i++) notes = addNotes(notes, { know: [`k${i}`], decided: [`d${i}`] }, NOW + i)
    expect(notes!.length).toBe(NOTES_MAX)
    expect(notes!.at(-1)!.text).toBe('d29')
    expect(notes![0]!.text).toBe('k5') // 60 added, the first 10 dropped
    expect(new Set(notes!.map(n => n.id)).size).toBe(NOTES_MAX)
  })

  test(`${TAG} the plan's Revisions: each dated line, only the ones under that heading`, () => {
    const plan = ['# Plan', '', '## Order of work', '- **2020-01-01, X:** not a revision', '', '## Revisions', '', 'Only after approval.', '', '- **2026-11-14, F92:** the owner chose "Escape returns keys only". F92 reworded.', '- **2026-11-12:** dropped the SVG', '', '## Notes', '- **2026-11-01, F1:** not a revision either'].join('\n')
    const out = parseRevisions(plan)
    expect(out.map(r => [r.ref, r.text])).toEqual([['F92', 'the owner chose "Escape returns keys only". F92 reworded.'], ['', 'dropped the SVG']])
    expect(new Date(out[0]!.at).getFullYear()).toBe(2026)
    expect(parseRevisions(null)).toEqual([])
    expect(parseRevisions('# no revisions')).toEqual([])
  })
})
