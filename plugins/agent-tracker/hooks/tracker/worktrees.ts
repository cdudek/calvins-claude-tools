// The worktree a session ran in: what git and `gh` say about it (reads only), and the one write, `git worktree remove <path>`, run
// after the owner's press of "Remove worktree". It re-checks every condition and re-reads the ignored files first, never passes a
// flag, never a shell, runs from the main checkout, and leaves the branch. `$` is passed only to plain top-level functions.
import type { EngineInterface } from 'claude-code'

import { WORKTREE_WORDS, failedOf, gitArgv, ignoredOf, isGithubRemote, listingOf, liveFolders, parseWorktrees, reasonOf, under, whyOf } from './core'
import type { Facts, PrState, WtOutcome } from './core'
import { readRows } from './clear'

type Engine = EngineInterface
const GIT_MS = 15_000
const REMOVE_MS = 120_000 // a big tree takes a while to delete; cutting git off midway would leave half of it

// A command's stdout when it exits 0, else null. A command that cannot start (no gh installed) is null too.
async function out($: Engine, argv: string[], cwd: string): Promise<string | null> {
  const run = await $.process.run(argv, { cwd, timeoutMs: GIT_MS }).catch(() => null)
  return run !== null && run.exitCode === 0 ? run.stdout : null
}

// The default branch: what origin's HEAD points at, else main, else master. null: there is none, and the PR alone decides.
async function defaultRef($: Engine, cwd: string): Promise<string | null> {
  const head = ((await out($, gitArgv('symbolic-ref', '--short', 'refs/remotes/origin/HEAD'), cwd)) ?? '').trim()
  if (head !== '') return head
  for (const name of ['main', 'master'])
    for (const ref of [`refs/remotes/origin/${name}`, `refs/heads/${name}`]) if ((await out($, gitArgv('rev-parse', '--verify', '--quiet', ref), cwd)) !== null) return ref
  return null
}

// The state of the branch's pull requests, for a GitHub remote only. null: `gh` is missing or gave no answer (F38).
async function prState($: Engine, branch: string, cwd: string): Promise<PrState | null> {
  if (!isGithubRemote((await out($, gitArgv('remote', 'get-url', 'origin'), cwd)) ?? '')) return null
  const json = await out($, ['gh', 'pr', 'list', '--head', branch, '--state', 'all', '--json', 'state', '--limit', '20'], cwd)
  let list: unknown
  try {
    list = JSON.parse(json ?? '')
  } catch {
    return null
  }
  if (!Array.isArray(list)) return null
  const states = list.map(p => String((p as { state?: unknown } | null)?.state ?? ''))
  return states.includes('OPEN') ? 'open' : states.includes('MERGED') ? 'merged' : states.length > 0 ? 'closed' : 'none'
}

// Everything the five conditions need, read from the session's folder. `deep` false (a session with a process): only which worktree it
// is in, which is all the page's line needs. null: git could not say, or the folder is in no repository.
export async function readWorktree($: Engine, cwd: string, live: string[] | null, deep = true): Promise<Facts | null> {
  const trees = parseWorktrees((await out($, gitArgv('worktree', 'list', '--porcelain'), cwd)) ?? '')
  const main = trees[0]
  const tree = trees.filter(t => under(cwd, t.path)).sort((a, b) => b.path.length - a.path.length)[0]
  if (main === undefined || tree === undefined) return null
  const facts: Facts = { path: tree.path, main: main.path, linked: tree.path !== main.path, branch: tree.branch, status: [], unpushed: null, inDefault: false, pr: null, live }
  if (!facts.linked || !deep) return facts
  // No optional lock: reading a worktree must not refresh its index under a session that is using it.
  const status = await out($, gitArgv('--no-optional-locks', 'status', '--porcelain', '--ignored'), tree.path)
  if (status === null) return null
  const count = ((await out($, gitArgv('rev-list', '--count', 'HEAD', '--not', '--remotes'), tree.path)) ?? '').trim()
  const ref = await defaultRef($, tree.path)
  const merged = ref === null ? false : (await $.process.run(gitArgv('merge-base', '--is-ancestor', 'HEAD', ref), { cwd: tree.path, timeoutMs: GIT_MS }).catch(() => null))?.exitCode === 0
  return {
    ...facts,
    status: status.split('\n').filter(l => l !== ''),
    unpushed: /^\d+$/.test(count) ? Number(count) : null,
    inDefault: merged,
    pr: merged || tree.branch === null ? null : await prState($, tree.branch, tree.path),
  }
}

// After `claude rm`: is the worktree still there? 'gone': Claude Code removed it (F46). Else what git says now.
export async function afterRm($: Engine, f: Facts, live: string[] | null): Promise<Facts | null | 'gone'> {
  const trees = parseWorktrees((await out($, gitArgv('worktree', 'list', '--porcelain'), f.main)) ?? '')
  if (trees.length === 0) return null
  return trees.some(t => t.path === f.path) ? readWorktree($, f.path, live) : 'gone'
}

// Remove the worktree, or say why not. All five conditions are checked again on fresh reads, and so are the ignored files: a list
// that differs from the one the offer showed is a change (F42, F44). `facts` in the answer is what the page keeps.
export async function removeWorktree($: Engine, offered: Facts, label: string): Promise<{ outcome: WtOutcome; facts: Facts | null }> {
  const rows = await readRows($)
  const now = await readWorktree($, offered.path, rows === null ? null : liveFolders(rows, listingOf(rows)))
  const changed = (why: string) => ({ outcome: { kind: 'changed', why } as const, facts: now })
  if (now === null || !now.path.startsWith('/')) return { outcome: { kind: 'changed', why: WORKTREE_WORDS.unreadable }, facts: null }
  const failed = failedOf(now)
  if (failed !== null) return changed(failed === 'linked' ? WORKTREE_WORDS.unreadable : whyOf(failed))
  if (ignoredOf(now.status).all.join('\n') !== ignoredOf(offered.status).all.join('\n')) return changed(WORKTREE_WORDS.ignoredChanged)
  // The one write: the path as git listed it, last, so nothing after it can be read as a flag.
  const run = await $.process.run(gitArgv('worktree', 'remove', now.path), { cwd: now.main, timeoutMs: REMOVE_MS }).catch(() => null)
  if (run !== null && run.exitCode === 0) return { outcome: { kind: 'removed', label, branch: now.branch }, facts: null }
  return { outcome: { kind: 'refused', why: reasonOf(run?.stderr || run?.stdout) }, facts: await readWorktree($, now.path, now.live) }
}
