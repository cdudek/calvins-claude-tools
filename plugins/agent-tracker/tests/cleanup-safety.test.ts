import { describe, expect, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'
import type { On } from 'claude-code'

import { CLEAR_WORDS, PANE_BUTTONS, WORKTREE_WORDS, gitArgv } from '../hooks/tracker/core'
import { AGENT_ROWS, CLEANUP, DEAD, DEAD_ROW, FOLDER, LISTED, UNLISTED, dead, open, page, press } from './fixtures/ui'
import * as uiFixture from './fixtures/ui'
import { MAIN, TREE, inTree, isWorktreeRead, openTree } from './fixtures/git'
import { settle } from './fixtures/world'
import type { World } from './fixtures/world'

// What the tracker may run, and nothing else. The source greps are `tests/test_git_cleanup_run.py`'s: this file cannot read the
// disk, so it holds the argument lists the tracker really runs. The reads are `claude agents --json` and the git and gh reads of the
// worktree check (fixtures/git.ts `isWorktreeRead`); the writes are `claude rm <job id>` and `git worktree remove <path>`, both after a press.
const BANNED = ['--force', '--force-remove-worktree', '--discard-unpushed', '-f', '-D']
const SHELLS = ['sh', 'bash', 'zsh', 'dash', 'fish', 'env']
const isBanned = (argv: readonly string[]) => argv.some(a => BANNED.includes(a)) || argv.join(' ').includes('branch -D') || (argv[0] === 'claude' && argv[1] === 'stop') || SHELLS.includes(argv[0] ?? '')
// The reads, and the two writes by their exact argument lists: `claude rm <that job id>`, and `git worktree remove <that path>` with no flag.
const isWrite = (argv: readonly string[]) => (argv[0] === 'claude' && argv[1] === 'rm') || (argv[0] === 'git' && argv.includes('worktree') && argv.includes('remove'))
const isAllowed = (argv: readonly string[], jobId: string, path = TREE) =>
  argv.join(' ') === 'claude agents --json' ||
  isWorktreeRead(argv) ||
  (argv.length === 3 && argv[0] === 'claude' && argv[1] === 'rm' && argv[2] === jobId) ||
  argv.join('\0') === gitArgv('worktree', 'remove', path).join('\0')

const argvs = (w: World) => w.procs.map(p => p.argv)
const claudeArgvs = (w: World) => argvs(w).filter(a => a[0] === 'claude')
const writesOf = (w: World) => argvs(w).filter(isWrite)
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

  for (const [name, setup, press2] of [
    ['removes', () => undefined, 'remove-worktree'],
    ['keeps', () => undefined, 'keep-worktree'],
    ['is refused by git', (r: { refuse: string | null }) => (r.refuse = 'fatal: locked'), 'remove-worktree'],
  ] as const)
    test(`@F64 ${CLEANUP} none in any tracker argv when the owner ${name} the worktree: no force, no discard, no branch deletion`, async ($, on) => {
      const h = await openTree($, on, { session: inTree({ asks: [] }), extra: { listing: { ...UNLISTED } }, row: 'command', setup: (_, r) => setup(r) })
      await press(h.ui, 'clear')
      await press(h.ui, press2)
      await settle()
      await h.ui.redraw()
      expect(argvs(h.w).filter(isBanned)).toEqual([])
      expect(argvs(h.w).filter(a => !isAllowed(a, 'bg-dead'))).toEqual([])
      expect(argvs(h.w).some(a => a.includes('branch'))).toBe(false)
      expect(writesOf(h.w).length).toBe(press2 === 'keep-worktree' ? 0 : 1)
      await h.ui.unmount()
    })

  const SOURCES = ['claude', 'git', 'gh', 'bd', 'tail']
  test(`@F69 ${CLEANUP} every process Clear session runs is claude, git, gh, bd or tail`, async ($, on) => {
    const { w, ui } = await runs($, on)
    expect(argvs(w).length).toBeGreaterThan(1)
    expect(argvs(w).filter(a => !SOURCES.includes(a[0] ?? ''))).toEqual([])
    await ui.unmount()
  })

  test(`@F69 ${CLEANUP} every process Remove worktree runs is claude, git, gh, bd or tail`, async ($, on) => {
    const h = await openTree($, on, { session: inTree({ asks: [] }), extra: { listing: { ...UNLISTED } }, row: 'command' })
    await press(h.ui, 'clear')
    await press(h.ui, 'remove-worktree')
    await settle()
    expect(argvs(h.w).length).toBeGreaterThan(1)
    expect(argvs(h.w).filter(a => !SOURCES.includes(a[0] ?? ''))).toEqual([])
    await h.ui.unmount()
  })

  test(`@F64 ${CLEANUP} the scan catches each banned argument`, () => {
    for (const bad of [['git', 'worktree', 'remove', '--force', 'x'], ['claude', 'rm', '-f', 'x'], ['git', 'branch', '-D', 'x'], ['git', 'worktree', 'remove', '-f', 'x'], ['git', 'push', '--discard-unpushed'], ['claude', 'stop', 'x'], ['sh', '-c', 'claude rm x'], ['git', 'worktree', 'remove', '--force-remove-worktree']]) expect(isBanned(bad)).toBe(true)
    expect(isBanned(['claude', 'rm', 'bg-dead'])).toBe(false)
    expect(isBanned(gitArgv('worktree', 'remove', TREE))).toBe(false)
    for (const bad of [[...gitArgv('worktree', 'remove'), '--force', TREE], [...gitArgv('worktree', 'remove'), '-f', TREE], gitArgv('branch', '-D', 'x')]) expect(isBanned(bad)).toBe(true)
    // The allow-list takes the exact removal and no other shape of it.
    expect(isAllowed(gitArgv('worktree', 'remove', TREE), 'bg-dead')).toBe(true)
    for (const other of [[...gitArgv('worktree', 'remove'), '--force', TREE], gitArgv('worktree', 'remove', `${TREE}/x`), gitArgv('worktree', 'prune'), gitArgv('branch', '-d', 'x'), gitArgv('push'), ['gh', 'pr', 'merge'], ['claude', 'rm', 'other-id']]) expect(isAllowed(other, 'bg-dead')).toBe(false)
  })

  test(`@F65 ${CLEANUP} no claude stop, no rm or removal with a pid or a live session: a pid at the press runs nothing but the read`, async ($, on) => {
    const running = await runs($, on, w => (w.agents.json = AGENT_ROWS([{ ...DEAD_ROW, pid: 4004 }])))
    expect(claudeArgvs(running.w)).toEqual([['claude', 'agents', '--json']])
    expect(writesOf(running.w)).toEqual([])
    expect(running.w.writes).toEqual([])
    await running.ui.unmount()
  })

  test(`@F65 ${CLEANUP} no claude rm when no row in the read has a pid`, async ($, on) => {
    const none = await runs($, on, w => (w.agents.json = JSON.stringify([DEAD_ROW])))
    expect(claudeArgvs(none.w)).toEqual([['claude', 'agents', '--json']])
    expect(writesOf(none.w)).toEqual([])
    await none.ui.unmount()
  })

  test(`@F65 ${CLEANUP} no claude rm when the read failed`, async ($, on) => {
    const failed = await runs($, on, w => (w.agents.json = null))
    expect(claudeArgvs(failed.w)).toEqual([['claude', 'agents', '--json']])
    expect(writesOf(failed.w)).toEqual([])
    await failed.ui.unmount()
  })

  test(`@F66 ${CLEANUP} each tracker write follows a press: opening, Cancel and leaving write and run nothing but git reads`, async ($, on) => {
    const { w, ui } = await open($, on)
    expect(argvs(w).filter(a => !isWorktreeRead(a))).toEqual([])
    await press(ui, 'clear')
    expect(argvs(w).filter(a => !isWorktreeRead(a))).toEqual([])
    await press(ui, 'cancel-clear')
    await press(ui, 'clear')
    await press(ui, 'crumb:0')
    expect(argvs(w).filter(a => !isWorktreeRead(a))).toEqual([])
    expect(writesOf(w)).toEqual([])
    expect(w.writes).toEqual([])
    await ui.unmount()
  })

  test(`@F66 ${CLEANUP} a removable worktree is removed only by Remove worktree: drawing the page, Clear, Keep and leaving write nothing`, async ($, on) => {
    const h = await openTree($, on, { session: inTree({ asks: [] }), extra: { listing: { ...UNLISTED } }, row: 'command' })
    expect(writesOf(h.w)).toEqual([])
    await press(h.ui, 'clear') // opens the offer: not a write
    expect(writesOf(h.w)).toEqual([])
    await press(h.ui, 'keep-worktree')
    await press(h.ui, 'clear')
    await press(h.ui, 'crumb:0')
    expect(writesOf(h.w)).toEqual([])
    expect(h.repo.trees.map(t => t.path)).toContain(TREE)
    await h.ui.unmount()
  })

  test(`@F66 ${CLEANUP} Remove worktree runs git worktree remove once, from the main checkout, and nothing else writes`, async ($, on) => {
    const owner = await openTree($, on, { session: inTree({ asks: [] }), extra: { listing: { ...UNLISTED } }, row: 'command' })
    await press(owner.ui, 'clear')
    await press(owner.ui, 'remove-worktree')
    await settle()
    expect(writesOf(owner.w)).toEqual([gitArgv('worktree', 'remove', TREE)])
    expect(owner.w.procs.find(p => isWrite(p.argv))!.cwd).toBe(MAIN)
    await owner.ui.unmount()
  })

  test(`@F66 ${CLEANUP} Clear session runs the read and the one rm, and writes only the owner's marks; Reopen tasks runs nothing`, async ($, on) => {
    const { w, ui } = await runs($, on)
    expect(argvs(w).every(a => isAllowed(a, 'bg-dead'))).toBe(true)
    expect(claudeArgvs(w)).toEqual([['claude', 'agents', '--json'], ['claude', 'rm', 'bg-dead']])
    expect(w.writes.every(p => p.endsWith('/agent-tracker/settings.json'))).toBe(true)
    const before = w.procs.length
    await press(ui, 'reopen')
    expect(w.procs.length).toBe(before)
    expect(writesOf(w)).toEqual([['claude', 'rm', 'bg-dead']])
    expect(w.writes.every(p => p.endsWith('/agent-tracker/settings.json'))).toBe(true)
    await ui.unmount()
  })

  for (const mode of ['ok', 'fail'] as const)
    test(`@F67 ${CLEANUP} no branch deletion, no shell when claude rm ${mode === 'ok' ? 'works' : 'fails'}: every argument list is one the allow-list knows`, async ($, on) => {
      const { w, ui } = await runs($, on, w => (w.rm = { mode, stderr: 'refused', drops: mode === 'ok' }))
      expect(argvs(w).filter(a => !isAllowed(a, 'bg-dead'))).toEqual([])
      expect(w.procs.every(p => Number(p.init?.timeoutMs ?? 0) > 0)).toBe(true) // a timeout on each, no stdin, no shell option
      expect(w.procs.every(p => Object.keys(p.init ?? {}).every(k => k === 'timeoutMs' || k === 'cwd'))).toBe(true)
      await ui.unmount()
    })

  test(`@F68 ${CLEANUP} new words hold no path, internal name or URL`, async ($, on) => {
    const leak = /\/Users\/|\/home\/|[\w.+-]+@[\w-]+\.[\w.-]+|https?:\/\//
    const wt = [WORKTREE_WORDS.line('x', 'y'), WORKTREE_WORDS.safe('x', 'branch'), WORKTREE_WORDS.ignored('.env'), WORKTREE_WORDS.ask('y'), WORKTREE_WORDS.removed('x', 'y'), WORKTREE_WORDS.claudeRemoved('x'), WORKTREE_WORDS.changed('r'), WORKTREE_WORDS.gitFailed(': r'), WORKTREE_WORDS.stays('x', 'r', '')]
    const words: string[] = [...wt, ...Object.values(CLEAR_WORDS).flatMap(v => (typeof v === 'string' ? [v as string] : [])), CLEAR_WORDS.madeWorktree('x'), CLEAR_WORDS.closed(2), CLEAR_WORDS.reopened(1), CLEAR_WORDS.failed(': r'), CLEAR_WORDS.partly(': r', true), CLEAR_WORDS.partly('', false), ...Object.values(PANE_BUTTONS)]
    expect(words.filter(w => leak.test(w))).toEqual([])
    expect(leak.test(JSON.stringify({ ...uiFixture, dead: dead(), DEAD, FOLDER, LISTED }))).toBe(false)
    const { ui } = await open($, on)
    expect(leak.test(await page(ui))).toBe(false)
    await ui.unmount()
    for (const s of ['/Users/someone/repo', '/home/someone', 'someone@example.com', 'https://example.com']) expect(leak.test(s)).toBe(true)
  })
})
