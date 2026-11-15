import { describe, expect, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'
import type { On } from 'claude-code'

import { CLEAR_WORDS, PANE_BUTTONS } from '../hooks/tracker/core'
import { AGENT_ROWS, CLEANUP, DEAD, DEAD_ROW, FOLDER, LISTED, dead, open, page, press } from './fixtures/ui'
import * as uiFixture from './fixtures/ui'
import { settle } from './fixtures/world'
import type { World } from './fixtures/world'

// What the tracker may write after an owner press, and nothing else. The source greps are `tests/test_git_cleanup_run.py`'s: this
// file cannot read the disk, so it holds the argument lists the tracker really runs. Row 3 adds `git worktree remove <path>`.
const BANNED = ['--force', '--force-remove-worktree', '--discard-unpushed', '-f', '-D']
const SHELLS = ['sh', 'bash', 'zsh', 'dash', 'fish', 'env']
const isBanned = (argv: readonly string[]) => argv.some(a => BANNED.includes(a)) || argv.join(' ').includes('branch -D') || (argv[0] === 'claude' && argv[1] === 'stop') || SHELLS.includes(argv[0] ?? '')
// The read, and the one write: `claude rm <that job id>`, the exact argument list.
const isAllowed = (argv: readonly string[], jobId: string) => argv.join(' ') === 'claude agents --json' || (argv.length === 3 && argv[0] === 'claude' && argv[1] === 'rm' && argv[2] === jobId)

const argvs = (w: World) => w.procs.map(p => p.argv)
const runs = async ($: Engine, on: On, setup: (w: World) => void = () => undefined) => {
  const h = await open($, on)
  setup(h.w)
  await press(h.ui, 'clear')
  await press(h.ui, 'confirm-clear')
  await settle()
  await h.ui.redraw()
  return h
}

describe('what the tracker writes after an owner press', () => {
  for (const mode of ['ok', 'fail', 'hang'] as const)
    test(`@F64 ${CLEANUP} none in any tracker argv when claude rm ${mode === 'ok' ? 'works' : mode === 'fail' ? 'fails' : 'hangs'}: no force, no discard, no branch deletion`, async ($, on) => {
      const { w, ui } = await runs($, on, w => (w.rm = { mode, stderr: 'no', drops: false }))
      expect(argvs(w).filter(isBanned)).toEqual([])
      expect(argvs(w).length).toBeGreaterThan(1)
      await ui.unmount()
    })

  test(`@F64 ${CLEANUP} the scan catches each banned argument`, () => {
    for (const bad of [['git', 'worktree', 'remove', '--force', 'x'], ['claude', 'rm', '-f', 'x'], ['git', 'branch', '-D', 'x'], ['git', 'worktree', 'remove', '-f', 'x'], ['git', 'push', '--discard-unpushed'], ['claude', 'stop', 'x'], ['sh', '-c', 'claude rm x'], ['git', 'worktree', 'remove', '--force-remove-worktree']]) expect(isBanned(bad)).toBe(true)
    expect(isBanned(['claude', 'rm', 'bg-dead'])).toBe(false)
  })

  test(`@F65 ${CLEANUP} no claude stop, no rm or removal with a pid or a live session: a pid at the press runs nothing but the read`, async ($, on) => {
    const running = await runs($, on, w => (w.agents.json = AGENT_ROWS([{ ...DEAD_ROW, pid: 4004 }])))
    expect(argvs(running.w)).toEqual([['claude', 'agents', '--json']])
    expect(running.w.writes).toEqual([])
    await running.ui.unmount()
  })

  test(`@F65 ${CLEANUP} no claude rm when no row in the read has a pid`, async ($, on) => {
    const none = await runs($, on, w => (w.agents.json = JSON.stringify([DEAD_ROW])))
    expect(argvs(none.w)).toEqual([['claude', 'agents', '--json']])
    await none.ui.unmount()
  })

  test(`@F65 ${CLEANUP} no claude rm when the read failed`, async ($, on) => {
    const failed = await runs($, on, w => (w.agents.json = null))
    expect(argvs(failed.w)).toEqual([['claude', 'agents', '--json']])
    await failed.ui.unmount()
  })

  test(`@F66 ${CLEANUP} each tracker write follows a press: opening, Cancel and leaving write and run nothing`, async ($, on) => {
    const { w, ui } = await open($, on)
    expect(argvs(w)).toEqual([])
    await press(ui, 'clear')
    expect(argvs(w)).toEqual([])
    await press(ui, 'cancel-clear')
    await press(ui, 'clear')
    await press(ui, 'crumb:0')
    expect(argvs(w)).toEqual([])
    expect(w.writes).toEqual([])
    await ui.unmount()
  })

  test(`@F66 ${CLEANUP} Clear session runs the read and the one rm, and writes only the owner's marks; Reopen tasks runs nothing`, async ($, on) => {
    const { w, ui } = await runs($, on)
    expect(argvs(w).every(a => isAllowed(a, 'bg-dead'))).toBe(true)
    expect(argvs(w)).toEqual([['claude', 'agents', '--json'], ['claude', 'rm', 'bg-dead']])
    expect(w.writes.every(p => p.endsWith('/agent-tracker/settings.json'))).toBe(true)
    const before = w.procs.length
    await press(ui, 'reopen')
    expect(w.procs.length).toBe(before)
    expect(w.writes.every(p => p.endsWith('/agent-tracker/settings.json'))).toBe(true)
    await ui.unmount()
  })

  for (const mode of ['ok', 'fail'] as const)
    test(`@F67 ${CLEANUP} no branch deletion, no shell when claude rm ${mode === 'ok' ? 'works' : 'fails'}: every argument list is one the allow-list knows`, async ($, on) => {
      const { w, ui } = await runs($, on, w => (w.rm = { mode, stderr: 'refused', drops: mode === 'ok' }))
      expect(argvs(w).filter(a => !isAllowed(a, 'bg-dead'))).toEqual([])
      expect(w.procs.every(p => (p.init?.timeoutMs ?? 0) > 0)).toBe(true) // a timeout on each, no stdin, no shell option
      expect(w.procs.every(p => Object.keys(p.init ?? {}).every(k => k === 'timeoutMs'))).toBe(true)
      await ui.unmount()
    })

  test(`@F68 ${CLEANUP} new words hold no path, internal name or URL`, async ($, on) => {
    const leak = /\/Users\/|\/home\/|[\w.+-]+@[\w-]+\.[\w.-]+|https?:\/\//
    const words = [...Object.values(CLEAR_WORDS).map(v => (typeof v === 'function' ? v('x', true) : v)), ...Object.values(PANE_BUTTONS)]
    expect(words.filter(w => leak.test(w))).toEqual([])
    expect(leak.test(JSON.stringify({ ...uiFixture, dead: dead(), DEAD, FOLDER, LISTED }))).toBe(false)
    const { ui } = await open($, on)
    expect(leak.test(await page(ui))).toBe(false)
    await ui.unmount()
    for (const s of ['/Users/someone/repo', '/home/someone', 'someone@example.com', 'https://example.com']) expect(leak.test(s)).toBe(true)
  })
})
