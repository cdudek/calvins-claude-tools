import { describe, expect, test } from 'claude-code/testing'
import type { On } from 'claude-code'
import type { Engine } from 'claude-code/testing'

import { ONLY_THIS, PRS_NOT_SHOWN, cells, staleTop } from '../hooks/tracker/core'
import type { SessionRecord, Snapshot } from '../hooks/tracker/types'
import { MIN, NOON, SELF, aloneTown, at, paneTown, rec, sess, snapAt, use } from './fixtures/pane'
import type { Ask } from '../hooks/tracker/types'
import { scan } from './fixtures/band'
import { world } from './fixtures/world'
import type { World } from './fixtures/world'

const TAG = '@2026-11-13-agent-tracker'

// The snapshot the collector would have written, as the state read answers it. `box.value` changes between draws.
const withSnap = (on: On, sessions: SessionRecord[], extra: Partial<Snapshot> = {}, now = NOON) => {
  const w = world(on, { now, id: SELF, cwd: '/work/platform-tools-suite', panes: true })
  const box = { value: snapAt(sessions, extra) }
  on('state.get', (_, e, next) => (e.key === 'snapshot' ? ({ value: { value: box.value, version: 1 } } as never) : next(e)))
  return { w, box }
}

const PANE = (columns: number, isFocused: boolean) =>
  ({ component: 'Pane', requestId: 'tracker', props: { title: 'Tracker', isFocused, bodyColumns: columns, placement: 'dock', scroll: { offset: 0, bodyRows: 40 }, view: {} } }) as const
const mount = ($: Engine, columns = 115, isFocused = false, surface: 'terminal' | 'desktop' = 'terminal') => $.ui.mount({ plugin: 'agent-tracker', surface, ...PANE(columns, isFocused) } as never)
const props = (columns: number, isFocused: boolean) => PANE(columns, isFocused).props as never
const run = ($: Engine, args: string) => $.command.run({ command: 'tracker', args, origin: { kind: 'composer' }, presentation: {} as never })

type Ui = Awaited<ReturnType<typeof mount>>
const texts = async (ui: Ui) => (await ui.findAll({ type: 'Text' })).map(t => t.text ?? '')
const buttons = async (ui: Ui, prefix = '') => (await ui.findAll({ type: 'Button' })).filter(b => String(b.props.key ?? '').startsWith(prefix))
const keys = async (ui: Ui, prefix: string) => (await buttons(ui, prefix)).map(b => String(b.props.key))
const rowText = async (ui: Ui, key: string) => (await ui.find({ key }))?.text
const headings = async (ui: Ui) => (await texts(ui)).filter(t => ['Needs you', 'Running', 'Done', 'Ended today'].includes(t))

describe('Home, the shell', () => {
  test(`@F38 ${TAG} Pane button and /tracker open Home with focus on the first row`, async ($, on) => {
    const { w } = withSnap(on, paneTown())
    await run($, '')
    expect(w.opens).toEqual([{ id: 'tracker', title: 'Tracker', focus: true }])
    const ui = await mount($, 115, true)
    expect((await texts(ui))[0]).toBe('Tracker') // the title, first line of the page
    const first = (await buttons(ui, 'session:'))[0]!
    expect(first.props.key).toBe('session:web-1')
    expect(first.props.autoFocus).toBe(true) // focus starts on the first row, not on Close
    expect((await ui.find({ key: 'close' }))?.props.autoFocus).not.toBe(true)
    await ui.unmount()
  })

  test(`@F38 ${TAG} the band's Pane button opens the same pane`, async ($, on) => {
    const { w } = withSnap(on, paneTown())
    const band = await $.ui.mount({ plugin: 'agent-tracker', surface: 'terminal', component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 12, bodyColumns: 115, scroll: { offset: 0, bodyRows: 12 }, view: {} } } as never)
    await band.press({ key: 'pane' })
    expect(w.opens.map(o => o.id)).toEqual(['tracker'])
    expect([w.opens[0]!.focus, w.opens[0]!.closeOnEscape]).toEqual([true, undefined])
    await band.unmount()
  })

  test(`@F38 ${TAG} Home draws on every surface`, async ($, on) => {
    withSnap(on, paneTown())
    for (const surface of ['terminal', 'desktop', 'vscode', 'mobile'] as const) {
      const ui = await $.ui.mount({ plugin: 'agent-tracker', surface, ...PANE(54, false) } as never)
      expect((await ui.find({ type: 'Text', text: 'Needs you' }))?.text).toBe('Needs you')
      expect((await ui.findAll({ type: 'Button' })).length).toBeGreaterThan(5)
      await ui.unmount()
    }
  })

  test(`@F92 ${TAG} Escape only hands the keys back: the pane opens with focus and without closeOnEscape, and Close closes it`, async ($, on) => {
    const { w } = withSnap(on, paneTown())
    await run($, '')
    expect(w.opens[0]!.focus).toBe(true)
    expect(w.opens[0]!.closeOnEscape).toBeUndefined() // no Escape-close path: the engine closes on Escape only when asked to
    const ui = await mount($, 115, true)
    expect(w.closes).toEqual([]) // nothing closed it
    await ui.press({ key: 'close' })
    expect(w.closes).toEqual(['tracker'])
    await ui.unmount()
  })

  test(`@F91 ${TAG} Close closes the pane, and nothing here refuses the person's own close (ctrl+x x, Escape)`, async ($, on) => {
    const { w } = withSnap(on, paneTown())
    const ui = await mount($)
    await ui.press({ key: 'close' })
    expect(w.closes).toEqual(['tracker'])
    await ui.unmount()
  })

  test(`@F39 ${TAG} section order: Needs you, Running, Done, Ended today, Repos`, async ($, on) => {
    withSnap(on, paneTown())
    const ui = await mount($)
    expect(await headings(ui)).toEqual(['Needs you', 'Running', 'Done', 'Ended today'])
    const all = await texts(ui)
    expect(all.indexOf('Ended today')).toBeLessThan(all.indexOf('Repos:'))
    expect(all.at(-1)).not.toBe('Tracker')
    await ui.unmount()
  })

  test(`@F40 ${TAG} Needs you rows, longest wait first, with the reason, errors and retries`, async ($, on) => {
    withSnap(on, paneTown())
    const ui = await mount($)
    const needs = (await keys(ui, 'session:')).slice(0, 2)
    expect(needs).toEqual(['session:web-1', 'session:docs-1']) // 6m before 2m
    expect(await rowText(ui, 'session:web-1')).toBe('● fix login redirect   web-app · feat/login · 6m · asks permission · 2 errors · 1 retry')
    expect(await rowText(ui, 'session:docs-1')).toBe('● edit pages   docs-site · main · 2m · asks a question')
    await ui.unmount()
  })

  test(`@F40 ${TAG} the reason words: state unknown and waiting`, async ($, on) => {
    withSnap(on, [sess('a', 'needs-you', 3, 'web-app', 'x', { reason: 'unknown', unknownValue: 'weird' }), sess('b', 'needs-you', 2, 'web-app', 'y', { reason: 'waiting' }), sess(SELF, 'running', 1, 'web-app', 'me')])
    const ui = await mount($)
    expect(await rowText(ui, 'session:a')).toContain('3m · state unknown')
    expect(await rowText(ui, 'session:b')).toContain('2m · waiting')
    await ui.unmount()
  })

  test(`@F41 ${TAG} Done and Ended today caps, then a more line`, async ($, on) => {
    const done = Array.from({ length: 12 }, (_, i) => sess(`d${i}`, 'done', i + 1, 'web-app', `done ${i}`))
    const ended = Array.from({ length: 7 }, (_, i) => sess(`e${i}`, 'ended', 60 + i, 'web-app', `ended ${i}`, { endedAt: at(60 + i) }))
    withSnap(on, [sess(SELF, 'running', 1, 'web-app', 'me'), ...done, ...ended])
    const ui = await mount($)
    expect((await keys(ui, 'session:')).filter(k => k.startsWith('session:d')).length).toBe(10)
    expect((await keys(ui, 'session:')).filter(k => k.startsWith('session:e')).length).toBe(5)
    expect((await texts(ui)).filter(t => t.startsWith('and '))).toEqual(['and 2 more on the Repo pages', 'and 2 more on the Repo pages'])
    await ui.unmount()
  })

  test(`@F42 ${TAG} the Repos line, most recent session first, entries are buttons, in every state`, async ($, on) => {
    const { box } = withSnap(on, paneTown())
    const ui = await mount($)
    const entries = await buttons(ui, 'repos:')
    expect(entries.map(b => b.props.label ?? b.text)).toEqual(['docs-site', 'api', 'web-app 4 PRs', 'platform-tools-suite'])
    expect(await texts(ui)).toContain('Repos:')
    // Alone, stale, partial and quiet states keep the line.
    for (const next of [snapAt(aloneTown()), snapAt(paneTown(), { failedReads: 2 }), snapAt(paneTown().map(r => (r.scan ? { ...r, scan: { ...r.scan, ghOk: false } } : r))), snapAt(paneTown().filter(r => r.state !== 'needs-you'))]) {
      box.value = next
      await ui.redraw()
      expect(await texts(ui)).toContain('Repos:')
      expect((await buttons(ui, 'repos:')).length).toBeGreaterThan(0)
    }
    await ui.unmount()
  })

  test(`@F44 ${TAG} empty Needs you reads Nothing needs you`, async ($, on) => {
    withSnap(on, paneTown().filter(r => r.state !== 'needs-you'))
    const ui = await mount($)
    expect(await texts(ui)).toContain('Nothing needs you.')
    expect(await texts(ui)).not.toContain(ONLY_THIS)
    await ui.unmount()
  })

  test(`@F45 ${TAG} Empty, alone: the one line, no Running section, then Repos`, async ($, on) => {
    withSnap(on, aloneTown())
    const ui = await mount($)
    const all = await texts(ui)
    expect(all).toContain('Only this session is running. Sessions in other terminals show up here when they start.')
    expect(all).not.toContain('Nothing needs you.')
    expect(await headings(ui)).toEqual(['Needs you'])
    expect(all).toContain('Repos:')
    await ui.unmount()
  })

  test(`@F102 ${TAG} alone and waiting: this session under Needs you, no Empty line`, async ($, on) => {
    withSnap(on, aloneTown('needs-you'))
    const ui = await mount($)
    expect(await rowText(ui, `session:${SELF}`)).toBe('● this session   platform-tools-suite · main · 4m · waiting')
    expect(await texts(ui)).not.toContain(ONLY_THIS)
    await ui.unmount()
  })

  test(`@F43 ${TAG} frozen order, the new mark, re-sort on leave and reopen`, async ($, on) => {
    const { box } = withSnap(on, paneTown())
    const ui = await mount($, 115, true) // the pane has the keyboard
    const order = async () => (await keys(ui, 'session:')).slice(0, 3)
    expect(await order()).toEqual(['session:web-1', 'session:docs-1', 'session:api-1'])
    // A session waits for 30 minutes: it would sort first, but the order is frozen and it is added last, marked new.
    box.value = snapAt([...paneTown(), sess('late-1', 'needs-you', 30, 'api', 'late one', { reason: 'waiting' })])
    await ui.redraw()
    expect((await keys(ui, 'session:')).slice(0, 3)).toEqual(['session:web-1', 'session:docs-1', 'session:late-1'])
    expect(await rowText(ui, 'session:late-1')).toContain('30m · waiting · new')
    expect(await rowText(ui, 'session:web-1')).not.toContain('new')
    // The keyboard leaves: it sorts, and the mark goes.
    await ui.redraw(props(115, false))
    expect((await keys(ui, 'session:'))[0]).toBe('session:late-1')
    expect(await rowText(ui, 'session:late-1')).not.toContain('new')
    // The keyboard returns: the order is frozen again from here.
    await ui.redraw(props(115, true))
    box.value = snapAt([...paneTown(), sess('late-1', 'needs-you', 30, 'api', 'late one', { reason: 'waiting' }), sess('late-2', 'needs-you', 40, 'api', 'later one', { reason: 'waiting' })])
    await ui.redraw()
    expect((await keys(ui, 'session:')).slice(0, 4)).toEqual(['session:late-1', 'session:web-1', 'session:docs-1', 'session:late-2'])
    // Reopening starts afresh.
    await run($, '')
    await ui.redraw()
    expect((await keys(ui, 'session:'))[0]).toBe('session:late-2')
    expect(await rowText(ui, 'session:late-2')).not.toContain('new')
    await ui.unmount()
  })

  test(`@F53 ${TAG} loading line`, async ($, on) => {
    withSnap(on, [], { at: 0, okAt: 0 })
    const ui = await mount($)
    const all = await texts(ui)
    expect(all).toContain('Reading sessions…')
    expect(all[0]).toBe('Tracker')
    expect(await headings(ui)).toEqual([])
    expect(await ui.find({ key: 'close' })).toBeDefined()
    await ui.unmount()
  })

  test(`@F54 ${TAG} partial line: gh missing, headings without PR counts`, async ($, on) => {
    withSnap(on, paneTown().map(r => (r.scan ? { ...r, scan: { ...r.scan, ghOk: false } } : r)))
    const ui = await mount($)
    const all = await texts(ui)
    expect(all).toContain(PRS_NOT_SHOWN)
    expect(PRS_NOT_SHOWN).toBe('PRs not shown: gh is not installed or not signed in. Run gh auth login to see them.')
    expect(all.indexOf(PRS_NOT_SHOWN)).toBeLessThan(all.indexOf('Needs you')) // directly under the title row
    for (const b of await buttons(ui, 'repo:')) expect(String(b.text)).not.toMatch(/PR/)
    for (const b of await buttons(ui, 'repos:')) expect(String(b.text)).not.toMatch(/PR/)
    await ui.unmount()
  })

  test(`@F123 ${TAG} stale line on Home, the last list dimmed`, async ($, on) => {
    withSnap(on, paneTown(), { failedReads: 2, okAt: NOON - 2 * MIN })
    const ui = await mount($)
    const all = await texts(ui)
    expect(all).toContain('Session list unavailable. Showing what was read 2m ago. Retrying every 5 seconds; if it keeps failing, update Claude Code.')
    expect(staleTop(null)).toBe('Session list unavailable. Retrying every 5 seconds; if it keeps failing, update Claude Code.')
    const title = (await ui.find({ type: 'Text', text: /fix login redirect/ }))!
    expect(title.props.dimColor).toBe(true)
    await ui.unmount()
  })

  test(`@F123 ${TAG} one failed read does not show the stale line`, async ($, on) => {
    withSnap(on, paneTown(), { failedReads: 1 })
    const ui = await mount($)
    expect((await texts(ui)).some(t => t.startsWith('Session list unavailable'))).toBe(false)
    await ui.unmount()
  })

  test(`@F101 ${TAG} updated just now and updated 2m ago`, async ($, on) => {
    const { w } = withSnap(on, paneTown())
    const ui = await mount($)
    expect(await texts(ui)).toContain('updated just now')
    await w.clock.advance(2 * MIN)
    await ui.redraw()
    expect(await texts(ui)).toContain('updated 2m ago')
    await ui.unmount()
  })

  test(`@F126 ${TAG} redraw after one minute with no data change`, async ($, on) => {
    const { w } = withSnap(on, paneTown())
    const ui = await mount($)
    const before = w.invalidations
    await w.clock.advance(60_000)
    expect(w.invalidations).toBeGreaterThan(before) // the pane asked for a redraw with no band mounted
    await ui.redraw()
    expect(await rowText(ui, 'session:web-1')).toContain('7m · asks permission')
    await ui.unmount()
  })

  test(`@F131 ${TAG} without-the-tracker line for one and many sessions, hidden at none`, async ($, on) => {
    const engine = (id: string) => sess(id, 'running', 3, 'web-app', `e ${id}`, { source: 'engine' })
    const { box } = withSnap(on, [...paneTown(), engine('x1'), engine('x2')])
    const ui = await mount($)
    const many = '2 sessions run without the tracker. Questions they ask in text are not detected.'
    expect(await texts(ui)).toContain(many)
    expect((await ui.find({ type: 'Text', text: many }))?.props.dimColor).toBe(true)
    box.value = snapAt([...paneTown(), engine('x1')])
    await ui.redraw()
    expect(await texts(ui)).toContain('1 session runs without the tracker. Questions it asks in text are not detected.')
    box.value = snapAt(paneTown())
    await ui.redraw()
    expect((await texts(ui)).some(t => t.includes('without the tracker'))).toBe(false)
    // An ended session without a file is not running: it does not count.
    box.value = snapAt([...paneTown(), sess('x3', 'ended', 90, 'web-app', 'gone', { source: 'engine', endedAt: at(90) })])
    await ui.redraw()
    expect((await texts(ui)).some(t => t.includes('without the tracker'))).toBe(false)
    await ui.unmount()
  })
})

describe('Home, the lists', () => {
  test(`@F93 ${TAG} Running rows under repo headings, the repo with the longest-running session first`, async ($, on) => {
    withSnap(on, paneTown())
    const ui = await mount($)
    const order = (await keys(ui, 'session:')).filter(k => ['session:api-1', 'session:api-2', `session:${SELF}`].includes(k))
    expect(order).toEqual(['session:api-1', 'session:api-2', `session:${SELF}`])
    expect(await rowText(ui, 'session:api-1')).toBe('◐ migrate users   feat/users · 22m · 41k tokens · 2 errors · 1 retry')
    expect(await rowText(ui, 'session:api-2')).toBe('◐ seed data   main · 5m · 900 tokens')
    expect(await rowText(ui, `session:${SELF}`)).toBe('◐ build the band   milestone/agent-tracker-1 · 20m · 41k tokens')
    const headings = (await keys(ui, 'repo:')).slice(0, 2)
    expect(headings).toEqual(['repo:/work/api', 'repo:/work/platform-tools-suite'])
    await ui.unmount()
  })

  test(`@F94 ${TAG} Done rows, latest first, under repo headings`, async ($, on) => {
    withSnap(on, paneTown())
    const ui = await mount($)
    expect(await rowText(ui, 'session:docs-2')).toBe('✓ rename skills   main · 3m ago · 12k tokens')
    expect(await rowText(ui, 'session:web-2')).toBe('✓ dark mode   feat/dark · 9m ago · 4k tokens · 1 error')
    const keysInOrder = await keys(ui, 'session:')
    expect(keysInOrder.indexOf('session:docs-2')).toBeLessThan(keysInOrder.indexOf('session:web-2'))
    await ui.unmount()
  })

  test(`@F95 ${TAG} Ended today rows since local midnight, newest first`, async ($, on) => {
    withSnap(on, paneTown())
    const ui = await mount($)
    expect(await rowText(ui, 'session:web-3')).toBe('○ fix typo   main · ended 2h ago · 4k tokens')
    expect(await ui.find({ key: 'session:web-4' })).toBeUndefined() // ended yesterday
    await ui.unmount()
  })

  test(`@F96 ${TAG} empty sections are hidden`, async ($, on) => {
    withSnap(on, paneTown().filter(r => r.state !== 'done' && r.state !== 'ended'))
    const ui = await mount($)
    expect(await headings(ui)).toEqual(['Needs you', 'Running'])
    await ui.unmount()
  })

  test(`@F97 ${TAG} each repo heading is a button with its PR counts`, async ($, on) => {
    withSnap(on, paneTown())
    const ui = await mount($)
    const web = (await ui.find({ key: 'repo:/work/web-app' }))!
    expect(web.text).toBe('web-app · 4 PRs · 2 failing')
    expect(web.type).toBe('Button')
    await ui.unmount()
  })

  test(`@F98 ${TAG} no repos reads No repos yet`, async ($, on) => {
    withSnap(on, [rec(SELF, { state: 'running', cwd: '/work/solo' }), rec('b', { state: 'done', cwd: '/work/solo2' })])
    const ui = await mount($)
    expect(await texts(ui)).toContain('No repos yet.')
    expect(await buttons(ui, 'repos:')).toEqual([])
    await ui.unmount()
  })

  test(`@F99 ${TAG} two-line rows at 54 columns, one line at 70`, async ($, on) => {
    withSnap(on, paneTown())
    const narrow = await mount($, 54)
    expect((await rowText(narrow, 'session:web-1'))!.split('\n')).toEqual(['● fix login redirect', '  web-app · feat/login · 6m · asks permission · 2 errors · 1 retry'])
    expect((await rowText(narrow, 'session:api-2'))!.split('\n')).toEqual(['◐ seed data', '  main · 5m · 900 tokens'])
    await narrow.unmount()
    const wide = await mount($, 70)
    expect((await rowText(wide, 'session:web-1'))!.includes('\n')).toBe(false)
    await wide.unmount()
  })

  test(`@F99 ${TAG} only the title is cut, with an ellipsis`, async ($, on) => {
    const long = 'a very long title that cannot fit in the pane at all, not even in the wide view of seventy columns'
    withSnap(on, [sess(SELF, 'running', 1, 'web-app', 'me'), sess('long-1', 'running', 7, 'web-app', long, { branch: 'feat/x' })])
    const narrow = await mount($, 54)
    const [first, second] = (await rowText(narrow, 'session:long-1'))!.split('\n')
    expect(cells(first!)).toBeLessThanOrEqual(54)
    expect(first!.endsWith('…')).toBe(true)
    expect(second).toBe('  feat/x · 7m')
    await narrow.unmount()
    const wide = await mount($, 70)
    const line = (await rowText(wide, 'session:long-1'))!
    expect(cells(line)).toBeLessThanOrEqual(70)
    expect(line).toContain('…   feat/x · 7m')
    await wide.unmount()
  })

  test(`@F100 ${TAG} below 40 columns the second line drops tokens, then the branch; wait, reason, errors and retries stay`, async ($, on) => {
    withSnap(on, paneTown())
    const at39 = await mount($, 39)
    expect((await rowText(at39, 'session:api-1'))!.split('\n')[1]).toBe('  feat/users · 22m · 2 errors · 1 retry') // tokens go first
    await at39.unmount()
    const at30 = await mount($, 30)
    expect((await rowText(at30, 'session:api-1'))!.split('\n')[1]).toBe('  22m · 2 errors · 1 retry') // then the branch
    expect((await rowText(at30, 'session:web-1'))!.split('\n')[1]).toContain('6m · asks permission · 2 errors · 1 retry')
    await at30.unmount()
  })

  test(`@F100 ${TAG} a repo heading cuts its label, never its counts`, async ($, on) => {
    const prs = scan([], true, at(1))
    const many = [1, 2].map(n => ({ number: n, title: `t${n}`, url: `https://example.test/${n}`, branch: `b${n}`, createdAt: '2026-11-01T00:00:00Z', checks: n === 1 ? ('failing' as const) : ('pass' as const), review: 'none' as const, mergeable: 'unknown' as const }))
    withSnap(on, [sess(SELF, 'running', 1, 'web-app', 'me'), sess('r1', 'running', 4, 'a-very-long-repository-name', 'x', { scan: { ...prs, prs: many } })])
    const ui = await mount($, 30)
    const heading = (await ui.find({ key: 'repo:/work/a-very-long-repository-name' }))!.text!
    expect(heading.endsWith(' · 2 PRs · 1 failing')).toBe(true)
    expect(heading).toContain('…')
    expect(cells(heading)).toBeLessThanOrEqual(30)
    await ui.unmount()
  })

  test(`@F124 ${TAG} a word or a count beside every glyph`, async ($, on) => {
    withSnap(on, paneTown())
    const ui = await mount($)
    const rows = await buttons(ui, 'session:')
    expect(rows.length).toBeGreaterThan(5)
    for (const b of rows) {
      expect(String(b.text)).toMatch(/^[●◐✓○] \S/) // a glyph, then the title
      expect(String(b.text)).toMatch(/\d+(m|h|d)\b|<1m/) // a count of time beside it
    }
    expect(await headings(ui)).toEqual(['Needs you', 'Running', 'Done', 'Ended today']) // the section names the state
    await ui.unmount()
  })
})

describe('the pane only observes', () => {
  test(`${TAG} every page, press and /tracker word writes nothing, runs nothing and touches no session`, async ($, on) => {
    const ended = sess('gone-9', 'ended', 90, 'web-app', 'old job', { endedAt: at(90) })
    const { w } = withSnap(on, [...paneTown().map(r => (r.sessionId === 'web-1' ? { ...r, cwd: '/work/web-app/.worktrees/login' } : r)), ended])
    const ui = await mount($, 115, true)
    for (const key of ['session:web-1', 'repo:/work/web-app', 'back', 'home', 'repos:/work/api', 'home', 'session:web-3', 'resume', 'back', 'close']) {
      await ui.press({ key }).catch(() => undefined) // a key the page does not draw is not pressed
      await ui.redraw()
    }
    for (const args of ['', 'session login', 'repo web', 'session zzz', 'repo zzz', 'frobnicate']) await run($, args)
    // No file, prompt, tool call, command, process, network or model call; the only copy is the resume command.
    expect([w.writes.length, w.origins.length, w.toolCalls, w.commandRuns, w.procs.length, w.net.length, w.models.length]).toEqual([0, 0, 0, 0, 0, 0, 0])
    expect(w.copies.map(c => c.text)).toEqual(["cd '/work/web-app' && claude --resume web-3"])
    await ui.unmount()
  })
})

describe('navigation between pages', () => {
  test(`@F88 ${TAG} Close on Home; Back, Home and Close on a Session page, no quick keys`, async ($, on) => {
    withSnap(on, paneTown())
    const ui = await mount($)
    const close = (await ui.find({ key: 'close' }))!
    expect([close.props.label, close.props.hotkey, close.props.plain]).toEqual(['Close', undefined, true])
    expect(await ui.find({ key: 'back' })).toBeUndefined()
    expect(await ui.find({ key: 'home' })).toBeUndefined()
    await ui.press({ key: 'session:web-1' })
    await ui.redraw()
    const nav = await Promise.all(['back', 'home', 'close'].map(async k => (await ui.find({ key: k }))!.props))
    expect(nav.map(p => [p.label, p.hotkey, p.plain])).toEqual([['Back', undefined, true], ['Home', undefined, true], ['Close', undefined, true]])
    await ui.unmount()
  })

  test(`@F89 ${TAG} Back shows the previous page with the same row focused`, async ($, on) => {
    withSnap(on, paneTown())
    const ui = await mount($, 115, true)
    await ui.press({ key: 'session:docs-1' })
    await ui.redraw()
    expect(await ui.find({ key: 'session:docs-1' })).toBeUndefined() // the Session page
    await ui.press({ key: 'back' })
    await ui.redraw()
    expect((await ui.find({ key: 'session:docs-1' }))?.props.autoFocus).toBe(true)
    expect((await ui.find({ key: 'session:web-1' }))?.props.autoFocus).not.toBe(true)
    await ui.unmount()
  })

  test(`@F90 ${TAG} Home button shows the Home page`, async ($, on) => {
    withSnap(on, paneTown())
    const ui = await mount($)
    await ui.press({ key: 'session:web-1' })
    await ui.redraw()
    await ui.press({ key: 'home' })
    await ui.redraw()
    expect(await headings(ui)).toEqual(['Needs you', 'Running', 'Done', 'Ended today'])
    expect((await ui.find({ key: 'session:web-1' }))?.props.autoFocus).toBe(true) // the first row again
    await ui.unmount()
  })
})

// Session page: open a session from its Home row, as the person does.
const openSession = async (ui: Ui, id: string) => {
  await ui.press({ key: `session:${id}` })
  await ui.redraw()
}
const ask = (n: number, text: string, extra: Partial<Ask> = {}): Ask => ({ n, text, kind: 'task', status: 'replied', at: at(30 - n), ...extra })
const STARTED = new Date(2026, 10, 14, 10, 42).getTime()
// This session at its fullest: a goal, a subagent, a background session, a milestone and two asks.
const full = (extra: Partial<SessionRecord> = {}) =>
  sess(SELF, 'running', 22, 'web-app', 'fix login redirect', {
    branch: 'feat/login',
    startedAt: STARTED,
    lastActivityAt: at(1),
    usage: use(41000, 9000, 2, 1),
    runs: { goalSince: at(14), subagents: [{ id: 's1', name: 'review-code-reviewer', status: 'running' }], background: [{ id: 'b1', name: 'docs check', since: at(2) }] },
    asks: [ask(1, 'add a compact view'), ask(2, 'why does login redirect twice?', { kind: 'question', status: 'needs-you' })],
    scan: { at: at(1), ghOk: true, worktrees: [], prs: [{ number: 42, title: 'fix login redirect', url: 'https://example.test/pr/42', branch: 'feat/login', createdAt: '2026-11-10T08:00:00Z', checks: 'failing', review: 'requested', mergeable: 'conflicts' }] },
    milestone: { slug: 'agent-tracker-1', sentence: 'Open any session and see every session.', features: [{ n: 1, name: 'collector', state: 'done abc1234' }, { n: 2, name: 'backfill', state: 'merged' }, { n: 3, name: 'band', state: 'building' }, { n: 4, name: 'pane', state: 'todo' }, { n: 5, name: 'web', state: 'blocked' }] },
    ...extra,
  })
const sessionPage = async ($: Engine, on: On, sessions: SessionRecord[], id = SELF, columns = 115, extra: Partial<Snapshot> = {}) => {
  // Alone, Home lists no Running row for this session: a second live session makes it reachable by its row.
  const reachable = sessions.some(r => r.sessionId !== SELF && r.state !== 'ended') ? sessions : [...sessions, sess('bystander', 'running', 1, 'api', 'bystander')]
  const h = withSnap(on, reachable, extra)
  const ui = await mount($, columns)
  await openSession(ui, id)
  return { ...h, ui }
}
// The lines of an ask row, one Text each.
const askLines = async (ui: Ui, n: number) => (await ui.findAll({ key: `ask:${n}` }))[0]!.children!.map(c => (c as { children: string[] }).children.join(''))

describe('the Session page', () => {
  test(`@F46 ${TAG} Session section order: header, Running now, Usage, Milestone, Asks`, async ($, on) => {
    const { ui } = await sessionPage($, on, [full()])
    const all = await texts(ui)
    const at = (s: string) => all.indexOf(s)
    expect(at('fix login redirect')).toBeGreaterThanOrEqual(0)
    expect([at('Running now'), at('Usage'), at('Milestone'), at('Asks')].every(i => i >= 0)).toBe(true)
    expect(at('fix login redirect')).toBeLessThan(at('Running now'))
    expect(at('Running now')).toBeLessThan(at('Usage'))
    expect(at('Usage')).toBeLessThan(at('Milestone'))
    expect(at('Milestone')).toBeLessThan(at('Asks'))
    await ui.unmount()
  })

  test(`@F46 ${TAG} the page opens from a session row`, async ($, on) => {
    withSnap(on, paneTown())
    const ui = await mount($)
    await openSession(ui, 'web-1')
    expect(await texts(ui)).toContain('fix login redirect')
    expect(await ui.find({ key: 'session:web-1' })).toBeUndefined()
    await ui.unmount()
  })

  test(`@F103 ${TAG} header: title, state line, the repo as a button to Repo, the branch`, async ($, on) => {
    const { ui } = await sessionPage($, on, [full()])
    const all = await texts(ui)
    expect(all.indexOf('fix login redirect')).toBeLessThan(all.indexOf('◐ running · 22m'))
    const repo = (await ui.find({ key: 'repo:/work/web-app' }))!
    expect([repo.type, repo.text]).toEqual(['Button', 'web-app'])
    expect(all).toContain('feat/login')
    await ui.unmount()
  })

  test(`@F104 ${TAG} the state line in each state`, async ($, on) => {
    const { ui, box } = await sessionPage($, on, [full({ state: 'needs-you', reason: 'permission', engine: { since: at(6) } })])
    expect(await texts(ui)).toContain('● needs you · 6m · asks permission')
    const lines = async (r: Partial<SessionRecord>) => {
      box.value = snapAt([full(r)])
      await ui.redraw()
      return texts(ui)
    }
    expect(await lines({ state: 'running', engine: { since: at(22) } })).toContain('◐ running · 22m')
    expect(await lines({ state: 'done', engine: { since: at(3) } })).toContain('✓ done · 3m ago')
    expect(await lines({ state: 'ended', endedAt: at(4), engine: { since: at(22) } })).toContain('○ ended 4m ago')
    expect(await lines({ state: 'needs-you', reason: 'unknown', unknownValue: 'weird', engine: { since: at(6) } })).toContain('● needs you · 6m · state unknown (weird)')
    await ui.unmount()
  })

  test(`@F105 ${TAG} the branch and the link to its PR with its checks`, async ($, on) => {
    const { ui, box } = await sessionPage($, on, [full()])
    const link = (await ui.find({ type: 'Link' }))!
    expect([link.props.href, link.text]).toEqual(['https://example.test/pr/42', '#42'])
    const all = await texts(ui)
    expect(all).toContain('feat/login')
    expect(all).toContain(' · PR ')
    expect(all).toContain(' ✗ checks failing')
    // A branch with no PR shows the branch alone.
    box.value = snapAt([full({ branch: 'feat/other' })])
    await ui.redraw()
    expect(await ui.find({ type: 'Link' })).toBeUndefined()
    expect((await texts(ui)).some(t => t.includes('PR '))).toBe(false)
    await ui.unmount()
  })

  test(`@F106 ${TAG} the Usage line`, async ($, on) => {
    const { ui, box } = await sessionPage($, on, [full()])
    expect(await texts(ui)).toContain('41k tokens in · 9k out · 2 tool errors · 1 retry · started 10:42 · last activity 1m ago')
    box.value = snapAt([full({ usage: use(500, 0, 1, 2) })])
    await ui.redraw()
    expect(await texts(ui)).toContain('500 tokens in · 0 out · 1 tool error · 2 retries · started 10:42 · last activity 1m ago')
    await ui.unmount()
  })

  test(`@F107 ${TAG} Running now: goal, subagents, background sessions; hidden when empty`, async ($, on) => {
    const { ui, box } = await sessionPage($, on, [full()])
    const all = await texts(ui)
    const rows = ['goal · 14m', 'subagent · review-code-reviewer · running', 'background session · docs check · 2m'].map(s => all.indexOf(s))
    expect(rows.every(i => i > all.indexOf('Running now'))).toBe(true)
    expect(rows).toEqual([...rows].sort((a, b) => a - b))
    box.value = snapAt([full({ runs: { goalSince: null, subagents: [], background: [] } })])
    await ui.redraw()
    expect(await texts(ui)).not.toContain('Running now')
    // A goal of a session that is done is not running.
    box.value = snapAt([full({ state: 'done', runs: { goalSince: at(14), subagents: [], background: [] } })])
    await ui.redraw()
    expect(await texts(ui)).not.toContain('Running now')
    await ui.unmount()
  })

  test(`@F48 ${TAG} Milestone only with sdlc-run; done reads complete, merged reads merged`, async ($, on) => {
    const { ui, box } = await sessionPage($, on, [full()])
    const all = await texts(ui)
    expect(all).toContain('agent-tracker-1: Open any session and see every session.')
    expect(all).toContain('2 of 5 features complete')
    for (const row of ['1  collector   complete', '2  backfill   merged', '3  band   building', '4  pane   to do', '5  web   blocked']) expect(all).toContain(row)
    box.value = snapAt([full({ milestone: null })])
    await ui.redraw()
    expect(await texts(ui)).not.toContain('Milestone')
    await ui.unmount()
  })

  test(`@F108 ${TAG} the sentence, then the count, then one row per feature in milestone order`, async ($, on) => {
    const { ui } = await sessionPage($, on, [full()])
    const all = await texts(ui)
    const order = ['Milestone', 'agent-tracker-1: Open any session and see every session.', '2 of 5 features complete', '1  collector   complete', '5  web   blocked'].map(s => all.indexOf(s))
    expect(order.every(i => i >= 0)).toBe(true)
    expect(order).toEqual([...order].sort((a, b) => a - b))
    await ui.unmount()
  })

  test(`@F47 ${TAG} asks oldest first, the empty line, and the transcript note`, async ($, on) => {
    const { ui, box } = await sessionPage($, on, [full()])
    expect(await askLines(ui, 1)).toEqual(['1  task      replied       29m    add a compact view'])
    expect((await askLines(ui, 2))[0]).toMatch(/^2  question  needs you     28m    why does/)
    const keysOf = (await ui.findAll({ type: 'Box' })).map(b => String(b.props.key ?? '')).filter(k => k.startsWith('ask:'))
    expect(keysOf).toEqual(['ask:1', 'ask:2'])
    box.value = snapAt([full({ asks: [] })])
    await ui.redraw()
    expect(await texts(ui)).toContain('No asks yet.')
    box.value = snapAt([full({ source: 'transcript', asks: [ask(1, 'old work', { kind: 'not-classified' })] })])
    await ui.redraw()
    const t = await texts(ui)
    expect(t).toContain('Not classified: this session ran without the tracker.')
    expect(t.some(x => x.startsWith('1  not classified'))).toBe(true)
    expect(t.indexOf('Not classified: this session ran without the tracker.')).toBeGreaterThan(t.indexOf('Asks'))
    await ui.unmount()
  })

  test(`@F109 ${TAG} an ask row at 70 columns: number, kind, status, time and the wrapped text`, async ($, on) => {
    const long = 'make the compact view fit a narrow dock without cutting the count and keep every word readable'
    const { ui } = await sessionPage($, on, [full({ asks: [ask(1, long)] })], SELF, 70)
    const [first, ...rest] = await askLines(ui, 1)
    expect(first).toBe('1  task      replied       29m    make the compact view fit a narrow')
    expect(rest.every(l => l.startsWith(' '.repeat(34)))).toBe(true)
    expect([first!.slice(34), ...rest.map(l => l.slice(34))].join(' ')).toBe(long)
    expect([first, ...rest].every(l => [...l!].length <= 70)).toBe(true)
    await ui.unmount()
  })

  test(`@F110 ${TAG} an ask row at 54 columns takes two lines, the text cut at 4 lines`, async ($, on) => {
    const long = Array.from({ length: 40 }, (_, i) => `word${i}`).join(' ')
    const { ui } = await sessionPage($, on, [full({ asks: [ask(1, long), ask(2, 'short ask', { kind: 'question' })] })], SELF, 54)
    const one = await askLines(ui, 1)
    expect(one[0]).toBe('1  task  replied  29m')
    expect(one.length).toBe(5) // the first line, then the text cut at 4
    expect(one[4]!.endsWith('…')).toBe(true)
    expect(one.every(l => [...l].length <= 54)).toBe(true)
    expect(await askLines(ui, 2)).toEqual(['2  question  replied  28m', '   short ask'])
    await ui.unmount()
  })

  test(`@F49 ${TAG} the resume command for an ended session only, the folder single-quoted`, async ($, on) => {
    const ended = sess('gone-1', 'ended', 90, 'web-app', 'old job', { endedAt: at(90), cwd: "/work/my web-app's copy" })
    const { ui, w, box } = await sessionPage($, on, [sess(SELF, 'running', 1, 'web-app', 'me'), ended], 'gone-1')
    const resume = (await ui.find({ key: 'resume' }))!
    expect([resume.props.label, resume.props.hotkey, resume.props.plain]).toEqual(['Copy resume command', undefined, true])
    await ui.press({ key: 'resume' })
    expect(w.copies.map(c => c.text)).toEqual(["cd '/work/my web-app'\\''s copy' && claude --resume gone-1"])
    // A live session offers none.
    box.value = snapAt([sess('gone-1', 'running', 1, 'web-app', 'old job')])
    await ui.redraw()
    expect(await ui.find({ key: 'resume' })).toBeUndefined()
    await ui.unmount()
  })

  test(`@F49 ${TAG} a failed copy says how to retry`, async ($, on) => {
    const ended = sess('gone-2', 'ended', 90, 'web-app', 'old job', { endedAt: at(90), cwd: '/work/web app' })
    const { ui, w } = await sessionPage($, on, [sess(SELF, 'running', 1, 'web-app', 'me'), ended], 'gone-2')
    w.failCopy = 'no-clipboard'
    await ui.press({ key: 'resume' })
    expect(w.copies[0]!.text).toBe("cd '/work/web app' && claude --resume gone-2")
    expect(w.toasts).toEqual(['Copy failed: no-clipboard. Press Copy resume command again.'])
    await ui.unmount()
  })

  test(`@F112 ${TAG} resume toast`, async ($, on) => {
    const ended = sess('gone-3', 'ended', 90, 'web-app', 'old job', { endedAt: at(90) })
    const { ui, w } = await sessionPage($, on, [sess(SELF, 'running', 1, 'web-app', 'me'), ended], 'gone-3')
    await ui.press({ key: 'resume' })
    expect(w.toasts).toEqual(['Resume command copied'])
    await ui.unmount()
  })

  test(`@F111 ${TAG} an open page turns ended when the session leaves the list`, async ($, on) => {
    const { ui, box } = await sessionPage($, on, [full(), sess('other', 'running', 1, 'web-app', 'x')], 'other')
    expect(await texts(ui)).toContain('◐ running · 1m')
    expect(await ui.find({ key: 'resume' })).toBeUndefined()
    box.value = snapAt([full(), sess('other', 'ended', 1, 'web-app', 'x', { endedAt: at(1) })])
    await ui.redraw()
    expect(await texts(ui)).toContain('○ ended 1m ago')
    expect(await ui.find({ key: 'resume' })).toBeDefined()
    await ui.unmount()
  })

  test(`@F113 ${TAG} the breadcrumb`, async ($, on) => {
    const { ui } = await sessionPage($, on, [full()])
    expect(await texts(ui)).toContain('Home › web-app › fix login redirect')
    await ui.unmount()
  })

  test(`@F124 ${TAG} the Session page puts a word or count beside every glyph`, async ($, on) => {
    const { ui } = await sessionPage($, on, [full()])
    for (const t of await texts(ui)) {
      if (/[●◐✓○]/.test(t)) expect(t).toMatch(/[●◐✓○] (needs you|running|done|ended)/)
      if (t.includes('✗')) expect(t).toMatch(/✗ checks failing/)
    }
    await ui.unmount()
  })
})

// Repo page. web-app has four PRs (two failing), a main checkout and a worktree with a live session each.
const webTown = (): SessionRecord[] =>
  paneTown().map(r => (r.sessionId === 'web-1' ? { ...r, cwd: '/work/web-app/.worktrees/login' } : r))
const repoPage = async ($: Engine, on: On, sessions: SessionRecord[] = webTown(), columns = 115) => {
  const h = withSnap(on, sessions)
  const ui = await mount($, columns)
  await ui.press({ key: 'repo:/work/web-app' })
  await ui.redraw()
  return { ...h, ui }
}
const prBox = async (ui: Ui, n: number) => (await ui.find({ key: `pr:${n}` }))!
const prKeys = async (ui: Ui) => (await ui.findAll({ type: 'Box' })).map(b => String(b.props.key ?? '')).filter(k => k.startsWith('pr:'))

describe('the Repo page', () => {
  test(`@F50 ${TAG} Repo section order: Open PRs, Worktrees, Ended; opened from a repo heading`, async ($, on) => {
    const { ui } = await repoPage($, on)
    const all = await texts(ui)
    const order = ['Open PRs', 'Worktrees', 'Ended'].map(s => all.indexOf(s))
    expect(order.every(i => i >= 0)).toBe(true)
    expect(order).toEqual([...order].sort((a, b) => a - b))
    expect(all).toContain('web-app') // the title
    // The Repos line on Home opens it too.
    await ui.press({ key: 'home' })
    await ui.redraw()
    await ui.press({ key: 'repos:/work/web-app' })
    await ui.redraw()
    expect(await texts(ui)).toContain('Open PRs')
    await ui.unmount()
  })

  test(`@F51 ${TAG} PRs: failing first, then newest by creation time; a session button only where a session ran on the branch`, async ($, on) => {
    const { ui } = await repoPage($, on)
    expect(await prKeys(ui)).toEqual(['pr:44', 'pr:42', 'pr:43', 'pr:41']) // 44 and 42 fail (newest first), then 43 and 41
    const sessionButtons = (await buttons(ui, 'pr-session:')).map(b => [b.props.key, b.text])
    // web-1 ran on feat/login (PR 42) and web-2 on feat/dark (PR 43); nothing ran on the other two.
    expect(sessionButtons).toEqual([['pr-session:42', 'session: fix login redirect'], ['pr-session:43', 'session: dark mode']])
    await ui.unmount()
  })

  test(`@F114 ${TAG} PR row words, the number is a link that opens the PR`, async ($, on) => {
    const { ui } = await repoPage($, on)
    expect((await prBox(ui, 42)).text).toBe('#42 fix login redirect · ✗ checks failing · review requested · conflicts · session: fix login redirect')
    const link = (await ui.findAll({ type: 'Link' }))[0]!
    expect([link.text, typeof link.props.href]).toEqual(['#44', 'string'])
    expect((await ui.findAll({ type: 'Link' })).map(l => [l.text, l.props.href])).toContainEqual(['#42', 'https://example.test/pr/42'])
    await ui.unmount()
  })

  test(`@F115 ${TAG} PR states: checks, review and mergeable words`, async ($, on) => {
    const { ui } = await repoPage($, on)
    expect((await prBox(ui, 41)).text).toBe('#41 old cleanup · ✓ checks pass · approved · ↓ mergeable')
    expect((await prBox(ui, 43)).text).toBe('#43 dark mode · checks running · changes requested · mergeable unknown · session: dark mode')
    expect((await prBox(ui, 44)).text).toBe('#44 newest broken · ✗ checks failing · no review · ↓ mergeable')
    await ui.unmount()
  })

  test(`@F116 ${TAG} a PR row at 54 columns takes two lines; failing checks in the error colour, never dim`, async ($, on) => {
    const { ui } = await repoPage($, on, webTown(), 54)
    // A line is a Box of a Link (its label), Texts and a Button (its label).
    type Node = { type: string; props?: { label?: string }; children?: (Node | string)[] }
    const flat = (n: Node | string): string => (typeof n === 'string' ? n : n.type === 'Link' || n.type === 'Button' ? (n.props?.label ?? '') : (n.children ?? []).map(flat).join(''))
    const lines = async (n: number) => (await prBox(ui, n)).children!.map(c => flat(c as Node))
    const failing = await prBox(ui, 42)
    expect(failing.children!.length).toBe(2)
    expect(await lines(42)).toEqual(['#42 fix login redirect ✗ checks failing', 'review requested · conflicts · session: fix login redirect'])
    const checks = (await ui.find({ type: 'Text', text: '✗ checks failing' }))!
    expect(checks.props.color).toBe('error')
    expect(checks.props.dimColor).not.toBe(true)
    await ui.unmount()
  })

  test(`@F116 ${TAG} from 70 columns a PR row takes one line`, async ($, on) => {
    const { ui } = await repoPage($, on, webTown(), 70)
    expect((await prBox(ui, 41)).children!.length).toBeGreaterThan(2) // one Box of Link, title and words, not two lines
    expect((await prBox(ui, 41)).children!.every(c => (c as { type: string }).type !== 'Box')).toBe(true)
    await ui.unmount()
  })

  test(`@F117 ${TAG} Worktrees: the main checkout first, then by most recent session, with the live sessions as rows`, async ($, on) => {
    const { ui } = await repoPage($, on)
    const all = await texts(ui)
    expect(all.indexOf('main checkout · main')).toBeGreaterThan(all.indexOf('Worktrees'))
    expect(all.indexOf('main checkout · main')).toBeLessThan(all.indexOf('.worktrees/login · feat/login'))
    const sessionKeys = await keys(ui, 'session:')
    // web-2 (done) is in the main checkout; web-1 (waiting) in the login worktree.
    expect(sessionKeys.indexOf('session:web-2')).toBeLessThan(sessionKeys.indexOf('session:web-1'))
    expect(await rowText(ui, 'session:web-1')).toContain('6m · asks permission')
    await ui.unmount()
  })

  test(`@F117 ${TAG} worktrees after the main checkout go by most recent session`, async ($, on) => {
    const extra = { at: at(1), ghOk: true, prs: [], worktrees: [{ path: '/work/web-app', branch: 'main' }, { path: '/work/web-app/.worktrees/old', branch: 'feat/old' }, { path: '/work/web-app/.worktrees/login', branch: 'feat/login' }] }
    const sessions = [sess('w1', 'running', 30, 'web-app', 'older', { cwd: '/work/web-app/.worktrees/old', scan: extra }), sess('w2', 'running', 3, 'web-app', 'newer', { cwd: '/work/web-app/.worktrees/login' }), sess(SELF, 'running', 1, 'web-app', 'me', { cwd: '/work/web-app' })]
    const { ui } = await repoPage($, on, sessions)
    const all = await texts(ui)
    expect([all.indexOf('main checkout · main'), all.indexOf('.worktrees/login · feat/login'), all.indexOf('.worktrees/old · feat/old')].every(i => i >= 0)).toBe(true)
    expect(all.indexOf('main checkout · main')).toBeLessThan(all.indexOf('.worktrees/login · feat/login'))
    expect(all.indexOf('.worktrees/login · feat/login')).toBeLessThan(all.indexOf('.worktrees/old · feat/old'))
    await ui.unmount()
  })

  test(`@F118 ${TAG} no worktrees to list`, async ($, on) => {
    const noTrees = webTown().map(r => (r.scan ? { ...r, scan: { ...r.scan, worktrees: [] } } : r))
    const { ui } = await repoPage($, on, noTrees)
    expect(await texts(ui)).toContain('No worktrees found.')
    await ui.unmount()
  })

  test(`@F119 ${TAG} gh works and no PR is open`, async ($, on) => {
    const none = webTown().map(r => (r.scan ? { ...r, scan: { ...r.scan, prs: [] } } : r))
    const { ui } = await repoPage($, on, none)
    expect(await texts(ui)).toContain('No open PRs.')
    expect(await prKeys(ui)).toEqual([])
    await ui.unmount()
  })

  test(`@F54 ${TAG} Repo, no gh: the PRs not shown line`, async ($, on) => {
    const noGh = webTown().map(r => (r.scan ? { ...r, scan: { ...r.scan, ghOk: false } } : r))
    const { ui } = await repoPage($, on, noGh)
    const all = await texts(ui)
    expect(all).toContain(PRS_NOT_SHOWN)
    expect(all.indexOf(PRS_NOT_SHOWN)).toBeGreaterThan(all.indexOf('Open PRs'))
    expect(all).not.toContain('No open PRs.')
    await ui.unmount()
  })

  test(`@F69 ${TAG} stored PRs say how old they are while no session of the tracker runs in the repo`, async ($, on) => {
    const stored = webTown().map(r => (r.repo?.name === 'web-app' ? { ...r, source: 'transcript' as const, scan: r.scan ? { ...r.scan, at: at(120) } : null } : r))
    withSnap(on, [...stored, sess('x', 'running', 1, 'api', 'elsewhere')])
    await run($, 'repo web-app')
    const ui = await mount($)
    expect(await texts(ui)).toContain('PRs as of 2h ago: no live session in this repo')
    await ui.unmount()
  })

  test(`@F69 ${TAG} no stored-state line while a session of the tracker runs there`, async ($, on) => {
    const live = await repoPage($, on)
    expect((await texts(live.ui)).some(t => t.startsWith('PRs as of'))).toBe(false)
    await live.ui.unmount()
  })

  test(`@F120 ${TAG} Ended rows from the last 7 days, newest first, hidden when none`, async ($, on) => {
    const week = [...webTown(), sess('web-5', 'ended', 2 * 24 * 60, 'web-app', 'rename skills', { branch: 'main', usage: use(10000, 2000), endedAt: at(2 * 24 * 60) })]
    const { ui, box } = await repoPage($, on, week)
    expect(await rowText(ui, 'session:web-5')).toBe('○ rename skills   main · ended 2d ago · 12k tokens')
    const ended = (await keys(ui, 'session:')).filter(k => ['session:web-3', 'session:web-4', 'session:web-5'].includes(k))
    expect(ended).toEqual(['session:web-3', 'session:web-4', 'session:web-5']) // 2h, 13h, 2d
    box.value = snapAt(webTown().filter(r => r.state !== 'ended'))
    await ui.redraw()
    expect(await texts(ui)).not.toContain('Ended')
    await ui.unmount()
  })

  test(`@F113 ${TAG} the Repo breadcrumb`, async ($, on) => {
    const { ui } = await repoPage($, on)
    expect(await texts(ui)).toContain('Home › web-app')
    await ui.unmount()
  })

  test(`@F88 ${TAG} Back, Home and Close on the Repo page, and Back returns to the same row`, async ($, on) => {
    const { ui } = await repoPage($, on)
    const nav = await Promise.all(['back', 'home', 'close'].map(async k => (await ui.find({ key: k }))!.props))
    expect(nav.map(p => [p.label, p.hotkey, p.plain])).toEqual([['Back', undefined, true], ['Home', undefined, true], ['Close', undefined, true]])
    await ui.press({ key: 'session:web-1' })
    await ui.redraw()
    await ui.press({ key: 'repo:/work/web-app' }) // the header button of the Session page
    await ui.redraw()
    expect(await texts(ui)).toContain('Open PRs')
    await ui.press({ key: 'back' })
    await ui.redraw()
    expect(await texts(ui)).toContain('Home › web-app › fix login redirect')
    await ui.unmount()
  })

  test(`@F124 ${TAG} the Repo page puts a word beside every glyph`, async ($, on) => {
    const { ui } = await repoPage($, on)
    for (const t of await texts(ui)) {
      if (t.includes('✗')) expect(t).toMatch(/✗ checks failing/)
      if (t.includes('✓') && !/^[●◐✓○]/.test(t)) expect(t).toMatch(/✓ checks pass/)
      if (t.includes('↓')) expect(t).toMatch(/↓ mergeable/)
    }
    await ui.unmount()
  })
})

describe('/tracker page words', () => {
  const opened = async ($: Engine, on: On, args: string, sessions = paneTown()) => {
    const h = withSnap(on, sessions)
    await run($, args)
    const ui = await mount($, 115, true)
    return { ...h, ui }
  }

  test(`@F122 ${TAG} /tracker session matches the title by substring, case-insensitive, else the id by prefix`, async ($, on) => {
    const { ui, w } = await opened($, on, 'session LOGIN')
    expect(w.opens.length).toBe(1)
    expect(await texts(ui)).toContain('fix login redirect')
    expect(await ui.find({ key: 'back' })).toBeDefined() // a Session page
    await ui.unmount()
  })

  const two = [sess('abcd-1111', 'running', 30, 'web-app', 'alpha job'), sess('abcd-2222', 'running', 3, 'web-app', 'beta job'), sess(SELF, 'running', 1, 'api', 'me')]

  test(`@F122 ${TAG} the id by prefix`, async ($, on) => {
    const { ui } = await opened($, on, 'session abcd-1', two)
    expect(await texts(ui)).toContain('alpha job')
    await ui.unmount()
  })

  test(`@F122 ${TAG} several matches open the most recent`, async ($, on) => {
    const { ui } = await opened($, on, 'session abcd', two)
    expect(await texts(ui)).toContain('beta job') // 3m ago beats 30m ago
    await ui.unmount()
  })

  test(`@F122 ${TAG} a title match wins over an id match`, async ($, on) => {
    const { ui } = await opened($, on, 'session job', [...two, sess('job-9999', 'running', 1, 'web-app', 'gamma', { lastActivityAt: at(0) })])
    expect(await texts(ui)).toContain('beta job')
    await ui.unmount()
  })

  test(`@F122 ${TAG} /tracker repo uses the same rule on repo names`, async ($, on) => {
    const { ui } = await opened($, on, 'repo WEB')
    expect(await texts(ui)).toContain('Home › web-app')
    await ui.unmount()
  })

  test(`@F122 ${TAG} /tracker repo, several matches open the most recent`, async ($, on) => {
    const { ui } = await opened($, on, 'repo e', [sess('a', 'running', 30, 'web-app', 'x'), sess('b', 'running', 3, 'api-gateway', 'y'), sess(SELF, 'running', 1, 'docs', 'me')])
    expect(await texts(ui)).toContain('Home › api-gateway')
    await ui.unmount()
  })

  test(`@F59 ${TAG} session not found line`, async ($, on) => {
    const { ui } = await opened($, on, 'session nothing-like-it')
    expect(await texts(ui)).toContain('No session matches "nothing-like-it". Pick one on Home.')
    expect((await ui.find({ key: 'home' }))?.props.hotkey).toBeUndefined()
    expect((await ui.find({ key: 'close' }))?.props.hotkey).toBeUndefined()
    await ui.press({ key: 'home' })
    await ui.redraw()
    expect(await headings(ui)).toContain('Needs you')
    await ui.unmount()
  })

  test(`@F121 ${TAG} repo not found line`, async ($, on) => {
    const { ui } = await opened($, on, 'repo Nope')
    expect(await texts(ui)).toContain('No repo named "Nope" has had a session. Pick one on Home.')
    expect(await ui.find({ key: 'home' })).toBeDefined()
    await ui.unmount()
  })

  test(`${TAG} /tracker with no word opens Home; an unknown word shows the one-line hint; the band's words pass`, async ($, on) => {
    const h = withSnap(on, paneTown())
    expect((await run($, '')) as unknown).toMatchObject({ text: 'Tracker pane opened.' })
    expect(h.w.opens.length).toBe(1)
    expect((await run($, 'frobnicate')) as unknown).toMatchObject({ text: 'Try /tracker, details, compact, copy, repo, session, band on, band off.' })
    expect(h.w.opens.length).toBe(1) // nothing opened
    // The band's words are not the pane's: they are answered by the band, and open nothing.
    await run($, 'details')
    await run($, 'band off')
    expect(h.w.opens.length).toBe(1)
    expect(h.w.writes.length).toBeGreaterThan(0)
  })
})
