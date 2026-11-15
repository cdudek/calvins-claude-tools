// The pane on screen for the Clear tests: a mounted Pane over a scripted snapshot, and a made-up ended session with work left.
// Every name, folder and id is invented.
import type { On } from 'claude-code'
import type { Engine } from 'claude-code/testing'

import type { Listing, SessionRecord, Snapshot } from '../../hooks/tracker/types'
import { NOON, SELF, at, sess, snapAt } from './pane'
import { ask } from './tasks'
import { settle, world } from './world'
import type { World } from './world'

export const DIR = '/u/.claude/agent-tracker'
export const CLEANUP = '@2026-11-14-tracker-session-cleanup'

// The snapshot the collector would have written, as the state read answers it. `box.value` changes between draws.
export const withSnap = (on: On, sessions: SessionRecord[], extra: Partial<Snapshot> = {}) => {
  const w = world(on, { now: NOON, id: SELF, cwd: '/work/platform-tools-suite', panes: true })
  const box = { value: snapAt(sessions, extra) }
  on('state.get', (_, e, next) => (e.key === 'snapshot' ? ({ value: { value: box.value, version: 1 } } as never) : next(e)))
  return { w, box }
}

export const PANE = (columns: number, isFocused = false) =>
  ({ component: 'Pane', requestId: 'tracker', props: { title: 'Tracker', isFocused, bodyColumns: columns, placement: 'dock', scroll: { offset: 0, bodyRows: 40 }, view: {} } }) as const
export const mount = ($: Engine, columns = 80) => $.ui.mount({ plugin: 'agent-tracker', surface: 'terminal', ...PANE(columns) } as never)
export type Ui = Awaited<ReturnType<typeof mount>>
export const texts = async (ui: Ui) => (await ui.findAll({ type: 'Text' })).map(t => t.text ?? '')
export const page = async (ui: Ui) => (await texts(ui)).join('\n')
export const keys = async (ui: Ui) => (await ui.findAll({ type: 'Button' })).map(b => String(b.props.key))
export const focused = async (ui: Ui) => (await ui.findAll({ type: 'Button' })).filter(b => b.props.autoFocus === true).map(b => String(b.props.key))
export const press = async (ui: Ui, key: string) => {
  await ui.press({ key })
  await ui.redraw()
}
export const settings = (w: { json: (p: string) => unknown }) => w.json(`${DIR}/settings.json`) as { closed: string[]; kept: string[] } | null

export const DEAD = 'dead-1'
export const FOLDER = '/work/web-app'
// An ended session of web-app with two tasks Home lists (judged not done), a job id in Claude Code's list and no process.
export const dead = (extra: Partial<SessionRecord> = {}): SessionRecord =>
  sess(DEAD, 'ended', 120, 'web-app', 'old login work', {
    repo: { path: FOLDER, name: 'web-app' },
    cwd: FOLDER,
    branch: 'feat/login',
    kind: 'background',
    endedAt: at(120),
    asks: [ask(1, 'Fix the login redirect', 180, { verdict: 'not-started' }), ask(2, 'Add a retry on 401', 150, { verdict: 'partly' })],
    ...extra,
  })

// What `claude agents --json` showed: this session and a live job carry a pid; the dead job has an id and no pid.
export const LISTED: Listing = { [SELF]: { pid: 2001 }, live: { id: 'bg-live', pid: 2002 }, [DEAD]: { id: 'bg-dead' } }
export const UNLISTED: Listing = { [SELF]: { pid: 2001 }, live: { id: 'bg-live', pid: 2002 } }
export const THIS = sess(SELF, 'running', 4, 'platform-tools-suite', 'build', { branch: 'main' })
export const AGENT_ROWS = (rows: Record<string, unknown>[] = []) =>
  JSON.stringify([{ kind: 'interactive', status: 'busy', sessionId: SELF, cwd: '/work/platform-tools-suite', name: 'this session', startedAt: 1, pid: 2001 }, ...rows])
export const DEAD_ROW = { kind: 'background', state: 'blocked', sessionId: DEAD, cwd: FOLDER, name: 'old login work', startedAt: 1, id: 'bg-dead' }

// The page of a session, opened as the person does: from its row on Home (a task row while it has a task Home lists).
export const open = async ($: Engine, on: On, session: SessionRecord = dead(), extra: Partial<Snapshot> = { listing: LISTED }, o: { folder?: boolean; row?: string; setup?: (w: World) => void } = {}) => {
  const h = withSnap(on, [THIS, session], extra)
  if (o.folder !== false) h.w.put(`${session.cwd}/README`, '')
  h.w.agents.json = AGENT_ROWS([DEAD_ROW])
  o.setup?.(h.w) // before the page draws, so what it reads from git is in place
  const ui = await mount($)
  await ui.redraw()
  if (o.row === 'command') {
    await $.command.run({ command: 'tracker', args: `session ${session.title}`, origin: { kind: 'composer' }, presentation: {} as never })
    await ui.redraw()
  } else await press(ui, o.row ?? `task:${session.sessionId}:1`)
  return { ...h, ui }
}
