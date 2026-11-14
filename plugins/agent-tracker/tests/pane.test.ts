import { describe, expect, test } from 'claude-code/testing'
import type { On } from 'claude-code'
import type { Engine } from 'claude-code/testing'

import { REPLY_COPIED, resumeCommand } from '../hooks/tracker/core'
import type { Note, SessionRecord, Settings, Snapshot } from '../hooks/tracker/types'
import { NOON, SELF, aloneTown, at, paneTown, sess, snapAt, use } from './fixtures/pane'
import { taskTown } from './fixtures/tasks'
import { world } from './fixtures/world'
import type { World } from './fixtures/world'

// The pane follows the owner's mockups (agent-tracker-designs.html and agent-tracker-drill-in.html, 2026-11-14): Home as the
// triage queue with "You should know" and "Decided without you", the Repo, Milestone and Feature pages, the Session page.
// The layout facts of change 2026-11-13-agent-tracker are superseded by them; its behaviour facts keep their tags.
const TAG = '@2026-11-13-agent-tracker'
const DIR = '/u/.claude/agent-tracker'

// The snapshot the collector would have written, as the state read answers it. `box.value` changes between draws.
const withSnap = (on: On, sessions: SessionRecord[], extra: Partial<Snapshot> = {}, now = NOON) => {
  const w = world(on, { now, id: SELF, cwd: '/work/platform-tools-suite', panes: true })
  const box = { value: snapAt(sessions, extra) }
  on('state.get', (_, e, next) => (e.key === 'snapshot' ? ({ value: { value: box.value, version: 1 } } as never) : next(e)))
  return { w, box }
}

const PANE = (columns: number, isFocused: boolean) =>
  ({ component: 'Pane', requestId: 'tracker', props: { title: 'Tracker', isFocused, bodyColumns: columns, placement: 'dock', scroll: { offset: 0, bodyRows: 40 }, view: {} } }) as const
const mount = ($: Engine, columns = 70, isFocused = false, surface: 'terminal' | 'desktop' | 'vscode' | 'mobile' = 'terminal') => $.ui.mount({ plugin: 'agent-tracker', surface, ...PANE(columns, isFocused) } as never)
const run = ($: Engine, args: string) => $.command.run({ command: 'tracker', args, origin: { kind: 'composer' }, presentation: {} as never })

type Ui = Awaited<ReturnType<typeof mount>>
const texts = async (ui: Ui) => (await ui.findAll({ type: 'Text' })).map(t => t.text ?? '')
const buttons = async (ui: Ui, prefix = '') => (await ui.findAll({ type: 'Button' })).filter(b => String(b.props.key ?? '').startsWith(prefix))
const keys = async (ui: Ui, prefix = '') => (await buttons(ui, prefix)).map(b => String(b.props.key))
const rowText = async (ui: Ui, key: string) => (await ui.find({ key }))?.text
// The props of the innermost Text with that text: a line's own Text wraps the Text of each span, and the span carries the colour.
const colorOf = async (ui: Ui, text: string | RegExp) => (await ui.findAll({ type: 'Text', text })).at(-1)?.props
const go = async (ui: Ui, key: string) => {
  await ui.press({ key })
  await ui.redraw()
}
const settings = (w: World) => w.json(`${DIR}/settings.json`) as Settings | null

// Notes of the session web-1, as the collector wrote them.
const note = (id: string, kind: Note['kind'], text: string, agoMin: number): Note => ({ id, kind, text, at: at(agoMin), seen: false })
const withNotes = (notes: Record<string, Note[]>) => paneTown().map(r => (notes[r.sessionId] ? { ...r, notes: notes[r.sessionId] } : r))
const NOTED = withNotes({
  'web-1': [note('n1', 'know', 'Tests hit the real payment sandbox, not a mock', 22), note('n2', 'decided', 'Dark mode follows the system', 20)],
  'api-1': [note('n1', 'know', 'Skipped F13: needs a browser that is not installed', 40), note('n2', 'decided', 'Store as one JSON file per session', 35)],
})

// A change folder of an sdlc-run repo, as the Repo, Milestone and Feature pages read it.
const CHANGE = '2026-11-10-design-tokens'
const MILESTONE = `---
type: milestone
milestone: design-tokens-1
branch: feat/dark
status: building
---

# Milestone: design-tokens-1

> Colours, spacing and motion come from tokens.

## Features

| # | Change | Feature | PR or commit | State |
|---|---|---|---|---|
| 0 | ${CHANGE} | sync with main | a1f3e2c | done a1f3e2c |
| 1 | ${CHANGE} | token file and lint rule | b72c9d1 | done b72c9d1 |
| 2 | ${CHANGE} | motion durations | <commit> | building |
| 3 | ${CHANGE} | z-index scale | <commit> | todo |
| 4 | ${CHANGE} | dark mode | <commit> | blocked: needs F12 answer |
`
const DONE = { facts: [{ id: 'F1', feature: 1, check: '`tokens.test.ts` › the file' }, { id: 'F9', feature: 2, check: '`motion.test.ts` › durations' }, { id: 'F10', feature: 2, check: '`motion.test.ts` › easing' }, { id: 'F12', feature: 4, check: '`dark.test.ts` › follows' }] }
const VALIDATION = '| F1 | x | y | z | met |\n| F9 | x | y | z | unmet |\n'
const QUESTIONS = '# Questions\n\n- **Q1 (F12): Dark mode: system or toggle?** The plan says nothing. **Default taken:** follow the system. **To change:** add a toggle.\n'
const PLAN = '# Plan\n\n## Revisions\n\n- **2026-11-14, F9:** moved the motion work before spacing, so the durations land first.\n'
const putChange = (w: World) => {
  const base = `/work/web-app/changes/${CHANGE}`
  w.put(`${base}/milestone.md`, MILESTONE)
  w.put(`${base}/done.json`, DONE)
  w.put(`${base}/validation.md`, VALIDATION)
  w.put(`${base}/questions.md`, QUESTIONS)
  w.put(`${base}/plan.md`, PLAN)
  w.put(`${base}/decisions.json`, { project: { slug: 'design system' }, ticket: 'ABC-210' })
}

describe('Home leads with your tasks not done', () => {
  const TASKED = [...aloneTown(), ...taskTown()]
  const ROWS = ['task:need-1:1', 'task:lost-2:1', 'task:lost-1:1', 'task:sup-1:1', 'task:sup-1:2', 'task:prog-1:1', 'task:prog-2:1']

  test(`${TAG} the heading and the count come first, then the rows: needs you, forgotten, superseded, in progress, newest first`, async ($, on) => {
    withSnap(on, TASKED)
    const ui = await mount($)
    const all = await texts(ui)
    const head = all.findIndex(t => t.startsWith('YOUR TASKS NOT DONE'))
    expect(head).toBeGreaterThanOrEqual(0)
    expect(all.slice(head, head + 3).join('')).toContain('7') // the count beside the heading
    expect(head).toBeLessThan(all.findIndex(t => t.startsWith('NEEDS YOU'))) // before every other section
    expect(all.findIndex(t => t.startsWith('NEEDS YOU'))).toBeLessThan(all.findIndex(t => t.startsWith('RUNNING')))
    expect(await keys(ui, 'task:')).toEqual(ROWS)
    expect((await buttons(ui))[0]!.props.key).toBe(ROWS[0]) // the ring starts on the first task
    expect(await rowText(ui, 'task:need-1:1')).toContain('● Fix the login redirect so users land back on the page they came …') // one line, cut to the pane's width
    expect(await rowText(ui, 'task:lost-1:1')).toContain('Forgotten: session ended 2h ago, not done, no milestone, no PR')
    expect(await rowText(ui, 'task:lost-2:1')).toContain('Forgotten: idle 45m, not done, no milestone, no PR')
    expect(await rowText(ui, 'task:sup-1:1')).toContain('Superseded? a later ask at 11:52, “Fix the login redirect and…”, may have replaced it')
    expect(await rowText(ui, 'task:prog-1:1')).toContain('In progress: agent-tracker-1, 2 of 4 features')
    await ui.unmount()
  })

  test(`${TAG} the colours: red needs you and forgotten, purple superseded, yellow in progress`, async ($, on) => {
    withSnap(on, TASKED)
    const ui = await mount($)
    expect(await colorOf(ui, 'YOUR TASKS NOT DONE')).toMatchObject({ color: 'error', bold: true })
    expect(await colorOf(ui, /^You: waiting/)).toMatchObject({ color: 'error' })
    expect(await colorOf(ui, /^Forgotten: idle/)).toMatchObject({ color: 'error' })
    expect(await colorOf(ui, /^Superseded\?/)).toMatchObject({ color: 'merged' })
    expect(await colorOf(ui, /^In progress: agent/)).toMatchObject({ color: 'warning' })
    await ui.unmount()
  })

  test(`${TAG} only a superseded row has Keep and Close: plain Buttons, no quick key, two cells apart`, async ($, on) => {
    withSnap(on, TASKED)
    const ui = await mount($)
    expect(await keys(ui, 'keep:')).toEqual(['keep:sup-1:1'])
    expect(await keys(ui, 'close:')).toEqual(['close:sup-1:1'])
    const pair = [...(await buttons(ui, 'keep:')), ...(await buttons(ui, 'close:'))]
    expect(pair.map(b => b.props.label)).toEqual(['Keep', 'Close'])
    expect(pair.every(b => b.props.plain === true && b.props.hotkey === undefined)).toBe(true)
    const row = (await ui.findAll({ type: 'Box' })).find(b => b.props.flexDirection === 'row' && Number(b.props.gap) >= 2 && (b.text ?? '').startsWith('KeepClose'))
    expect(row).toBeDefined()
    await ui.unmount()
  })

  test(`${TAG} Keep writes settings.json only; the task goes on as in progress, without its buttons`, async ($, on) => {
    const { w } = withSnap(on, TASKED)
    const ui = await mount($)
    await go(ui, 'keep:sup-1:1')
    expect(settings(w)).toMatchObject({ kept: ['sup-1:1'], closed: [] })
    expect(w.writes.every(p => p === `${DIR}/settings.json`)).toBe(true) // no session file, no other file
    expect(await ui.find({ key: 'keep:sup-1:1' })).toBeUndefined()
    expect(await rowText(ui, 'task:sup-1:1')).toContain('In progress')
    expect(await keys(ui, 'task:')).toHaveLength(7) // kept is still not done
    await ui.unmount()
  })

  test(`${TAG} Close writes settings.json only; the task leaves the list and the count`, async ($, on) => {
    const { w } = withSnap(on, TASKED)
    w.put(`${DIR}/settings.json`, { v: 1, view: 'compact', bandHidden: false, seen: ['x:1'] }) // a file from before Keep and Close
    const ui = await mount($)
    await go(ui, 'close:sup-1:1')
    expect(settings(w)).toMatchObject({ seen: ['x:1'], kept: [], closed: ['sup-1:1'] })
    expect(w.writes.every(p => p === `${DIR}/settings.json`)).toBe(true)
    expect(await ui.find({ key: 'task:sup-1:1' })).toBeUndefined()
    expect(await keys(ui, 'task:')).toHaveLength(6)
    expect((await texts(ui)).some(t => t === '6')).toBe(true)
    await ui.unmount()
  })

  test(`${TAG} a long list stops at 8 rows and says where the rest is; with none, the heading says so`, async ($, on) => {
    const many = Array.from({ length: 10 }, (_, i) => sess(`m-${i}`, 'running', 1, 'web-app', `t${i}`, { repo: { path: '/work/web-app', name: 'web-app' }, asks: [{ n: 1, text: `task ${i}`, kind: 'task', status: 'in-progress', at: at(10 + i) }] }))
    const { box } = withSnap(on, many)
    const ui = await mount($)
    expect(await keys(ui, 'task:')).toHaveLength(8)
    expect((await texts(ui)).some(t => t === 'and 2 more, all on the Board (/tracker web)')).toBe(true)
    box.value = snapAt(aloneTown())
    await ui.redraw()
    expect((await texts(ui)).some(t => t === 'Every task you gave is done.')).toBe(true)
    await ui.unmount()
  })
})

describe('Home, the triage queue', () => {
  test(`@F38 ${TAG} Pane button and /tracker open Home with focus on the first row`, async ($, on) => {
    const { w } = withSnap(on, paneTown())
    await run($, '')
    expect(w.opens).toEqual([{ id: 'tracker', title: 'Tracker', focus: true }])
    const ui = await mount($, 70, true)
    expect((await texts(ui))[0]).toBe('Agent tracker')
    // Home leads with the tasks, and a session that waits is one of them: the ring starts on the first.
    const first = (await buttons(ui, 'task:'))[0]!
    expect(first.props.key).toBe('task:docs-1:0')
    expect(first.props.autoFocus).toBe(true)
    expect((await keys(ui, 'session:')).slice(0, 2)).toEqual(['session:web-1', 'session:docs-1'])
    expect((await ui.find({ key: 'close' }))?.props.autoFocus).not.toBe(true)
    await ui.unmount()
  })

  test(`@F38 ${TAG} Home draws on every surface`, async ($, on) => {
    withSnap(on, NOTED)
    for (const surface of ['terminal', 'desktop', 'vscode', 'mobile'] as const) {
      const ui = await mount($, 54, false, surface)
      expect(await texts(ui)).toContain('NEEDS YOU')
      expect(await texts(ui)).toContain('YOU SHOULD KNOW')
      await ui.unmount()
    }
  })

  test(`@F39 ${TAG} section order: needs you, you should know, decided without you, running, repos; the sessions without the tracker last`, async ($, on) => {
    withSnap(on, [...NOTED, sess('plain-1', 'running', 3, 'web-app', 'no mod', { source: 'transcript', engine: { since: at(3), status: 'busy' } })])
    const ui = await mount($)
    const all = await texts(ui)
    const order = ['NEEDS YOU', 'YOU SHOULD KNOW', 'DECIDED WITHOUT YOU', 'RUNNING', 'REPOS', '1 session runs without the tracker'].map(h => all.findIndex(t => t.startsWith(h)))
    expect(order.every(i => i >= 0)).toBe(true)
    expect(order).toEqual([...order].sort((a, b) => a - b))
    // The note about sessions without the tracker is one dim line, the last one before the key words.
    const last = all.findIndex(t => t.startsWith('1 session runs'))
    expect(all.findIndex(t => t.startsWith('↑↓ move'))).toBeGreaterThan(last)
    expect(all.findIndex(t => t.startsWith('REPOS'))).toBeLessThan(last)
    expect((await colorOf(ui, /^1 session runs/))?.dimColor).toBe(true)
    await ui.unmount()
  })

  test(`@F40 ${TAG} needs you rows, longest wait first, the reason and the wait; no token or error counts on a row`, async ($, on) => {
    withSnap(on, paneTown())
    const ui = await mount($)
    expect((await keys(ui, 'session:')).slice(0, 2)).toEqual(['session:web-1', 'session:docs-1'])
    expect(await rowText(ui, 'session:web-1')).toMatch(/^● web-app\/fix login redirect\s+permission\s+6m$/)
    expect(await rowText(ui, 'session:docs-1')).toMatch(/^● docs-site\/edit pages\s+question\s+2m$/)
    expect((await texts(ui)).join('\n')).not.toMatch(/tokens|errors?\b|retries|retry/)
    await ui.unmount()
  })

  test(`${TAG} colour on Home: the headings, the glyphs, the reason, the dim wait`, async ($, on) => {
    withSnap(on, NOTED)
    const ui = await mount($)
    expect(await colorOf(ui, 'NEEDS YOU')).toMatchObject({ color: 'error', bold: true })
    expect(await colorOf(ui, 'YOU SHOULD KNOW')).toMatchObject({ color: 'suggestion', bold: true })
    expect(await colorOf(ui, 'DECIDED WITHOUT YOU')).toMatchObject({ color: 'merged', bold: true })
    expect(await colorOf(ui, 'RUNNING')).toMatchObject({ color: 'warning', bold: true })
    expect(await colorOf(ui, '●')).toMatchObject({ color: 'error' })
    expect(await colorOf(ui, /^permission/)).toMatchObject({ color: 'error' })
    expect(await colorOf(ui, '6m')).toMatchObject({ dimColor: true })
    expect((await ui.findAll({ type: 'Text', text: /^2 new$/ })).map(t => t.props.color)).toEqual(expect.arrayContaining(['suggestion', 'merged'])) // one count per section
    await ui.unmount()
  })

  test(`${TAG} every Button is plain and has no quick key`, async ($, on) => {
    withSnap(on, NOTED)
    const ui = await mount($)
    const all = await buttons(ui)
    expect(all.length).toBeGreaterThan(8)
    expect(all.every(b => b.props.plain === true && b.props.hotkey === undefined)).toBe(true)
    await ui.unmount()
  })

  test(`${TAG} the notes: unseen first with a count, a seen one is one dim line, newest first`, async ($, on) => {
    const { box } = withSnap(on, NOTED)
    const ui = await mount($)
    expect(await texts(ui)).toContain('2 new')
    // Two know items, newest first (web-1 22 minutes ago, api-1 40).
    expect((await keys(ui, 'note:')).filter(k => k.includes(':n1'))).toEqual(['note:web-1:n1', 'note:api-1:n1'])
    expect(await rowText(ui, 'note:web-1:n1')).toMatch(/^! web-app\/fix login redirect\s+11:38\n\s+Tests hit the real payment sandbox, not a mock$/)
    expect(await rowText(ui, 'note:web-1:n2')).toMatch(/^◆ web-app\/fix login redirect\s+11:40\n\s+Dark mode follows the system$/)
    // One seen: it drops below the unseen, to one line ending in "seen".
    await go(ui, 'note:web-1:n1')
    await go(ui, 'seen')
    await go(ui, 'back')
    expect(await rowText(ui, 'note:web-1:n1')).toMatch(/^· web-app\/fix login redirect\s+11:38  seen$/)
    expect((await keys(ui, 'note:')).filter(k => k.includes(':n1'))).toEqual(['note:api-1:n1', 'note:web-1:n1'])
    expect(await texts(ui)).toContain('1 new')
    box.value = snapAt(NOTED.map(r => ({ ...r, notes: undefined })))
    await ui.redraw()
    expect(await texts(ui)).not.toContain('YOU SHOULD KNOW') // nothing to show, no empty section
    await ui.unmount()
  })

  test(`${TAG} a folder named by digits is no repo: it groups under "other"`, async ($, on) => {
    withSnap(on, [...paneTown(), sess('num-1', 'needs-you', 4, 'x', 'scratch job', { reason: 'waiting', cwd: '/work/5019', repo: null }), sess('num-2', 'running', 4, '5178', 'other job', { cwd: '/work/5178', repo: { path: '/work/5178', name: '5178' } })])
    const ui = await mount($)
    expect(await rowText(ui, 'session:num-1')).toMatch(/^● other\/scratch job/)
    expect((await keys(ui, 'repos:')).some(k => k.includes('5178') || k.includes('5019'))).toBe(false)
    expect((await texts(ui)).some(t => t === 'other 2')).toBe(true)
    await ui.unmount()
  })

  test(`@F42 ${TAG} the running line and the repos: sessions, PRs behind and red, one Button per repo`, async ($, on) => {
    withSnap(on, paneTown())
    const ui = await mount($)
    const all = await texts(ui)
    expect(all).toContain('◐ 3 sessions')
    expect(all).toContain('PRs ')
    expect(all).toContain('4') // open PRs
    expect(await colorOf(ui, '2 red')).toMatchObject({ color: 'error' })
    expect((await buttons(ui, 'repos:')).map(b => b.text)).toEqual(expect.arrayContaining(['docs-site ●', 'api ◐']))
    await go(ui, 'repos:/work/api')
    expect((await texts(ui)).slice(0, 3)).toEqual(['Home', ' › ', 'api'])
    await ui.unmount()
  })

  test(`@F53 ${TAG} loading, and a stale list says so and dims the rows`, async ($, on) => {
    const { box } = withSnap(on, paneTown(), { at: 0, okAt: 0 })
    const ui = await mount($)
    expect(await texts(ui)).toContain('Reading sessions…')
    box.value = snapAt(paneTown(), { failedReads: 2, okAt: NOON - 120_000 })
    await ui.redraw()
    expect((await texts(ui)).some(t => t.startsWith('Session list unavailable. Showing what was read 2m ago.'))).toBe(true)
    expect((await colorOf(ui, '6m'))?.dimColor).toBe(true)
    await ui.unmount()
  })

  test(`@F45 ${TAG} this session alone: the one line, no running line`, async ($, on) => {
    withSnap(on, aloneTown())
    const ui = await mount($)
    expect(await texts(ui)).toContain('Only this session is running.')
    expect((await texts(ui)).some(t => t.startsWith('REPOS'))).toBe(true)
    await ui.unmount()
  })
})

describe('One item, opened', () => {
  test(`${TAG} a turn's item: what, when, session, the reply to overrule; Back returns to its row`, async ($, on) => {
    const { w } = withSnap(on, NOTED)
    const ui = await mount($, 70, true)
    await go(ui, 'note:web-1:n2')
    const all = await texts(ui)
    expect(all.slice(0, 5)).toEqual(['Home', ' › ', 'decided without you', ' › ', 'web-app/fix login redirect'])
    expect(all).toContain('◆ Dark mode follows the system')
    expect(all).toContain('11:40')
    expect(all).toContain('fix login redirect') // the session's own name
    expect(await colorOf(ui, '◆ Dark mode follows the system')).toMatchObject({ color: 'merged', bold: true })
    expect(all).toContain('Copy this, to paste into that session:')
    expect(all.some(t => t === 'Overruling "Dark mode follows the system"')).toBe(true)
    expect(await colorOf(ui, '<your call>')).toMatchObject({ color: 'warning' })
    await go(ui, 'overrule')
    expect(w.copies.map(c => c.text)).toEqual(['Overruling "Dark mode follows the system"\n(web-app/fix login redirect). Instead: <your call>'])
    expect(w.toasts.at(-1)).toBe(REPLY_COPIED)
    // The resume command is on the page, for that session.
    await go(ui, 'resume')
    expect(w.copies.at(-1)!.text).toBe(resumeCommand('/work/web-app', 'web-1'))
    await go(ui, 'back')
    expect((await ui.find({ key: 'note:web-1:n2' }))?.props.autoFocus).toBe(true)
    await ui.unmount()
  })

  test(`${TAG} a "you should know" item has no overrule: only Mark seen and the resume command`, async ($, on) => {
    withSnap(on, NOTED)
    const ui = await mount($)
    await go(ui, 'note:api-1:n1')
    expect(await keys(ui)).toEqual(expect.arrayContaining(['seen', 'resume']))
    expect(await ui.find({ key: 'overrule' })).toBeUndefined()
    await ui.unmount()
  })

  test(`${TAG} mark seen writes settings.json only, and the count and the band follow; "Mark all seen" marks every one`, async ($, on) => {
    const { w } = withSnap(on, NOTED)
    const ui = await mount($)
    await go(ui, 'note:web-1:n2')
    await go(ui, 'seen')
    expect(settings(w)).toMatchObject({ seen: ['web-1:n2'] })
    expect(w.writes.every(p => p === `${DIR}/settings.json`)).toBe(true)
    expect(await ui.find({ key: 'seen' })).toBeUndefined() // already seen: no button
    await go(ui, 'back')
    expect(await texts(ui)).toContain('1 new')
    await go(ui, 'allseen')
    expect(settings(w)!.seen.sort()).toEqual(['api-1:n1', 'api-1:n2', 'web-1:n1', 'web-1:n2'])
    expect(await ui.find({ key: 'allseen' })).toBeUndefined()
    expect(w.writes.every(p => p === `${DIR}/settings.json`)).toBe(true)
    await ui.unmount()
  })

  test(`${TAG} the open questions of questions.md and the plan's Revisions are decided items, read as files`, async ($, on) => {
    const { w } = withSnap(on, paneTown())
    putChange(w)
    const ui = await mount($)
    const decided = (await keys(ui, 'note:')).filter(k => k.startsWith('note:q:') || k.startsWith('note:r:'))
    expect(decided.length).toBe(2)
    const q = decided.find(k => k.startsWith('note:q:'))!
    expect(await rowText(ui, q)).toMatch(/^◆ web-app\/design-tokens-1\s+\S+\n\s+follow the system \(default taken, Q1\)$/)
    expect(await rowText(ui, decided.find(k => k.startsWith('note:r:'))!)).toMatch(/\n\s+moved the motion work before spacing/)
    await go(ui, q)
    const all = await texts(ui)
    expect(all).toContain('The question:')
    expect(all).toContain('"Dark mode: system or toggle?"')
    expect(all).toContain('changes/2026-11-10-design-tokens/questions.md')
    await go(ui, 'overrule')
    expect(w.copies.at(-1)!.text).toBe('Overruling "follow the system (default taken, Q1)"\n(questions.md, Q1). Instead: <your call>')
    // The revision has a date and no clock time: it reads "today".
    await go(ui, 'back')
    expect((await rowText(ui, decided.find(k => k.startsWith('note:r:'))!))!.split('\n')[0]).toMatch(/today$/)
    // Read only: nothing but the pane's own copy was written, no change file touched.
    expect(w.writes).toEqual([])
    await ui.unmount()
  })

  test(`${TAG} an item that is gone shows one line`, async ($, on) => {
    const { box } = withSnap(on, NOTED)
    const ui = await mount($)
    await go(ui, 'note:web-1:n1')
    box.value = snapAt(NOTED.map(r => ({ ...r, notes: undefined })))
    await ui.redraw()
    expect(await texts(ui)).toContain('That item is gone. Pick one on Home.')
    await ui.unmount()
  })
})

// Open a session from its Home row, as the person does.
const sessionPage = async ($: Engine, on: On, sessions: SessionRecord[], id: string, columns = 70) => {
  const h = withSnap(on, sessions)
  const ui = await mount($, columns)
  await go(ui, `session:${id}`)
  return { ...h, ui }
}
const STARTED = new Date(2026, 10, 14, 10, 42).getTime()
const waiting = (extra: Partial<SessionRecord> = {}) =>
  sess('web-9', 'needs-you', 4, 'web-app', 'fix login redirect', {
    reason: 'permission',
    branch: 'feat/login',
    startedAt: STARTED,
    lastActivityAt: at(1),
    usage: use(41000, 9000, 2, 3),
    asks: [{ n: 1, text: 'Fix login redirect', kind: 'task', status: 'in-progress', at: at(30) }, { n: 2, text: 'why does it loop?', kind: 'question', status: 'replied', at: at(20) }],
    runs: { goalSince: at(14), subagents: [{ id: 's1', name: 'Explore', status: 'running' }], background: [] },
    scan: { at: NOON, ghOk: true, worktrees: [], prs: [{ number: 212, title: 'fix login', url: 'https://example.test/pr/212', branch: 'feat/login', createdAt: '2026-11-10T08:00:00Z', checks: 'pass', review: 'requested', mergeable: 'mergeable', behind: true }] },
    milestone: { slug: 'fix-login-1', sentence: 'x', features: [{ n: 1, name: 'reproduce', state: 'done abc1234' }, { n: 2, name: 'fix', state: 'building' }, { n: 3, name: 'test', state: 'todo' }] },
    ...extra,
  })

describe('Session detail', () => {
  test(`@F103 ${TAG} the breadcrumb, the state at the right, then one line each for branch, tokens, struggles, running, milestone, tasks and PR`, async ($, on) => {
    const { ui } = await sessionPage($, on, [...paneTown(), waiting()], 'web-9')
    const all = await texts(ui)
    expect(all.slice(0, 5)).toEqual(['Home', ' › ', 'web-app', ' › ', 'fix login redirect'])
    expect(await colorOf(ui, '● permission 4m')).toMatchObject({ color: 'error' })
    const body = all.join('\n')
    expect(body).toContain('branch ')
    expect(body).toContain('since ')
    expect(body).toContain('10:42')
    expect(body).toContain('in 41k')
    expect(body).toContain('out 9k')
    expect(all).toContain('3 retries')
    expect(await colorOf(ui, '3 retries')).toMatchObject({ color: 'warning' })
    expect(all).toContain('/goal 14m')
    expect(body).toContain('subagent Explore running')
    expect(all).toContain('fix-login-1')
    expect(body).toContain('1/3')
    expect(all).toContain('Fix login redirect') // the task, not the question
    expect(body).not.toContain('why does it loop?')
    expect((await ui.find({ type: 'Link' }))?.props).toMatchObject({ href: 'https://example.test/pr/212', label: '#212' }) // the PR is a link
    expect(all).toContain('BEHIND')
    expect(await colorOf(ui, 'BEHIND')).toMatchObject({ color: 'warning' })
    // Nothing the collector does not have: no model, context or cost line.
    expect(body).not.toMatch(/\bmodel\b|context|~\$/)
    await ui.unmount()
  })

  test(`@F49 ${TAG} Copy resume command, for any session with a plain id; the folder single-quoted`, async ($, on) => {
    const odd = waiting({ cwd: "/work/my web-app's copy" })
    const { ui, w } = await sessionPage($, on, [...paneTown(), odd], 'web-9')
    const resume = (await ui.find({ key: 'resume' }))!
    expect([resume.props.label, resume.props.hotkey, resume.props.plain]).toEqual(['Copy resume command', undefined, true])
    await go(ui, 'resume')
    expect(w.copies.map(c => c.text)).toEqual(["cd '/work/my web-app'\\''s copy' && claude --resume web-9"])
    expect(w.toasts).toEqual(['Resume command copied'])
    w.failCopy = 'no-clipboard'
    await go(ui, 'resume')
    expect(w.toasts.at(-1)).toBe('Copy failed: no-clipboard. Press Copy resume command again.')
    await ui.unmount()
  })

  test(`@F49 ${TAG} an id with shell characters is never a command: no helper result, no button`, async ($, on) => {
    expect(resumeCommand('/work/web-app', 'x; rm -rf ~')).toBeNull()
    expect(resumeCommand('/work/web-app', '$(touch pwned)')).toBeNull()
    expect(resumeCommand('/work/web-app', '')).toBeNull()
    expect(resumeCommand('/work/web-app', 'a'.repeat(65))).toBeNull()
    expect(resumeCommand("/work/it's", 'Ab_9-z')).toBe("cd '/work/it'\\''s' && claude --resume Ab_9-z")
    const { ui, w } = await sessionPage($, on, [...paneTown(), waiting({ sessionId: 'x; rm -rf ~' })], 'x; rm -rf ~')
    expect(await ui.find({ key: 'resume' })).toBeUndefined()
    expect(w.copies).toEqual([])
    await ui.unmount()
  })

  test(`@F111 ${TAG} an open page turns ended when the session leaves the list; a session not found says so`, async ($, on) => {
    const { ui, box } = await sessionPage($, on, [...paneTown(), waiting()], 'web-9')
    box.value = snapAt([...paneTown(), waiting({ state: 'ended', endedAt: at(0), reason: null })])
    await ui.redraw()
    expect(await texts(ui)).toContain('○ ended <1m ago')
    box.value = snapAt(paneTown())
    await ui.redraw()
    expect(await texts(ui)).toContain('No session matches "web-9". Pick one on Home.')
    await ui.unmount()
  })

  test(`${TAG} Back and the crumbs: Back returns to the row, the Home crumb to Home`, async ($, on) => {
    const { ui } = await sessionPage($, on, [...paneTown(), waiting()], 'web-9')
    await go(ui, 'back')
    expect((await ui.find({ key: 'session:web-9' }))?.props.autoFocus).toBe(true)
    await go(ui, 'session:web-9')
    await go(ui, 'crumb:0')
    expect(await texts(ui)).toContain('NEEDS YOU')
    await go(ui, 'session:web-9')
    await go(ui, 'crumb:1') // web-app: the Repo page
    expect((await texts(ui)).slice(0, 3)).toEqual(['Home', ' › ', 'web-app'])
    await ui.unmount()
  })
})

describe('the Repo, Milestone and Feature pages', () => {
  const open = async ($: Engine, on: On) => {
    const h = withSnap(on, paneTown())
    putChange(h.w)
    const ui = await mount($, 70, true)
    await go(ui, 'repos:/work/web-app')
    return { ...h, ui }
  }

  test(`${TAG} Repo: milestones from the change folders, your asks here, worktrees, other PRs`, async ($, on) => {
    const { ui } = await open($, on)
    const all = await texts(ui)
    expect(all.slice(0, 3)).toEqual(['Home', ' › ', 'web-app'])
    expect(all).toContain('MILESTONES')
    expect(all).toContain('YOUR ASKS HERE')
    expect(all).toContain('WORKTREES')
    expect(all).toContain('OTHER PRs')
    expect(await colorOf(ui, 'MILESTONES')).toMatchObject({ bold: true })
    // The milestone is a Button, its progress counted from the files: the facts that pass when there is a gate report.
    const row = await rowText(ui, `milestone:${CHANGE}`)
    expect(row).toMatch(/^● design-tokens-1\s+1\/4 facts/) // red: feature 4 is blocked
    expect(row).toContain('project: design system · ABC-210')
    expect((await buttons(ui)).every(b => b.props.hotkey === undefined)).toBe(true)
    await ui.unmount()
  })

  test(`${TAG} Milestone: where it lives, ticket and PR, stage, features as Buttons, facts coloured by the gate report, the open question`, async ($, on) => {
    const { ui } = await open($, on)
    await go(ui, `milestone:${CHANGE}`)
    const all = await texts(ui)
    expect(all.slice(0, 7)).toEqual(['Home', ' › ', 'web-app', ' › ', 'design system', ' › ', 'design-tokens-1'])
    expect(all).toContain(`changes/${CHANGE} · branch feat/dark`)
    expect(all).toContain('ABC-210')
    expect(all).toContain('STAGE')
    expect(all).toContain('FEATURES')
    expect(await keys(ui, 'feature:')).toEqual(['feature:0', 'feature:1', 'feature:2', 'feature:3', 'feature:4'])
    expect(await rowText(ui, 'feature:2')).toMatch(/^◐ 2 motion durations\s+building$/)
    expect(await rowText(ui, 'feature:4')).toMatch(/^✗ 4 dark mode\s+blocked: needs F12 answer$/)
    expect(await rowText(ui, 'feature:1')).toMatch(/✓ 1 token file and lint rule\s+b72c9d1$/)
    expect(await colorOf(ui, /^F1$/)).toMatchObject({ color: 'success' }) // met
    expect(await colorOf(ui, /^F9$/)).toMatchObject({ color: 'error' }) // unmet
    expect(await colorOf(ui, /^F10$/)).toMatchObject({ dimColor: true }) // not checked
    expect(await colorOf(ui, '1 open')).toMatchObject({ color: 'error' })
    expect(all).toContain('QUESTIONS')
    expect(all).toContain('FINDINGS')
    await ui.unmount()
  })

  test(`${TAG} Feature: its facts and the test files they name, with the verdict`, async ($, on) => {
    const { ui } = await open($, on)
    await go(ui, `milestone:${CHANGE}`)
    await go(ui, 'feature:2')
    const all = await texts(ui)
    expect(all.slice(0, 5)).toEqual(['…', ' › ', 'design-tokens-1', ' › ', '2 motion durations'])
    expect(all).toContain('◐ building')
    expect(await colorOf(ui, '◐ building')).toMatchObject({ color: 'warning' })
    expect(all.join('\n')).toContain('facts ')
    expect(all).toContain('TESTS')
    expect(all.some(t => t.includes('motion.test.ts'))).toBe(true)
    expect(all.some(t => t === '2 not met')).toBe(true)
    // Back, then the crumb to the Repo page.
    await go(ui, 'back')
    expect(await keys(ui, 'feature:')).toContain('feature:2')
    await go(ui, 'feature:2')
    await go(ui, 'crumb:0')
    expect(await texts(ui)).toContain('MILESTONES')
    await ui.unmount()
  })

  test(`@F121 ${TAG} a repo with no change folders shows no milestones section; a repo not found says so`, async ($, on) => {
    withSnap(on, paneTown())
    const ui = await mount($, 70, true)
    await go(ui, 'repos:/work/api')
    expect(await texts(ui)).not.toContain('MILESTONES')
    await run($, 'repo zzz')
    await ui.redraw()
    expect(await texts(ui)).toContain('No repo named "zzz" has had a session. Pick one on Home.')
    await ui.unmount()
  })
})

describe('/tracker words and what the pane touches', () => {
  test(`@F122 ${TAG} /tracker session and repo match by substring, an unknown word gives the hint, web goes on to the Board`, async ($, on) => {
    const { w } = withSnap(on, paneTown())
    expect(((await run($, 'frobnicate')) as { text: string }).text).toBe('Try /tracker, details, compact, copy, repo, session, web, band on, band off.')
    await run($, 'session LOGIN')
    expect(w.opens.at(-1)!.id).toBe('tracker')
    const ui = await mount($)
    expect((await texts(ui)).slice(0, 5)).toEqual(['Home', ' › ', 'web-app', ' › ', 'fix login redirect'])
    await run($, 'repo docs')
    await ui.redraw()
    expect((await texts(ui)).slice(0, 3)).toEqual(['Home', ' › ', 'docs-site'])
    await run($, 'session zzz')
    await ui.redraw()
    expect(await texts(ui)).toContain('No session matches "zzz". Pick one on Home.')
    // `web` is the Board's (registered before the pane): it writes the page and answers, never the pane's hint.
    expect(((await run($, 'web')) as { text: string }).text).toContain('~/.claude/agent-tracker/board.html')
    await ui.unmount()
  })

  test(`${TAG} every page and press writes nothing but settings.json, runs nothing and touches no session`, async ($, on) => {
    const { w } = withSnap(on, NOTED)
    putChange(w)
    const ui = await mount($, 70, true)
    for (const key of ['note:web-1:n2', 'overrule', 'back', 'repos:/work/web-app', `milestone:${CHANGE}`, 'feature:2', 'crumb:0', 'back', 'back', 'session:web-1', 'resume', 'back', 'allseen', 'close']) {
      await ui.press({ key }).catch(() => undefined) // a key the page does not draw is not pressed
      await ui.redraw()
    }
    for (const args of ['', 'session login', 'repo web', 'session zzz', 'repo zzz', 'frobnicate']) await run($, args)
    expect(w.writes.every(p => p === `${DIR}/settings.json`)).toBe(true)
    expect([w.origins.length, w.toolCalls, w.net.length, w.models.length]).toEqual([0, 0, 0, 0])
    expect(w.procs.length).toBe(0)
    // Copies: the reply to overrule and the resume commands, and nothing else.
    expect(w.copies.every(c => c.text.startsWith('Overruling') || c.text.startsWith("cd '"))).toBe(true)
    await ui.unmount()
  })
})
