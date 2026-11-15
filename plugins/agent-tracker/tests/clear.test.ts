import { describe, expect, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'

import { IDLE, sessionModel, taskItems } from '../hooks/tracker/core'
import type { Block, Local, PaneModel, SessionCtx, WorktreeFact } from '../hooks/tracker/core'
import type { SessionRecord } from '../hooks/tracker/types'
import { NOON, SELF, at, sess, snapAt } from './fixtures/pane'
import { CLEANUP, DEAD, DEAD_ROW, FOLDER, LISTED, UNLISTED, AGENT_ROWS, THIS, dead, focused, keys, open, page, press, settings, withSnap } from './fixtures/ui'
import { TREE, inTree, isWorktreeRead, openTree } from './fixtures/git'
import { settle } from './fixtures/world'
import type { World } from './fixtures/world'

// The Session page of an ended session: Clear, its confirm, its run and the lines it leaves. Every id and folder is invented.
// The page reads git when it opens (row 3): nothing else may run before a press.
const ran = (w: World) => w.procs.filter(p => !isWorktreeRead(p.argv))
const rms = (w: World) => w.procs.filter(p => p.argv[1] === 'rm').map(p => p.argv)
const reads = (w: World) => w.procs.filter(p => p.argv[1] === 'agents').length
const NONE = ['clear', 'confirm-clear', 'cancel-clear', 'reopen']

// The page as a model, for the cases the seam `ctx.worktree` and the pure parts decide (row 3 completes the worktree half).
const local: Local = { midnight: NOON - 3_600_000, clock: () => '10:00', day: () => 'Mon', date: () => '14 Nov' }
const textOf = (b: Block) => (b.kind === 'lines' ? b.lines.map(l => l.map(s => s.text).join('')) : [])
const modelOf = (r: SessionRecord, ctx: Partial<SessionCtx>, listing = LISTED, failedReads = 0): PaneModel => {
  const tasks = taskItems(snapAt([r]), NOON)
  return sessionModel(snapAt([THIS, r], { listing, failedReads }), r.sessionId, NOON, local, 80, { tasks, folder: true, clear: null, worktree: null, ...ctx })!
}
const actionsOf = (m: PaneModel) => m.blocks.flatMap(b => (b.kind === 'actions' ? b.items.map(i => i.key) : []))
const linesOf = (m: PaneModel) => m.blocks.flatMap(textOf)
const WORKTREE: WorktreeFact = { label: 'login', branch: 'fix-login', removable: true, failed: null, how: 'branch', ignored: { secret: [], other: [], more: 0, all: [] } }

describe('Clear: when it is offered', () => {
  test(`@F8 ${CLEANUP} Clear is drawn for an ended session with something to clear`, async ($, on) => {
    const { ui } = await open($, on)
    expect(await keys(ui)).toContain('clear')
    expect(await keys(ui)).toEqual(expect.arrayContaining(['resume', 'clear']))
    expect((await keys(ui)).indexOf('resume')).toBeLessThan((await keys(ui)).indexOf('clear')) // Copy resume command, then Clear
    const clear = (await ui.find({ key: 'clear' }))!
    expect([clear.props.label, clear.props.plain, clear.props.hotkey]).toEqual(['Clear', true, undefined])
    expect(await page(ui)).toContain('○ ended 2h ago')
    await ui.unmount()
    // Each kind of work alone is enough: a listing, an open task, a removable worktree (through the seam).
    const listedOnly = modelOf(dead({ asks: [] }), {})
    expect(actionsOf(listedOnly)).toContain('clear')
    const tasksOnly = modelOf(dead(), {}, UNLISTED)
    expect(actionsOf(tasksOnly)).toContain('clear')
    const worktreeOnly = modelOf(dead({ asks: [] }), { worktree: WORKTREE }, UNLISTED)
    expect(actionsOf(worktreeOnly)).toContain('clear')
    expect(actionsOf(modelOf(dead({ asks: [] }), { worktree: { ...WORKTREE, removable: false } }, UNLISTED))).not.toContain('clear')
  })

  test(`@F9 ${CLEANUP} a session with a process gets the reason line and no Clear or resume`, async ($, on) => {
    const live = sess('live-9', 'needs-you', 4, 'web-app', 'login', { reason: 'waiting', repo: { path: FOLDER, name: 'web-app' }, cwd: FOLDER })
    const a = await open($, on, live, { listing: { ...LISTED, 'live-9': { pid: 3001 } } }, { row: 'session:live-9' })
    expect(await page(a.ui)).toContain('Clear is for ended sessions. Close its terminal first.')
    expect(await keys(a.ui)).not.toEqual(expect.arrayContaining(['resume']))
    expect((await keys(a.ui)).filter(k => NONE.includes(k))).toEqual([])
    await a.ui.unmount()
  })

  test(`@F9 ${CLEANUP} a background session with a process says it is still running`, async ($, on) => {
    const live = sess('live-9', 'needs-you', 4, 'web-app', 'login', { reason: 'waiting', kind: 'background', repo: { path: FOLDER, name: 'web-app' }, cwd: FOLDER })
    const a = await open($, on, live, { listing: { ...LISTED, 'live-9': { id: 'bg-9', pid: 3001 } } }, { row: 'session:live-9' })
    expect(await page(a.ui)).toContain('Clear is for ended sessions. This one is still running. Resume comes back when it ends.')
    expect(await keys(a.ui)).not.toContain('resume')
    expect(await keys(a.ui)).not.toContain('clear')
    await a.ui.unmount()
  })

  test(`@F9 ${CLEANUP} a listed row with a pid is live even when the record says ended`, async () => {
    const m = modelOf(dead(), {}, { ...LISTED, [DEAD]: { id: 'bg-dead', pid: 4004 } })
    expect(linesOf(m)).toContain('Clear is for ended sessions. This one is still running. Resume comes back when it ends.')
    expect(actionsOf(m)).toEqual([])
  })

  test(`@F10 ${CLEANUP} nothing to clear draws the line and no Clear`, async ($, on) => {
    const { ui } = await open($, on, dead({ asks: [] }), { listing: UNLISTED }, { row: 'command' })
    expect(await page(ui)).toContain("Nothing to clear: it is not in Claude Code's list and has no open tasks.")
    expect(await keys(ui)).toContain('resume')
    expect((await keys(ui)).filter(k => NONE.includes(k))).toEqual([])
    await ui.unmount()
    const m = modelOf(dead({ asks: [] }), {}, UNLISTED)
    expect(linesOf(m)).toContain("Nothing to clear: it is not in Claude Code's list and has no open tasks.")
    expect(actionsOf(m)).toEqual(['resume'])
  })

  test(`@F11 ${CLEANUP} pid not reported withholds Clear`, async () => {
    const m = modelOf(dead(), {}, { [DEAD]: { id: 'bg-dead' } })
    expect(linesOf(m)).toContain("Clear waits: Claude Code did not say which sessions have a process.")
    expect(actionsOf(m)).toEqual(['resume'])
  })

  test(`@F12 ${CLEANUP} unreadable list withholds Clear`, async () => {
    const m = modelOf(dead(), {}, LISTED, 2)
    expect(linesOf(m)).toContain("Clear waits: Claude Code's session list could not be read. Retrying every 5 seconds.")
    expect(actionsOf(m)).toEqual(['resume'])
    expect(actionsOf(modelOf(dead(), {}, LISTED, 1))).toContain('clear') // one failed read is not yet unreadable
  })

  test(`@F13 ${CLEANUP} the ring starts on Copy resume command or the Home crumb`, async ($, on) => {
    const a = await open($, on)
    expect(await focused(a.ui)).toEqual(['resume'])
    await a.ui.unmount()
  })

  test(`@F13 ${CLEANUP} the ring starts on the Home crumb when there is no resume button, never on Clear`, async ($, on) => {
    const b = await open($, on, dead(), { listing: LISTED }, { folder: false })
    expect(await keys(b.ui)).toContain('clear')
    expect(await focused(b.ui)).toEqual(['crumb:0']) // never Clear
    await b.ui.unmount()
  })

  test(`@F14 ${CLEANUP} no resume button when the worktree folder is gone`, async ($, on) => {
    const gone = await open($, on, dead(), { listing: LISTED }, { folder: false })
    expect(await keys(gone.ui)).not.toContain('resume')
    expect(await keys(gone.ui)).toContain('clear')
    await gone.ui.unmount()
  })

  test(`@F14 ${CLEANUP} the resume button is drawn while the folder exists, and drawing runs nothing`, async ($, on) => {
    const here = await open($, on)
    expect(await keys(here.ui)).toContain('resume')
    expect(ran(here.w)).toEqual([]) // the page draws without running anything but its git reads
    await here.ui.unmount()
  })

  test(`@F16 ${CLEANUP} a transcript-only session closes no task`, async ($, on) => {
    const t = dead({ source: 'transcript', asks: [{ n: 1, text: 'Fix the login redirect', kind: 'not-classified', status: 'replied', at: at(180) }] })
    const { ui, w } = await open($, on, t, { listing: LISTED }, { row: 'command' })
    await press(ui, 'clear')
    expect(await page(ui)).toContain("It leaves Claude Code's list.")
    expect(await page(ui)).not.toContain('closes the')
    await press(ui, 'confirm-clear')
    await settle()
    await ui.redraw()
    expect(await page(ui)).toContain("✓ Left Claude Code's list. The conversation is kept.")
    expect(await page(ui)).not.toContain('tasks closed')
    const m = modelOf(t, {})
    expect(linesOf(m)).toContain('Not classified: this session ran without the tracker.')
    expect(linesOf(m).some(l => l.includes('tasks'))).toBe(false)
    expect(actionsOf(m)).toContain('clear')
    // Even with a task on its record, Clear closes none: its asks are not classified.
    const withTask = modelOf({ ...t, asks: dead().asks }, {})
    expect(linesOf(withTask).join('\n')).not.toContain('closes the')
    await ui.unmount()
    expect(settings(w)).toBeNull()
  })
})

describe('Clear: the confirm', () => {
  test(`@F17 ${CLEANUP} pressing Clear opens the confirm and writes nothing`, async ($, on) => {
    const { ui, w } = await open($, on)
    await press(ui, 'clear')
    const all = await page(ui)
    expect(all).toContain('Clear this session?')
    expect(await keys(ui)).toEqual(expect.arrayContaining(['confirm-clear', 'cancel-clear']))
    expect(await keys(ui)).not.toContain('clear') // the confirm replaces the actions
    const buttons = await ui.findAll({ type: 'Button' })
    expect(buttons.filter(b => ['confirm-clear', 'cancel-clear'].includes(String(b.props.key))).map(b => b.props.label)).toEqual(['Clear session', 'Cancel'])
    expect(ran(w)).toEqual([])
    expect(w.writes).toEqual([])
    await ui.unmount()
  })

  test(`@F18 ${CLEANUP} the confirm's focus is on Cancel`, async ($, on) => {
    const { ui } = await open($, on)
    await press(ui, 'clear')
    expect(await focused(ui)).toEqual(['cancel-clear'])
    await ui.unmount()
  })

  test(`@F19 ${CLEANUP} the confirm lines for each combination of parts`, async () => {
    const confirm = (r: SessionRecord, ctx: Partial<SessionCtx>, listing = LISTED) => {
      const m = modelOf(r, { clear: { ...IDLE, step: 'confirm' }, ...ctx }, listing)
      const at = m.blocks.findIndex(b => b.kind === 'lines' && b.key === 'confirm')
      return textOf(m.blocks[at]!)
    }
    const KEPT = 'The conversation is kept. The list entry does not come back.'
    const REOPEN = 'You can reopen the tasks afterwards.'
    expect(confirm(dead(), {})).toEqual(['Clear this session?', "It leaves Claude Code's list and closes the 2 tasks above.", `${KEPT} ${REOPEN}`])
    expect(confirm(dead({ asks: dead().asks.slice(0, 1) }), {})).toEqual(['Clear this session?', "It leaves Claude Code's list and closes the 1 task above.", `${KEPT} ${REOPEN}`])
    expect(confirm(dead({ asks: [] }), {})).toEqual(['Clear this session?', "It leaves Claude Code's list.", KEPT])
    expect(confirm(dead(), {}, UNLISTED)).toEqual(['Clear this session?', 'It closes the 2 tasks above.', REOPEN])
    // A listed session in a linked worktree adds the Claude Code line; an unlisted one does not.
    expect(confirm(dead(), { worktree: WORKTREE })).toEqual(['Clear this session?', "It leaves Claude Code's list and closes the 2 tasks above.", 'If it made the worktree login, Claude Code also removes it, when that is safe.', `${KEPT} ${REOPEN}`])
    expect(confirm(dead(), { worktree: WORKTREE }, UNLISTED).join('\n')).not.toContain('If it made the worktree')
  })

  test(`@F20 ${CLEANUP} Cancel and leaving the page change nothing`, async ($, on) => {
    const { ui, w } = await open($, on)
    await press(ui, 'clear')
    await press(ui, 'cancel-clear')
    expect(await page(ui)).not.toContain('Clear this session?')
    expect(await keys(ui)).toEqual(expect.arrayContaining(['resume', 'clear']))
    expect(await focused(ui)).toEqual(['clear']) // back on Clear
    await press(ui, 'clear')
    await press(ui, 'crumb:0') // leave the page with the confirm open
    await press(ui, 'task:dead-1:1')
    expect(await page(ui)).not.toContain('Clear this session?')
    expect(await keys(ui)).toContain('clear')
    expect(ran(w)).toEqual([])
    expect(w.writes).toEqual([])
    await ui.unmount()
  })
})

describe('Clear: the run', () => {
  test(`@F22 ${CLEANUP} Clear session re-reads the list before any write`, async ($, on) => {
    const { ui, w } = await open($, on)
    await press(ui, 'clear')
    let release = () => {}
    w.hold = new Promise<void>(done => (release = done))
    await ui.press({ key: 'confirm-clear' })
    await ui.redraw()
    expect(await page(ui)).toContain('Clearing…')
    expect((await keys(ui)).filter(k => NONE.includes(k))).toEqual([]) // no button while it runs: a second press lands on nothing
    expect(await focused(ui)).toEqual(['crumb:0'])
    expect(reads(w)).toBe(1)
    expect(rms(w)).toEqual([]) // nothing is written before the re-read answers
    expect(w.writes).toEqual([])
    release()
    await settle()
    await ui.redraw()
    expect(ran(w).map(p => p.argv.slice(0, 2).join(' '))).toEqual(['claude agents', 'claude rm'])
    await ui.unmount()
  })

  test(`@F23 ${CLEANUP} a pid at the press refuses and writes nothing`, async ($, on) => {
    const { ui, w } = await open($, on)
    w.agents.json = AGENT_ROWS([{ ...DEAD_ROW, pid: 4004 }])
    await press(ui, 'clear')
    await press(ui, 'confirm-clear')
    await settle()
    await ui.redraw()
    expect(await page(ui)).toContain('This session is running again. Nothing was changed.')
    expect(rms(w)).toEqual([])
    expect(w.writes).toEqual([])
    await ui.unmount()
  })

  test(`@F23 ${CLEANUP} a read where no row carries a pid refuses too: the process fact is unknown`, async ($, on) => {
    const { ui, w } = await open($, on)
    w.agents.json = JSON.stringify([DEAD_ROW])
    await press(ui, 'clear')
    await press(ui, 'confirm-clear')
    await settle()
    await ui.redraw()
    expect(await page(ui)).toContain("Clear waits: Claude Code did not say which sessions have a process. Nothing was changed.")
    expect(rms(w)).toEqual([])
    expect(w.writes).toEqual([])
    await ui.unmount()
  })

  test(`@F24 ${CLEANUP} a failed re-read refuses and writes nothing`, async ($, on) => {
    const { ui, w } = await open($, on)
    w.agents.json = null
    await press(ui, 'clear')
    await press(ui, 'confirm-clear')
    await settle()
    await ui.redraw()
    expect(await page(ui)).toContain("Clear waits: Claude Code's session list could not be read. Nothing was changed.")
    expect(rms(w)).toEqual([])
    expect(w.writes).toEqual([])
    await ui.unmount()
  })

  test(`@F25 ${CLEANUP} claude rm runs for a listed session with a job id and no pid; no id, no claude rm`, async ($, on) => {
    const { ui, w } = await open($, on)
    await press(ui, 'clear')
    await press(ui, 'confirm-clear')
    await settle()
    await ui.redraw()
    expect(rms(w)).toEqual([['claude', 'rm', 'bg-dead']]) // the exact argument list: no flag, no shell
    expect(w.procs.find(p => p.argv[1] === 'rm')!.init).toEqual({ timeoutMs: 15_000 }) // no stdin, no shell, no folder
    const all = await page(ui)
    expect(all).toContain("✓ Left Claude Code's list. The conversation is kept.")
    expect(all).toContain('✓ 2 tasks closed.')
    await ui.unmount()
  })

  test(`@F25 ${CLEANUP} an interactive row has no job id: it is not listed as far as Clear goes, so no claude rm`, async ($, on) => {
    const b = await open($, on)
    b.w.agents.json = AGENT_ROWS([{ kind: 'interactive', status: 'idle', sessionId: DEAD, cwd: FOLDER, name: 'closed terminal', startedAt: 1 }])
    await press(b.ui, 'clear')
    await press(b.ui, 'confirm-clear')
    await settle()
    await b.ui.redraw()
    expect(rms(b.w)).toEqual([])
    expect(await page(b.ui)).not.toContain('Left Claude Code')
    expect(await page(b.ui)).toContain('✓ 2 tasks closed.')
    await b.ui.unmount()
  })

  test(`@F26 ${CLEANUP} an unlisted session, or one with no job id, gets no claude rm and still closes tasks`, async ($, on) => {
    const { ui, w } = await open($, on)
    w.agents.json = AGENT_ROWS() // gone from the list by the time of the press
    await press(ui, 'clear')
    await press(ui, 'confirm-clear')
    await settle()
    await ui.redraw()
    expect(rms(w)).toEqual([])
    const all = await page(ui)
    expect(all).toContain('✓ 2 tasks closed.')
    expect(all).not.toContain('Left Claude Code')
    expect([...settings(w)!.closed].sort()).toEqual(['dead-1:1', 'dead-1:2'])
    await ui.unmount()
  })

  test(`@F27 ${CLEANUP} a failed \`claude rm\` is treated as not listed when a fresh read no longer lists the session`, async ($, on) => {
    const { ui, w } = await open($, on)
    w.rm = { mode: 'fail', stderr: 'No job matching bg-dead', drops: true } // it failed, and yet the row is gone
    await press(ui, 'clear')
    await press(ui, 'confirm-clear')
    await settle()
    await ui.redraw()
    expect(rms(w)).toEqual([['claude', 'rm', 'bg-dead']])
    expect(reads(w)).toBe(2) // the press, then the read after the failure
    const all = await page(ui)
    expect(all).not.toContain('✗')
    expect(all).not.toContain('Left Claude Code')
    expect(all).toContain('✓ 2 tasks closed.')
    await ui.unmount()
  })

  test(`@F27 ${CLEANUP} the words of claude rm never decide: a message that says removed, with the row still listed, is a failure`, async ($, on) => {
    const b = await open($, on)
    b.w.rm = { mode: 'fail', stderr: 'removed bg-dead', drops: false }
    await press(b.ui, 'clear')
    await press(b.ui, 'confirm-clear')
    await settle()
    await b.ui.redraw()
    expect(await page(b.ui)).toContain('✗ Claude Code could not clear this session: removed bg-dead. Nothing else was changed. Press Clear to try again.')
    await b.ui.unmount()
  })

  test(`@F28 ${CLEANUP} claude rm failure with the session still listed shows the error line and Clear again`, async ($, on) => {
    const { ui, w } = await open($, on)
    w.rm = { mode: 'fail', stderr: '\u001b[31mpermission denied: this is a very long reason that goes on and on past sixty cells\nsecond line', drops: false }
    await press(ui, 'clear')
    await press(ui, 'confirm-clear')
    await settle()
    await ui.redraw()
    const all = await page(ui)
    expect(all).toContain('✗ Claude Code could not clear this session: permission denied: this is a very long reason that goes on …')
    expect(all).toContain('…. Nothing else was changed. Press Clear to try again.')
    expect(all).not.toContain('\u001b')
    expect(all).not.toContain('second line') // one line
    expect(await keys(ui)).toContain('clear') // Clear again
    expect(settings(w)).toBeNull() // nothing else changed: the tasks are open
    expect(await keys(ui)).not.toContain('reopen')
    await ui.unmount()
  })

  test(`@F28 ${CLEANUP} a claude rm that hangs is cut at 15 seconds and reads as the error line; a reason that is not usable is dropped`, async ($, on) => {
    const { ui, w } = await open($, on)
    w.rm = { mode: 'hang', stderr: '', drops: false }
    await press(ui, 'clear')
    await press(ui, 'confirm-clear')
    await settle()
    await ui.redraw()
    expect(w.procs.find(p => p.argv[1] === 'rm')!.init?.timeoutMs).toBe(15_000)
    expect(await page(ui)).toContain('✗ Claude Code could not clear this session. Nothing else was changed. Press Clear to try again.')
    expect(await keys(ui)).toContain('clear')
    await ui.unmount()
  })

  test(`@F28 ${CLEANUP} a reason that is not usable is dropped from the error line`, async ($, on) => {
    const b = await open($, on)
    b.w.rm = { mode: 'fail', stderr: '   \n', drops: false }
    await press(b.ui, 'clear')
    await press(b.ui, 'confirm-clear')
    await settle()
    await b.ui.redraw()
    expect(await page(b.ui)).toContain('✗ Claude Code could not clear this session. Nothing else was changed.')
    await b.ui.unmount()
  })

  test(`@F30 ${CLEANUP} a failed save after claude rm shows the partly-cleared line`, async ($, on) => {
    const { ui, w } = await open($, on)
    w.failWrite = p => p.endsWith('/settings.json')
    await press(ui, 'clear')
    await press(ui, 'confirm-clear')
    await settle()
    await ui.redraw()
    expect(rms(w)).toEqual([['claude', 'rm', 'bg-dead']])
    const all = await page(ui)
    expect(all).toMatch(/✗ The tracker could not close the tasks: .+\. The session left Claude Code's list\. Press Clear to close them\./)
    expect(await keys(ui)).toContain('clear') // Clear again: the tasks are still open
    expect(await keys(ui)).not.toContain('reopen')
    // It does the rest: the session has left the list, so the second press closes only the tasks.
    w.failWrite = () => false
    await press(ui, 'clear')
    expect(await page(ui)).toContain('It closes the 2 tasks above.')
    await press(ui, 'confirm-clear')
    await settle()
    await ui.redraw()
    expect(rms(w).length).toBe(1)
    expect([...settings(w)!.closed].sort()).toEqual(['dead-1:1', 'dead-1:2'])
    expect(await page(ui)).toContain('✓ 2 tasks closed.')
    await ui.unmount()
  })

  test(`@F33 ${CLEANUP} result lines survive the 5-second re-read and not a new visit`, async ($, on) => {
    const { ui, w, box } = await open($, on)
    await press(ui, 'clear')
    await press(ui, 'confirm-clear')
    await settle()
    await ui.redraw()
    expect(await page(ui)).toContain("✓ Left Claude Code's list. The conversation is kept.")
    box.value = snapAt([THIS, dead()], { listing: UNLISTED }) // the collector's next read: the row is gone
    await ui.redraw()
    const all = await page(ui)
    expect(all).toContain("✓ Left Claude Code's list. The conversation is kept.")
    expect(all).toContain('✓ 2 tasks closed.')
    expect(all).not.toContain('Nothing to clear')
    expect(await keys(ui)).not.toContain('clear') // the work is done: no Clear beside the result
    // A new visit shows what is left.
    await press(ui, 'crumb:0')
    expect(await keys(ui)).not.toContain('task:dead-1:1') // Home stopped listing the closed tasks
    await $.command.run({ command: 'tracker', args: 'session old login', origin: { kind: 'composer' }, presentation: {} as never })
    await ui.redraw()
    const again = await page(ui)
    expect(again).toContain("Nothing to clear: it is not in Claude Code's list and has no open tasks.")
    expect(again).not.toContain('✓')
    expect(w.writes.every(p => p.endsWith('/settings.json'))).toBe(true)
    await ui.unmount()
  })

  test(`@F73 ${CLEANUP} focus after a Clear: offer, resume, Home crumb, never Reopen tasks`, async ($, on) => {
    const a = await open($, on)
    await press(a.ui, 'clear')
    await press(a.ui, 'confirm-clear')
    await settle()
    await a.ui.redraw()
    expect(await keys(a.ui)).toEqual(expect.arrayContaining(['resume', 'reopen']))
    expect(await focused(a.ui)).toEqual(['resume'])
    await a.ui.unmount()
  })

  test(`@F73 ${CLEANUP} focus after a Clear goes to the Home crumb when there is no resume button, never Reopen tasks`, async ($, on) => {
    const b = await open($, on, dead(), { listing: LISTED }, { folder: false })
    await press(b.ui, 'clear')
    await press(b.ui, 'confirm-clear')
    await settle()
    await b.ui.redraw()
    expect(await keys(b.ui)).toContain('reopen')
    expect(await focused(b.ui)).toEqual(['crumb:0']) // no resume button: the Home crumb
    await b.ui.unmount()
  })
})

// The worktree half of Clear, on the made-up repository of fixtures/git.ts: the offer-only Clear (F21), what Claude Code removed (F46),
// the confirm's worktree line and the focus after a Clear (F73).
const NO_LISTING = { listing: { ...UNLISTED } }
const onlyTree = { session: inTree({ asks: [] }), extra: NO_LISTING, row: 'command' } as const
const settled = async (ui: { redraw: () => Promise<void> }) => {
  await settle()
  await ui.redraw()
}

describe('Clear and the worktree', () => {
  test(`@F8 ${CLEANUP} a removable worktree alone is work left: Clear is drawn and a line says Clear offers to remove it`, async ($, on) => {
    const h = await openTree($, on, onlyTree)
    expect(await keys(h.ui)).toContain('clear')
    expect(await page(h.ui)).toContain('Clear offers to remove the worktree below.')
    expect(await page(h.ui)).not.toContain('Nothing to clear')
    await h.ui.unmount()
  })

  test(`@F8 ${CLEANUP} a worktree that stays is not work left: Clear is for the listing and the tasks alone`, async ($, on) => {
    const h = await openTree($, on, { repo: { status: { [TREE]: [' M a'] } } })
    await press(h.ui, 'clear')
    expect(await page(h.ui)).toContain('Clear this session?')
    expect(await page(h.ui)).not.toContain('Clear offers to remove the worktree below.')
    await h.ui.unmount()
  })

  test(`@F21 ${CLEANUP} only a worktree left opens the offer, no confirm, and writes nothing`, async ($, on) => {
    const h = await openTree($, on, onlyTree)
    await press(h.ui, 'clear')
    const all = await page(h.ui)
    expect(all).not.toContain('Clear this session?')
    expect(all).toContain('Worktree login is clean, pushed and merged.')
    expect(await keys(h.ui)).toEqual(expect.arrayContaining(['remove-worktree', 'keep-worktree']))
    expect(await keys(h.ui)).not.toContain('confirm-clear')
    expect(h.w.procs.filter(p => !isWorktreeRead(p.argv) && p.argv[1] !== 'agents')).toEqual([])
    expect(rms(h.w)).toEqual([])
    expect(h.w.writes).toEqual([])
    await h.ui.unmount()
  })

  test(`@F21 ${CLEANUP} a session that is still listed, or has open tasks, gets the confirm first even with a removable worktree`, async ($, on) => {
    const h = await openTree($, on)
    await press(h.ui, 'clear')
    expect(await page(h.ui)).toContain('Clear this session?')
    expect(await keys(h.ui)).not.toContain('remove-worktree')
    await h.ui.unmount()
  })

  test(`@F19 ${CLEANUP} a listed session in a linked worktree gets the Claude Code line in its confirm`, async ($, on) => {
    const h = await openTree($, on)
    await press(h.ui, 'clear')
    expect(await page(h.ui)).toContain('If it made the worktree login, Claude Code also removes it, when that is safe.')
    await h.ui.unmount()
  })

  test(`@F46 ${CLEANUP} Claude Code removing its own worktree is named and no offer follows`, async ($, on) => {
    const h = await openTree($, on, { setup: (w, r) => (w.onRm = () => void (r.trees = r.trees.filter(t => t.path !== TREE))) })
    await press(h.ui, 'clear')
    await press(h.ui, 'confirm-clear')
    await settled(h.ui)
    const all = await page(h.ui)
    expect(all).toContain('✓ Claude Code also removed the worktree login.')
    expect(all).toContain('To resume this conversation, make the worktree again from the branch first.')
    expect(all.indexOf("✓ Left Claude Code's list.")).toBeGreaterThan(-1)
    expect(all.indexOf("✓ Left Claude Code's list.")).toBeLessThan(all.indexOf('✓ Claude Code also removed')) // the order the steps ran: list, tasks, worktree
    expect(await keys(h.ui)).not.toContain('remove-worktree')
    expect(await keys(h.ui)).not.toContain('resume') // the folder is gone
    expect(h.w.procs.filter(p => p.argv[0] === 'git' && p.argv.includes('remove'))).toEqual([]) // the tracker removed nothing itself
    expect(await focused(h.ui)).toEqual(['crumb:0'])
    await h.ui.unmount()
  })

  test(`@F46 ${CLEANUP} a worktree that is still there after claude rm is not claimed: the offer follows instead`, async ($, on) => {
    const h = await openTree($, on)
    await press(h.ui, 'clear')
    await press(h.ui, 'confirm-clear')
    await settled(h.ui)
    expect(await page(h.ui)).not.toContain('Claude Code also removed')
    expect(await keys(h.ui)).toEqual(expect.arrayContaining(['remove-worktree', 'keep-worktree']))
    expect(rms(h.w)).toEqual([['claude', 'rm', 'bg-dead']])
    await h.ui.unmount()
  })

  test(`@F46 ${CLEANUP} no claude rm, no claim: a session that was not listed says nothing about Claude Code and the worktree`, async ($, on) => {
    const h = await openTree($, on, { session: inTree(), extra: NO_LISTING, setup: w => (w.agents.json = AGENT_ROWS()) }) // the press's read does not list it either
    await press(h.ui, 'clear')
    await press(h.ui, 'confirm-clear')
    await settled(h.ui)
    expect(rms(h.w)).toEqual([])
    expect(await page(h.ui)).not.toContain('Claude Code also removed')
    expect(await page(h.ui)).toContain('✓ 2 tasks closed.')
    await h.ui.unmount()
  })

  test(`@F73 ${CLEANUP} focus after a Clear goes to Keep worktree when there is an offer, never Reopen tasks`, async ($, on) => {
    const h = await openTree($, on)
    await press(h.ui, 'clear')
    await press(h.ui, 'confirm-clear')
    await settled(h.ui)
    expect(await keys(h.ui)).toEqual(expect.arrayContaining(['resume', 'reopen', 'keep-worktree']))
    expect(await focused(h.ui)).toEqual(['keep-worktree'])
    await h.ui.unmount()
  })

  test(`@F73 ${CLEANUP} after Keep worktree the focus is Copy resume command, never Clear or Reopen tasks`, async ($, on) => {
    const h = await openTree($, on)
    await press(h.ui, 'clear')
    await press(h.ui, 'confirm-clear')
    await settled(h.ui)
    await press(h.ui, 'keep-worktree')
    expect(await focused(h.ui)).toEqual(['resume'])
    await h.ui.unmount()
  })
})
