import { describe, expect, test } from 'claude-code/testing'

import { IDLE_MS, isNews, unseenCount, taskLists, applyVerdicts, firstWords, mergedKey, noMarks, noteItems, notesPrompt, parseChange, parseNotes, taskCounts, taskItems, taskKey, taskStatus } from '../hooks/tracker/core'
import type { TaskMarks } from '../hooks/tracker/core'
import type { Ask } from '../hooks/tracker/types'
import { MILESTONE } from './fixtures/band'
import { MILESTONE_MD } from './fixtures/milestone'
import { NOON, at, sess, snapAt } from './fixtures/pane'
import { ask, taskTown } from './fixtures/tasks'
import { CLEANUP, DEAD, dead, focused, keys, open, page, press, settings } from './fixtures/ui'
import { settle } from './fixtures/world'

const TAG = '@2026-11-13-agent-tracker'
const marks = (m: Partial<TaskMarks>): TaskMarks => ({ ...noMarks, ...m })
const web = { repo: { path: '/work/web-app', name: 'web-app' } }
// A session of web-app on feat/x, quiet for 5 minutes, with the given asks.
const one = (asks: Ask[], extra: Parameters<typeof sess>[5] = {}) => sess('t-1', 'done', 5, 'web-app', 'tokens', { ...web, branch: 'feat/x', asks, ...extra })
const statusOf = (r: ReturnType<typeof one>, m: TaskMarks = noMarks, hasPr = false) => taskStatus(r, r.asks[r.asks.length - 1]!, NOON, m, hasPr)

describe('the status of a task ask', () => {
  test(`${TAG} done: a verdict of done, a merged change on the branch, or closed by the owner; each is off the list`, () => {
    expect(statusOf(one([ask(1, 'x', 60, { verdict: 'done' })]))).toBeNull()
    expect(statusOf(one([ask(1, 'x', 60)]), marks({ merged: new Set([mergedKey('/work/web-app', 'feat/x')]) }))).toBeNull()
    expect(statusOf(one([ask(1, 'x', 60)]), marks({ merged: new Set([mergedKey('/work/web-app', 'feat/other')]) }))).not.toBeNull() // another branch
    expect(statusOf(one([ask(1, 'x', 60)]), marks({ closed: new Set([taskKey('t-1', 1)]) }))).toBeNull()
    // partly, not started and replaced are not done
    for (const verdict of ['partly', 'not-started'] as const) expect(statusOf(one([ask(1, 'x', 60, { verdict })]))).not.toBeNull()
  })

  test(`${TAG} needs you: the session waits and this is its last ask; an earlier ask is not it`, () => {
    const r = one([ask(1, 'first', 30), ask(2, 'second', 10)], { state: 'needs-you', engine: { since: at(4) } })
    expect(taskStatus(r, r.asks[1]!, NOON, noMarks, false)).toMatchObject({ status: 'needs-you', detail: 'waiting for your answer for 4m' })
    expect(taskStatus(r, r.asks[0]!, NOON, noMarks, false)?.status).toBe('in-progress')
    expect(statusOf({ ...r, engine: { since: null } })?.detail).toBe('waiting for your answer') // the wait is unknown
  })

  test(`${TAG} forgotten: the session ended, or was quiet for more than 30 minutes; the reason says which, and "no milestone, no PR"`, () => {
    const ended = one([ask(1, 'x', 180, { verdict: 'partly' })], { state: 'ended', endedAt: at(120), milestone: MILESTONE })
    expect(statusOf(ended)).toMatchObject({ status: 'forgotten', detail: 'session ended 2h ago, not done' })
    expect(statusOf({ ...ended, endedAt: null, lastActivityAt: at(150) })?.detail).toBe('session ended 2h 30m ago, not done') // no end time: the last activity
    expect(statusOf({ ...ended, milestone: null })?.detail).toBe('session ended 2h ago, not done, no milestone, no PR')
    expect(statusOf({ ...ended, milestone: null }, noMarks, true)?.detail).toBe('session ended 2h ago, not done') // a PR is on the branch
    const idle = one([ask(1, 'x', 60, { verdict: 'not-started' })], { lastActivityAt: at(45), milestone: null })
    expect(statusOf(idle)).toMatchObject({ status: 'forgotten', detail: 'idle 45m, not done, no milestone, no PR' })
    // The edge: 30 minutes exactly is not more than 30 minutes.
    expect(statusOf(one([ask(1, 'x', 60, { verdict: 'partly' })], { lastActivityAt: NOON - IDLE_MS }))?.status).toBe('in-progress')
    expect(statusOf(one([ask(1, 'x', 60, { verdict: 'partly' })], { lastActivityAt: NOON - IDLE_MS - 1 }))).toMatchObject({ status: 'forgotten', detail: 'idle 30m, not done, no milestone, no PR' })
    // No verdict is not "not done": an ended or idle session with none is unchecked; a live one is in progress.
    expect(statusOf({ ...ended, asks: [ask(1, 'x', 180)] })?.status).toBe('unchecked')
    expect(statusOf(one([ask(1, 'x', 60)], { lastActivityAt: at(45) }))?.status).toBe('unchecked')
    expect(statusOf(one([ask(1, 'x', 60)], { lastActivityAt: at(5) }))?.status).toBe('in-progress')
    // A session at work is not idle, however old its last prompt.
    expect(statusOf(one([ask(1, 'x', 600)], { state: 'running', lastActivityAt: at(240) }))?.status).toBe('in-progress')
  })

  test(`${TAG} superseded: replaced and not kept; kept goes on as in progress; an ended session keeps it superseded; kept on an ended one is forgotten`, () => {
    const asks = [ask(1, 'Add retry on 401 responses in the API client.', 30, { verdict: 'replaced', replacedBy: 2 }), ask(2, 'Fix the login redirect so users land back where they came from.', 20)]
    const r = one(asks)
    expect(taskStatus(r, asks[0]!, NOON, noMarks, false)).toMatchObject({ status: 'superseded', later: { at: at(20), text: 'Fix the login redirect so…' } })
    expect(taskStatus(r, asks[0]!, NOON, marks({ kept: new Set([taskKey('t-1', 1)]) }), false)?.status).toBe('in-progress')
    expect(taskStatus({ ...r, state: 'ended', endedAt: at(10) }, asks[0]!, NOON, noMarks, false)?.status).toBe('superseded') // replaced, so not forgotten
    expect(taskStatus({ ...r, state: 'ended', endedAt: at(10) }, asks[0]!, NOON, marks({ kept: new Set([taskKey('t-1', 1)]) }), false)?.status).toBe('forgotten') // the owner kept it, and the session is over
    expect(taskStatus(r, { ...asks[0]!, replacedBy: 9 }, NOON, noMarks, false)).toMatchObject({ status: 'superseded', later: null }) // the later ask is gone
    expect(firstWords('  one two   three ')).toBe('one two three')
  })

  test(`${TAG} in progress: everything else, with the milestone when there is one`, () => {
    expect(statusOf(one([ask(1, 'x', 30)], { milestone: MILESTONE }))).toMatchObject({ status: 'in-progress', progress: { slug: 'agent-tracker-1', done: 2, total: 4 } })
    expect(statusOf(one([ask(1, 'x', 30)]))).toMatchObject({ status: 'in-progress', progress: null })
  })
})

describe('the list', () => {
  test(`${TAG} order: needs you, forgotten, superseded, in progress; newest first inside each; tasks only`, () => {
    const items = taskItems(snapAt(taskTown()), NOON)
    expect(items.map(i => [i.status, i.key])).toEqual([
      ['needs-you', 'need-1:1'],
      ['forgotten', 'lost-2:1'], // asked 50 minutes ago, after the 180
      ['forgotten', 'lost-1:1'],
      ['superseded', 'sup-1:1'],
      ['in-progress', 'sup-1:2'], // 8 minutes ago
      ['in-progress', 'prog-1:1'], // 70
      ['in-progress', 'prog-2:1'], // 100
    ])
    expect(items[0]).toMatchObject({ repo: 'web-app', text: 'Fix the login redirect so users land back on the page they came from.', at: at(20) })
    // Unchecked, not listed: the ended session with no verdict. The headless run is nowhere.
    const { unchecked } = taskLists(snapAt(taskTown()), NOON)
    expect(unchecked.map(u => u.key)).toEqual(['chk-1:1'])
    expect(unchecked[0]).toMatchObject({ repo: 'api', text: 'Rename the config keys.' })
    expect(items.some(i => i.sessionId === 'head-1')).toBe(false)
    // Not on it: the question, the ask nobody classified, the task judged done.
    expect(items.some(i => i.sessionId === 'else-1')).toBe(false)
    expect(taskCounts(items)).toEqual({ notDone: 7, needsYou: 1, alarm: true })
    expect(taskCounts(items.filter(i => i.status === 'in-progress'))).toEqual({ notDone: 3, needsYou: 0, alarm: false })
  })

  test(`${TAG} only the last week's asks count, and the owner's marks and a merged change take tasks off`, () => {
    const old = sess('old-1', 'ended', 10 * 24 * 60, 'web-app', 'old', { ...web, endedAt: NOON - 8 * 24 * 3600_000, asks: [ask(1, 'ancient', 8 * 24 * 60)] })
    expect(taskItems(snapAt([old]), NOON)).toEqual([])
    const town = taskTown()
    const closed = taskItems(snapAt(town), NOON, marks({ closed: new Set(['sup-1:1']), merged: new Set([mergedKey('/work/web-app', 'milestone/agent-tracker-1')]) }))
    expect(closed.map(i => i.key)).not.toContain('sup-1:1')
    expect(closed.map(i => i.key)).not.toContain('prog-1:1')
    // A PR on the branch (the repo's scan) is why a forgotten task does not say "no PR".
    const lost = sess('l-1', 'ended', 120, 'web-app', 'x', { ...web, branch: 'feat/pr', endedAt: at(120), asks: [ask(1, 'task', 200, { verdict: 'partly' })], scan: { at: at(1), ghOk: true, worktrees: [], prs: [{ number: 5, title: 't', url: '', branch: 'feat/pr', createdAt: '', checks: 'pass', review: 'none', mergeable: 'mergeable' }] } })
    expect(taskItems(snapAt([lost]), NOON)[0]!.detail).toBe('session ended 2h ago, not done')
  })
})

describe('the verdicts of the notes call', () => {
  const asked = { open: new Set([1, 2]), all: new Set([1, 2, 3]) }
  const reply = (verdicts: unknown) => JSON.stringify({ know: [], decided: [], verdicts })

  test(`${TAG} a verdict must name a task that was asked about; a replaced one must name a later ask of the session`, () => {
    const out = parseNotes(reply([{ n: 1, verdict: 'replaced', by: 3 }, { n: 2, verdict: 'done' }, { n: 7, verdict: 'done' }, { n: 2, verdict: 'finished' }]), asked)
    expect(out!.verdicts).toEqual([{ n: 1, verdict: 'replaced', by: 3 }, { n: 2, verdict: 'done' }])
    for (const bad of [{ n: 2, verdict: 'replaced' }, { n: 2, verdict: 'replaced', by: 1 }, { n: 2, verdict: 'replaced', by: 9 }, { n: 'x', verdict: 'done' }, null]) expect(parseNotes(reply([bad]), asked)!.verdicts).toBeUndefined()
    expect(parseNotes(reply('nope'), asked)).toEqual({ know: [], decided: [] }) // not a list: the notes stay
    expect(parseNotes(reply([{ n: 1, verdict: 'done' }]))).toEqual({ know: [], decided: [] }) // nobody asked: no verdict taken
    expect(parseNotes('{"verdicts":[{"n":1,"verdict":"partly"}]}', asked)).toEqual({ know: [], decided: [], verdicts: [{ n: 1, verdict: 'partly' }] }) // a reply of verdicts alone
    expect(parseNotes('{"other":[]}', asked)).toBeNull()
  })

  test(`${TAG} applyVerdicts sets verdict and replacedBy on task asks only, and drops an old replacedBy`, () => {
    const asks: Ask[] = [ask(1, 'a', 30, { verdict: 'replaced', replacedBy: 2 }), ask(2, 'b', 20), ask(3, 'why?', 10, { kind: 'question' })]
    const out = applyVerdicts(asks, [{ n: 1, verdict: 'partly' }, { n: 2, verdict: 'replaced', by: 3 }, { n: 3, verdict: 'done' }])
    expect(out[0]).toEqual({ ...asks[0], verdict: 'partly', replacedBy: undefined })
    expect(Object.keys(out[0]!)).not.toContain('replacedBy')
    expect(out[1]).toMatchObject({ verdict: 'replaced', replacedBy: 3 })
    expect(out[2]).toBe(asks[2]) // a question gets no verdict
  })

  test(`${TAG} the prompt lists the open tasks only when there are some`, () => {
    expect(notesPrompt('msg')).not.toContain('verdicts')
    const p = notesPrompt('msg', [{ n: 4, text: 'Fix  the\nlogin' }])
    expect(p).toContain('4: Fix the login')
    expect(p).toContain('"verdicts"')
    expect(p.endsWith('Message:\nmsg')).toBe(true)
  })
})

describe('decided without you: the change folders', () => {
  test(`${TAG} a change folder's question or revision is never news, whatever its age; a turn's note is news until marked`, () => {
    const day = 24 * 3600_000
    const change = parseChange({
      dir: '2026-11-13-demo',
      root: '/work/web-app',
      milestone: MILESTONE_MD,
      done: null,
      validation: null,
      questions: '- **Q1 (F4): fresh question?** x. **Default taken:** a\n- **Q2 (F5): old question?** x. **Default taken:** b\n',
      questionsAt: NOON - 2 * day,
      plan: '## Revisions\n\n- **2026-11-14, F9:** fresh revision.\n- **2026-11-10, F8:** old revision.\n',
      findings: null,
      decisions: null,
      has: { intent: false, ux: false, facts: false, plan: true, locked: false },
    })!
    const mine = sess('n-1', 'running', 1, 'web-app', 'x', { ...web, notes: [{ id: 'n1', kind: 'decided', text: 'an old note', at: NOON - 3 * day, seen: false }] })
    const items = noteItems(snapAt([mine]), new Map([['/work/web-app', [{ ...change, slug: 'demo-1' }]]]), new Set(), NOON)
    const by = (needle: string) => items.find(i => i.text.includes(needle))!
    expect(isNews(by('fresh revision'))).toBe(false)
    expect(isNews(by('old revision'))).toBe(false)
    expect(isNews(by('Q2'))).toBe(false)
    expect(isNews(by('an old note'))).toBe(true)
    expect(unseenCount(items, 'decided')).toBe(1) // the band's count: the note alone
  })
})

// Clear closes the open tasks of the session with the owner's closed marks, Reopen tasks takes them away, and Home follows.
describe('Clear closes tasks and Reopen tasks opens them again', () => {
  const clear = async (ui: Parameters<typeof press>[0]) => {
    await press(ui, 'clear')
    await press(ui, 'confirm-clear')
    await settle()
    await ui.redraw()
  }

  test(`@F29 ${CLEANUP} Clear marks the session's open tasks closed`, async ($, on) => {
    const { ui, w } = await open($, on)
    const before = await keys(ui) // the page of dead-1, opened from its first task row on Home
    expect(before).toContain('clear')
    await clear(ui)
    expect([...settings(w)!.closed].sort()).toEqual([`${DEAD}:1`, `${DEAD}:2`])
    expect(await page(ui)).toContain('✓ 2 tasks closed.')
    expect(settings(w)!.kept).toEqual([]) // only closed marks, only this session's tasks
    await ui.unmount()
  })

  test(`@F29 ${CLEANUP} one task reads "1 task"`, async ($, on) => {
    const { ui, w } = await open($, on, dead({ asks: dead().asks.slice(0, 1) }))
    await clear(ui)
    expect(settings(w)!.closed).toEqual([`${DEAD}:1`])
    expect(await page(ui)).toContain('✓ 1 task closed.')
    await ui.unmount()
  })

  test(`@F31 ${CLEANUP} Reopen tasks removes the closed marks`, async ($, on) => {
    const { ui, w } = await open($, on)
    w.put('/u/.claude/agent-tracker/settings.json', { v: 1, view: 'compact', bandHidden: false, seen: [], kept: [], closed: ['other-1:1'] }) // a mark of the owner's own
    await clear(ui)
    expect(settings(w)!.closed).toEqual(['other-1:1', `${DEAD}:2`, `${DEAD}:1`])
    expect(await keys(ui)).toContain('reopen')
    expect(await focused(ui)).not.toContain('reopen') // never the first press after a Clear
    await press(ui, 'reopen')
    expect(settings(w)!.closed).toEqual(['other-1:1']) // the owner's own mark stays
    const all = await page(ui)
    expect(all).toContain('✓ 2 tasks reopened.')
    expect(await keys(ui)).not.toContain('reopen') // the button is for one press
    expect(await keys(ui)).toContain('clear') // work is left again
    expect(all).not.toContain('✓ 2 tasks closed.')
    await ui.unmount()
  })

  test(`@F31 ${CLEANUP} Reopen tasks does not survive leaving the page`, async ($, on) => {
    const { ui } = await open($, on)
    await clear(ui)
    await press(ui, 'crumb:0')
    await $.command.run({ command: 'tracker', args: 'session old login', origin: { kind: 'composer' }, presentation: {} as never })
    await ui.redraw()
    expect(await keys(ui)).not.toContain('reopen')
    await ui.unmount()
  })

  test(`@F32 ${CLEANUP} closed tasks leave Home; tasks over 7 days never list`, () => {
    const r = sess('old-1', 'ended', 120, 'web-app', 'old', { ...web, endedAt: at(120), asks: [ask(1, 'Fix it', 180, { verdict: 'not-started' }), ask(2, 'Fix more', 9 * 24 * 60, { verdict: 'not-started' })] })
    expect(taskItems(snapAt([r]), NOON).map(t => t.key)).toEqual(['old-1:1']) // the ask of 9 days ago never lists
    expect(taskItems(snapAt([r]), NOON, marks({ closed: new Set([taskKey('old-1', 1)]) }))).toEqual([]) // closed: off Home
    // An ended session older than a week still has its page (it stays listed), and its old task still does not list.
    const old = sess('old-2', 'ended', 13 * 24 * 60, 'web-app', 'older', { ...web, endedAt: at(13 * 24 * 60), asks: [ask(1, 'Old ask', 13 * 24 * 60 + 5, { verdict: 'partly' })] })
    expect(taskItems(snapAt([old]), NOON)).toEqual([])
  })
})
