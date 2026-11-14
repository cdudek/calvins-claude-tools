import { describe, expect, test } from 'claude-code/testing'
import type { On } from 'claude-code'
import type { Engine } from 'claude-code/testing'

import { boardHtml } from '../hooks/tracker/board-page'
import { boardData, inlineJson, needsCount, titleOf } from '../hooks/tracker/core/board-html'
import type { ChangeFiles } from '../hooks/tracker/core/board-html'
import type { SessionRecord, Snapshot } from '../hooks/tracker/types'
import { MILESTONE_MD } from './fixtures/milestone'
import { NOON, SELF, paneTown, rec, sess, snapAt } from './fixtures/pane'
import { ask, taskTown } from './fixtures/tasks'
import { DIR, settle, start, world } from './fixtures/world'

const TAG = '@2026-11-13-agent-tracker'
const RUN = { stderr: '', isStdoutTruncated: false, isStderrTruncated: false } as const

// The JSON block the page draws from, read back out of the HTML.
const dataOf = (html: string) => JSON.parse(/<script type="application\/json" id="data">([\s\S]*?)<\/script>/.exec(html)![1]!)

const FACTS = `## Acceptance criteria

- [ ] **F1** (A1, A10) While the mod runs, the lease holder shall list every session. Tag: \`@F1\`.
- [ ] **F2** (A1) A busy session is running. Tag: \`@F2\`.
- [ ] **F3** (A1) A waiting session needs you. Tag: \`@F3\`.
`
const VALIDATION = `## Facts

| ID | Expected | Observed | Evidence | Verdict |
|---|---|---|---|---|
| F1 | lists | listed | collector.test.ts | met |
| F2 | busy | busy | collector.test.ts | partial |
`
const DONE = JSON.stringify({ facts: [{ id: 'F1', feature: 1, check: 'collector.test.ts lists sessions' }, { id: 'F2', feature: 1, check: 'busy is running' }, { id: 'F3', feature: 3, check: 'waiting needs you' }] })
const QUESTIONS = `# Questions

- **Q1 (F4, step 3): which waitingFor value means a permission prompt?** A session was waiting. **Default taken:** none recorded, so any value is "waiting". **To change:** set the constant.
`
const FINDINGS = `# Findings

## Fix round

- [x] **S1 Strip control characters** (security review).
- [ ] **R2 Open item** (code review).

## Advisory

- [ ] **A1 not blocking**
`
const CHANGE: ChangeFiles = { repoPath: '/work/platform-tools-suite', folder: '2026-01-01-demo', milestone: MILESTONE_MD, facts: FACTS, validation: VALIDATION, questions: QUESTIONS, findings: FINDINGS, done: DONE }

const withSnap = (on: On, sessions: SessionRecord[], opens?: ReturnType<typeof opener>, extra: Partial<Snapshot> = {}) => {
  const w = world(opens?.on ?? on, { now: NOON, id: SELF, cwd: '/work/platform-tools-suite' })
  const snap = snapAt(sessions, extra)
  on('state.get', (_, e, next) => (e.key === 'snapshot' ? ({ value: { value: snap, version: 1 } } as never) : next(e)))
  return w
}

// The world answers every process; the opener answers 0 in front of it and records what it was asked. `on` is wrapped
// because a second process.run hook may not be registered.
const opener = (on: On, exitCode = 0) => {
  const calls: string[][] = []
  const wrapped = ((event: string, ...rest: unknown[]) => {
    if (event !== 'process.run') return (on as (...a: unknown[]) => unknown)(event, ...rest)
    const world = rest[rest.length - 1] as (c: unknown, e: { argv: readonly string[] }, n: unknown) => unknown
    return (on as (...a: unknown[]) => unknown)(event, (c: unknown, e: { argv: readonly string[] }, n: unknown) => {
      if (e.argv[0] === 'uname') return { value: { exitCode: 0, stdout: 'Darwin\n', ...RUN } }
      if (e.argv[0] === 'open' || e.argv[0] === 'xdg-open') {
        calls.push([...e.argv])
        return { value: { exitCode, stdout: '', ...RUN } }
      }
      return world(c, e, n)
    })
  }) as unknown as On
  return { calls, on: wrapped }
}

const run = ($: Engine, args: string) => $.command.run({ command: 'tracker', args, origin: { kind: 'composer' }, presentation: {} as never })

describe('the web page, built from a snapshot', () => {
  test(`web page ${TAG} the HTML holds the data, the routes, the reload and the count in the title`, () => {
    const html = boardHtml(boardData(snapAt(paneTown()), [CHANGE], NOON))
    const d = dataOf(html)
    expect(d.builtAt).toBe(NOON)
    expect(d.sessions.map((s: { id: string }) => s.id)).toEqual(expect.arrayContaining(['web-1', 'docs-1', 'api-1']))
    const web = d.sessions.find((s: { id: string }) => s.id === 'web-1')
    expect(web).toMatchObject({ repo: 'web-app', title: 'fix login redirect', state: 'needs-you', reason: 'permission', branch: 'feat/login' })
    expect(d.repos.map((r: { label: string }) => r.label)).toEqual(expect.arrayContaining(['web-app', 'api', 'docs-site']))
    expect(d.repos.find((r: { label: string }) => r.label === 'web-app').prs.list.length).toBe(4)
    expect(html).toContain('<title>(2) Agent tracker - your tasks not done yet</title>') // web-app and docs-site wait
    expect(needsCount(boardData(snapAt(aloneOf()), [], NOON))).toBe(0)
    expect(titleOf(0)).toBe('Agent tracker - your tasks not done yet')
    // The routes of the pages, and the page keeps its route through the reload.
    for (const route of ["'#/repo/'", "'/milestone/'", "'/feature/'", "'#/session/'", "'/note/'"]) expect(html).toContain(route)
    expect(html).toContain('location.hash')
    expect(html).toContain('location.reload()')
    expect(html).toContain('5000')
    expect(html).toContain('agent-tracker-compact') // the compact toggle, kept in localStorage
    expect(html).not.toContain('innerHTML')
    expect(html).not.toMatch(/<link|@import|\ssrc=/) // self-contained: no outside script, style or font
  })

  test(`web page ${TAG} a name with <script> and quotes cannot leave the data block`, () => {
    const evil = '</script><script>alert("x")</script> "quoted" & <b>'
    const html = boardHtml(boardData(snapAt([sess('x-1', 'needs-you', 3, 'web-app', evil, { reason: 'waiting' })]), [], NOON))
    expect(html.split('</script>').length - 1).toBe(2) // the data block and the page script, and no more
    expect(html).not.toContain('<script>alert')
    expect(html).not.toContain(evil)
    expect(dataOf(html).sessions[0].title).toBe(evil) // read back whole, quote and all
    const line = String.fromCharCode(0x2028)
    expect(inlineJson({ a: `x${line}y<>&` })).not.toMatch(new RegExp(`[<>&${line}]`))
    expect(JSON.parse(inlineJson({ a: `x${line}y<>&` })).a).toBe(`x${line}y<>&`)
  })

  test(`web page ${TAG} the change folders give features, facts with verdicts, questions and findings`, () => {
    const d = boardData(snapAt(paneTown()), [CHANGE, { ...CHANGE, repoPath: '/work/not-in-the-snapshot' }], NOON)
    expect(d.milestones.length).toBe(1) // a repo with no session is left out
    const m = d.milestones[0]!
    expect(m).toMatchObject({ slug: 'demo-1', branch: 'milestone/demo-1', change: '2026-01-01-demo' })
    expect(m.features.map(f => [f.n, f.state])).toEqual([[0, 'done abc1234'], [1, 'done def5678'], [2, 'building'], [3, 'merged'], [4, 'blocked: waits on review']])
    expect(m.features[1]!.ref).toBe('def5678')
    expect(m.facts.map(f => [f.id, f.feature, f.verdict])).toEqual([['F1', 1, 'met'], ['F2', 1, 'partial'], ['F3', 3, null]])
    expect(m.facts[0]!.text).toContain('lease holder shall list every session')
    expect(m.questions).toEqual([{ id: 'Q1', text: 'which waitingFor value means a permission prompt?', taken: 'none recorded, so any value is "waiting".' }])
    expect(m.findings.map(f => f.open)).toEqual([false, true]) // the Advisory item does not count
  })

  test(`web page ${TAG} notes show when a session carries them, and nothing when it does not`, () => {
    const notes = [{ id: 'n1', kind: 'know', text: 'Tests hit the real sandbox', at: NOON - 1000, seen: false }, { id: 'n2', kind: 'decided', text: 'Dark mode follows the system', at: NOON - 2000, seen: true }, { id: 'bad', kind: 'other', text: 'x', at: 1 }]
    const withNotes = { ...rec('n-1', { repo: { path: '/work/web-app', name: 'web-app' }, title: 'tokens' }), notes } as SessionRecord
    const d = boardData(snapAt([withNotes, rec('n-2', { repo: { path: '/work/api', name: 'api' } })]), [], NOON)
    expect(d.sessions.find(s => s.id === 'n-1')!.notes).toEqual([notes[0], notes[1]]) // an unknown kind is dropped
    expect(d.sessions.find(s => s.id === 'n-2')!.notes).toEqual([])
    const html = boardHtml(d)
    for (const word of ['YOU SHOULD KNOW', 'DECIDED WITHOUT YOU', 'Copy overrule']) expect(html).toContain(word)
  })

  test(`web page ${TAG} the resume command holds only a plain session id`, () => {
    const ended = (id: string) => sess(id, 'ended', 30, 'web-app', 'done work', { endedAt: NOON - 30 * 60_000, cwd: "/work/it's here" })
    const d = boardData(snapAt([ended('abc-123_X'), ended('x; rm -rf ~'), ended('a'.repeat(65))]), [], NOON)
    const resume = (id: string) => d.sessions.find(s => s.id === id)!.resume
    expect(resume('abc-123_X')).toBe("cd '/work/it'\\''s here' && claude --resume abc-123_X") // the folder stays single-quoted
    expect(resume('x; rm -rf ~')).toBeNull() // no command, so no button
    expect(resume('a'.repeat(65))).toBeNull()
    expect(boardHtml(d)).not.toContain('claude --resume x;')
  })

  test(`web page ${TAG} an old session is left out and a stale list is marked`,() => {
    const old = sess('old-1', 'ended', 10 * 24 * 60, 'web-app', 'ancient', { endedAt: NOON - 10 * 24 * 3600_000, lastActivityAt: NOON - 10 * 24 * 3600_000 })
    const d = boardData(snapAt([old, ...aloneOf()], { failedReads: 2 }), [], NOON)
    expect(d.sessions.map(s => s.id)).toEqual([SELF])
    expect(d.stale).toBe(true)
  })
})

describe('the web page: your tasks not done', () => {
  const data = (sessions: SessionRecord[], marks?: Parameters<typeof boardData>[3], extra: Partial<Snapshot> = {}) => boardData(snapAt(sessions, extra), [], NOON, marks)
  // The page's own script, the part of the HTML that runs in the browser.
  const scriptOf = (html: string) => [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)![1]!
  const SIX = ['Running', 'You should know', 'Decided without you', 'Pull requests', 'Done today', 'Ended today']

  test(`web page ${TAG} the data holds the tasks not done, in order, with the words each row shows`, () => {
    const d = data(taskTown())
    expect(d.tasks.map(t => [t.key, t.status])).toEqual([['need-1:1', 'needs-you'], ['lost-2:1', 'forgotten'], ['lost-1:1', 'forgotten'], ['sup-1:1', 'superseded'], ['sup-1:2', 'in-progress'], ['prog-1:1', 'in-progress'], ['prog-2:1', 'in-progress']])
    expect(d.counts).toEqual({ notDone: 7, needsYou: 1, alarm: true })
    expect(needsCount(d)).toBe(1) // "1 needs you now": the sessions that wait
    expect(d.tasks[0]).toMatchObject({ text: 'Fix the login redirect so users land back on the page they came from.', repo: 'web-app', at: NOON - 20 * 60_000, detail: 'waiting for your answer for 4m' }) // the whole ask
    expect(d.tasks[1]!.detail).toBe('idle 45m, not done, no milestone, no PR')
    expect(d.tasks[3]!.later).toEqual({ at: NOON - 8 * 60_000, text: 'Fix the login redirect and…' })
    expect(d.tasks[5]!.progress).toEqual({ slug: 'agent-tracker-1', done: 2, total: 4 })
    expect(d.sessions.find(s => s.id === 'need-1')).toBeDefined() // each row's session has its page
  })

  test(`web page ${TAG} the page draws the top bar, the one list and six collapsed sections; Keep and Close are shown, not wired`, () => {
    const html = boardHtml(data(taskTown()))
    const script = scriptOf(html)
    for (const words of ['Agent tracker', "' of your tasks '", "' not done · '", ' you now', 'Your tasks not done yet', 'Everything else', 'Open session', 'Updated ', 'Every task you gave is done']) expect(script).toContain(words)
    for (const name of SIX) expect(script).toContain(`'${name}'`)
    expect(script).toContain('Keep and Close are chosen in the terminal pane.')
    expect(script).toContain("['Keep','Close']")
    expect(script).toContain("setAttribute('aria-disabled','true')") // shown, and does nothing
    expect(script).toContain("el('details',cls)")
    expect(script).not.toMatch(/setAttribute\('open'|\.open\s*=|'details'[^)]*open/) // no section starts open
    expect(script).toContain("'#/session/'") // Open session is the session route the drill-in page has
    expect(html).toContain('data-look=web') // the mockup's look, the drill-in pages keep the terminal look
    expect(html).toContain('data-look=term')
    expect(html).toContain('STALE=180000') // the amber line after a few minutes
  })

  test(`web page ${TAG} the page stays read-only, with no fetch and no server, and text stays text`, () => {
    const evil = '</script><img src=x onerror=alert(1)> "q" & \u001b[31m'
    const html = boardHtml(data([sess('x-1', 'ended', 90, 'web-app', 'evil', { repo: { path: '/work/web-app', name: 'web-app' }, endedAt: NOON - 90 * 60_000, asks: [ask(1, evil, 120)] })]))
    expect(html).not.toContain('<img src=x')
    expect(html.split('</script>').length - 1).toBe(2) // the data block and the page script, and no more
    expect(dataOf(html).tasks[0].text).toBe('</script><img src=x onerror=alert(1)> "q" & [31m') // the escape character is gone, the rest is whole
    const page = html.replace(/<script type="application\/json" id="data">[\s\S]*?<\/script>/, '') // the markup, the style and the script: not the session's data
    expect(page).not.toMatch(/fetch\(|XMLHttpRequest|WebSocket|EventSource|sendBeacon|\ssrc=|<link|@import/)
    expect(page).not.toContain('innerHTML')
    expect(scriptOf(html)).toContain("h.indexOf('https://')===0") // an outside link is https only
  })

  test(`web page ${TAG} Keep, Close and a merged change take tasks away; the owner's seen marks reach the notes`, () => {
    const keys = (d: ReturnType<typeof data>) => d.tasks.map(t => `${t.key}:${t.status}`)
    expect(keys(data(taskTown(), { seen: new Set(), kept: new Set(['sup-1:1']), closed: new Set(['need-1:1']) }))).toEqual(expect.arrayContaining(['sup-1:1:in-progress']))
    expect(keys(data(taskTown(), { seen: new Set(), kept: new Set(), closed: new Set(['need-1:1']) }))).not.toContain('need-1:1:needs-you')
    const merged = { ...CHANGE, repoPath: '/work/web-app', milestone: MILESTONE_MD.replace('status: building', 'status: merged').replace('milestone/demo-1', 'milestone/agent-tracker-1') }
    expect(boardData(snapAt(taskTown()), [merged], NOON).tasks.some(t => t.key === 'prog-1:1')).toBe(false) // its branch is a merged change
    expect(boardData(snapAt(taskTown()), [], NOON).tasks.some(t => t.key === 'prog-1:1')).toBe(true)
    const notes = [{ id: 'n1', kind: 'know', text: 'a', at: NOON - 1000, seen: false }, { id: 'n2', kind: 'know', text: 'b', at: NOON - 2000, seen: false }]
    const town = taskTown().map(r => (r.sessionId === 'prog-1' ? ({ ...r, notes } as SessionRecord) : r))
    expect(data(town, { seen: new Set(['prog-1:n2']), kept: new Set(), closed: new Set() }).sessions.find(s => s.id === 'prog-1')!.notes.map(n => [n.id, n.seen])).toEqual([['n1', false], ['n2', true]])
  })

  test(`web page ${TAG} the sections that are not tasks come from the same data: running, done and ended today, pull requests`, () => {
    const d = data(paneTown())
    expect(d.sessions.filter(s => s.live && s.state === 'running').length).toBe(3)
    expect(d.repos.find(r => r.label === 'web-app')!.prs!.list.filter(p => p.checks === 'failing').length).toBe(2)
    expect(d.tasks).toEqual([]) // no ask, no task
    expect(d.counts).toEqual({ notDone: 0, needsYou: 0, alarm: false })
  })
})

const aloneOf = (): SessionRecord[] => [sess(SELF, 'running', 4, 'platform-tools-suite', 'build the band', { branch: 'main' })]

describe('/tracker web', () => {
  test(`web page ${TAG} writes board.html, opens it, and answers the path`, async ($, on) => {
    const o = opener(on)
    const w = withSnap(on, paneTown(), o)
    const r = await run($, 'web')
    expect(r).toEqual({ text: 'Board opened: ~/.claude/agent-tracker/board.html' })
    expect(w.writes).toEqual([`${DIR}/board.html`])
    expect(o.calls).toEqual([['open', `${DIR}/board.html`]])
    const d = dataOf(w.files.get(`${DIR}/board.html`)!)
    expect(d.sessions.length).toBe(paneTown().length) // every session of the last week, the ended ones too
  })

  test(`web page ${TAG} reads the change folders of the repos the sessions work in`, async ($, on) => {
    const w = withSnap(on, paneTown().map(r => (r.sessionId === SELF ? { ...r, repo: { path: '/work/platform-tools-suite', name: 'platform-tools-suite' } } : r)), opener(on))
    w.put('/work/platform-tools-suite/changes/2026-01-01-demo/milestone.md', MILESTONE_MD)
    w.put('/work/platform-tools-suite/changes/2026-01-01-demo/facts.md', FACTS)
    w.put('/work/platform-tools-suite/changes/2026-01-01-other/plan.md', 'no milestone here') // a changes folder alone is none
    await run($, 'web')
    const d = dataOf(w.files.get(`${DIR}/board.html`)!)
    expect(d.milestones.map((m: { slug: string }) => m.slug)).toEqual(['demo-1'])
    expect(d.milestones[0].facts.map((f: { id: string }) => f.id)).toEqual(['F1', 'F2', 'F3'])
    expect(w.writes.every(p => p === `${DIR}/board.html`)).toBe(true) // reads the repo, writes only the board
  })

  test(`web page ${TAG} says so when no browser opens, and the file is still written`, async ($, on) => {
    const w = withSnap(on, paneTown(), opener(on, 1))
    const r = await run($, 'web')
    expect(String((r as { text: string }).text)).toContain('no browser could be opened')
    expect(w.files.has(`${DIR}/board.html`)).toBe(true)
  })

  test(`web page ${TAG} the band's and the pane's words still reach their hooks`, async ($, on) => {
    const w = withSnap(on, paneTown(), opener(on))
    expect(await run($, 'compact')).toEqual({ text: 'Band switched to compact.' })
    expect(String(((await run($, 'nonsense')) as { text: string }).text)).toContain('Try /tracker')
    expect(w.files.has(`${DIR}/board.html`)).toBe(false) // nothing but `web` builds the page
  })
})

describe('the board rewrites', () => {
  const lease = (w: ReturnType<typeof world>, who: string) => {
    w.put(`${DIR}/poller.json`, { v: 1, sessionId: who, heartbeat: w.clock.now() })
    w.put(`${DIR}/agents.json`, { v: 1, readAt: w.clock.now(), agents: [] })
  }
  const boards = (w: ReturnType<typeof world>) => w.writes.filter(p => p === `${DIR}/board.html`).length
  const turn = ($: Engine) => $.turn.start({ turnId: 't1' } as never)
  const quiet = (on: On) => on('turn.start', (_, e) => ({ turnId: e.turnId }) as never) // the harness has no turn.start beneath the mod; register before the first call on $

  test(`web page ${TAG} only the session holding the poller lease rewrites it, every 10 seconds`, async ($, on) => {
    const w = world(on, { now: NOON, id: SELF })
    quiet(on)
    w.agents.json = '[]'
    w.put(`${DIR}/board.html`, 'old')
    await start($, w) // this session takes the lease: nobody holds a fresh one
    await turn($)
    expect(boards(w)).toBe(0)
    await w.clock.advance(10_000)
    await settle()
    expect(boards(w)).toBe(1)
    expect(w.files.get(`${DIR}/board.html`)).toContain('<title>')
    await w.clock.advance(10_000)
    await settle()
    expect(boards(w)).toBe(2)
    await w.clock.advance(5000)
    expect(boards(w)).toBe(2) // between two writes: none
  })

  test(`web page ${TAG} a session that does not hold the lease never rewrites it`, async ($, on) => {
    const w = world(on, { now: NOON, id: SELF })
    quiet(on)
    w.put(`${DIR}/board.html`, 'old')
    lease(w, 'someone-else')
    await start($, w)
    await turn($)
    for (let i = 0; i < 6; i++) {
      lease(w, 'someone-else') // the other keeps its lease fresh
      await w.clock.advance(5000)
    }
    await settle()
    expect(boards(w)).toBe(0)
    expect(w.files.get(`${DIR}/board.html`)).toBe('old')
  })

  test(`web page ${TAG} no board.html, no rewrite: a machine that never asked for the page never gets the file`, async ($, on) => {
    const w = world(on, { now: NOON, id: SELF })
    quiet(on)
    await start($, w)
    await turn($)
    await w.clock.advance(30_000)
    await settle()
    expect(boards(w)).toBe(0)
  })
})
