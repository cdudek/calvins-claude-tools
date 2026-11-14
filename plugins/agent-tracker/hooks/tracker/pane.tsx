// The pane: Home, Repo, Milestone, Feature and Session pages, and the /tracker words that open them. It only reads the
// snapshot, the clock and the change folders; the one thing it writes is the clipboard. `$` is passed only to plain
// top-level functions.
import { atom, read } from 'claude-code'
import type { EngineInterface, On } from 'claude-code'

import { COMMAND_HELP, PANE_ID, PANE_OPENED, RESUME_COPIED, featureModel, homeModel, matchRepo, matchSession, milestoneModel, milestoneNotFound, missingModel, repoModel, repoNotFound, resumeCommand, resumeFailed, sessionModel, sessionNotFound } from './core'
import type { Local, Page, PaneModel } from './core'
import type { Actions } from './pane/view'
import { paneView } from './pane/view'
import { changesOf } from './changes'
import { ensureCollector } from './collector'
import { openPane, startUi } from './store'
import type { State } from './store'
import type { Snapshot } from './types'

type Engine = EngineInterface
// The collector writes it; the band and the pane read it. The same literal, declared where it is read.
const snapshot = atom({ plugin: 'agent-tracker', key: 'snapshot' } as const, { at: 0, agentsOk: true, okAt: 0, failedReads: 0, sessions: [] } as Snapshot)

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

// The local day and clock face: core reads no time zone, so they come from here.
function localDay(now: number): Local {
  const day = new Date(now)
  day.setHours(0, 0, 0, 0)
  const two = (n: number) => String(n).padStart(2, '0')
  return { midnight: day.getTime(), clock: ms => `${two(new Date(ms).getHours())}:${two(new Date(ms).getMinutes())}`, day: ms => DAYS[new Date(ms).getDay()] ?? '' }
}

// Go to a page: the row that opened it keeps the ring for when the person comes back (F89).
function go($: Engine, s: State, page: Page, from: string | null) {
  s.pane = { ...s.pane, history: [...s.pane.history, { page: s.pane.page, focus: from }], page, focus: null }
  $.ui.invalidate('ui.render')
}

// A crumb: straight to an upper page, the pages above it become the way back.
function jump($: Engine, s: State, page: Page) {
  s.pane = { ...s.pane, history: [], page, focus: null }
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

// The model of the page the pane is on. The Repo, Milestone and Feature pages read the repo's change folders.
async function modelOf($: Engine, s: State, snap: Snapshot, now: number, selfId: string, columns: number): Promise<PaneModel> {
  const local = localDay(now)
  const page = s.pane.page
  switch (page.kind) {
    case 'session':
      return sessionModel(snap, page.id, now, local, columns) ?? missingModel(sessionNotFound(page.id))
    case 'missing':
      return missingModel(page.what === 'session' ? sessionNotFound(page.text) : repoNotFound(page.text))
    case 'repo':
      return repoModel(snap, page.path, await changesOf($, s, snap, page.path, now), now, local, columns) ?? missingModel(repoNotFound(page.path))
    case 'milestone': {
      const c = (await changesOf($, s, snap, page.repo, now)).find(x => x.dir === page.change)
      return (c && milestoneModel(snap, page.repo, c, now, columns)) ?? missingModel(milestoneNotFound(page.change))
    }
    case 'feature': {
      const c = (await changesOf($, s, snap, page.repo, now)).find(x => x.dir === page.change)
      return (c && featureModel(snap, page.repo, c, page.n, now, columns)) ?? missingModel(milestoneNotFound(page.change))
    }
    default:
      return homeModel(snap, selfId, now, local, null, columns)
  }
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
    return { text: PANE_OPENED }
  })

  // The ring moves by Tab, the arrows or a click: remember where, so a redraw and a return keep it (Q27).
  on('ui.focus', async ($, e, next) => {
    if (e.requestId === PANE_ID && e.element !== undefined) s.pane.focus = e.element
    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: 'tracker' }, async ($, e) => {
    await startUi($, s)
    await ensureCollector($, s)
    const snap = await read($, snapshot)
    const now = await $.clock.now()
    const selfId = await $.session.id()
    const ui = $.ui.resolve(e)
    const columns = Math.max(20, e.props.bodyColumns - 1) // one cell of margin on the left
    const page = s.pane.page
    // Home keeps its order while the pane has the keyboard, and sorts again when the keyboard leaves (F43).
    let model: PaneModel
    if (page.kind === 'home') {
      const home = homeModel(snap, selfId, now, localDay(now), e.props.isFocused ? s.pane.frozen : null, columns)
      s.pane.frozen = e.props.isFocused ? home.frozen : null
      model = home
    } else model = await modelOf($, s, snap, now, selfId, columns)
    const session = page.kind === 'session' ? snap.sessions.find(r => r.sessionId === page.id) : undefined
    const actions: Actions = {
      open: (key, to) => go($, s, to, key),
      jump: to => jump($, s, to),
      close: () => void close($),
      resume: () => {
        const text = session === undefined ? null : resumeCommand(session.cwd, session.sessionId)
        if (text !== null) void copyResume($, text, e.surface)
      },
      ring: s.pane.focus,
    }
    return paneView(ui, model, actions, columns)
  })
}
