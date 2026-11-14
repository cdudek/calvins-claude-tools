import { describe, expect, test } from 'claude-code/testing'

import { clean, foldTranscript, fragments, isGithubRemote, parsePrs, parseWorktrees, prsLine, repoPrs } from '../hooks/tracker/core'
import type { SessionRecord } from '../hooks/tracker/types'
import { EXPECTED_PRS, EXPECTED_WORKTREES, GH_JSON, GH_PRS, WORKTREES_PORCELAIN } from './fixtures/scans'
import { DIR, start, world } from './fixtures/world'
import type { World } from './fixtures/world'

const TAG = '@2026-11-13-agent-tracker'
const NOW = Date.parse('2026-11-11T00:00:00Z')
const MINUTE = 60_000
const HOUR = 60 * MINUTE

const own = (w: World) => w.json(`${DIR}/sessions/${w.id}.json`) as SessionRecord
const ghCalls = (w: World) => w.procs.filter(p => p.argv[0] === 'gh')
const wtCalls = (w: World) => w.procs.filter(p => p.argv[0] === 'git' && p.argv.includes('worktree'))
const scripted = (w: World) => {
  w.worktrees[w.cwd] = WORKTREES_PORCELAIN
  w.gh.json = GH_JSON
}

const record = (id: string, extra: Partial<SessionRecord> = {}): SessionRecord => ({
  v: 1, sessionId: id, source: 'mod', writtenAt: NOW, kind: 'interactive', title: null, cwd: '/work/x', repo: { path: '/work/repo-9', name: 'repo-9' },
  branch: 'main', startedAt: NOW - 5 * HOUR, lastActivityAt: NOW, endedAt: null, engine: { since: NOW }, state: 'done', reason: null, unknownValue: null,
  questionFlag: null, usage: { tokensIn: 0, tokensOut: 0, toolErrors: 0, retries: 0 }, asks: [],
  runs: { goalSince: null, subagents: [], background: [] }, milestone: null, scan: null, ...extra,
})

describe('git and gh scans', () => {
  test(`@F14 ${TAG} git and gh output fixtures`, async ($, on) => {
    // The parsers, on the recorded output.
    expect(parseWorktrees(WORKTREES_PORCELAIN)).toEqual(EXPECTED_WORKTREES)
    expect(parsePrs(GH_JSON)).toEqual(EXPECTED_PRS)
    expect(parsePrs('not json')).toBeNull()
    expect(parsePrs('{}')).toBeNull()
    expect(GH_PRS.length).toBe(4)

    // The scan itself: worktrees by `git worktree list`, open PRs by `gh pr list --json` with checks, review, mergeable.
    const w = world(on, { now: NOW })
    scripted(w)
    await start($, w)
    await w.clock.advance(1000)
    const wt = wtCalls(w)
    expect(wt.length).toBe(1)
    expect(wt[0]!.argv.join(' ')).toBe('git -c core.fsmonitor=false -c core.hooksPath=/dev/null worktree list --porcelain')
    expect(wt[0]!.cwd).toBe(w.cwd)
    const gh = ghCalls(w)
    expect(gh.length).toBe(1)
    expect(gh[0]!.argv.slice(0, 3)).toEqual(['gh', 'pr', 'list'])
    const fields = gh[0]!.argv[gh[0]!.argv.indexOf('--json') + 1]!.split(',')
    expect(fields).toEqual(expect.arrayContaining(['number', 'title', 'url', 'headRefName', 'createdAt', 'statusCheckRollup', 'reviewDecision', 'mergeable']))
    expect(own(w).scan).toEqual({ at: NOW, ghOk: true, worktrees: EXPECTED_WORKTREES, prs: EXPECTED_PRS })
    await w.clock.advance(5000) // the next poll merges it into the snapshot the band and the pane read
    expect(w.snapshot().sessions.find(s => s.sessionId === w.id)?.scan?.prs.length).toBe(4)
  })

  test(`@F67 ${TAG} own repo only, every 2 minutes`, async ($, on) => {
    const w = world(on, { now: NOW })
    scripted(w)
    // Another session's file for another repo: the mod reads it and never scans that repo.
    w.put(`${DIR}/sessions/other.json`, record('other', { cwd: '/work/repo-other', repo: { path: '/work/repo-other', name: 'repo-other' }, scan: { at: NOW - HOUR, ghOk: true, worktrees: [], prs: [] } }))
    await start($, w)
    await w.clock.advance(1000)
    expect(ghCalls(w).length).toBe(1)
    await w.clock.advance(118_000) // 1m59s after the start
    expect(ghCalls(w).length).toBe(1)
    await w.clock.advance(1000) // 2 minutes
    expect(ghCalls(w).length).toBe(2)
    await w.clock.advance(4 * MINUTE)
    expect(ghCalls(w).length).toBe(4)
    expect(wtCalls(w).length).toBe(4)
    // Every scan ran in this session's own folder; none in the other repo.
    expect([...ghCalls(w), ...wtCalls(w)].every(p => p.cwd === w.cwd)).toBe(true)
    expect(w.procs.some(p => p.cwd === '/work/repo-other')).toBe(false)
    expect((w.json(`${DIR}/sessions/other.json`) as SessionRecord).scan?.at).toBe(NOW - HOUR)
  })

  test(`@F67 ${TAG} a session in no repo scans nothing`, async ($, on) => {
    const w = world(on, { now: NOW })
    scripted(w)
    w.git[w.cwd] = { commonDir: null, branch: null }
    await start($, w)
    await w.clock.advance(5 * MINUTE)
    expect(ghCalls(w).length).toBe(0)
    expect(wtCalls(w).length).toBe(0)
    expect(own(w).scan).toBeNull()
  })

  test(`@F54 ${TAG} gh missing`, async ($, on) => {
    const w = world(on, { now: NOW })
    scripted(w)
    await start($, w)
    await w.clock.advance(1000)
    expect(own(w).scan?.prs.length).toBe(4)
    // gh is signed out: it exits 1. The last PRs stay, with their own time; the worktrees are read again.
    w.gh.json = null
    w.worktrees[w.cwd] = 'worktree /work/repo-9\nHEAD 1111\nbranch refs/heads/main\n'
    await w.clock.advance(2 * MINUTE)
    expect(ghCalls(w).length).toBe(2)
    expect(own(w).scan).toEqual({ at: NOW, ghOk: false, worktrees: [{ path: '/work/repo-9', branch: 'main' }], prs: EXPECTED_PRS })
    // gh is not installed: the call cannot start. Same result, and the session carries on.
    w.gh.missing = true
    await w.clock.advance(2 * MINUTE)
    expect(ghCalls(w).length).toBe(3)
    expect(own(w).scan?.ghOk).toBe(false)
    expect(own(w).scan?.prs).toEqual(EXPECTED_PRS)
    expect(w.statuses.every(s => s === undefined)).toBe(true) // no error line: a missing gh is a state, not a failure
    // gh signed in again: the next scan is whole.
    w.gh.missing = false
    w.gh.json = GH_JSON
    await w.clock.advance(2 * MINUTE)
    expect(own(w).scan).toMatchObject({ ghOk: true, prs: EXPECTED_PRS })
  })

  test(`@F54 ${TAG} a remote that is not GitHub: gh never runs and the no-gh line shows (S2)`, async ($, on) => {
    const w = world(on, { now: NOW })
    scripted(w)
    w.git[w.cwd] = { commonDir: `${w.cwd}/.git`, branch: 'main', remote: 'https://gitlab.example.test/acme/repo.git' }
    await start($, w)
    await w.clock.advance(1000)
    expect(ghCalls(w).length).toBe(0)
    expect(own(w).scan).toEqual({ at: NOW, ghOk: false, worktrees: EXPECTED_WORKTREES, prs: [] })
    // Every git call carries the guard; a remote that names github.com in its path only is not GitHub.
    expect(w.procs.filter(p => p.argv[0] === 'git').every(p => p.argv.slice(1, 5).join(' ') === '-c core.fsmonitor=false -c core.hooksPath=/dev/null')).toBe(true)
    for (const url of ['https://github.com/a/b', 'git@github.com:a/b.git', 'ssh://git@github.com/a/b']) expect(isGithubRemote(url)).toBe(true)
    for (const url of ['', 'https://gitlab.test/github.com/b', 'git@evilgithub.com:a/b', 'https://github.com.evil.test/a/b']) expect(isGithubRemote(url)).toBe(false)
  })

  test(`@F54 ${TAG} control characters in a PR title and an ask never reach the record; only https links stay (S1)`, async ($, on) => {
    const w = world(on, { now: NOW })
    w.worktrees[w.cwd] = WORKTREES_PORCELAIN
    w.gh.json = JSON.stringify([
      { ...GH_PRS[0], title: 'Fix\u001b[2J\u001b]0;pwned\u0007 login\u009b', url: 'javascript:alert(1)', headRefName: 'feat/\u001bx' },
      { ...GH_PRS[1], title: 'x'.repeat(5000) },
      GH_PRS[2],
    ])
    await start($, w)
    await w.clock.advance(1000)
    const [a, b, c] = own(w).scan!.prs
    expect(a).toMatchObject({ title: 'Fix[2J]0;pwned login', url: '', branch: 'feat/x' })
    expect(b!.title.length).toBe(200)
    expect(c!.url).toBe('https://example.test/pr/103')
    expect(clean('a\u001b[31mb\u009b\u007f\r\nc', 50)).toBe('a[31mb\nc') // newline stays, carriage return goes
    // A transcript's ask text and title go through the same filter.
    const lines = [
      JSON.stringify({ isSidechain: false, type: 'user', message: { role: 'user', content: 'run \u001b[2Jthis' }, timestamp: '2026-11-10T08:00:00Z', aiTitle: 'T\u001b[1mitle' }),
    ].join('\n')
    const f = foldTranscript(fragments(lines))
    expect(f.asks.map(x => x.text)).toEqual(['run [2Jthis'])
    expect(f.title).toBe('T[1mitle')
  })

  test(`@F54 ${TAG} gh missing from the first scan: no PRs`, async ($, on) => {
    const w = world(on, { now: NOW })
    scripted(w)
    w.gh.missing = true
    await start($, w)
    await w.clock.advance(1000)
    expect(own(w).scan).toEqual({ at: NOW, ghOk: false, worktrees: EXPECTED_WORKTREES, prs: [] })
  })

  test(`@F69 ${TAG} stored PR state and its age with no live mod session`, () => {
    const old = record('old', { endedAt: NOW - 3 * HOUR, state: 'ended', scan: { at: NOW - 2 * HOUR, ghOk: true, worktrees: [], prs: EXPECTED_PRS.slice(0, 1) as never } })
    const older = record('older', { endedAt: NOW - 9 * HOUR, state: 'ended', scan: { at: NOW - 5 * HOUR, ghOk: true, worktrees: [], prs: [] } })
    const fromTranscript = record('t', { source: 'transcript', state: 'ended', scan: null })
    const elsewhere = record('else', { repo: { path: '/work/repo-other', name: 'repo-other' }, scan: { at: NOW - MINUTE, ghOk: true, worktrees: [], prs: [] } })
    const sessions = [older, old, fromTranscript, elsewhere]

    // The newest scan among the repo's sessions is the repo's PR state, with its age.
    const s = repoPrs(sessions, '/work/repo-9', NOW)!
    expect(s.at).toBe(NOW - 2 * HOUR)
    expect(s.ageMs).toBe(2 * HOUR)
    expect(s.prs.length).toBe(1)
    expect(s.hasLive).toBe(false)
    expect(prsLine(s)).toBe('PRs as of 2h ago: no live session in this repo')

    // A live session of the mod in the repo: its scan is current and no line shows.
    const live = record('live', { source: 'mod', state: 'running', scan: { at: NOW - MINUTE, ghOk: true, worktrees: [], prs: [] } })
    const l = repoPrs([...sessions, live], '/work/repo-9', NOW)!
    expect(l.hasLive).toBe(true)
    expect(l.at).toBe(NOW - MINUTE)
    expect(prsLine(l)).toBeNull()
    // A session the list shows without the mod is not a live mod session.
    expect(repoPrs([old, record('e', { source: 'engine', state: 'running' })], '/work/repo-9', NOW)!.hasLive).toBe(false)
    // A repo no scan ever read has no PR state.
    expect(repoPrs(sessions, '/work/unknown', NOW)).toBeNull()
  })
})
