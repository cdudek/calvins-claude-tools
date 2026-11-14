import { describe, expect, test } from 'claude-code/testing'
import type { On } from 'claude-code'
import type { Engine } from 'claude-code/testing'

import {
  BUTTONS_COMPACT,
  BUTTONS_DETAILS,
  COPIED,
  LOADING,
  PRS_NOT_SHOWN,
  bandData,
  homeModel,
  columnsSvg,
  compactLayout,
  detailsLayout,
  duration,
  mergeSessions,
  stateMarkdown,
} from '../hooks/tracker/core'
import type { CompactLayout, Details } from '../hooks/tracker/core'
import type { SessionRecord, Settings, Snapshot } from '../hooks/tracker/types'
import { AGENTS_JSON, ID, T0 } from './fixtures/agents'
import { MIN, MILESTONE, NOW, PRS, SELF, inState, pr, rec, scan, snap, town, townSelfWaiting } from './fixtures/band'
import { DIR, settle, start, world } from './fixtures/world'
import type { World } from './fixtures/world'

const TAG = '@2026-11-13-agent-tracker'

const text = (l: CompactLayout) => l.segments.map(s => s.chunks.map(c => c.text).join('')).join('')
const compact = (sessions: SessionRecord[], columns: number, extra: Partial<Snapshot> = {}) => compactLayout(bandData(snap(sessions, extra), SELF, NOW), columns)
const details = (sessions: SessionRecord[], columns: number, extra: Partial<Snapshot> = {}) => detailsLayout(bandData(snap(sessions, extra), SELF, NOW), columns)
const ids = (d: Details) => d.rows.map(r => r.map(c => c.key))
const col = (d: Details, key: string) => d.rows.flat().find(c => c.key === key)!
// What a Text on screen reads, every Text of a mounted band.
const texts = async (ui: { findAll: (q: object) => Promise<{ text?: string }[]> }) => (await ui.findAll({ type: 'Text' })).map(t => t.text ?? '')
const row = async (ui: { findAll: (q: object) => Promise<{ text?: string }[]> }) => (await texts(ui)).join('')

// Layout superseded 2026-11-14: the band follows the owner's mockup (agent-tracker-designs.html), work first, no done column,
// no quick keys, fixed 21-cell columns. The facts of change 2026-11-13-agent-tracker keep their tags; the owner's words win.
describe('compact band, the model', () => {
  const seg = (l: CompactLayout, id: string) => l.segments.find(s => s.id === id)!.chunks.map(c => c.text).join('')

  test(`@F24 ${TAG} segments in order: work, needs you, running, PRs, the waiting session, then the buttons; 95 cells at full width`, () => {
    const l = compact(town(), 200)
    expect(text(l)).toBe('agent-tracker-1 2/4 goal 14m · ● 2 need you  ◐3  PRs 1✗ 2↓  · fix login waits 6m')
    expect(l.segments.map(s => s.id)).toEqual(['work', 'needs', 'run', 'prs', 'tail'])
    expect(l.width).toBe(95) // 80 cells of text and 15 for Pane and Details, 2 apart and 2 after the text
    expect(BUTTONS_COMPACT).toBe(15)
  })

  test(`@F22 ${TAG} the compact row is the default; two spaces between the segments`, () => {
    expect(text(compact(town(), 200))).toContain('● 2 need you  ◐3  PRs 1✗ 2↓  · ')
  })

  test(`@F25 ${TAG} needs you in the warning colour, then the session waiting longest`, () => {
    const l = compact(town(), 200)
    expect(l.segments.find(s => s.id === 'needs')!.chunks).toEqual([{ text: ' · ' }, { text: '● 2 need you', tone: 'warning' }])
    expect(seg(l, 'tail')).toBe('  · fix login waits 6m') // the oldest wait
  })

  test(`@F76 ${TAG} one needs you`, () => {
    const one = town().map(r => (r.sessionId === 'docs-1' ? { ...r, state: 'done' as const } : r))
    expect(seg(compact(one, 200), 'needs')).toBe(' · ● 1 needs you')
  })

  test(`@F77 ${TAG} nothing waiting: all clear, dim, and no waiting session`, () => {
    const quiet = town().filter(r => r.state !== 'needs-you')
    const l = compact(quiet, 200)
    expect(l.segments.find(s => s.id === 'needs')!.chunks.at(-1)).toEqual({ text: '○ all clear', tone: 'dim' })
    expect(text(l)).toBe('agent-tracker-1 2/4 goal 14m · ○ all clear  ◐3  PRs 1✗ 2↓')
    // With no work segment and no gh the line goes quiet: "○ all clear  ◐3".
    expect(text(compact([inState('x', 'running', 1, 'api', 'job')].map(r => ({ ...r, sessionId: 'other' })), 200))).toBe('○ all clear  ◐1')
  })

  test(`${TAG} a wait with no known start reads "waiting", with a start "waits 6m"`, () => {
    // An unknown wait sorts after every known one, so it is the oldest only when it is the only one.
    const unknown = town().filter(r => r.sessionId !== 'docs-1').map(r => (r.sessionId === 'web-1' ? { ...r, engine: { since: null } } : r))
    expect(seg(compact(unknown, 200), 'tail')).toBe('  · fix login waiting')
    expect(seg(compact(town(), 200), 'tail')).toBe('  · fix login waits 6m')
    expect(col(details(unknown, 200), 'needs').line).toBe('fix login · waiting') // the reason stays, the age goes
  })

  test(`@F26 ${TAG} the waiting session is named, "this session" when it is this one`, () => {
    expect(seg(compact(townSelfWaiting(), 200), 'tail')).toBe('  · fix login waits 6m') // web-app waits longer than this session
    const mine = town().map(r => (r.sessionId === SELF ? { ...r, state: 'needs-you' as const, engine: { since: NOW - MIN } } : r)).filter(r => r.sessionId === SELF || r.state !== 'needs-you')
    expect(seg(compact(mine, 200), 'tail')).toBe('  · this session waits 1m')
    expect(seg(compact(mine, 200), 'needs')).toBe(' · ● 1 needs you')
  })

  test(`@F27 ${TAG} work segment with and without sdlc-run`, () => {
    expect(seg(compact(town(), 200), 'work')).toBe('agent-tracker-1 2/4 goal 14m')
    const plain = town().map(r => (r.sessionId === SELF ? inState(SELF, 'running', 20, 'web-app', 'fix login redirect') : r))
    expect(seg(compact(plain, 200), 'work')).toBe('web-app · fix login redirect')
    // A goal without sdlc-run still shows its age; a done session has none (F11).
    const goal = town().map(r => (r.sessionId === SELF ? inState(SELF, 'running', 20, 'web-app', 'fix login redirect', { runs: { goalSince: NOW - 14 * MIN, subagents: [], background: [] } }) : r))
    expect(seg(compact(goal, 200), 'work')).toBe('web-app · fix login redirect goal 14m')
    const finished = goal.map(r => (r.sessionId === SELF ? { ...r, state: 'done' as const } : r))
    expect(seg(compact(finished, 200), 'work')).toBe('web-app · fix login redirect')
    // No title yet: the folder name and "untitled session".
    expect(seg(compact([rec(SELF, { cwd: '/work/some-folder' })], 200), 'work')).toBe('some-folder · untitled session')
  })

  test(`@F28 ${TAG} drop order: the waiting session, PRs, the goal age, the work shortened; below 40 columns the work and the running count`, () => {
    const w100 = compact(town(), 100)
    expect(w100.width).toBe(95)
    expect(text(w100)).toBe('agent-tracker-1 2/4 goal 14m · ● 2 need you  ◐3  PRs 1✗ 2↓  · fix login waits 6m')
    // 1 the waiting session: 73.
    const w90 = compact(town(), 94)
    expect(text(w90)).toBe('agent-tracker-1 2/4 goal 14m · ● 2 need you  ◐3  PRs 1✗ 2↓')
    expect(w90.width).toBe(73)
    // 2 PRs: 62.
    const w70 = compact(town(), 72)
    expect(text(w70)).toBe('agent-tracker-1 2/4 goal 14m · ● 2 need you  ◐3')
    expect(w70.width).toBe(62)
    // 3 the goal age: 53.
    const w60 = compact(town(), 61)
    expect(text(w60)).toBe('agent-tracker-1 2/4 · ● 2 need you  ◐3')
    expect(w60.width).toBe(53)
    // 4 the work shortened: 37.
    const w50 = compact(town(), 50)
    expect(text(w50)).toBe('2/4 · ● 2 need you  ◐3')
    expect(w50.width).toBe(37)
    // Below 40 columns only the count and the buttons stay: 27.
    expect(text(compact(town(), 39))).toBe('● 2 need you')
    expect(compact(town(), 30).width).toBe(27)
    // The count and the buttons never drop, at any width.
    for (const columns of [10, 20, 39, 40, 50, 54, 75, 79, 115, 200]) expect(text(compact(town(), columns))).toContain('● 2 need you')
    // Without sdlc-run the work shortens to the repo.
    const plain = town().map(r => (r.sessionId === SELF ? inState(SELF, 'running', 20, 'web-app', 'fix login redirect') : r))
    expect(text(compact(plain, 42))).toBe('web-app · ● 2 need you  ◐3')
  })

  test(`@F31 ${TAG} running count is the running sessions of the list`, () => {
    // Known values: 3 busy or working, 2 waiting, 2 idle.
    expect(seg(compact(town(), 200), 'run')).toBe('  ◐3')
    // A history record never counts, and neither does an ended session.
    const history = [...town(), rec('old-1', { source: 'transcript', state: 'running' }), rec('old-2', { state: 'ended' })]
    expect(seg(compact(history, 200), 'run')).toBe('  ◐3')
  })

  test(`@F32 ${TAG} no alone note any more: a lone session reads all clear, and the details line counts the live sessions`, () => {
    const alone = [inState(SELF, 'running', 20, 'platform-tools-suite', 'build the band', { scan: scan(PRS), milestone: MILESTONE })]
    expect(text(compact(alone, 200))).toBe('agent-tracker-1 2/4 · ○ all clear  ◐1  PRs 1✗ 2↓')
    expect(details(alone, 200).header[1]).toBe('1 live')
    expect(details([...alone, inState('x', 'running', 1, 'api', 'job')], 200).header[1]).toBe('2 live')
  })

  test(`@F78 ${TAG} PR count over repos with a session in 7 days, each from its latest scan`, () => {
    const two = pr(11, { checks: 'failing' })
    const files = [
      inState(SELF, 'running', 5, 'platform-tools-suite', 'build', { scan: scan([pr(21)], true, NOW - 10 * MIN) }),
      // Two sessions of one repo: the later scan wins, not the sum.
      inState('api-1', 'running', 5, 'api', 'a', { scan: scan([pr(12), pr(13)], true, NOW - 60 * MIN) }),
      inState('api-2', 'running', 5, 'api', 'b', { scan: scan([two, pr(14), pr(15)], true, NOW - 2 * MIN) }),
      // A repo whose gh failed adds nothing.
      inState('web-1', 'running', 5, 'web-app', 'c', { scan: scan([pr(31)], false, NOW - 5 * MIN) }),
      // A session older than 7 days is not in the merge, so its repo is not counted.
      rec('old-1', { state: 'ended', endedAt: NOW - 8 * 24 * 60 * MIN, lastActivityAt: NOW - 8 * 24 * 60 * MIN, repo: { path: '/work/old', name: 'old' }, scan: scan([pr(41), pr(42)]) }),
    ]
    const merged = mergeSessions({ files, transcripts: [], agents: null, now: NOW, selfId: SELF })
    expect(merged.some(r => r.sessionId === 'old-1')).toBe(false)
    const d = bandData(snap(merged), SELF, NOW)
    expect(d.prs).toMatchObject({ open: 4, failing: 1 }) // platform-tools-suite 1 + api 3
    expect(seg(compactLayout(d, 200), 'prs')).toBe('  PRs 1✗')
    // Nothing failing or mergeable: the open count. Failing and mergeable: only those.
    const one = [inState(SELF, 'running', 1, 'a', 't', { scan: scan([pr(1)]) }), inState('x', 'running', 1, 'b', 'u')]
    expect(seg(compact(one, 200), 'prs')).toBe('  PRs 1')
    expect(text(compact(one, 200))).not.toContain('✗')
    expect(seg(compact(town(), 200), 'prs')).toBe('  PRs 1✗ 2↓')
    expect(seg(compact(town().map(r => (r.scan ? { ...r, scan: scan([pr(1, { mergeable: 'mergeable' })]) } : r)), 200), 'prs')).toBe('  PRs 1↓') // only the parts above 0
  })

  test(`@F54 ${TAG} a repo that is not on GitHub is not a gh failure: no PR segment, no gh line, on the band and in Home (R9)`, () => {
    const elsewhere = town().map(r => (r.scan ? { ...r, scan: { ...r.scan, ghOk: false, github: false as const, prs: [] } } : r))
    expect(bandData(snap(elsewhere), SELF, NOW)).toMatchObject({ prs: null, partial: false })
    expect(homeModel(snap(elsewhere), SELF, NOW, { midnight: 0, clock: () => '' }, null).partial).toBe(false)
    const missing = town().map(r => (r.scan ? { ...r, scan: { ...r.scan, ghOk: false } } : r)) // gh itself failed: the line stays
    expect(homeModel(snap(missing), SELF, NOW, { midnight: 0, clock: () => '' }, null).partial).toBe(true)
  })

  test(`@F54 ${TAG} no PR segment when gh gave nothing`, () => {
    const noGh = town().map(r => (r.scan ? { ...r, scan: { ...r.scan, ghOk: false } } : r))
    expect(compact(noGh, 200).segments.map(s => s.id)).toEqual(['work', 'needs', 'run', 'tail'])
    expect(bandData(snap(noGh), SELF, NOW).partial).toBe(true)
    // Never scanned: no segment either, and nothing is "partial".
    const never = town().map(r => ({ ...r, scan: null }))
    expect(compact(never, 200).segments.map(s => s.id)).toEqual(['work', 'needs', 'run', 'tail'])
    expect(bandData(snap(never), SELF, NOW).partial).toBe(false)
  })

  test(`@F52 ${TAG} stale after two failed reads, and "stale 2m" below 60 columns`, () => {
    const failed = { failedReads: 2, agentsOk: false, okAt: NOW - 2 * MIN }
    const l = compact(town(), 115, failed)
    const line = text(l)
    expect(line).toContain('session list unavailable · counts from 2m ago')
    expect(line).not.toContain('agent-tracker-1') // the text takes the work segment's place
    // The last counts are dimmed; the words are not.
    const tones = l.segments.filter(s => s.id !== 'stale').flatMap(s => s.chunks.map(c => c.tone))
    expect(tones.every(t => t === 'dim')).toBe(true)
    expect(l.segments.find(s => s.id === 'stale')!.chunks[0]!.tone).toBeUndefined()
    // It never drops: the other parts give way first.
    expect(text(compact(town(), 100, failed))).toContain('session list unavailable · counts from 2m ago')
    expect(text(compact(town(), 70, failed))).toContain('counts from 2m ago')
    // Below 60 it shortens.
    expect(text(compact(town(), 59, failed))).toContain('stale 2m')
    expect(text(compact(town(), 59, failed))).not.toContain('session list')
    expect(compact(town(), 59, failed).width).toBeLessThanOrEqual(59)
    // One failed read is not stale.
    expect(text(compact(town(), 200, { failedReads: 1, agentsOk: false, okAt: NOW - MIN }))).not.toContain('unavailable')
  })

  test(`@F53 ${TAG} loading line`, () => {
    const l = compactLayout(bandData(snap([], { at: 0, okAt: 0 }), SELF, NOW), 115)
    expect(text(l)).toBe(LOADING)
    expect(l.segments[0]!.chunks[0]!.tone).toBe('dim')
    expect(LOADING).toBe('Reading sessions…')
  })

  test(`@F125 ${TAG} duration format at 6m, 2h 10m and 3d`, () => {
    expect([duration(0), duration(59_000), duration(6 * MIN), duration(59 * MIN), duration(130 * MIN), duration(2 * 60 * MIN), duration(3 * 24 * 60 * MIN + 5 * MIN)]).toEqual(['<1m', '<1m', '6m', '59m', '2h 10m', '2h', '3d'])
    // The band writes durations in this format.
    const long = town().map(r => (r.sessionId === 'web-1' ? { ...r, engine: { since: NOW - 130 * MIN } } : r))
    expect(text(compact(long, 200))).toContain('fix login waits 2h 10m')
    const days = town().map(r => (r.sessionId === 'web-1' ? { ...r, engine: { since: NOW - 3 * 24 * 60 * MIN } } : r))
    expect(text(compact(days, 200))).toContain('fix login waits 3d')
  })
})

describe('details view, the model', () => {
  const NO_RUNS = { goalSince: null, subagents: [], background: [] }
  const branch = (b: string | null, extra: Partial<SessionRecord> = {}) => town().map(r => (r.sessionId === SELF ? { ...r, branch: b, runs: NO_RUNS, ...extra } : r))
  const plain = (extra: Partial<SessionRecord> = {}) =>
    town().map(r => (r.sessionId === SELF ? inState(SELF, 'running', 20, 'web-app', 'fix login redirect', { branch: 'feat/login', ...extra }) : r))

  test(`@F33 ${TAG} first line in both forms: repo, project, the feature being built and its progress; else repo, title, branch`, () => {
    // The branch is not shown in an sdlc-run repo.
    expect(details(branch('milestone/agent-tracker-1'), 200).header[0]).toBe('platform-tools-suite · agent-tracker-1 · band ◐ 2/4')
    expect(details(branch('feat/band'), 200).header[0]).toBe('platform-tools-suite · agent-tracker-1 · band ◐ 2/4')
    // Without sdlc-run: the title and the branch.
    expect(details(plain(), 200).header[0]).toBe('web-app · fix login redirect · feat/login')
    // Fallbacks: no title, detached HEAD.
    expect(details(plain({ title: null, branch: null }), 200).header[0]).toBe('web-app · untitled session · detached HEAD')
    // Every feature complete: the progress alone.
    const finished = branch(null, { milestone: { ...MILESTONE, features: MILESTONE.features.map(f => ({ ...f, state: 'done abc1234' })) } })
    expect(details(finished, 200).header[0]).toBe('platform-tools-suite · agent-tracker-1 · ◐ 4/4')
  })

  test(`@F34 ${TAG} second line: what runs, then the other sessions that need you and the live count; each part only when there is one`, () => {
    const runs = (goal: number | null, subagents: number, background: number) =>
      plain({ runs: { goalSince: goal === null ? null : NOW - goal * MIN, subagents: Array.from({ length: subagents }, (_, i) => ({ id: `s${i}`, name: 'x', status: 'running' })), background: Array.from({ length: background }, (_, i) => ({ id: `b${i}`, name: 'x', since: NOW })) } })
    expect(details(runs(14, 2, 1), 200).header).toEqual(['web-app · fix login redirect · feat/login', '/goal running 14m · 2 subagents · 1 background session · ● 2 need you elsewhere · 7 live'])
    // Each part only when above 0, and singular at 1.
    expect(details(runs(null, 1, 0), 200).header[1]).toBe('1 subagent · ● 2 need you elsewhere · 7 live')
    expect(details(runs(null, 0, 2), 200).header[1]).toBe('2 background sessions · ● 2 need you elsewhere · 7 live')
    expect(details(runs(null, 0, 0), 200).header[1]).toBe('● 2 need you elsewhere · 7 live')
    // This session waiting is not "elsewhere".
    const mine = plain().map(r => (r.sessionId === SELF ? { ...r, state: 'needs-you' as const } : r)).filter(r => r.state !== 'needs-you' || r.sessionId === SELF)
    expect(details(mine, 200).header[1]).toBe('5 live')
    // A narrow line gives up its last parts rather than wrap.
    expect(details(runs(14, 2, 1), 60).header[1]).toBe('/goal running 14m · 2 subagents · 1 background session')
  })

  test(`@F84 ${TAG} first line cut order`, () => {
    const sdlc = () => branch('feat/band')
    const full = 'platform-tools-suite · agent-tracker-1 · band ◐ 2/4'
    expect(details(sdlc(), 200).header[0]).toBe(full)
    // The full line and the 21 button cells are 72.
    expect(details(sdlc(), 72).header[0]).toBe(full)
    // Cut 1: the feature being built.
    expect(details(sdlc(), 71).header[0]).toBe('platform-tools-suite · agent-tracker-1 · ◐ 2/4')
    expect(details(sdlc(), 67).header[0]).toBe('platform-tools-suite · agent-tracker-1 · ◐ 2/4')
    // Last the milestone name.
    expect(details(sdlc(), 66).header[0]).toBe('platform-tools-suite · ◐ 2/4')
    expect(details(sdlc(), 40).header[0]).toBe('platform-tools-suite · ◐ 2/4')
    // Without sdlc-run: the branch, then the title.
    expect(details(plain(), 62).header[0]).toBe('web-app · fix login redirect · feat/login')
    expect(details(plain(), 61).header[0]).toBe('web-app · fix login redirect')
    expect(details(plain(), 49).header[0]).toBe('web-app · fix login redirect')
    expect(details(plain(), 48).header[0]).toBe('web-app')
    expect(BUTTONS_DETAILS).toBe(21) // Copy, Pane, Compact: 15 label cells, 2 before the buttons and 2 between
  })

  test(`@F35 ${TAG} three columns of 21 cells, empty column`, () => {
    const d = details(town(), 200)
    expect(ids(d)).toEqual([['needs', 'running', 'prs']])
    expect(d.rows[0]!.map(c => c.label)).toEqual(['needs you', 'running', 'PRs']) // no done column
    expect(d.rows[0]!.map(c => c.count)).toEqual(['2', '3', '4 open'])
    expect(d.colWidth).toBe(21) // never stretched to the terminal
    expect(details(town(), 115).colWidth).toBe(21)
    expect(details(town(), 63).colWidth).toBe(21)
    expect(details(town(), 60).colWidth).toBe(20) // three columns of the width that is left
    // A column with 0 shows the count and no line.
    const none = town().filter(r => r.state !== 'running')
    expect(col(details(none, 115), 'running')).toMatchObject({ count: '0', line: '' })
    // Every line fits its column with a 2-cell gutter: 19 of the 21.
    for (const c of d.rows.flat()) expect([...c.line].length).toBeLessThanOrEqual(d.colWidth - 2)
    // Below 80 the lines drop except needs you.
    const narrow = details(town(), 79)
    expect(narrow.rows[0]!.map(c => c.line !== '')).toEqual([true, false, false])
    expect(details(town(), 80).rows[0]!.every(c => c.line !== '')).toBe(true)
  })

  test(`@F81 ${TAG} needs you and running lines`, () => {
    const worded = town().map(r => (r.sessionId === 'web-1' ? { ...r, reason: 'permission' as const } : r.sessionId === 'api-1' ? { ...r, title: 'tracker', milestone: MILESTONE } : r))
    const d = details(worded, 115)
    expect(col(d, 'needs').line).toBe('fix login · perm 6m') // the oldest waiting, with its reason
    expect(col(d, 'running').line).toBe('tracker 2/4 · 50%') // the longest running, with its milestone progress
    // Without a milestone: its name and how long it has run.
    expect(col(details(town(), 115), 'running').line).toBe('migrate users 22m')
    // Needs you in the normal colour, running dim.
    expect(col(d, 'needs').tone).toBeUndefined()
    expect(col(d, 'running').tone).toBe('dim')
    // A long name gives way to "…", the wait stays.
    const long = town().map(r => (r.sessionId === 'web-1' ? { ...r, title: 'fix the login redirect loop' } : r))
    expect(col(details(long, 115), 'needs').line.endsWith('· waiting 6m')).toBe(true)
    expect(col(details(long, 115), 'needs').line).toContain('…')
    // "this session" when it is this one.
    const mine = town().map(r => (r.sessionId === SELF ? { ...r, state: 'needs-you' as const, reason: 'question' as const, engine: { since: NOW - 10 * MIN } } : r))
    expect(col(details(mine, 115), 'needs').line).toMatch(/^thi.*· question 10m$/)
  })

  test(`@F82 ${TAG} PRs count and line`, () => {
    const d = details(town(), 115)
    expect(col(d, 'prs')).toMatchObject({ count: '4 open', line: '1 ✗ · 2 mergeable' })
    const some = town().map(r => (r.scan ? { ...r, scan: scan([pr(1, { mergeable: 'mergeable' }), pr(2)]) } : r))
    expect(col(details(some, 115), 'prs')).toMatchObject({ count: '2 open', line: '1 mergeable' })
    const clean = town().map(r => (r.scan ? { ...r, scan: scan([pr(1)]) } : r))
    expect(col(details(clean, 115), 'prs')).toMatchObject({ count: '1 open', line: '' })
  })

  test(`@F83 ${TAG} columns fold below 60 bodyColumns`, () => {
    expect(ids(details(town(), 60))).toEqual([['needs', 'running', 'prs']])
    expect(ids(details(town(), 59))).toEqual([['needs', 'running'], ['prs']])
    expect(details(town(), 59).colWidth).toBe(21)
    expect(ids(details(town(), 30))).toEqual([['needs', 'running'], ['prs']])
    expect(details(town(), 30).colWidth).toBe(15)
  })

  test(`@F87 ${TAG} Loading, Partial and Stale line under the header`, () => {
    expect(details(town(), 115).note).toBeNull()
    expect(detailsLayout(bandData(snap([], { at: 0, okAt: 0 }), SELF, NOW), 115).note).toBe(LOADING)
    const failed = { failedReads: 2, agentsOk: false, okAt: NOW - 2 * MIN }
    expect(details(town(), 115, failed).note).toBe('session list unavailable · counts from 2m ago')
    expect(details(town(), 59, failed).note).toBe('stale 2m')
    // The last counts stay, dimmed.
    expect(details(town(), 115, failed).rows.flat().every(c => c.tone === 'dim')).toBe(true)
    // gh gave nothing: the line says why, and the PR column goes.
    const noGh = town().map(r => (r.scan ? { ...r, scan: { ...r.scan, ghOk: false } } : r))
    const partial = details(noGh, 115)
    expect(partial.note).toBe(PRS_NOT_SHOWN)
    expect(ids(partial)).toEqual([['needs', 'running']])
    // One line: stale wins over partial.
    expect(details(noGh, 115, failed).note).toBe('session list unavailable · counts from 2m ago')
  })

  test(`@F37 ${TAG} the SVG packs fixed columns from the left`, () => {
    const d = details(town(), 115)
    const svg = columnsSvg(d.rows.flat())
    expect(svg.startsWith('<svg')).toBe(true)
    expect(svg).toContain('width="480"') // three columns of 160, whatever the terminal
    for (const c of d.rows.flat()) expect(svg).toContain(c.label)
    // Escaped: a title can hold markup.
    const risky = town().map(r => (r.sessionId === 'web-1' ? { ...r, title: 'a<b>&c' } : r))
    expect(columnsSvg(details(risky, 115).rows.flat())).toContain('a&lt;b&gt;&amp;c')
  })
})

describe('every width the spec lists', () => {
  const WIDTHS = [40, 50, 54, 60, 70, 75, 80, 115] // the widths done.json lists
  const failed = { failedReads: 2, agentsOk: false, okAt: NOW - 2 * MIN }
  const cases: [string, SessionRecord[], Partial<Snapshot>][] = [
    ['town', town(), {}],
    ['this session waits', townSelfWaiting(), {}],
    ['quiet', town().filter(r => r.state !== 'needs-you'), {}],
    ['stale', town(), failed],
    ['alone', [inState(SELF, 'running', 20, 'platform-tools-suite', 'build', { milestone: MILESTONE, scan: scan(PRS) })], {}],
    ['loading', [], { at: 0, okAt: 0 }],
  ]

  test(`@F28 ${TAG} the compact row fits bodyColumns at each width, except below the count and the buttons`, () => {
    for (const columns of WIDTHS) {
      for (const [name, sessions, extra] of cases) {
        const l = compact(sessions, columns, extra)
        const floor = compact(sessions, 1, extra).width // the count and the buttons
        expect([name, columns, l.width <= Math.max(columns, floor)]).toEqual([name, columns, true])
        expect(l.width).toBe([...text(l)].length + BUTTONS_COMPACT)
      }
    }
  })

  test(`@F84 ${TAG} the details header and its buttons fit bodyColumns at each width`, () => {
    for (const columns of WIDTHS) {
      for (const [name, sessions, extra] of cases) {
        const first = details(sessions, columns, extra).header[0]!
        const narrowest = details(sessions, 1, extra).header[0] // the ladder's last form: nothing is left to cut
        expect([name, columns, [...first].length + BUTTONS_DETAILS <= columns || first === narrowest]).toEqual([name, columns, true])
        const second = details(sessions, columns, extra).header[1]
        if (second !== undefined) expect([name, columns, [...second].length <= columns]).toEqual([name, columns, true])
      }
    }
  })
})

describe('copy as Markdown', () => {
  test(`@F85 ${TAG} Markdown content and no paths`, () => {
    const md = stateMarkdown(bandData(snap(town()), SELF, NOW))
    // The four counts.
    expect(md).toContain('Needs you:** 2')
    expect(md).toContain('Running:** 3')
    expect(md).toContain('Done:** 2')
    expect(md).toContain('PRs:** 4 open')
    // One line per needs-you and running session: repo, title, wait or duration.
    expect(md).toContain('- web-app: fix login, waiting 6m')
    expect(md).toContain('- docs-site: edit pages, waiting 2m')
    expect(md).toContain('- api: migrate users, running 22m')
    expect(md.split('\n').filter(l => l.startsWith('- ') && /fix login|edit pages|migrate users|seed data|build the band/.test(l)).length).toBe(5)
    expect(md).not.toContain('rename skills') // a done session has no line
    // The open PRs with their state.
    expect(md).toContain('#2 PR 2')
    expect(md).toContain('checks failing')
    expect(md).toContain('mergeable')
    // No path beyond a repo name.
    expect(md).not.toMatch(/\/work\//)
    // gh gave nothing: no PR lines.
    const noGh = town().map(r => (r.scan ? { ...r, scan: { ...r.scan, ghOk: false } } : r))
    expect(stateMarkdown(bandData(snap(noGh), SELF, NOW))).not.toContain('Open PRs')
  })
})

// A world with the town as the state the band reads. `on` hooks beneath the mod answer the state read.
// The collector writes the snapshot; here the state read answers with the town, as the engine would hand it back.
const withTown = async (_$: Engine, on: On, sessions: SessionRecord[], extra: Partial<Snapshot> = {}) => {
  const w = world(on, { now: NOW, id: SELF, cwd: '/work/platform-tools-suite' })
  const value = snap(sessions, extra)
  on('state.get', (_, e, next) => (e.key === 'snapshot' ? ({ value: { value, version: 1 } } as never) : next(e)))
  return w
}
const BAND = (columns: number) => ({ component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 12, bodyColumns: columns, scroll: { offset: 0, bodyRows: 12 }, view: {} } }) as const
const mount = ($: Engine, surface: 'terminal' | 'desktop', columns = 115) => $.ui.mount({ plugin: 'agent-tracker', surface, ...BAND(columns) } as never)
const settings = (w: World) => w.json(`${DIR}/settings.json`) as Settings | null
const run = ($: Engine, args: string) => $.command.run({ command: 'tracker', args, origin: { kind: 'composer' }, presentation: {} as never })

describe('the band on screen', () => {
  test(`@F22 ${TAG} default compact, view kept in settings.json`, async ($, on) => {
    const w = await withTown($, on, town())
    const ui = await mount($, 'terminal')
    expect(await ui.find({ key: 'pane' })).toBeDefined() // compact: the buttons are Pane and Details
    expect(await ui.find({ key: 'copy' })).toBeUndefined()
    expect(settings(w)).toBeNull() // nothing stored: compact
    await ui.press({ key: 'details' })
    expect(settings(w)).toEqual({ v: 1, view: 'details', bandHidden: false })
    expect(w.invalidations).toBeGreaterThan(0) // every mounted band is asked to draw again
    await ui.redraw()
    expect(await ui.find({ key: 'copy' })).toBeDefined() // details drawn
    await ui.press({ key: 'details' })
    expect(settings(w)).toEqual({ v: 1, view: 'compact', bandHidden: false })
    await ui.redraw()
    expect(await ui.find({ key: 'copy' })).toBeUndefined()
    await ui.unmount()
  })

  test(`@F23 ${TAG} buttons are Pane and Details only, with no quick keys`, async ($, on) => {
    await withTown($, on, town())
    const ui = await mount($, 'terminal')
    const pane = (await ui.find({ key: 'pane' }))!
    const detailsButton = (await ui.find({ key: 'details' }))!
    expect([pane.props.label, pane.props.hotkey, pane.props.plain]).toEqual(['Pane', undefined, true])
    expect([detailsButton.props.label, detailsButton.props.hotkey, detailsButton.props.plain]).toEqual(['Details', undefined, true])
    expect(await ui.find({ key: 'board' })).toBeUndefined() // no Board button
    expect((await ui.findAll({ type: 'Button' })).length).toBe(2)
    // The row is as wide as the terminal and is drawn from the layout.
    expect(await row(ui)).toBe('agent-tracker-1 2/4 goal 14m · ● 2 need you  ◐3  PRs 1✗ 2↓  · fix login waits 6m')
    await ui.unmount()
  })

  test(`${TAG} no button has a quick key, and the buttons sit 2 cells apart, in both views`, async ($, on) => {
    await withTown($, on, town())
    const ui = await mount($, 'terminal')
    for (const view of ['compact', 'details']) {
      await run($, view)
      await ui.redraw()
      const buttons = await ui.findAll({ type: 'Button' })
      expect(buttons.length).toBe(view === 'compact' ? 2 : 3)
      expect(buttons.every(b => b.props.hotkey === undefined)).toBe(true)
      expect((await ui.findAll({ type: 'Box' })).some(b => b.props.gap === 2)).toBe(true) // the row of buttons
    }
    await ui.unmount()
  })

  test(`${TAG} each band command answers with one short line`, async ($, on) => {
    const w = await withTown($, on, town())
    const said = async (args: string) => ((await run($, args)) as { text: string }).text
    expect(await said('details')).toBe('Band switched to details.')
    expect(await said('compact')).toBe('Band switched to compact.')
    expect(await said('band off')).toBe('Band hidden. /tracker band on shows it again.')
    expect(await said('band on')).toBe('Band shown.')
    expect(await said('copy')).toBe(COPIED) // the reply is the toast
    expect(w.toasts.at(-1)).toBe(COPIED)
    w.failCopy = 'no-clipboard'
    expect(await said('copy')).toBe('Copy failed: no-clipboard. Press Copy again or run /tracker copy.')
  })

  test(`@F29 ${TAG} band off and on, kept in settings.json, every session`, async ($, on) => {
    const w = await withTown($, on, town())
    // Another mod in the same slot, beneath this one in the chain.
    on('ui.render', ($, e) => $.ui.resolve(e).Text({ children: 'other band' }))
    const ui = await mount($, 'terminal')
    expect(await ui.find({ key: 'pane' })).toBeDefined()
    await run($, 'band off')
    expect(settings(w)).toEqual({ v: 1, view: 'compact', bandHidden: true })
    await ui.redraw()
    expect(await ui.find({ key: 'pane' })).toBeUndefined() // no tracker row
    expect(await ui.find({ type: 'Text', text: /other band/ })).toBeDefined() // other mods' rows stay
    await run($, 'band on')
    expect(settings(w)).toEqual({ v: 1, view: 'compact', bandHidden: false })
    await ui.redraw()
    expect(await ui.find({ key: 'pane' })).toBeDefined()
    // Another session wrote the file: this band follows it.
    w.put(`${DIR}/settings.json`, { v: 1, view: 'compact', bandHidden: true } satisfies Settings)
    await ui.redraw()
    expect(await ui.find({ key: 'pane' })).toBeUndefined()
    // The command is registered, so `band on` is always there.
    expect(w.commands).toContain('tracker')
    await ui.unmount()
  })

  test(`@F79 ${TAG} /tracker details and /tracker compact switch the view`, async ($, on) => {
    const w = await withTown($, on, town())
    const ui = await mount($, 'terminal')
    await run($, 'details')
    expect(settings(w)?.view).toBe('details')
    await ui.redraw()
    expect(await ui.find({ key: 'copy' })).toBeDefined()
    await run($, 'compact')
    expect(settings(w)?.view).toBe('compact')
    await ui.redraw()
    expect(await ui.find({ key: 'copy' })).toBeUndefined()
    // Case and spaces do not matter; a word that is not the band's goes on to the pane.
    await run($, '  Details ')
    expect(settings(w)?.view).toBe('details')
    await ui.unmount()
  })

  test(`@F80 ${TAG} details buttons, no quick keys`, async ($, on) => {
    const w = await withTown($, on, town())
    const ui = await mount($, 'terminal')
    await run($, 'details')
    await ui.redraw()
    const keys = await ui.findAll({ type: 'Button' })
    expect(keys.map(b => [b.props.key, b.props.label, b.props.hotkey])).toEqual([['copy', 'Copy', undefined], ['pane', 'Pane', undefined], ['details', 'Compact', undefined]])
    expect(keys.every(b => b.props.plain === true)).toBe(true)
    await ui.press({ key: 'details' }) // Compact
    expect(settings(w)?.view).toBe('compact')
    await ui.redraw()
    expect(await ui.find({ key: 'copy' })).toBeUndefined()
    await ui.unmount()
  })

  test(`@F35 ${TAG} the columns on screen: a label, a count and a line each, a rule above`, async ($, on) => {
    await withTown($, on, town())
    const ui = await mount($, 'terminal', 115)
    await run($, 'details')
    await ui.redraw()
    const all = await texts(ui)
    for (const word of ['needs you', 'running', 'PRs', '2', '3', '4 open', 'fix l… · waiting 6m', 'migrate users 22m', '1 ✗ · 2 mergeable']) expect(all).toContain(word)
    expect(all).not.toContain('done') // no done column
    expect(all).toContain('/goal running 14m · ● 2 need you elsewhere · 7 live') // the second header line
    expect(all.some(t => /^─+$/.test(t) && t.length === 115)).toBe(true) // the rule across bodyColumns
    // Three columns of 21 cells, packed from the left: no stretching to the 115 columns.
    expect((await ui.findAll({ type: 'Box' })).filter(b => b.props.width === 21).length).toBe(3)
    await ui.unmount()
  })

  test(`@F37 ${TAG} Svg alt lists every value`, async ($, on) => {
    await withTown($, on, town())
    const ui = await mount($, 'desktop')
    await run($, 'details')
    await ui.redraw()
    const svg = (await ui.find({ type: 'Svg' }))!
    expect(svg).toBeDefined()
    const alt = String(svg.props.alt)
    for (const part of ['needs you 2: fix l… · waiting 6m', 'running 3: migrate users 22m', 'PRs 4 open: 1 ✗ · 2 mergeable']) expect(alt).toContain(part)
    expect(alt).not.toContain('done')
    // The terminal draws Text instead; the desktop draws no rule.
    expect(await ui.find({ type: 'Text', text: /^─+$/ })).toBeUndefined()
    await ui.unmount()
  })

  test(`@F36 ${TAG} Copy writes Markdown and toasts`, async ($, on) => {
    const w = await withTown($, on, town())
    const ui = await mount($, 'terminal')
    await run($, 'details')
    await ui.redraw()
    await ui.press({ key: 'copy' })
    expect(w.copies.length).toBe(1)
    expect(w.copies[0]!.text).toContain('Needs you:** 2')
    expect(w.toasts).toEqual([COPIED])
    expect(COPIED).toBe('Tracker state copied as Markdown')
    // The command does the same, with no button.
    await run($, 'copy')
    expect(w.copies.length).toBe(2)
    expect(w.copies[1]!.text).toBe(w.copies[0]!.text)
    expect(w.toasts).toEqual([COPIED, COPIED])
    await ui.unmount()
  })

  test(`@F86 ${TAG} copy failure toast`, async ($, on) => {
    const w = await withTown($, on, town())
    w.failCopy = 'no-clipboard'
    const ui = await mount($, 'terminal')
    await run($, 'details')
    await ui.redraw()
    await ui.press({ key: 'copy' })
    expect(w.toasts).toEqual(['Copy failed: no-clipboard. Press Copy again or run /tracker copy.'])
    await run($, 'copy')
    expect(w.toasts[1]).toBe('Copy failed: no-clipboard. Press Copy again or run /tracker copy.')
    await ui.unmount()
  })

  test(`@F87 ${TAG} Loading, Partial and Stale line under the details header`, async ($, on) => {
    await withTown($, on, town(), { at: 0, okAt: 0 })
    const ui = await mount($, 'terminal')
    await run($, 'details')
    await ui.redraw()
    expect(await texts(ui)).toContain(LOADING)
    await ui.unmount()
  })

  test(`@F53 ${TAG} loading line on screen`, async ($, on) => {
    await withTown($, on, [], { at: 0, okAt: 0 })
    const ui = await mount($, 'terminal')
    expect(await row(ui)).toBe(LOADING)
    expect((await ui.find({ key: 'pane' }))).toBeDefined() // the buttons stay
    await ui.unmount()
  })

  test(`@F52 ${TAG} stale on screen`, async ($, on) => {
    await withTown($, on, town(), { failedReads: 2, agentsOk: false, okAt: NOW - 2 * MIN })
    const ui = await mount($, 'terminal', 59)
    expect(await row(ui)).toContain('stale 2m')
    await ui.unmount()
  })

  test(`@F54 ${TAG} no PR segment on screen when gh is missing`, async ($, on) => {
    await withTown($, on, town().map(r => (r.scan ? { ...r, scan: { ...r.scan, ghOk: false } } : r)))
    const ui = await mount($, 'terminal', 200)
    expect(await row(ui)).not.toMatch(/PRs/)
    await ui.unmount()
  })

  test(`${TAG} the Pane button opens the pane, and the band only observes: no write to a session, no process, no network`, async ($, on) => {
    const w = await withTown($, on, town())
    const opened: string[] = []
    on('ui.open', (_, e) => {
      opened.push(e.id)
      return { value: { isPlaced: true } }
    })
    const ui = await mount($, 'terminal')
    await ui.press({ key: 'pane' })
    expect(opened).toEqual(['tracker'])
    await run($, 'details')
    await ui.redraw()
    await ui.press({ key: 'copy' })
    await ui.press({ key: 'details' })
    await run($, 'band off')
    await run($, 'band on')
    await run($, 'copy')
    // The only file it writes is settings.json; it raises no prompt, tool call or command, and runs no process.
    expect(w.writes.length).toBeGreaterThan(0)
    expect(w.writes.every(p => p === `${DIR}/settings.json`)).toBe(true)
    expect([w.origins.length, w.toolCalls, w.commandRuns, w.procs.length, w.net.length, w.models.length]).toEqual([0, 0, 0, 0, 0, 0])
    await ui.unmount()
  })

  test(`@F124 ${TAG} every glyph has a word or count beside it`, () => {
    for (const columns of [200, 115, 90, 79, 75, 54, 50, 39]) {
      const line = text(compact(town(), columns))
      expect(line).not.toMatch(/●(?! \d)/) // a count follows ●
      expect(line).not.toMatch(/◐(?!\d)/) // and ◐
      expect(line).not.toMatch(/(^|\D)[✗↓]/) // a count comes before ✗ and ↓
    }
    expect(text(compact(town().filter(r => r.state !== 'needs-you'), 200))).toContain('○ all clear') // ○ has its words
    // At full width each count has its word as well.
    expect(text(compact(town(), 200))).toMatch(/● 2 need you.*◐3.*PRs 1✗ 2↓/)
  })
})

describe('the band follows the data', () => {
  test(`@F31 ${TAG} running count against an agents fixture of known values`, async ($, on) => {
    const w = world(on, { now: T0 + 3_600_000, id: ID.busy, cwd: '/work/repo-4' })
    w.agents.json = AGENTS_JSON // busy and working run, blocked and waiting wait, idle is done
    await start($, w)
    await w.clock.advance(5000)
    const ui = await mount($, 'terminal', 200)
    const line = await row(ui)
    expect(line).toContain('● 2 need you')
    expect(line).toContain('◐2')
    await ui.unmount()
  })

  test(`@F53 ${TAG} a mod loaded mid-session gets no session.start: its first draw starts the collector, and the band loads`, async ($, on) => {
    const w = world(on, { now: T0 + 3_600_000, id: ID.busy, cwd: '/work/repo-4' })
    w.agents.json = AGENTS_JSON
    const ui = await mount($, 'terminal', 200) // no start(): nothing has polled yet
    await settle() // the poll the draw started and did not wait for
    await ui.redraw()
    expect(await row(ui)).not.toContain(LOADING)
    expect(await row(ui)).toContain('● 2 need you')
    expect(w.snapshot().at).not.toBe(0)
    const polls = () => w.procs.filter(p => p.argv[1] === 'agents').length
    expect(polls()).toBe(1)
    await ui.redraw() // a second draw does not start a second collector
    await settle()
    expect(polls()).toBe(1)
    await w.clock.advance(5000) // the timer polls on
    expect(polls()).toBe(2)
    await ui.unmount()
  })

  test(`@F30 ${TAG} redraw by the next poll after a state change`, async ($, on) => {
    const w = world(on, { now: T0 + 3_600_000, id: ID.busy, cwd: '/work/repo-4' })
    const rows = JSON.parse(AGENTS_JSON) as Record<string, unknown>[]
    w.agents.json = JSON.stringify(rows.map(r => (r.sessionId === ID.idle ? { ...r, status: 'busy' } : r)))
    await start($, w)
    await w.clock.advance(5000)
    const ui = await mount($, 'terminal', 200)
    expect(await row(ui)).toContain('● 2 need you')
    // The idle session starts to wait.
    w.agents.json = JSON.stringify(rows.map(r => (r.sessionId === ID.idle ? { ...r, status: 'waiting', waitingFor: 'input needed' } : r)))
    await w.clock.advance(5000) // the next poll
    expect(w.snapshot().sessions.filter(s => s.state === 'needs-you').length).toBe(3)
    await ui.redraw()
    expect(await row(ui)).toContain('● 3 need you')
    await ui.unmount()
  })

  test(`@F52 ${TAG} two failed reads in a row make the band stale; one does not`, async ($, on) => {
    const w = world(on, { now: T0 + 3_600_000, id: ID.busy, cwd: '/work/repo-4' })
    w.agents.json = AGENTS_JSON
    await start($, w)
    await w.clock.advance(5000) // a good read
    w.agents.json = null // `claude agents --json` fails from now on
    await w.clock.advance(5000) // the first failed read
    expect(w.snapshot().failedReads).toBe(1)
    const ui = await mount($, 'terminal', 115)
    expect(await row(ui)).not.toContain('unavailable')
    await w.clock.advance(120_000)
    expect(w.snapshot().failedReads).toBeGreaterThanOrEqual(2)
    await ui.redraw()
    expect(await row(ui)).toContain('session list unavailable · counts from 2m ago')
    w.agents.json = AGENTS_JSON // the next read works
    await w.clock.advance(5000)
    await ui.redraw()
    expect(w.snapshot().failedReads).toBe(0)
    expect(await row(ui)).not.toContain('unavailable')
    await ui.unmount()
  })

  test(`@F126 ${TAG} redraw after one minute with no data change`, async ($, on) => {
    const w = await withTown($, on, town())
    const ui = await mount($, 'terminal', 200)
    const before = w.invalidations
    await w.clock.advance(60_000)
    expect(w.invalidations).toBeGreaterThan(before) // the band asked for a redraw
    // The times are read at each draw: a minute later the wait reads one minute more.
    await ui.redraw()
    expect(await row(ui)).toContain('fix login waits 7m')
    await ui.unmount()
  })
})
