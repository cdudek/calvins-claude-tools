import { describe, expect, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'

import { askStatuses } from '../hooks/tracker/core'
import { register } from '../hooks/tracker/register'
import type { Ask, SessionRecord } from '../hooks/tracker/types'
import { AGENTS, T0 } from './fixtures/agents'
import { DIR, start, world } from './fixtures/world'
import type { World } from './fixtures/world'

const TAG = '@2026-11-13-agent-tracker'
const NOW = T0 + 3_600_000
const ASK_LABELS = ['task', 'question']

const submit = ($: Engine, text: string) => $.prompt.submit({ text, wait: false, origin: { kind: 'composer' } })
const complete = ($: Engine) => $.turn.complete({ answer: 'ok', durationMs: 1, isAborted: false, turnId: 't1', reason: 'answer' })
const mine = (w: World) => w.json(`${DIR}/sessions/${w.id}.json`) as SessionRecord
const lastAsk = (w: World) => mine(w).asks.at(-1)!
const say = (w: World, text: string) => {
  w.messages = [{ role: 'user', text: 'go', toolUses: [] }, { role: 'assistant', text, toolUses: [] }]
}
// This session as the engine lists it.
const engineSays = (w: World, status: string) => {
  w.agents.json = JSON.stringify([{ kind: 'interactive', status, sessionId: w.id, cwd: w.cwd, name: 'this one', startedAt: NOW }])
}
const checks = (w: World) => w.models.filter(m => !ASK_LABELS.every(l => m.labels?.includes(l)))
// The model: an ask is a question when it holds "?", a checked message asks the owner when told to.
const model = (w: World, verdict: string | Error = 'asks-owner') => {
  w.classify = (text, labels) => (labels.includes('task') ? (text.includes('?') ? 'question' : 'task') : verdict)
}

describe('asks and the question check', () => {
  test(`@F15 ${TAG} prompt stored in order, classified at prompt.submit`, async ($, on) => {
    const w = world(on, { now: NOW })
    model(w)
    await start($, w)
    await submit($, 'fix the login redirect')
    await submit($, 'why does it loop?')
    const asks = mine(w).asks
    expect(asks.map(a => [a.n, a.text, a.kind])).toEqual([[1, 'fix the login redirect', 'task'], [2, 'why does it loop?', 'question']])
    expect(w.models.map(m => [m.op, m.labels, m.model])).toEqual([['classify', ASK_LABELS, 'haiku'], ['classify', ASK_LABELS, 'haiku']])
  })

  test(`@F16 ${TAG} ask status derives from session state`, () => {
    const asks = [1, 2].map(n => ({ n, text: 'x', kind: 'task', status: 'replied', at: 0 }) satisfies Ask)
    const status = (state: SessionRecord['state'], open: boolean) => askStatuses(asks, state, open).map(a => a.status)
    expect(status('running', true)).toEqual(['replied', 'in-progress'])
    expect(status('needs-you', true)).toEqual(['replied', 'needs-you'])
    expect(status('done', false)).toEqual(['replied', 'replied'])
  })

  test(`@F17 ${TAG} turn.complete reads the transcript and calls the check only when the final paragraph holds a question mark`, async ($, on) => {
    const w = world(on, { now: NOW })
    model(w)
    await start($, w)
    say(w, 'I read the config.\n\nWhich branch should I use?')
    await complete($)
    expect(checks(w).length).toBe(1)
    expect(checks(w)[0]).toMatchObject({ op: 'classify', model: 'haiku' })
    expect(checks(w)[0]!.text).toContain('Which branch should I use?') // the transcript's last assistant message, not the turn's answer
  })

  test(`@F18 ${TAG} the check registers no classic hook`, () => {
    const names: string[] = []
    const on = (name: string) => {
      names.push(name)
      return { catch: () => undefined }
    }
    register(on as never, {} as never)
    expect(names.length).toBeGreaterThan(0)
    expect(names.filter(n => n.startsWith('classic'))).toEqual([])
  })

  test(`@F19 ${TAG} flagged question shows needs you`, async ($, on) => {
    const w = world(on, { now: NOW })
    model(w)
    engineSays(w, 'idle')
    await start($, w)
    await submit($, 'pick a branch')
    say(w, 'Done so far.\n\nWhich branch should I use?')
    await complete($)
    expect(mine(w)).toMatchObject({ questionFlag: { at: NOW }, state: 'needs-you', reason: 'question' })
    await w.clock.advance(5000) // the engine says idle and the flag is set: still needs you
    expect(w.snapshot().sessions.find(s => s.sessionId === w.id)).toMatchObject({ state: 'needs-you', reason: 'question' })
    await submit($, 'main') // the next prompt clears the flag and the session runs again
    expect(mine(w)).toMatchObject({ questionFlag: null, state: 'running', reason: null })
  })

  test(`@F20 ${TAG} a session without the mod stays done`, async ($, on) => {
    const w = world(on, { now: NOW })
    engineSays(w, 'idle')
    w.agents.json = JSON.stringify([...JSON.parse(w.agents.json!), AGENTS[2]]) // an idle session with no file, no mod
    await start($, w)
    const other = w.snapshot().sessions.find(s => s.sessionId === AGENTS[2].sessionId)
    expect(other).toMatchObject({ state: 'done', source: 'engine', questionFlag: null })
  })

  test(`${TAG} the question check is not run for a subagent's turn or an aborted turn`, async ($, on) => {
    const w = world(on, { now: NOW })
    model(w)
    await start($, w)
    say(w, 'Which one?')
    await $.turn.complete({ answer: 'x', durationMs: 1, isAborted: false, turnId: 't2', reason: 'answer', agentId: 'sub-1' })
    await $.turn.complete({ answer: 'x', durationMs: 1, isAborted: true, turnId: 't3', reason: 'aborted' })
    expect(checks(w).length).toBe(0)
  })

  test(`@F56 ${TAG} check failure leaves done`, async ($, on) => {
    const w = world(on, { now: NOW })
    model(w, new Error('model down'))
    engineSays(w, 'idle')
    await start($, w)
    say(w, 'Which branch should I use?')
    await complete($)
    expect(checks(w).length).toBe(1)
    await w.clock.advance(5000)
    expect(mine(w)).toMatchObject({ questionFlag: null, state: 'done', reason: null })
  })

  test(`@F57 ${TAG} classify failure keeps the ask`, async ($, on) => {
    const w = world(on, { now: NOW })
    w.classify = () => new Error('model down')
    await start($, w)
    await submit($, 'fix the login redirect')
    expect(lastAsk(w)).toMatchObject({ n: 1, text: 'fix the login redirect', kind: 'not-classified' })
  })

  test(`@F72 ${TAG} in progress from submit to turn end`, async ($, on) => {
    const w = world(on, { now: NOW })
    model(w)
    engineSays(w, 'busy')
    await start($, w)
    await submit($, 'build it')
    expect(lastAsk(w).status).toBe('in-progress')
    await w.clock.advance(5000)
    expect(lastAsk(w).status).toBe('in-progress')
    say(w, 'Built it.')
    await complete($)
    expect(lastAsk(w).status).toBe('replied')
  })

  test(`@F73 ${TAG} needs you while the session waits during the ask`, async ($, on) => {
    const w = world(on, { now: NOW })
    model(w)
    engineSays(w, 'busy')
    await start($, w)
    await submit($, 'build it')
    engineSays(w, 'waiting')
    await w.clock.advance(5000)
    expect(mine(w).state).toBe('needs-you')
    expect(lastAsk(w).status).toBe('needs-you')
  })

  test(`@F74 ${TAG} replied at turn end, or needs you when flagged`, async ($, on) => {
    const w = world(on, { now: NOW })
    model(w)
    await start($, w)
    await submit($, 'first')
    say(w, 'All done.')
    await complete($)
    expect(lastAsk(w).status).toBe('replied')
    await submit($, 'second')
    say(w, 'Done.\n\nShould I merge it?')
    await complete($)
    expect(lastAsk(w).status).toBe('needs-you')
  })

  test(`@F75 ${TAG} the next prompt closes the previous ask as replied`, async ($, on) => {
    const w = world(on, { now: NOW })
    model(w)
    await start($, w)
    await submit($, 'first')
    expect(mine(w).asks.map(a => a.status)).toEqual(['in-progress'])
    await submit($, 'second')
    expect(mine(w).asks.map(a => a.status)).toEqual(['replied', 'in-progress'])
  })

  test(`@F132 ${TAG} no question mark in the final paragraph: no model call, no flag`, async ($, on) => {
    const w = world(on, { now: NOW })
    model(w)
    await start($, w)
    say(w, 'Should I use the new branch?\n\nI went with main, as it was the only one.')
    await complete($)
    expect(w.models.length).toBe(0)
    expect(mine(w).questionFlag).toBeNull()
  })
})
