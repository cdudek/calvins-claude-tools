import { describe, expect, test } from 'claude-code/testing'
import type { On } from 'claude-code'
import type { Engine } from 'claude-code/testing'

import {
  ALONE,
  BUTTONS_COMPACT,
  BUTTONS_DETAILS,
  COPIED,
  LOADING,
  PRS_NOT_SHOWN,
  SEP,
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

const text = (l: CompactLayout) => l.segments.map(s => s.chunks.map(c => c.text).join('')).join(SEP)
const compact = (sessions: SessionRecord[], columns: number, extra: Partial<Snapshot> = {}) => compactLayout(bandData(snap(sessions, extra), SELF, NOW), columns)
const details = (sessions: SessionRecord[], columns: number, extra: Partial<Snapshot> = {}) => detailsLayout(bandData(snap(sessions, extra), SELF, NOW), columns)
const ids = (d: Details) => d.rows.map(r => r.map(c => c.key))
const col = (d: Details, key: string) => d.rows.flat().find(c => c.key === key)!
// What a Text on screen reads, every Text of a mounted band.
const texts = async (ui: { findAll: (q: object) => Promise<{ text?: string }[]> }) => (await ui.findAll({ type: 'Text' })).map(t => t.text ?? '')
const row = async (ui: { findAll: (q: object) => Promise<{ text?: string }[]> }) => (await texts(ui)).join('')

describe('compact band, the model', () => {
  test(`@F24 ${TAG} segments in order: needs you, running and done, PRs, work, then the buttons; 123 cells at full width`, () => {
    const l = compact(town(), 200)
    expect(text(l)).toBe('● 2 need you · web-app: fix login 6m │ ◐ 3 running · ✓ 2 done │ 4 PRs · 1 ✗ │ agent-tracker-1 2/4 · goal 14m')
    expect(l.segments.map(s => s.id)).toEqual(['needs', 'run', 'prs', 'work'])
    expect(l.width).toBe(123) // 39 + 25 + 14 + 33, the 3 gaps, and 15 for the buttons (no quick keys: 2 less than the spec's 17)
    expect(BUTTONS_COMPACT).toBe(15)
  })

  test(`@F22 ${TAG} the compact row is the default and its buttons are Pane and Details`, () => {
    // Words: "◐ 3 running · ✓ 2 done" and "4 PRs · 1 ✗".
    expect(text(compact(town(), 200))).toContain('◐ 3 running · ✓ 2 done')
    expect(text(compact(town(), 200))).toContain('4 PRs · 1 ✗')
  })

  test(`@F25 ${TAG} needs you with the oldest waiting session, in the warning colour`, () => {
    const l = compact(town(), 200)
    expect(l.segments[0]!.chunks[0]).toEqual({ text: '● 2 need you', tone: 'warning' })
    expect(l.segments[0]!.chunks[1]).toEqual({ text: ' · web-app: fix login 6m' }) // the oldest, in the normal colour
  })

  test(`@F76 ${TAG} one needs you`, () => {
    const one = town().map(r => (r.sessionId === 'docs-1' ? { ...r, state: 'done' as const } : r))
    expect(text(compact(one, 200)).startsWith('● 1 needs you · web-app: fix login 6m')).toBe(true)
  })

  test(`@F77 ${TAG} zero need you, dim`, () => {
    const quiet = town().filter(r => r.state !== 'needs-you')
    const l = compact(quiet, 200)
    expect(l.segments[0]!.chunks).toEqual([{ text: '0 need you', tone: 'dim' }])
    expect(text(l).startsWith('0 need you │ ◐ 3 running')).toBe(true)
  })

  test(`@F26 ${TAG} this session names itself, then the oldest other one`, () => {
    const l = compact(townSelfWaiting(), 200)
    expect(l.segments[0]!.chunks.map(c => c.text).join('')).toBe('● 2 need you · this session 1m · web-app 6m')
    // Only this session waits.
    const mine = town().map(r => (r.sessionId === SELF ? { ...r, state: 'needs-you' as const, engine: { since: NOW - MIN } } : r)).filter(r => r.sessionId === SELF || r.state !== 'needs-you')
    expect(text(compact(mine, 200)).startsWith('● 1 needs you · this session 1m')).toBe(true)
  })

  test(`@F27 ${TAG} work segment with and without sdlc-run`, () => {
    expect(compact(town(), 200).segments.at(-1)!.chunks.map(c => c.text).join('')).toBe('agent-tracker-1 2/4 · goal 14m')
    const plain = town().map(r => (r.sessionId === SELF ? inState(SELF, 'running', 20, 'web-app', 'fix login redirect') : r))
    expect(compact(plain, 200).segments.at(-1)!.chunks.map(c => c.text).join('')).toBe('web-app · fix login redirect')
    // A goal without sdlc-run still shows its age; a done session has none (F11).
    const goal = town().map(r => (r.sessionId === SELF ? inState(SELF, 'running', 20, 'web-app', 'fix login redirect', { runs: { goalSince: NOW - 14 * MIN, subagents: [], background: [] } }) : r))
    expect(compact(goal, 200).segments.at(-1)!.chunks.map(c => c.text).join('')).toBe('web-app · fix login redirect · goal 14m')
    const finished = goal.map(r => (r.sessionId === SELF ? { ...r, state: 'done' as const } : r))
    expect(compact(finished, 200).segments.at(-1)!.chunks.map(c => c.text).join('')).toBe('web-app · fix login redirect')
    // No title yet: the folder name and "untitled session".
    expect(compact([rec(SELF, { cwd: '/work/some-folder' })], 200).segments.at(-1)!.chunks.map(c => c.text).join('')).toBe('some-folder · untitled session')
  })

  test(`@F28 ${TAG} drop order at 115, 75 and 50 columns; below 40 bodyColumns`, () => {
    // 1 goal age: 123 -> 112, fits 115.
    const w115 = compact(town(), 115)
    expect(text(w115)).toBe('● 2 need you · web-app: fix login 6m │ ◐ 3 running · ✓ 2 done │ 4 PRs · 1 ✗ │ agent-tracker-1 2/4')
    expect(w115.width).toBe(112)
    // With "this session" (needs you 46 cells) the Work segment drops too: 97.
    const mine = compact(townSelfWaiting(), 115)
    expect(mine.width).toBe(97)
    expect(mine.segments.map(s => s.id)).toEqual(['needs', 'run', 'prs'])
    // Steps 1 to 3 together are 77 cells; the words go before the PR segment.
    const w79 = compact(town(), 79)
    expect(text(w79)).toBe('● 2 need you · web-app: fix login 6m │ ◐ 3 · ✓ 2 │ 4 PRs · 1 ✗')
    expect(w79.width).toBe(77)
    expect(text(compact(town(), 92))).toContain('◐ 3 running · ✓ 2 done') // words stay while the row fits (goal and work gone: 90)
    // 4 the PR segment: 63, fits 75.
    const w75 = compact(town(), 75)
    expect(text(w75)).toBe('● 2 need you · web-app: fix login 6m │ ◐ 3 · ✓ 2')
    expect(w75.width).toBe(63)
    // 5 the waiting session's title, keeping its repo and wait: 52.
    const w54 = compact(town(), 54)
    expect(text(w54)).toBe('● 2 need you · web-app 6m │ ◐ 3 · ✓ 2')
    expect(w54.width).toBe(52)
    // Nothing else fits at 50: the counts go before the waiting session (questions.md Q16).
    const w50 = compact(town(), 50)
    expect(text(w50)).toBe('● 2 need you · web-app 6m')
    expect(w50.width).toBe(40)
    // Below 40 only the count and the buttons stay.
    const w39 = compact(town(), 39)
    expect(text(w39)).toBe('● 2 need you')
    expect(w39.width).toBe(12 + BUTTONS_COMPACT)
    expect(text(compact(town(), 20))).toBe('● 2 need you')
    // The count and the buttons never drop, at any width.
    for (const columns of [10, 20, 39, 40, 50, 54, 75, 79, 115, 200]) expect(text(compact(town(), columns)).startsWith('● 2 need you')).toBe(true)
  })

  test(`@F31 ${TAG} running count is the running sessions of the list`, () => {
    // Known values: 3 busy or working, 2 waiting, 2 idle.
    const l = compact(town(), 200)
    expect(l.segments.find(s => s.id === 'run')!.chunks[0]!.text).toBe('◐ 3 running')
    // A history record never counts, and neither does an ended session.
    const history = [...town(), rec('old-1', { source: 'transcript', state: 'running' }), rec('old-2', { state: 'ended' })]
    expect(compact(history, 200).segments.find(s => s.id === 'run')!.chunks[0]!.text).toBe('◐ 3 running')
  })

  test(`@F32 ${TAG} alone note replaces running and PRs`, () => {
    const alone = [inState(SELF, 'running', 20, 'platform-tools-suite', 'build the band', { scan: scan(PRS), milestone: MILESTONE })]
    expect(text(compact(alone, 200))).toBe(`0 need you │ ${ALONE} │ agent-tracker-1 2/4`)
    // This session may still wait, and the work segment stays.
    const waiting = [{ ...alone[0]!, state: 'needs-you' as const, engine: { since: NOW - MIN } }]
    expect(text(compact(waiting, 200))).toBe(`● 1 needs you · this session 1m │ ${ALONE} │ agent-tracker-1 2/4`)
    expect(compact(alone, 200).segments[1]!.chunks[0]!.tone).toBe('dim')
    // Another live session: the note is gone.
    expect(text(compact([...alone, inState('x', 'running', 1, 'api', 'job')], 200))).not.toContain(ALONE)
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
    expect(text(compactLayout(d, 200))).toContain('4 PRs · 1 ✗')
    // No failing: no "✗". One PR: singular.
    const one = [inState(SELF, 'running', 1, 'a', 't', { scan: scan([pr(1)]) }), inState('x', 'running', 1, 'b', 'u')]
    expect(text(compact(one, 200))).toContain('1 PR')
    expect(text(compact(one, 200))).not.toContain('✗')
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
    expect(compact(noGh, 200).segments.map(s => s.id)).toEqual(['needs', 'run', 'work'])
    expect(bandData(snap(noGh), SELF, NOW).partial).toBe(true)
    // Never scanned: no segment either, and nothing is "partial".
    const never = town().map(r => ({ ...r, scan: null }))
    expect(compact(never, 200).segments.map(s => s.id)).toEqual(['needs', 'run', 'work'])
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
    expect(text(compact(long, 200))).toContain('web-app: fix login 2h 10m')
    const days = town().map(r => (r.sessionId === 'web-1' ? { ...r, engine: { since: NOW - 3 * 24 * 60 * MIN } } : r))
    expect(text(compact(days, 200))).toContain('web-app: fix login 3d')
  })
})

describe('details view, the model', () => {
  const NO_RUNS = { goalSince: null, subagents: [], background: [] }
  const branch = (b: string | null, extra: Partial<SessionRecord> = {}) => town().map(r => (r.sessionId === SELF ? { ...r, branch: b, runs: NO_RUNS, ...extra } : r))
  const plain = (extra: Partial<SessionRecord> = {}) =>
    town().map(r => (r.sessionId === SELF ? inState(SELF, 'running', 20, 'web-app', 'fix login redirect', { branch: 'feat/login', ...extra }) : r))

  test(`@F33 ${TAG} details header in both forms, branch left out when it holds the slug`, () => {
    // The slug is in the branch name: left out.
    expect(details(branch('milestone/agent-tracker-1'), 200).header[0]).toBe('platform-tools-suite · agent-tracker-1 · 2 of 4 features complete')
    // Any other branch follows the progress.
    expect(details(branch('feat/band'), 200).header[0]).toBe('platform-tools-suite · agent-tracker-1 · 2 of 4 features complete · feat/band')
    // Without sdlc-run: the title and the branch.
    expect(details(plain(), 200).header[0]).toBe('web-app · fix login redirect · feat/login')
    // Fallbacks: no title, detached HEAD.
    expect(details(plain({ title: null, branch: null }), 200).header[0]).toBe('web-app · untitled session · detached HEAD')
  })

  test(`@F34 ${TAG} what runs, zero parts hidden, second line when full`, () => {
    const runs = (goal: number | null, subagents: number, background: number) =>
      plain({ runs: { goalSince: goal === null ? null : NOW - goal * MIN, subagents: Array.from({ length: subagents }, (_, i) => ({ id: `s${i}`, name: 'x', status: 'running' })), background: Array.from({ length: background }, (_, i) => ({ id: `b${i}`, name: 'x', since: NOW })) } })
    // Wide: one line. Full header and runs would not fit 100 cells with the buttons: a second line.
    const all = details(runs(14, 2, 1), 100)
    expect(all.header).toEqual(['web-app · fix login redirect · feat/login', 'goal 14m · 2 subagents · 1 background session'])
    expect(details(runs(14, 2, 1), 160).header).toEqual(['web-app · fix login redirect · feat/login · goal 14m · 2 subagents · 1 background session'])
    // Each part only when above 0, and singular at 1.
    expect(details(runs(14, 0, 0), 100).header).toEqual(['web-app · fix login redirect · feat/login · goal 14m'])
    expect(details(runs(null, 1, 0), 100).header).toEqual(['web-app · fix login redirect · feat/login · 1 subagent'])
    expect(details(runs(null, 0, 2), 100).header).toEqual(['web-app · fix login redirect · feat/login · 2 background sessions'])
    expect(details(runs(null, 0, 0), 100).header).toEqual(['web-app · fix login redirect · feat/login'])
  })

  test(`@F84 ${TAG} header cut order at 80 columns`, () => {
    const sdlc = (b: string) => branch(b)
    const wide = 'platform-tools-suite · agent-tracker-1 · 2 of 4 features complete · feat/band'
    expect(details(sdlc('feat/band'), 200).header[0]).toBe(wide)
    // Cut 1: the branch. The full header and the 21 button cells are 98; without the branch, 86.
    expect(details(sdlc('feat/band'), 98).header[0]).toBe(wide)
    expect(details(sdlc('feat/band'), 97).header[0]).toBe('platform-tools-suite · agent-tracker-1 · 2 of 4 features complete')
    expect(details(sdlc('feat/band'), 86).header[0]).toBe('platform-tools-suite · agent-tracker-1 · 2 of 4 features complete')
    // Then "2 of 4 features complete" shortens: (77 columns now: 80 less the 3 cells the quick keys took).
    expect(details(sdlc('feat/band'), 85).header[0]).toBe('platform-tools-suite · agent-tracker-1 · 2/4 complete')
    expect(details(sdlc('feat/band'), 77).header[0]).toBe('platform-tools-suite · agent-tracker-1 · 2/4 complete')
    expect(details(sdlc('feat/band'), 74).header[0]).toBe('platform-tools-suite · agent-tracker-1 · 2/4 complete')
    // Last the milestone name.
    expect(details(sdlc('feat/band'), 73).header[0]).toBe('platform-tools-suite · 2/4 complete')
    expect(details(sdlc('feat/band'), 56).header[0]).toBe('platform-tools-suite · 2/4 complete')
    // Without sdlc-run: branch, then title.
    expect(details(plain(), 62).header[0]).toBe('web-app · fix login redirect · feat/login')
    expect(details(plain(), 61).header[0]).toBe('web-app · fix login redirect')
    expect(details(plain(), 49).header[0]).toBe('web-app · fix login redirect')
    expect(details(plain(), 48).header[0]).toBe('web-app')
    // What runs stays on its own line.
    const goal = plain({ runs: { goalSince: NOW - 14 * MIN, subagents: [], background: [] } })
    expect(details(goal, 57).header).toEqual(['web-app · fix login redirect', 'goal 14m'])
    expect(BUTTONS_DETAILS).toBe(21) // Copy, Pane, Compact: 15 label cells, 2 before the buttons and 2 between
  })

  test(`@F35 ${TAG} four columns, empty column`, () => {
    const d = details(town(), 115)
    expect(ids(d)).toEqual([['needs', 'running', 'done', 'prs']])
    expect(d.rows[0]!.map(c => c.label)).toEqual(['needs you', 'running', 'done', 'PRs'])
    expect(d.rows[0]!.map(c => c.count)).toEqual(['2', '3', '2', '4 open'])
    expect(d.colWidth).toBe(26) // 115 / 4 - 2
    // A column with 0 shows the count and no line.
    const none = town().filter(r => r.state !== 'done')
    expect(col(details(none, 115), 'done')).toMatchObject({ count: '0', line: '' })
    // At least 10 wide.
    expect(details(town(), 60).colWidth).toBeGreaterThanOrEqual(10)
    // Below 80 the lines drop except needs you.
    const narrow = details(town(), 79)
    expect(narrow.rows[0]!.map(c => c.line !== '')).toEqual([true, false, false, false])
    expect(details(town(), 80).rows[0]!.every(c => c.line !== '')).toBe(true)
  })

  test(`@F81 ${TAG} needs you, running and done lines`, () => {
    const d = details(town(), 115)
    expect(col(d, 'needs').line).toBe('web-app: fix login 6m') // the oldest waiting
    expect(col(d, 'running').line).toBe('api: migrate users 22m') // the longest running
    expect(col(d, 'done').line).toBe('docs-site: rename skills 3m ago') // the latest done
    // Needs you in the normal colour, the others dim.
    expect(col(d, 'needs').tone).toBeUndefined()
    expect([col(d, 'running').tone, col(d, 'done').tone]).toEqual(['dim', 'dim'])
    // "this session" when it is this one.
    const mine = town().map(r => (r.sessionId === SELF ? { ...r, state: 'needs-you' as const, engine: { since: NOW - 10 * MIN } } : r))
    expect(col(details(mine, 115), 'needs').line).toBe('this session 10m')
  })

  test(`@F82 ${TAG} PRs count and line`, () => {
    const d = details(town(), 115)
    expect(col(d, 'prs')).toMatchObject({ count: '4 open', line: '1 failing · 2 mergeable' })
    const some = town().map(r => (r.scan ? { ...r, scan: scan([pr(1, { mergeable: 'mergeable' }), pr(2)]) } : r))
    expect(col(details(some, 115), 'prs')).toMatchObject({ count: '2 open', line: '1 mergeable' })
    const clean = town().map(r => (r.scan ? { ...r, scan: scan([pr(1)]) } : r))
    expect(col(details(clean, 115), 'prs')).toMatchObject({ count: '1 open', line: '' })
  })

  test(`@F83 ${TAG} columns fold below 60 bodyColumns`, () => {
    expect(ids(details(town(), 60))).toEqual([['needs', 'running', 'done', 'prs']])
    expect(ids(details(town(), 59))).toEqual([['needs', 'running'], ['done', 'prs']])
    expect(details(town(), 59).colWidth).toBe(27) // 59 / 2 - 2
    expect(ids(details(town(), 30))).toEqual([['needs', 'running'], ['done', 'prs']])
    expect(details(town(), 30).colWidth).toBe(13)
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
    expect(ids(partial)).toEqual([['needs', 'running', 'done']])
    // One line: stale wins over partial.
    expect(details(noGh, 115, failed).note).toBe('session list unavailable · counts from 2m ago')
  })

  test(`@F37 ${TAG} the SVG alt lists every label and value`, () => {
    const d = details(town(), 115)
    const svg = columnsSvg(d.rows.flat(), 720)
    expect(svg.startsWith('<svg')).toBe(true)
    for (const c of d.rows.flat()) expect(svg).toContain(c.label)
    // Escaped: a title can hold markup.
    const risky = town().map(r => (r.sessionId === 'web-1' ? { ...r, title: 'a<b>&c' } : r))
    expect(columnsSvg(details(risky, 115).rows.flat(), 720)).toContain('a&lt;b&gt;&amp;c')
  })
})

describe('every width the spec lists', () => {
  const WIDTHS = [40, 50, 54, 60, 70, 75, 80, 115] // the widths done.json lists
  const failed = { failedReads: 2, agentsOk: false, okAt: NOW - 2 * MIN }
  const cases: [string, SessionRecord[], Partial<Snapshot>][] = [
    ['town', town(), {}],
    ['this session waits', townSelfWaiting(), {}],
    ['stale', town(), failed],
    ['alone', [inState(SELF, 'running', 20, 'platform-tools-suite', 'build', { milestone: MILESTONE, scan: scan(PRS) })], {}],
    ['loading', [], { at: 0, okAt: 0 }],
  ]

  test(`@F28 ${TAG} the compact row fits bodyColumns at each width, except below the count and the buttons`, () => {
    for (const columns of WIDTHS) {
      for (const [name, sessions, extra] of cases) {
        const l = compact(sessions, columns, extra)
        const floor = text(l).startsWith('●') || text(l).startsWith('0 need') ? 12 + BUTTONS_COMPACT : 0
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
    expect(await row(ui)).toBe('● 2 need you · web-app: fix login 6m │ ◐ 3 running · ✓ 2 done │ 4 PRs · 1 ✗ │ agent-tracker-1 2/4')
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
    for (const word of ['needs you', 'running', 'done', 'PRs', '2', '3', '4 open', 'web-app: fix login 6m', 'api: migrate users 22m', 'docs-site: rename skills 3m ago', '1 failing · 2 mergeable']) expect(all).toContain(word)
    expect(all.some(t => /^─+$/.test(t) && t.length === 115)).toBe(true) // the rule across bodyColumns
    expect((await ui.findAll({ type: 'Box' })).some(b => b.props.width === 26)).toBe(true)
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
    for (const part of ['needs you 2', 'running 3', 'done 2', 'PRs 4 open', 'web-app: fix login 6m', 'api: migrate users 22m', 'docs-site: rename skills 3m ago', '1 failing · 2 mergeable']) expect(alt).toContain(part)
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
      expect(line).not.toMatch(/[●◐✓] \D/) // a count follows ● ◐ ✓
      expect(line).not.toMatch(/(^|\D) ✗/) // a count comes before ✗
    }
    // At full width each count has its word as well.
    expect(text(compact(town(), 200))).toMatch(/● 2 need you.*◐ 3 running · ✓ 2 done.*4 PRs · 1 ✗/)
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
    expect(line).toContain('◐ 2 running · ✓ 1 done')
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
    expect(await row(ui)).toContain('web-app: fix login 7m')
    await ui.unmount()
  })
})
