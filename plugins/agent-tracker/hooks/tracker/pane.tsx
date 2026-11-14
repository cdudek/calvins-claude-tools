// The pane: Home, Session and Repo pages, and the /tracker words that open them. It only reads the snapshot and the
// clock; the one thing it writes is the clipboard. `$` is passed only to plain top-level functions.
import { atom, read } from 'claude-code'
import type { EngineInterface, On } from 'claude-code'

import { COMMAND_HELP, PANE_ID, RESUME_COPIED, homeModel, matchRepo, matchSession, repoModel, repoNotFound, resumeFailed, sessionModel, sessionNotFound } from './core'
import type { Page } from './core'
import type { Actions } from './pane/chrome'
import { homeView } from './pane/home'
import { missingView, repoView } from './pane/repo'
import { sessionView } from './pane/session'
import { newPane, openPane, startUi } from './store'
import type { State } from './store'
import type { Snapshot } from './types'

type Engine = EngineInterface
// The collector writes it; the band and the pane read it. The same literal, declared where it is read.
const snapshot = atom({ plugin: 'agent-tracker', key: 'snapshot' } as const, { at: 0, agentsOk: true, okAt: 0, failedReads: 0, sessions: [] } as Snapshot)

// The local day and clock face: core reads no time zone, so they come from here.
function localDay(now: number) {
  const day = new Date(now)
  day.setHours(0, 0, 0, 0)
  const two = (n: number) => String(n).padStart(2, '0')
  return { midnight: day.getTime(), clock: (ms: number) => `${two(new Date(ms).getHours())}:${two(new Date(ms).getMinutes())}` }
}

// Go to a page: Back returns to this one with the same row holding the ring (F89).
function go($: Engine, s: State, page: Page, from: string | null) {
  s.pane = { ...s.pane, history: [...s.pane.history, { page: s.pane.page, focus: from }], page, focus: null }
  $.ui.invalidate('ui.render')
}

function back($: Engine, s: State) {
  const last = s.pane.history.at(-1)
  s.pane = last === undefined ? newPane() : { ...s.pane, history: s.pane.history.slice(0, -1), page: last.page, focus: last.focus }
  $.ui.invalidate('ui.render')
}

function home($: Engine, s: State) {
  s.pane = newPane()
  $.ui.invalidate('ui.render')
}

type Surface = Parameters<Engine['ui']['copy']>[0]['surface']

// Copy the command that resumes an ended session. The toast says whether it worked (F49, F112).
async function copyResume($: Engine, text: string, surface: Surface) {
  const done = await $.ui.copy({ text, ...(surface === undefined ? {} : { surface }) })
  $.ui.toast(done.isCopied ? RESUME_COPIED : resumeFailed(done.reason))
}

// `/tracker session <text>` and `/tracker repo <text>`: the page of the match, else the not-found line (F59, F121, F122).
async function openFound($: Engine, s: State, text: string) {
  const found = matchSession((await read($, snapshot)).sessions, text)
  await openPane($, s, found === null ? { kind: 'missing', what: 'session', text } : { kind: 'session', id: found.sessionId })
}

async function openFoundRepo($: Engine, s: State, text: string) {
  const path = matchRepo((await read($, snapshot)).sessions, text)
  await openPane($, s, path === null ? { kind: 'missing', what: 'repo', text } : { kind: 'repo', path })
}

async function close($: Engine) {
  await $.ui.close({ id: PANE_ID }).catch(() => undefined)
}

export const registerPane = (on: On, s: State) => {
  // The pane's words: none (Home), `session <text>`, `repo <text>`, and a hint for any other. The band's words go on.
  on('command.run', { command: 'tracker' }, async ($, e, next) => {
    const args = e.args.trim()
    if (/^(details|compact|copy|band\s+(on|off))$/i.test(args)) return next(e)
    const [word = '', ...rest] = args.split(/\s+/)
    const text = rest.join(' ')
    const kind = word.toLowerCase()
    if (word === '' || ((kind === 'session' || kind === 'repo') && text === '')) await openPane($, s)
    else if (kind === 'session') await openFound($, s, text)
    else if (kind === 'repo') await openFoundRepo($, s, text)
    else return { text: COMMAND_HELP }
    return { text: '' }
  })

  on('ui.render', { component: 'Pane', requestId: 'tracker' }, async ($, e) => {
    await startUi($, s)
    const snap = await read($, snapshot)
    const now = await $.clock.now()
    const selfId = await $.session.id()
    const ui = $.ui.resolve(e)
    const columns = e.props.bodyColumns
    const local = localDay(now)
    const page = s.pane.page
    const session = page.kind === 'session' ? sessionModel(snap, page.id, now, local) : null
    const actions: Actions = {
      open: (key, to) => go($, s, to, key),
      back: () => back($, s),
      home: () => home($, s),
      close: () => void close($),
      resume: () => void copyResume($, session?.resume ?? '', e.surface),
    }
    if (session !== null) return sessionView(ui, session, actions, columns)
    if (page.kind === 'session') return missingView(ui, sessionNotFound(page.id), actions)
    if (page.kind === 'missing') return missingView(ui, page.what === 'session' ? sessionNotFound(page.text) : repoNotFound(page.text), actions)
    if (page.kind === 'repo') {
      const repo = repoModel(snap, page.path, now, selfId)
      return repo === null ? missingView(ui, repoNotFound(page.path), actions) : repoView(ui, repo, actions, columns)
    }
    // Home keeps its order while the pane has the keyboard, and sorts again when the keyboard leaves (F43).
    const model = homeModel(snap, selfId, now, local, e.props.isFocused ? s.pane.frozen : null)
    s.pane.frozen = e.props.isFocused ? model.frozen : null
    return homeView(ui, model, actions, columns, s.pane.focus)
  })
}
