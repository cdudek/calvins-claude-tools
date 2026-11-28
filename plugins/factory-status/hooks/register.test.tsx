import type { On } from 'claude-code'
import { expect, test } from 'claude-code/testing'

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

// `claude plugin test` runs without a process: each hook stands for the engine.
function engine(on: On, opts: { script: boolean; line: string }) {
  const seen = { status: [] as (string | undefined)[], opened: 0, argvs: [] as string[][] }
  on('command.register', () => ({ value: { command: 'factory-status' } }))
  on('ui.open', () => {
    seen.opened++
    return { value: { isPlaced: true } }
  })
  on('ui.status', (_, e) => {
    seen.status.push(e.text)
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
    if (argv.includes('--line')) return out(opts.line)
    return out(BOARD)
  })
  return seen
}

test('the line is set from the script', async ($, on) => {
  const seen = engine(on, { script: true, line: LINE + '\n' })
  await $.session.start({ cwd: '/repo/sub', surface: 'terminal', isInteractive: true })
  expect(seen.status).toEqual([LINE])
})

test('only the bundled reader runs, isolated, never the repo script', async ($, on) => {
  const seen = engine(on, { script: true, line: LINE })
  await $.session.start({ cwd: '/repo/sub', surface: 'terminal', isInteractive: true })
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
  await $.session.start({ cwd: '/repo/sub', surface: 'terminal', isInteractive: true })
  const tests = seen.argvs.filter(a => a[0] === 'test').map(a => a[2])
  expect(tests).toEqual(['/repo/sub/.git', '/repo/.git', '/repo/.factory', '/repo/changes'])
})

test('an empty line clears the status', async ($, on) => {
  const seen = engine(on, { script: true, line: '' })
  await $.session.start({ cwd: '/repo', surface: 'terminal', isInteractive: true })
  expect(seen.status).toEqual([undefined])
})

test('a missing script does nothing', async ($, on) => {
  const seen = engine(on, { script: false, line: LINE })
  await $.session.start({ cwd: '/repo', surface: 'terminal', isInteractive: true })
  expect(seen.status).toEqual([])
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text' }))?.text).toBe('No factory run found in this repo.')
  await ui.unmount()
})

test('the command opens a pane that lists milestones and tasks', async ($, on) => {
  const seen = engine(on, { script: true, line: LINE })
  await $.session.start({ cwd: '/repo', surface: 'terminal', isInteractive: true })
  await $.command.run({
    command: 'factory-status',
    args: '',
    origin: { kind: 'composer' },
    presentation: { isFullscreen: false, columns: 80 },
  })
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
