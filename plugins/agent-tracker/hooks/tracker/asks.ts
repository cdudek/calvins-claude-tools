// The asks and the question check: what the owner asked, in order, and whether a finished turn asks them back.
// Every hook is an observer: it lets the event through first and never throws after that.
import type { On } from 'claude-code'

import { ASKS_MAX, ASK_TEXT_MAX, MODEL, addTokens, finalParagraphHasQuestion } from './core'
import { initOwn, saveOwn } from './store'
import type { State } from './store'

// The owner's own prompts: a terminal, the bridge and an SDK host. Notifications, triggers and peers are not asks.
const OWNER = new Set(['composer', 'bridge', 'sdk'])
const CHECK_LABELS = ['asks-owner', 'does-not-ask'] as const

export const registerAsks = (on: On, s: State) => {
  on('prompt.submit', async ($, e, next) => {
    const r = await next(e)
    try {
      if ('drop' in r || e.command !== undefined || e.isMeta === true || !OWNER.has(e.origin.kind)) return r
      await initOwn($, s) // after a /clear no session.start fires: this starts the new record
      const now = await $.clock.now()
      const text = e.text.slice(0, ASK_TEXT_MAX)
      let n = 0
      s.turn.open = true
      // The next prompt closes the previous ask (the status is derived on write) and clears the question flag.
      await saveOwn($, s, m => {
        n = (m.asks.at(-1)?.n ?? 0) + 1
        const asks = [...m.asks, { n, text, kind: 'not-classified' as const, status: 'in-progress' as const, at: now }].slice(-ASKS_MAX)
        return { ...m, asks, questionFlag: null, state: 'running', reason: null, unknownValue: null, lastActivityAt: now }
      })
      // One classification per ask, after the prompt went on; a failure keeps the ask as "not classified" (F57).
      void $.model
        .classify(text, ['task', 'question'], { model: MODEL })
        .then(kind => (kind === 'task' || kind === 'question' ? saveOwn($, s, m => ({ ...m, asks: m.asks.map(a => (a.n === n ? { ...a, kind } : a)) })) : undefined))
        .catch(() => undefined)
    } catch {
      // an observer never fails the prompt
    }
    return r
  })

  on('turn.complete', async ($, e, next) => {
    const r = await next(e)
    try {
      const { usage } = e // tokens count for every turn of the session, a subagent's too (F21)
      if (usage) await saveOwn($, s, m => ({ ...m, usage: addTokens(m.usage, usage) }))
      if (e.agentId !== undefined) return r // but only the main loop's turn is this session's turn
      const now = await $.clock.now()
      s.turn.open = false
      let isFlagged = false
      if (!e.isAborted) {
        // The last assistant message from the session's own transcript; never a classic hook, which managed machines skip.
        const rows = await $.session.messages().catch(() => [])
        const message = [...rows].reverse().find(m => m.role === 'assistant')?.text ?? e.answer
        if (finalParagraphHasQuestion(message)) {
          const verdict = await $.model.classify(message.slice(-ASK_TEXT_MAX), CHECK_LABELS, { model: MODEL }).catch(() => undefined)
          isFlagged = verdict === 'asks-owner'
        }
      }
      const flag = isFlagged ? { questionFlag: { at: now }, state: 'needs-you' as const, reason: 'question' as const } : {}
      await saveOwn($, s, m => ({ ...m, lastActivityAt: now, ...flag }))
    } catch {
      // an observer never fails the turn
    }
    return r
  })
}
