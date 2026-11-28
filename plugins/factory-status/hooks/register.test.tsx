import type { On } from 'claude-code'
import { expect, mock, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'

import { ancestors, parseBoard, parseLine } from './status'

const LINE = 'M3a (4/20) · T2/6 building · gap 0/3 · 38m'
const BOARD = JSON.stringify({
  generated: '2026-11-28T19:00:00Z',
  warnings: [],
  projects: [
    {
      repo: '/repo',
      name: 'repo',
      changes: [
        { slug: 'old', title: 'Old', column: 'done', current: null, milestones: [], needs: null, prs: [] },
        {
          slug: 'board',
          title: 'The board',
          column: 'needs-you',
          approved: true,
          milestones: [
            { id: 'M1', state: 'shipped', tasks: [] },
            {
              id: 'M2',
              state: 'building',
              tasks: [{ id: 'T1', state: 'done' }, { id: 'T2', state: 'building' }],
            },
          ],
          current: { milestone: 'M2', task: 'T2', since: '2026-11-28T18:00:00Z' },
          needs: { kind: 'blocked', text: 'pick a color', where: 'changes/board/plan.md' },
          prs: [],
        },
      ],
    },
  ],
})

const PANE = {
  plugin: 'factory-status',
  component: 'Pane',
  requestId: 'factory-status',
  props: {
    title: 'Factory',
    isFocused: false,
    bodyColumns: 60,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 20 },
    view: {},
  },
} as const

const BAND = {
  plugin: 'factory-status',
  component: 'AbovePrompt',
  props: { hasSurvey: false, isWorking: false, maxRows: 12, bodyColumns: 100, scroll: { offset: 0, bodyRows: 12 }, view: {} },
} as const

type Opts = { script: boolean; line: string; board?: string; up?: boolean[] }

// `claude plugin test` runs without a process: each hook stands for the engine.
function engine(on: On, opts: Opts) {
  mock.store(on)
  const seen = { status: 0, opened: 0, argvs: [] as string[][], toasts: [] as string[] }
  const probes = [...(opts.up ?? [true])]
  on('command.register', () => ({ value: { command: 'factory-status' } }))
  on('ui.open', () => {
    seen.opened++
    return { value: { isPlaced: true } }
  })
  on('ui.status', () => {
    seen.status++
    return { value: undefined }
  })
  on('ui.toast', (_, e) => {
    seen.toasts.push(e.text)
    return { value: undefined }
  })
  on('clock.every', () => ({ value: undefined }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('process.run', (_, e) => {
    const argv = e.argv
    seen.argvs.push([...argv])
    const out = (stdout: string, exitCode = 0) => ({
      value: { exitCode, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false },
    })
    // a git root at /repo with a changes/ folder; /repo/sub has none
    if (argv[0] === 'test') return out('', opts.script && ['/repo/.git', '/repo/changes'].includes(argv[2] ?? '') ? 0 : 1)
    if (argv[0] === 'curl') return argv.includes('--retry') ? out('200') : probes.length > 1 ? (probes.shift() ? out('200') : out('000', 7)) : probes[0] ? out('200') : out('000', 7)
    if (argv[0] === 'uname') return out('Darwin\n')
    if (argv.includes('--line')) return out(opts.line)
    if (argv.includes('--json')) return out(opts.board ?? BOARD)
    return out('')
  })
  return seen
}

const start = ($: Engine, cwd = '/repo') => $.session.start({ cwd, surface: 'terminal', isInteractive: true })
const mountBand = ($: Engine) => $.ui.mount({ ...BAND, surface: 'terminal' } as never)
const texts = async (ui: { findAll: (q: object) => Promise<{ text?: string }[]> }) => (await ui.findAll({ type: 'Text' })).map(t => t.text ?? '').join('')
const run = ($: Engine, args: string) =>
  $.command.run({ command: 'factory-status', args, origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 80 } })

test('the band shows needs-you first, the line and the three buttons; the status line is never set', async ($, on) => {
  const seen = engine(on, { script: true, line: LINE + '\n' })
  await start($, '/repo/sub')
  const ui = await mountBand($)
  const row = await texts(ui)
  expect(row).toMatch(/^factory\s+needs you: pick a color\s+M3a \(4\/20\)/)
  for (const key of ['pane', 'board', 'hide']) expect(await ui.find({ key })).toBeDefined()
  expect(seen.status).toBe(0)
  await ui.unmount()
})

test('the band shows the line alone when nothing needs you, and nothing when no run is active', async ($, on) => {
  const quiet = JSON.stringify({ projects: [{ changes: [{ slug: 'x', column: 'building', milestones: [], current: null, needs: null }] }] })
  engine(on, { script: true, line: LINE, board: quiet })
  await start($)
  const ui = await mountBand($)
  const row = await texts(ui)
  expect(row).toContain(`factory  ${LINE}`)
  expect(row).not.toContain('needs you')
  await ui.unmount()
})

test('no band without a run, outside a factory repo, or when hidden', async ($, on) => {
  engine(on, { script: false, line: LINE })
  await start($)
  const ui = await mountBand($)
  expect(await ui.find({ key: 'board' })).toBeUndefined()
  await ui.unmount()
})

test('[–] hides the band and /factory-status band on brings it back', async ($, on) => {
  const seen = engine(on, { script: true, line: LINE })
  await start($)
  const ui = await mountBand($)
  await ui.press({ key: 'hide' })
  expect(seen.toasts.at(-1)).toBe('Band hidden. /factory-status band on shows it again.')
  await ui.redraw()
  expect(await ui.find({ key: 'board' })).toBeUndefined()
  expect((await run($, 'band on')).text).toBe('Band shown.')
  await ui.redraw()
  expect(await ui.find({ key: 'board' })).toBeDefined()
  await ui.unmount()
})

test('[pane] opens the pane', async ($, on) => {
  const seen = engine(on, { script: true, line: LINE })
  await start($)
  const ui = await mountBand($)
  await ui.press({ key: 'pane' })
  expect(seen.opened).toBe(1)
  await ui.unmount()
})

test('[board] opens the browser when the board is up, without installing', async ($, on) => {
  const seen = engine(on, { script: true, line: LINE, up: [true] })
  await start($)
  const ui = await mountBand($)
  await ui.press({ key: 'board' })
  expect(seen.argvs.some(a => a.includes('install'))).toBe(false)
  expect(seen.argvs.some(a => a[0] === 'open' && a[1] === 'http://127.0.0.1:8765/')).toBe(true)
  expect(seen.toasts.at(-1)).toBe('Board opened at http://127.0.0.1:8765')
  await ui.unmount()
})

test('/factory-status web installs the bundled board when down, waits, then opens it', async ($, on) => {
  const seen = engine(on, { script: true, line: LINE, up: [false, true] })
  await start($)
  const r = await run($, 'web')
  const install = seen.argvs.find(a => a.includes('install'))
  expect(install?.slice(0, 2)).toEqual(['python3', '-I'])
  expect(install?.[2]).toMatch(/\/bin\/factory-board\.py$/)
  expect(seen.argvs.some(a => a[0] === 'open')).toBe(true)
  expect(r.text).toBe('Board opened at http://127.0.0.1:8765')
})

test('the pane says so when no change is found', async ($, on) => {
  const seen = engine(on, { script: false, line: LINE })
  await start($)
  expect(seen.status).toBe(0)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text' }))?.text).toBe('No factory change in this repo.')
  await ui.unmount()
})

test('only the bundled reader runs, isolated, never the repo script', async ($, on) => {
  const seen = engine(on, { script: true, line: LINE })
  await start($, '/repo/sub')
  const runs = seen.argvs.filter(a => a[0] === 'python3')
  expect(runs.length).toBe(2)
  for (const a of runs) {
    expect(a[1]).toBe('-I')
    expect(a[2]).toMatch(/\/bin\/factory-status\.py$/)
    expect(a[2]).not.toMatch(/^\/repo/)
    expect(a.join(' ')).not.toContain('.factory')
  }
})

test('the root search stops at the git root and runs nothing from the repo', async ($, on) => {
  const seen = engine(on, { script: true, line: LINE })
  await start($, '/repo/sub')
  const tests = seen.argvs.filter(a => a[0] === 'test').map(a => a[2])
  expect(tests).toEqual(['/repo/sub/.git', '/repo/.git', '/repo/.factory', '/repo/changes'])
})

test('the command opens a pane that lists milestones and tasks', async ($, on) => {
  const seen = engine(on, { script: true, line: LINE })
  await start($)
  await run($, '')
  expect(seen.opened).toBe(1)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /Needs you/ }))?.text).toBe('Needs you: pick a color (changes/board/plan.md)')
  expect((await ui.find({ type: 'Text', text: /^T2/ }))?.text).toBe('T2 building')
  await ui.unmount()
})

test('pure parsing: ancestors, line, board', () => {
  expect(ancestors('/a/b')).toEqual(['/a/b', '/a', '/'])
  expect(parseLine('\n' + LINE + '\n')).toBe(LINE)
  expect(parseLine('')).toBe('')
  const b = parseBoard(BOARD)
  expect(b?.change).toBe('board')
  expect(b?.tasks.map(t => t.id)).toEqual(['T1', 'T2'])
  expect(b?.needs).toBe('pick a color')
  expect(b?.column).toBe('needs-you')
  expect(b?.milestones.map(m => m.id)).toEqual(['M1', 'M2'])
  expect(parseBoard('not json')).toBe(null)
})
