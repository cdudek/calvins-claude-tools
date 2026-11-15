import { describe, expect, test } from 'claude-code/testing'

import { WORKTREE_WORDS, conditions, failedOf, gitArgv, ignoredOf, ignoredWords, liveFolders, worktreeLabel } from '../hooks/tracker/core'
import type { Facts } from '../hooks/tracker/core'
import { frame, clipped } from './fixtures/frame'
import type { Node } from './fixtures/frame'
import { sess } from './fixtures/pane'
import { ask } from './fixtures/tasks'
import { BRANCH, MAIN, TREE, inTree, isWorktreeRead, openTree } from './fixtures/git'
import type { Repo } from './fixtures/git'
import { AGENT_ROWS, CLEANUP, DEAD_ROW, LISTED, THIS, UNLISTED, focused, keys, page, press } from './fixtures/ui'
import { settle } from './fixtures/world'
import type { World } from './fixtures/world'

// The worktree on the Session page: the five conditions of F35, the offer, Remove and Keep. The git reads and the one write run
// against a made-up repository (fixtures/git.ts). The case names linked, clean, pushed, merged and unused are the ones the
// script's tests use for the same five conditions (tests/test_git_cleanup_run.py, class FiveConditions): a drift shows.
// A test opens one page: the world registers its hooks once.
const facts = (over: Partial<Facts> = {}): Facts => ({ path: TREE, main: MAIN, linked: true, branch: BRANCH, status: [], unpushed: 0, inDefault: true, pr: null, live: [], ...over })
const removes = (w: World) => w.procs.filter(p => p.argv.includes('remove'))
const OFFER = 'Clear offers to remove it.'
// Only the worktree is left to clear: the session is not in Claude Code's list and has no open task.
const ONLY_TREE = { session: inTree({ asks: [] }), extra: { listing: { ...UNLISTED } }, row: 'command' } as const
const press2 = async (ui: Parameters<typeof press>[0], ...ks: string[]) => {
  for (const k of ks) await press(ui, k)
}
const settled = async (ui: Parameters<typeof press>[0]) => {
  await settle()
  await ui.redraw()
}

describe('the five conditions of F35', () => {
  test(`@F35 ${CLEANUP} linked: the first entry of the list is the main checkout, any other is linked`, async ($, on) => {
    const linked = await openTree($, on)
    expect(await page(linked.ui)).toContain('worktree login · fix-login')
    await linked.ui.unmount()
    expect(conditions(facts()).linked).toBe(true)
    expect(conditions(facts({ linked: false })).linked).toBe(false)
    expect(failedOf(facts({ linked: false }))).toBe('linked')
  })

  test(`@F35 ${CLEANUP} linked: a session in the main checkout has no worktree line and no offer`, async ($, on) => {
    const main = await openTree($, on, { session: inTree({ cwd: MAIN }) })
    expect(await page(main.ui)).not.toMatch(/orktree login/)
    expect(await page(main.ui)).not.toContain('Clear offers')
    expect(main.w.procs.filter(p => p.argv.includes('status'))).toEqual([]) // nothing else is read for the main checkout
    await main.ui.unmount()
  })

  test(`@F35 ${CLEANUP} clean: a modified, staged or untracked file fails; an ignored one does not`, () => {
    for (const bad of [' M src/a.ts', 'M  src/a.ts', 'A  src/new.ts', '?? notes.txt', 'D  gone.ts']) expect([bad, conditions(facts({ status: [bad] })).clean]).toEqual([bad, false])
    expect(conditions(facts({ status: ['!! .env', '!! build/'] })).clean).toBe(true)
    expect(conditions(facts({ status: ['!! .env', '?? notes.txt'] })).clean).toBe(false)
    expect(failedOf(facts({ status: [' M a'] }))).toBe('clean')
  })

  test(`@F35 ${CLEANUP} pushed: a commit on no remote fails, and so does a count that could not be read`, () => {
    expect(conditions(facts({ unpushed: 0 })).pushed).toBe(true)
    expect(conditions(facts({ unpushed: 1 })).pushed).toBe(false)
    expect(conditions(facts({ unpushed: null })).pushed).toBe(false)
    expect(failedOf(facts({ unpushed: 3 }))).toBe('pushed')
  })

  test(`@F35 ${CLEANUP} merged: in the default branch, or its PR merged or closed; an open PR, none, or no answer fails`, () => {
    expect(conditions(facts({ inDefault: true })).merged).toBe(true)
    for (const pr of ['merged', 'closed'] as const) expect(conditions(facts({ inDefault: false, pr })).merged).toBe(true)
    for (const pr of ['open', 'none', null] as const) expect([pr, conditions(facts({ inDefault: false, pr })).merged]).toEqual([pr, false])
    expect(failedOf(facts({ inDefault: false, pr: 'open' }))).toBe('merged')
  })

  test(`@F35 ${CLEANUP} unused: a live row at the worktree or under it fails; a sibling folder does not; an unread list fails`, () => {
    expect(conditions(facts({ live: [] })).unused).toBe(true)
    expect(conditions(facts({ live: [TREE] })).unused).toBe(false)
    expect(conditions(facts({ live: [`${TREE}/src/deep`] })).unused).toBe(false) // a session in a subfolder is using it
    expect(conditions(facts({ live: [`${TREE}-other`, MAIN] })).unused).toBe(true)
    expect(conditions(facts({ live: null })).unused).toBe(false)
    expect(failedOf(facts({ live: [TREE] }))).toBe('unused')
  })

  test(`@F35 ${CLEANUP} unused: a read with no pid counts every listed row as live, as the script does`, () => {
    const rows = [{ sessionId: 'a', cwd: TREE }, { sessionId: 'b', cwd: '/work/docs-site' }, { sessionId: 'c', cwd: '/work/not-listed' }]
    expect(liveFolders(rows, { a: { id: 'x', pid: 1 }, b: { id: 'y' } })).toEqual([TREE]) // only a has a process
    expect(liveFolders(rows, { a: { id: 'x' }, b: { id: 'y' } })).toEqual([TREE, '/work/docs-site']) // no pid anywhere: every listed row
    expect(liveFolders(rows, undefined)).toBeNull() // no read yet: not known
  })

  test(`@F35 ${CLEANUP} the first failed condition, in order linked, clean, pushed, merged, unused, is the one named`, () => {
    expect(failedOf(facts({ status: [' M a'], unpushed: 2, inDefault: false, pr: 'none', live: [TREE] }))).toBe('clean')
    expect(failedOf(facts({ unpushed: 2, inDefault: false, pr: 'none', live: [TREE] }))).toBe('pushed')
    expect(failedOf(facts({ inDefault: false, pr: 'none', live: [TREE] }))).toBe('merged')
    expect(failedOf(facts({ live: [TREE] }))).toBe('unused')
    expect(failedOf(facts())).toBeNull()
  })

  test(`@F35 ${CLEANUP} unused: a session in a subfolder of the worktree is in that worktree, and its own live row blocks it`, async ($, on) => {
    const h = await openTree($, on, { session: inTree({ cwd: `${TREE}/src/deep` }) })
    expect(await page(h.ui)).toContain('worktree login · fix-login')
    await h.ui.unmount()
  })
})

describe('the worktree line and why it stays', () => {
  test(`@F36 ${CLEANUP} the worktree line shows label and branch, never a path, and says Clear offers to remove it`, async ($, on) => {
    const h = await openTree($, on)
    const all = await page(h.ui)
    expect(all).toContain('worktree login · fix-login')
    expect(all).toContain(OFFER)
    expect(all).not.toMatch(/\/work\/|\.worktrees/)
    await h.ui.unmount()
  })

  test(`@F36 ${CLEANUP} a worktree that fails a condition adds no offer and still shows no path`, async ($, on) => {
    const h = await openTree($, on, { repo: { status: { [TREE]: [' M a'] } } })
    const all = await page(h.ui)
    expect(all).not.toContain(OFFER)
    expect(all).not.toMatch(/\/work\/|\.worktrees/)
    await h.ui.unmount()
  })

  test(`@F36 ${CLEANUP} one helper makes the label for the Session and the Repo page`, () => {
    expect(worktreeLabel(TREE, MAIN)).toBe('login')
    expect(worktreeLabel(MAIN, MAIN)).toBe('main checkout')
    expect(worktreeLabel('/elsewhere/other-tree', MAIN)).toBe('other-tree')
    expect(worktreeLabel(`${MAIN}/deep/folder`, MAIN)).toBe('deep/folder')
  })

  const other = sess('other-1', 'running', 3, 'web-app', 'other work', { cwd: `${TREE}/src` })
  const cases: [string, Partial<Repo> | undefined, Parameters<typeof openTree>[2], string][] = [
    ['clean', { status: { [TREE]: [' M src/a.ts'] } }, undefined, 'Worktree login stays: it has uncommitted changes. Commit or stash them in a terminal.'],
    ['pushed', { unpushed: { [TREE]: 2 } }, undefined, 'Worktree login stays: it has commits that are not pushed.'],
    ['merged', { ancestor: { [TREE]: false } }, undefined, 'Worktree login stays: its branch is not merged.'],
    ['unused', undefined, { extra: { listing: { ...LISTED, 'other-1': { id: 'bg-o', pid: 5005 } }, sessions: [THIS, inTree(), other] } }, 'Worktree login stays: another session is using it.'],
    ['clean first of two', { status: { [TREE]: ['?? x'] }, unpushed: { [TREE]: 4 } }, undefined, 'Worktree login stays: it has uncommitted changes. Commit or stash them in a terminal.'],
  ]
  for (const [name, repo, more, expected] of cases)
    test(`@F37 ${CLEANUP} the first failed condition is named with its next step: ${name}`, async ($, on) => {
      const h = await openTree($, on, { ...(repo === undefined ? {} : { repo }), ...(more ?? {}) })
      expect(await page(h.ui)).toContain(expected)
      expect(await keys(h.ui)).not.toContain('keep-worktree')
      expect(await page(h.ui)).not.toContain(OFFER)
      await h.ui.unmount()
    })

  test(`@F37 ${CLEANUP} Clear is not drawn for a worktree that stays when nothing else is left`, async ($, on) => {
    const h = await openTree($, on, { ...ONLY_TREE, repo: { ancestor: { [TREE]: false } } })
    expect(await page(h.ui)).toContain("Nothing to clear: it is not in Claude Code's list and has no open tasks.")
    expect(await keys(h.ui)).not.toContain('clear')
    await h.ui.unmount()
  })
})

describe('gh missing and the PR route', () => {
  test(`@F38 ${CLEANUP} no gh judges condition 4 by the branch only: an unmerged branch stays`, async ($, on) => {
    const h = await openTree($, on, { repo: { ancestor: { [TREE]: false } }, setup: w => (w.gh.missing = true) })
    expect(await page(h.ui)).toContain('Worktree login stays: its branch is not merged.')
    expect(h.w.procs.filter(p => p.argv[0] === 'gh').length).toBeGreaterThan(0) // it asked; the answer was no gh
    await h.ui.unmount()
  })

  test(`@F38 ${CLEANUP} no gh: a branch merged into the default branch needs no gh`, async ($, on) => {
    const h = await openTree($, on, { setup: w => (w.gh.missing = true) })
    expect(await page(h.ui)).toContain(OFFER)
    expect(h.w.procs.filter(p => p.argv[0] === 'gh')).toEqual([])
    await h.ui.unmount()
  })

  test(`@F38 ${CLEANUP} gh signed out is no answer either: the branch alone decides`, async ($, on) => {
    const h = await openTree($, on, { repo: { ancestor: { [TREE]: false } }, setup: w => (w.gh.heads = null) })
    expect(await page(h.ui)).toContain('Worktree login stays: its branch is not merged.')
    await h.ui.unmount()
  })

  for (const [states, offered] of [[['MERGED'], true], [['CLOSED'], true], [['MERGED', 'OPEN'], false], [['OPEN'], false], [[], false]] as [string[], boolean][])
    test(`@F38 ${CLEANUP} a PR that is ${states.join(' and ') || 'absent'} ${offered ? 'clears' : 'does not clear'} an unmerged branch`, async ($, on) => {
      const h = await openTree($, on, { repo: { ancestor: { [TREE]: false } }, setup: w => (w.gh.heads = { [BRANCH]: states }) })
      expect((await page(h.ui)).includes(OFFER)).toBe(offered)
      await h.ui.unmount()
    })

  const defaults: [string, Partial<Repo>, string[] | null, boolean][] = [
    ['main when origin HEAD is not set', { head: null, refs: ['refs/remotes/origin/main'] }, null, true],
    ['then master', { head: null, refs: ['refs/heads/master'] }, null, true],
    ['none: the PR alone, and there is none', { head: null, refs: [] }, null, false],
    ['none: the PR alone, and it is merged', { head: null, refs: [] }, ['MERGED'], true],
  ]
  for (const [name, repo, states, offered] of defaults)
    test(`@F35 ${CLEANUP} merged: the default branch is origin HEAD, then main, then master: ${name}`, async ($, on) => {
      const h = await openTree($, on, { repo, setup: w => (w.gh.heads = states === null ? {} : { [BRANCH]: states }) })
      expect((await page(h.ui)).includes(OFFER)).toBe(offered)
      await h.ui.unmount()
    })
})

describe('the offer', () => {
  test(`@F39 ${CLEANUP} the offer draws its lines and buttons when only the worktree is left (Clear opens it, no confirm)`, async ($, on) => {
    const h = await openTree($, on, ONLY_TREE)
    expect(await page(h.ui)).toContain('Clear offers to remove the worktree below.')
    await press(h.ui, 'clear')
    const all = await page(h.ui)
    expect(all).not.toContain('Clear this session?') // F21: no confirm before the offer
    expect(all).toContain('Worktree login is clean, pushed and merged.')
    expect(all).toContain('Remove it? The branch fix-login stays, so you can make it again.')
    expect(all).not.toContain('These ignored files')
    expect(await keys(h.ui)).toEqual(expect.arrayContaining(['remove-worktree', 'keep-worktree']))
    const buttons = await h.ui.findAll({ type: 'Button' })
    expect(buttons.filter(b => ['remove-worktree', 'keep-worktree'].includes(String(b.props.key))).map(b => [b.props.label, b.props.plain])).toEqual([['Remove worktree', true], ['Keep worktree', true]])
    expect(await keys(h.ui)).not.toContain('clear') // the offer is its own confirm
    expect(removes(h.w)).toEqual([]) // nothing is removed by opening it
    await h.ui.unmount()
  })

  test(`@F39 ${CLEANUP} the offer follows a Clear, under the actions row and above the result lines; a merged PR says so`, async ($, on) => {
    const h = await openTree($, on, { repo: { ancestor: { [TREE]: false } }, setup: w => (w.gh.heads = { [BRANCH]: ['MERGED'] }) })
    await press2(h.ui, 'clear', 'confirm-clear')
    await settled(h.ui)
    const all = await page(h.ui)
    expect(all).toContain('Worktree login is clean and pushed, and its PR is merged.')
    expect(all.indexOf('Remove it?')).toBeGreaterThan(-1)
    expect(all.indexOf('Remove it?')).toBeLessThan(all.indexOf("✓ Left Claude Code's list.")) // the offer is on screen before the results
    const order = await keys(h.ui)
    expect(order.indexOf('resume')).toBeLessThan(order.indexOf('remove-worktree')) // under the actions row
    expect(order.indexOf('remove-worktree')).toBeLessThan(order.indexOf('keep-worktree'))
    await h.ui.unmount()
  })

  test(`@F39 ${CLEANUP} a PR that is closed says so`, async ($, on) => {
    const h = await openTree($, on, { ...ONLY_TREE, repo: { ancestor: { [TREE]: false } }, setup: w => (w.gh.heads = { [BRANCH]: ['CLOSED'] }) })
    await press(h.ui, 'clear')
    expect(await page(h.ui)).toContain('Worktree login is clean and pushed, and its PR is closed.')
    await h.ui.unmount()
  })

  test(`@F40 ${CLEANUP} the offer's focus is on Keep worktree, never on Remove worktree`, async ($, on) => {
    const h = await openTree($, on, ONLY_TREE)
    expect(await focused(h.ui)).not.toContain('keep-worktree') // before the offer: the ring is where it started
    await press(h.ui, 'clear')
    expect(await focused(h.ui)).toEqual(['keep-worktree'])
    await h.ui.unmount()
  })

  test(`@F41 ${CLEANUP} ignored files: secret-looking names first and always listed, then cap 3, order, cut names, "and N more"`, () => {
    const lines = ['!! .env', '!! .env.local', '!! api_key.txt', '!! credentials.json', '!! server.pem', '!! a.log', '!! b.log', '!! c.tmp', '!! d.tmp', `!! ${'z'.repeat(40)}.log`, '!! build/', '!! node_modules/', ' M tracked.ts']
    const i = ignoredOf(lines)
    expect(i.secret).toEqual(['.env', '.env.local', 'api_key.txt', 'credentials.json', 'server.pem'])
    expect(i.other).toEqual(['a.log', 'b.log', 'c.tmp']) // files first, A to Z, at most 3
    expect(i.more).toBe(4) // d.tmp, the long name, build/, node_modules/: never a secret name among them
    expect(ignoredWords(i)).toBe('.env, .env.local, api_key.txt, credentials.json, server.pem, a.log, b.log, c.tmp and 4 more')
    // Files before folders, a long name cut at 30 cells with an ellipsis, a secret name never cut.
    expect(ignoredOf([`!! ${'z'.repeat(40)}.log`, '!! build/'])).toMatchObject({ secret: [], other: [`${'z'.repeat(29)}…`, 'build/'], more: 0 })
    expect(ignoredOf([`!! ${'k'.repeat(50)}key.txt`]).secret).toEqual([`${'k'.repeat(50)}key.txt`])
    // A secret name inside a folder counts by its own last part; a quote around a name is dropped.
    expect(ignoredOf(['!! config/.env.production', '!! "my notes.txt"'])).toMatchObject({ secret: ['config/.env.production'], other: ['my notes.txt'] })
    expect(ignoredOf(['!! a', '!! b', '!! c', '!! d']).more).toBe(1)
    expect(ignoredWords(ignoredOf(['!! a', '!! b', '!! c', '!! d']))).toBe('a, b, c and 1 more')
    expect(ignoredWords(ignoredOf([' M x']))).toBeNull() // nothing ignored: no line
  })

  test(`@F41 ${CLEANUP} the offer lists the ignored files and they never refuse it`, async ($, on) => {
    const h = await openTree($, on, { ...ONLY_TREE, repo: { status: { [TREE]: ['!! .env', '!! .env.local', '!! notes.txt', '!! a.log', '!! b.log', '!! c.tmp', '!! d.log'] } } })
    await press(h.ui, 'clear')
    expect(await page(h.ui)).toContain('These ignored files are deleted and do not come back: .env, .env.local, a.log, b.log, c.tmp and 2 more.')
    expect(await keys(h.ui)).toContain('remove-worktree') // ignored files never refuse the offer
    await h.ui.unmount()
  })
})

describe('Remove worktree and Keep worktree', () => {
  test(`@F42 ${CLEANUP} Remove worktree re-checks then runs git worktree remove from the main checkout, without force`, async ($, on) => {
    const h = await openTree($, on, ONLY_TREE)
    await press(h.ui, 'clear')
    const before = h.w.procs.length
    await press(h.ui, 'remove-worktree')
    await settled(h.ui)
    const ran = h.w.procs.slice(before)
    const remove = ran.filter(p => p.argv.includes('remove'))
    expect(remove.length).toBe(1)
    expect(remove[0]!.argv).toEqual(gitArgv('worktree', 'remove', TREE)) // the exact argument list: no flag, the path last
    expect(remove[0]!.cwd).toBe(MAIN) // from the main checkout, never from the worktree
    expect(ran[ran.length - 1]).toBe(remove[0]) // the re-check came first
    const checks = ran.slice(0, -1).map(p => p.argv.filter((a, i, all) => a !== '-c' && all[i - 1] !== '-c' && a !== '--no-optional-locks').slice(0, 3).join(' '))
    expect(checks).toEqual(['claude agents --json', 'git worktree list', 'git status --porcelain', 'git rev-list --count', 'git symbolic-ref --short', 'git merge-base --is-ancestor'])
    expect(ran.every(p => Number(p.init?.timeoutMs ?? 0) > 0)).toBe(true)
    await h.ui.unmount()
  })

  test(`@F42 ${CLEANUP} a second press while it runs is ignored`, async ($, on) => {
    const h = await openTree($, on, ONLY_TREE)
    await press(h.ui, 'clear')
    let release = () => {}
    h.w.hold = new Promise<void>(done => (release = done))
    await h.ui.press({ key: 'remove-worktree' })
    await h.ui.redraw()
    expect(await page(h.ui)).toContain('Removing worktree…')
    expect((await keys(h.ui)).filter(k => ['remove-worktree', 'keep-worktree', 'clear'].includes(k))).toEqual([]) // no button while it runs
    release()
    await settled(h.ui)
    expect(removes(h.w).length).toBe(1)
    await h.ui.unmount()
  })

  test(`@F43 ${CLEANUP} the branch is kept, the result lines say so and no resume button is drawn after removal`, async ($, on) => {
    const h = await openTree($, on, ONLY_TREE)
    await press2(h.ui, 'clear', 'remove-worktree')
    await settled(h.ui)
    const all = await page(h.ui)
    expect(all).toContain('✓ Worktree login removed. The branch fix-login stays.')
    expect(all).toContain('To resume this conversation, make the worktree again from the branch first.')
    expect(await keys(h.ui)).not.toContain('resume')
    expect(await keys(h.ui)).not.toContain('remove-worktree')
    expect(h.repo.trees.map(t => t.path)).toEqual([MAIN])
    expect(h.w.procs.some(p => p.argv.includes('branch'))).toBe(false) // git was never asked to touch the branch
    expect(await focused(h.ui)).toEqual(['crumb:0'])
    expect(all).not.toContain(OFFER) // the worktree is gone: no line
    await h.ui.unmount()
  })

  const changes: [string, (w: World, r: Repo) => void, string][] = [
    ['clean', (_, r) => (r.status[TREE] = [' M a.ts']), 'it has uncommitted changes'],
    ['pushed', (_, r) => (r.unpushed[TREE] = 1), 'it has commits that are not pushed'],
    ['merged', (_, r) => (r.ancestor[TREE] = false), 'its branch is not merged'],
    ['unused', w => (w.agents.json = AGENT_ROWS([DEAD_ROW, { kind: 'interactive', status: 'busy', sessionId: 'x-1', cwd: `${TREE}/src`, name: 'x', startedAt: 1, pid: 9 }])), 'another session is using it'],
    ['ignored', (_, r) => (r.status[TREE] = ['!! .env']), 'its ignored files changed'], // the list differs from the one in the offer
  ]
  for (const [name, change, why] of changes)
    test(`@F44 ${CLEANUP} a changed condition removes nothing and says which: ${name}`, async ($, on) => {
      const h = await openTree($, on, ONLY_TREE)
      await press(h.ui, 'clear')
      change(h.w, h.repo)
      await press(h.ui, 'remove-worktree')
      await settled(h.ui)
      expect(removes(h.w)).toEqual([])
      expect(h.repo.trees.map(t => t.path)).toContain(TREE)
      expect(await page(h.ui)).toContain(`✗ The worktree changed since it was checked: ${why}. Nothing was removed. Check it in a terminal.`)
      expect(await keys(h.ui)).not.toContain('remove-worktree') // the offer is gone
      await h.ui.unmount()
    })

  test(`@F44 ${CLEANUP} an unreadable session list at the press removes nothing`, async ($, on) => {
    const h = await openTree($, on, ONLY_TREE)
    await press(h.ui, 'clear')
    h.w.agents.json = null
    await press(h.ui, 'remove-worktree')
    await settled(h.ui)
    expect(removes(h.w)).toEqual([])
    expect(await page(h.ui)).toContain('✗ The worktree changed since it was checked: another session is using it. Nothing was removed.')
    await h.ui.unmount()
  })

  test(`@F44 ${CLEANUP} after a changed condition the page shows the worktree as it is now, and Clear brings the offer back when it holds again`, async ($, on) => {
    const h = await openTree($, on, ONLY_TREE)
    await press(h.ui, 'clear')
    h.repo.unpushed[TREE] = 2
    await press(h.ui, 'remove-worktree')
    await settled(h.ui)
    expect(await page(h.ui)).toContain('Worktree login stays: it has commits that are not pushed.')
    expect(await keys(h.ui)).not.toContain('clear') // nothing to offer while a condition fails
    await h.ui.unmount()
  })

  test(`@F45 ${CLEANUP} a git refusal shows the error line and loses nothing`, async ($, on) => {
    const h = await openTree($, on, { ...ONLY_TREE, repo: { refuse: 'fatal: cannot remove a locked working tree' } })
    await press2(h.ui, 'clear', 'remove-worktree')
    await settled(h.ui)
    expect(removes(h.w).length).toBe(1) // git was asked, without force, and said no
    expect(await page(h.ui)).toContain('✗ Git could not remove the worktree: fatal: cannot remove a locked working tree. Nothing was lost. Check it in a terminal.')
    expect(h.repo.trees.map(t => t.path)).toContain(TREE)
    await h.ui.unmount()
  })

  test(`@F45 ${CLEANUP} no usable reason: the clause is dropped`, async ($, on) => {
    const h = await openTree($, on, { ...ONLY_TREE, repo: { refuse: '' } })
    await press2(h.ui, 'clear', 'remove-worktree')
    await settled(h.ui)
    expect(await page(h.ui)).toContain('✗ Git could not remove the worktree. Nothing was lost. Check it in a terminal.')
    await h.ui.unmount()
  })

  test(`@F47 ${CLEANUP} Keep worktree removes the offer for this visit and changes nothing; Clear brings it back`, async ($, on) => {
    const h = await openTree($, on, ONLY_TREE)
    await press(h.ui, 'clear')
    const before = h.w.procs.length
    await press(h.ui, 'keep-worktree')
    await settled(h.ui)
    expect(h.w.procs.length).toBe(before) // not a single call
    expect(h.w.writes).toEqual([])
    expect(h.repo.trees.map(t => t.path)).toContain(TREE)
    expect(await page(h.ui)).not.toContain('Remove it?')
    expect(await keys(h.ui)).not.toContain('remove-worktree')
    expect(await keys(h.ui)).toContain('clear') // the way back: the offer returns when Clear is pressed again
    await press(h.ui, 'clear')
    expect(await keys(h.ui)).toEqual(expect.arrayContaining(['remove-worktree', 'keep-worktree']))
    await h.ui.unmount()
  })

  test(`@F47 ${CLEANUP} a new visit starts without the offer`, async ($, on) => {
    const h = await openTree($, on, ONLY_TREE)
    await press(h.ui, 'clear')
    expect(await keys(h.ui)).toContain('keep-worktree')
    await press(h.ui, 'crumb:0')
    await $.command.run({ command: 'tracker', args: 'session old login', origin: { kind: 'composer' }, presentation: {} as never })
    await h.ui.redraw()
    await settled(h.ui) // the visit reads git again
    expect(await keys(h.ui)).not.toContain('keep-worktree')
    expect(await keys(h.ui)).toContain('clear') // work is left, so Clear is drawn again
    await h.ui.unmount()
  })
})

describe('what the page reads from git', () => {
  test(`@F35 ${CLEANUP} the git reads run once per visit with a timeout and no shell; the 5-second redraws read nothing`, async ($, on) => {
    const h = await openTree($, on)
    const reads = h.w.procs.filter(p => p.argv[0] === 'git' || p.argv[0] === 'gh')
    expect(reads.length).toBeGreaterThan(3)
    expect(reads.every(p => isWorktreeRead(p.argv))).toBe(true)
    expect(reads.every(p => Number(p.init?.timeoutMs ?? 0) > 0)).toBe(true)
    expect(reads.filter(p => p.argv[0] === 'git').every(p => p.argv.slice(0, 5).join(' ') === 'git -c core.fsmonitor=false -c core.hooksPath=/dev/null')).toBe(true)
    const count = h.w.procs.length
    await h.ui.redraw()
    await h.ui.redraw()
    expect(h.w.procs.length).toBe(count)
    await h.ui.unmount()
  })

  test(`@F35 ${CLEANUP} a session with a process reads only which worktree it is in: no status, no gh`, async ($, on) => {
    const live = sess('live-9', 'needs-you', 4, 'web-app', 'login', { reason: 'waiting', repo: { path: MAIN, name: 'web-app' }, cwd: TREE, branch: BRANCH })
    const l = await openTree($, on, { session: live, extra: { listing: { ...LISTED, 'live-9': { pid: 3001 } } }, row: 'session:live-9' })
    expect(await page(l.ui)).toContain('worktree login · fix-login')
    expect(await page(l.ui)).not.toContain(OFFER)
    expect(l.w.procs.filter(p => p.argv[0] === 'git' || p.argv[0] === 'gh').map(p => p.argv.slice(-2).join(' '))).toEqual(['list --porcelain'])
    await l.ui.unmount()
  })

  test(`@F35 ${CLEANUP} a folder git cannot read draws no worktree line and no offer`, async ($, on) => {
    const h = await openTree($, on, { session: inTree({ cwd: '/work/not-a-repo' }), setup: w => w.put('/work/not-a-repo/README', '') })
    expect(await page(h.ui)).not.toMatch(/orktree login|Clear offers/)
    await h.ui.unmount()
  })

  test(`@F68 ${CLEANUP} the worktree words hold no path, internal name or URL`, () => {
    const leak = /\/Users\/|\/home\/|[\w.+-]+@[\w-]+\.[\w.-]+|https?:\/\//
    const fns = [WORKTREE_WORDS.line('login', 'fix-login'), WORKTREE_WORDS.stays('login', 'x', ''), WORKTREE_WORDS.safe('login', 'merged-pr'), WORKTREE_WORDS.ignored('.env'), WORKTREE_WORDS.more(2), WORKTREE_WORDS.ask('fix-login'), WORKTREE_WORDS.removed('login', 'fix-login'), WORKTREE_WORDS.claudeRemoved('login'), WORKTREE_WORDS.changed('x'), WORKTREE_WORDS.gitFailed(': r')]
    const strings = [...fns, ...Object.values(WORKTREE_WORDS.why), WORKTREE_WORDS.offersRemoval, WORKTREE_WORDS.onlyWorktree, WORKTREE_WORDS.commit, WORKTREE_WORDS.resume, WORKTREE_WORDS.removing, WORKTREE_WORDS.ignoredChanged, WORKTREE_WORDS.unreadable]
    expect(strings.filter(s => leak.test(s))).toEqual([])
  })
})

// N1: the Session page, its confirm, its offer and an error line, and Home, at 120, 80, 54 and 40 columns and a 24-column dock. The
// frames come from fixtures/frame.ts, a model of the layout (the test kit gives the element tree, not cells), so this proves no
// button is split or cut and counts rows; it is not a terminal screenshot. The frames of the same scenes are kept under
// changes/2026-11-14-tracker-session-cleanup/verify/shots/.
const MANY = Array.from({ length: 7 }, (_, i) => ask(i + 1, `Fix the login redirect on the account page number ${i + 1} please`, 180 - i * 10, { verdict: 'not-started' }))
const NOISY = ['!! .env', '!! .env.local', '!! server.pem', '!! api_key.txt', '!! credentials.json', '!! notes.txt', '!! build/', '!! very-long-generated-file-name-that-goes-on-and-on.log', '!! a.log', '!! b.log']
const REFUSAL = 'fatal: cannot remove a locked working tree because it is checked out elsewhere'
// The most rows each scene may take at each width (what the frames measured, with one row of room).
const ROWS: Record<string, Record<number, number>> = {
  offer: { 120: 16, 80: 16, 54: 20, 40: 25, 24: 38 },
  confirm: { 120: 17, 80: 20, 54: 26, 40: 31, 24: 47 },
  error: { 120: 12, 80: 12, 54: 15, 40: 18, 24: 27 },
}

describe('N1: no button is clipped at any width', () => {
  for (const width of [120, 80, 54, 40, 24])
    for (const scene of ['offer', 'confirm', 'error', 'home'] as const)
      test(`@N1 ${CLEANUP} ${scene} at ${width} columns: every button whole on one line, no line over the width, rows counted`, async ($, on) => {
        const quiet = scene === 'error'
        const h = await openTree($, on, {
          session: inTree({ asks: quiet ? [] : MANY }),
          columns: width,
          extra: { listing: quiet ? { ...UNLISTED } : LISTED },
          row: quiet ? 'command' : 'task:dead-1:1',
          repo: { status: { [TREE]: scene === 'confirm' ? [] : NOISY }, ...(quiet ? { refuse: REFUSAL } : {}) },
        })
        if (scene === 'offer') {
          await press2(h.ui, 'clear', 'confirm-clear')
          await settled(h.ui)
        } else if (scene === 'confirm') await press(h.ui, 'clear')
        else if (scene === 'error') {
          await press2(h.ui, 'clear', 'remove-worktree')
          await settled(h.ui)
        } else await press(h.ui, 'crumb:0')
        const lines = frame((await h.ui.drawn()) as Node, width)
        // A row Button of Home holds several lines of text: it wraps as a paragraph, so only the short labels of the action Buttons count.
        const labels = (await h.ui.findAll({ type: 'Button' })).map(b => String(b.props.label ?? '')).filter(l => l !== '' && !l.includes('\n') && !l.includes('…'))
        expect(labels.length).toBeGreaterThan(1)
        expect(clipped(lines, labels, width)).toEqual([])
        if (scene !== 'home') expect(lines.length).toBeLessThanOrEqual(ROWS[scene]![width]!)
        if (scene === 'offer') {
          const at = (label: string) => lines.findIndex(l => l.includes(label))
          expect(at('Keep worktree')).toBeLessThan(at('✓ Left Claude')) // the offer is on screen before the results
          // The two buttons share a line while they fit (30 cells), and wrap one per line in the narrowest dock.
          expect(at('Remove worktree') === at('Keep worktree')).toBe(width - 1 >= 30)
          expect(lines.filter(l => l.includes('Remove worktree') && l.includes('Keep worktree')).length).toBe(width - 1 >= 30 ? 1 : 0)
        }
        if (scene === 'confirm') expect(lines.some(l => l.includes('Clear session') && l.includes('Cancel'))).toBe(true) // 21 cells: fits the narrowest dock
        await h.ui.unmount()
      })
})
