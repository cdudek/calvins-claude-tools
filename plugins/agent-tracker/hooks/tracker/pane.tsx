// The pane: Home, Repo, Milestone, Feature and Session pages, and the /tracker words that open them. It reads the snapshot,
// the clock and the change folders. It writes the clipboard, the owner's marks in settings.json, and, after the owner presses
// "Clear session" on an ended session's page, Claude Code's list (clear.ts). `$` is passed only to plain top-level functions.
import { atom, read } from 'claude-code'
import type { EngineInterface, On } from 'claude-code'

import { COMMAND_HELP, IDLE, PANE_ID, noteModel, noteNotFound, overruleText, PANE_OPENED, REPLY_COPIED, RESUME_COPIED, replyFailed, featureModel, hasProcess, homeModel, judge, listingOf, liveFolders, matchRepo, matchSession, milestoneModel, milestoneNotFound, missingModel, onlyWorktree, repoModel, repoNotFound, resumeCommand, resumeFailed, sessionModel, sessionNotFound, workOf, worktreeLabel } from './core'
import type { ActionItem, ClearState, Local, NoteItem, Page, PaneModel, TaskItem, WtOutcome } from './core'
import type { Actions } from './pane/view'
import { paneView } from './pane/view'
import { changesOf } from './changes'
import { itemsOf, tasksOf } from './notes'
import { ensureCollector } from './collector'
import { clearSession, readRows, reopenTasks } from './clear'
import { markSeen, markTask, openPane, startUi } from './store'
import type { State } from './store'
import type { SessionRecord, Snapshot } from './types'
import { afterRm, readWorktree, removeWorktree } from './worktrees'

type Engine = EngineInterface
// The collector writes it; the band and the pane read it. The same literal, declared where it is read.
const snapshot = atom({ plugin: 'agent-tracker', key: 'snapshot' } as const, { at: 0, agentsOk: true, okAt: 0, failedReads: 0, sessions: [] } as Snapshot)

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

// The local day and clock face: core reads no time zone, so they come from here.
function localDay(now: number): Local {
  const day = new Date(now)
  day.setHours(0, 0, 0, 0)
  const two = (n: number) => String(n).padStart(2, '0')
  return {
    midnight: day.getTime(),
    clock: ms => `${two(new Date(ms).getHours())}:${two(new Date(ms).getMinutes())}`,
    day: ms => DAYS[new Date(ms).getDay()] ?? '',
    date: (ms, withYear) => `${new Date(ms).getDate()} ${MONTHS[new Date(ms).getMonth()] ?? ''}${withYear ? ` ${new Date(ms).getFullYear()}` : ''}`,
  }
}

// Go to a page: the row that opened it keeps the ring for when the person comes back (F89).
function go($: Engine, s: State, page: Page, from: string | null) {
  s.pane = { ...s.pane, history: [...s.pane.history, { page: s.pane.page, focus: from }], page, focus: null, clear: IDLE }
  $.ui.invalidate('ui.render')
}

// A crumb: straight to an upper page, the pages above it become the way back.
function jump($: Engine, s: State, page: Page) {
  s.pane = { ...s.pane, history: [], page, focus: null, clear: IDLE }
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

// Back: the page the person came from, with the ring on the row that opened this one.
function back($: Engine, s: State) {
  const last = s.pane.history[s.pane.history.length - 1]
  if (last === undefined) return
  s.pane = { ...s.pane, history: s.pane.history.slice(0, -1), page: last.page, focus: last.focus, clear: IDLE }
  $.ui.invalidate('ui.render')
}

// What git says about the folder a session ran in: read once per visit, in the background, and again when the session's process
// starts or ends. The page draws without it until it lands (a redraw follows). A result for a page the owner left is dropped.
function readFacts($: Engine, s: State, snap: Snapshot, r: SessionRecord) {
  const ended = !hasProcess(r, snap)
  const have = s.pane.clear.facts
  if (r.cwd === '' || (have !== null && have.id === r.sessionId && have.ended === ended)) return
  s.pane = { ...s.pane, clear: { ...s.pane.clear, facts: { id: r.sessionId, ended, value: have?.id === r.sessionId ? have.value : null, reading: true } } }
  void readWorktree($, r.cwd, liveFolders(snap.sessions, snap.listing), ended)
    .catch(() => null)
    .then(value => {
      const now = s.pane.clear.facts
      if (s.pane.page.kind !== 'session' || s.pane.page.id !== r.sessionId || now === null || now.id !== r.sessionId || now.ended !== ended) return
      s.pane = { ...s.pane, clear: { ...s.pane.clear, facts: { id: r.sessionId, ended, value, reading: false } } }
      $.ui.invalidate('ui.render')
    })
}

// The worktree of a session, judged: its folder label is the one the Repo page shows.
const worktreeOf = (s: State, r: SessionRecord) => {
  const f = s.pane.clear.facts?.id === r.sessionId ? s.pane.clear.facts.value : null
  return judge(f, worktreeLabel(f?.path ?? '', r.repo?.path ?? f?.main ?? ''))
}

// The Session page's Clear and worktree offer. Pressing "Clear" opens the confirm and writes nothing (when only a removable worktree
// is left it opens the offer instead, which is its own confirm); only "Clear session" and "Remove worktree" write. The page's state
// lives in `s.pane.clear` until the owner leaves the page; a result that lands after they left is dropped.
async function actClear($: Engine, s: State, it: ActionItem) {
  const page = s.pane.page
  if (page.kind !== 'session') return
  const c = s.pane.clear
  // A patch on the state as it is when the work lands: a read or a press may have changed it meanwhile.
  const set = (patch: Partial<ClearState>, focus: string | null = null) => {
    if (s.pane.page.kind !== 'session' || s.pane.page.id !== page.id) return
    s.pane = { ...s.pane, clear: { ...s.pane.clear, ...patch }, focus }
    $.ui.invalidate('ui.render')
  }
  const sessionOf = async () => (await read($, snapshot)).sessions.find(x => x.sessionId === page.id)
  if (it.action === 'clear' && c.step === 'idle') {
    const snap = await read($, snapshot)
    const r = snap.sessions.find(x => x.sessionId === page.id)
    const work = r === undefined ? null : workOf(r, snap, await tasksOf($, s, snap, await $.clock.now()), worktreeOf(s, r), c.left)
    if (work !== null && onlyWorktree(work)) set({ offer: true, wt: null })
    else set({ step: 'confirm' })
  } else if (it.action === 'cancel-clear' && c.step === 'confirm') set({ step: 'idle' }, 'clear')
  else if (it.action === 'reopen' && c.step === 'idle') {
    const keys = it.keys ?? []
    if (await reopenTasks($, s, keys)) set({ outcome: { kind: 'reopened', count: keys.length } })
  } else if (it.action === 'keep-worktree' && c.step === 'idle' && c.offer) set({ offer: false })
  else if (it.action === 'remove-worktree' && c.step === 'idle' && c.offer) {
    set({ step: 'removing' }) // before the first await: a second press meanwhile finds the step taken
    const r = await sessionOf()
    const have = s.pane.clear.facts
    const label = r === undefined ? null : worktreeOf(s, r)?.label
    if (have?.value == null || label == null) return set({ step: 'idle' })
    const done = await removeWorktree($, have.value, label)
    set({ step: 'idle', offer: false, wt: done.outcome, facts: { ...have, value: done.facts, reading: false } })
  } else if (it.action === 'confirm-clear' && c.step === 'confirm') {
    set({ step: 'clearing', outcome: null, wt: null })
    const snap = await read($, snapshot)
    const r = snap.sessions.find(x => x.sessionId === page.id)
    const keys = r === undefined ? [] : workOf(r, snap, await tasksOf($, s, snap, await $.clock.now()), null).tasks.map(t => t.key)
    const done = await clearSession($, s, page.id, keys)
    // `claude rm` may have removed the worktree the session made: look again, and say so (F46). Else a clean Clear is followed by the offer.
    const have = s.pane.clear.facts
    const before = r === undefined ? null : worktreeOf(s, r)
    let value = have?.id === page.id ? have.value : null
    let wt: WtOutcome | null = null
    if (done.left && value !== null) {
      const rows = await readRows($)
      const after = await afterRm($, value, rows === null ? null : liveFolders(rows, listingOf(rows)))
      if (after === 'gone' && before !== null) wt = { kind: 'claude-removed', label: before.label }
      value = after === 'gone' ? null : after
    }
    const facts = have === null ? null : { ...have, value, reading: false }
    const offer = done.outcome.kind === 'cleared' && before !== null && value !== null && value.linked && judge(value, before.label)?.removable === true
    set({ step: 'idle', left: c.left || done.left, outcome: done.outcome, wt, offer, facts })
  }
}

// An action Button: mark notes seen, keep or close a task (writes to settings.json), copy the reply that overrules an item, copy a resume command, Clear.
async function act($: Engine, s: State, it: ActionItem, item: NoteItem | undefined, resume: string | null, surface: Surface) {
  if (it.action === 'clear' || it.action === 'confirm-clear' || it.action === 'cancel-clear' || it.action === 'reopen' || it.action === 'remove-worktree' || it.action === 'keep-worktree') await actClear($, s, it)
  else if (it.action === 'seen') await markSeen($, s, it.keys ?? [])
  else if (it.action === 'keep' || it.action === 'close') await markTask($, s, it.action === 'keep' ? 'kept' : 'closed', it.keys ?? [])
  else if (it.action === 'overrule' && item !== undefined) {
    const done = await $.ui.copy({ text: overruleText(item), ...(surface === undefined ? {} : { surface }) })
    $.ui.toast(done.isCopied ? REPLY_COPIED : replyFailed(done.reason))
  } else if (it.action === 'resume' && resume !== null) await copyResume($, resume, surface)
}

async function close($: Engine) {
  await $.ui.close({ id: PANE_ID }).catch(() => undefined)
}

// The model of the page the pane is on. The Repo, Milestone and Feature pages read the repo's change folders.
async function modelOf($: Engine, s: State, snap: Snapshot, now: number, selfId: string, columns: number, items: NoteItem[], tasks: TaskItem[]): Promise<PaneModel> {
  const local = localDay(now)
  const page = s.pane.page
  switch (page.kind) {
    case 'session': {
      const r = snap.sessions.find(x => x.sessionId === page.id)
      // The resume command needs the session's folder. The worktree is what git said about it, read in the background (readFacts).
      const folder = r !== undefined && r.state === 'ended' && (await $.fs.exists(r.cwd).catch(() => false))
      if (r !== undefined) readFacts($, s, snap, r)
      const facts = s.pane.clear.facts?.id === page.id ? s.pane.clear.facts.value : null
      const worktree = r === undefined ? null : judge(facts, worktreeLabel(facts?.path ?? '', r.repo?.path ?? facts?.main ?? ''))
      return sessionModel(snap, page.id, now, local, columns, { tasks, folder, clear: s.pane.clear, worktree }) ?? missingModel(sessionNotFound(page.id))
    }
    case 'note': {
      const item = items.find(i => i.key === page.key)
      return item === undefined ? missingModel(noteNotFound) : noteModel(item, snap, local, columns)
    }
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
      return homeModel(snap, selfId, now, local, null, columns, items)
  }
}

export const registerPane = (on: On, s: State) => {
  // The pane's words: none (Home), `session <text>`, `repo <text>`, and a hint for any other. The band's words go on.
  on('command.run', { command: 'tracker' }, async ($, e, next) => {
    const args = e.args.trim()
    // `web` is the Board's: another hook answers it, so it goes on instead of getting the hint.
    if (/^(details|compact|copy|web|band\s+(on|off))$/i.test(args)) return next(e)
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
    const items = await itemsOf($, s, snap, now)
    const tasks = page.kind === 'home' || page.kind === 'session' ? await tasksOf($, s, snap, now) : []
    // Home keeps its order while the pane has the keyboard, and sorts again when the keyboard leaves (F43).
    let model: PaneModel
    if (page.kind === 'home') {
      const home = homeModel(snap, selfId, now, localDay(now), e.props.isFocused ? s.pane.frozen : null, columns, items, tasks)
      s.pane.frozen = e.props.isFocused ? home.frozen : null
      model = home
    } else model = await modelOf($, s, snap, now, selfId, columns, items, tasks)
    const item = page.kind === 'note' ? items.find(x => x.key === page.key) : undefined
    const sessionId = page.kind === 'session' ? page.id : item?.sessionId
    const session = sessionId === undefined || sessionId === null ? undefined : snap.sessions.find(r => r.sessionId === sessionId)
    const resume = session === undefined ? null : resumeCommand(session.cwd, session.sessionId)
    const actions: Actions = {
      open: (key, to) => go($, s, to, key),
      jump: to => jump($, s, to),
      close: () => void close($),
      act: it => void act($, s, it, item, resume, e.surface),
      back: s.pane.history.length > 0 ? () => back($, s) : null,
      ring: s.pane.focus,
    }
    return paneView(ui, model, actions, columns)
  })
}
