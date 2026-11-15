// A made-up repository for the worktree tests: a main checkout and one linked worktree, answered through the world's git hook.
// It models only what the offer reads (the list of worktrees, the status, the commits not pushed, the default branch) and the
// one write, `git worktree remove`. Every folder, branch and file name is invented.
import type { SessionRecord } from '../../hooks/tracker/types'
import type { On } from 'claude-code'
import type { Engine } from 'claude-code/testing'

import type { Snapshot } from '../../hooks/tracker/types'
import { FOLDER, LISTED, dead, open } from './ui'
import { settle } from './world'
import type { World } from './world'

export const MAIN = FOLDER // the repo's main checkout
export const TREE = `${MAIN}/.worktrees/login` // the label "login"
export const BRANCH = 'fix-login'

export type Repo = {
  trees: { path: string; branch: string | null }[] // the first is the main checkout
  status: Record<string, string[]> // `git status --porcelain --ignored`, by worktree
  unpushed: Record<string, number>
  ancestor: Record<string, boolean> // HEAD is in the default branch
  head: string | null // `git symbolic-ref --short refs/remotes/origin/HEAD`; null: not set
  refs: string[] // the refs that exist
  refuse: string | null // stderr of a `git worktree remove` that git refuses
}

const under = (path: string | undefined, base: string) => path !== undefined && (path === base || path.startsWith(`${base}/`))
const lines = (list: string[]) => list.map(l => `${l}\n`).join('')

// A clean, pushed and merged worktree; `over` changes what a test needs.
export const repoWorld = (w: World, over: Partial<Repo> = {}): Repo => {
  const r: Repo = {
    trees: [{ path: MAIN, branch: 'main' }, { path: TREE, branch: BRANCH }],
    status: { [TREE]: [] },
    unpushed: { [TREE]: 0 },
    ancestor: { [TREE]: true },
    head: 'origin/main',
    refs: ['refs/remotes/origin/main', 'refs/heads/main'],
    refuse: null,
    ...over,
  }
  w.put(`${TREE}/README`, '')
  w.gitHook = (sub, cwd) => {
    const tree = [...r.trees].sort((a, b) => b.path.length - a.path.length).find(t => under(cwd, t.path))
    if (tree === undefined) return undefined
    const done = (stdout = '', exitCode = 0, stderr = '') => ({ exitCode, stdout, stderr })
    if (sub[0] === 'worktree' && sub[1] === 'list') return done(r.trees.map(t => `worktree ${t.path}\nHEAD 0123abc\n${t.branch === null ? 'detached' : `branch refs/heads/${t.branch}`}\n`).join('\n'))
    if (sub[0] === 'worktree' && sub[1] === 'remove') {
      if (r.refuse !== null) return done('', 1, r.refuse)
      r.trees = r.trees.filter(t => t.path !== sub[2])
      for (const path of [...w.files.keys()]) if (under(path, sub[2]!)) w.files.delete(path)
      return done()
    }
    if (sub[0] === 'status') return done(lines(r.status[tree.path] ?? []))
    if (sub[0] === 'rev-list') return done(`${r.unpushed[tree.path] ?? 0}\n`)
    if (sub[0] === 'symbolic-ref') return r.head === null ? done('', 128, 'not a symbolic ref') : done(`${r.head}\n`)
    if (sub[0] === 'rev-parse' && sub.includes('--verify')) return r.refs.includes(sub[sub.length - 1]!) ? done('0123abc\n') : done('', 1)
    if (sub[0] === 'merge-base') return r.ancestor[tree.path] === true ? done() : done('', 1)
    return undefined
  }
  return r
}

// The session that ran in the worktree: ended, a listed job with two open tasks, like `dead()` but in TREE. `cwd` may be a subfolder.
export const inTree = (extra: Partial<SessionRecord> = {}): SessionRecord => dead({ cwd: TREE, branch: BRANCH, repo: { path: MAIN, name: 'web-app' }, ...extra })

// What a git or gh call of the worktree check looks like, for a test that wants "nothing but these ran".
export const isWorktreeRead = (argv: readonly string[]) => {
  const sub = argv.slice(1).filter((a, i, all) => a !== '-c' && all[i - 1] !== '-c')
  if (argv[0] === 'gh') return sub[0] === 'pr' && sub[1] === 'list'
  if (argv[0] !== 'git') return false
  return ['status', 'rev-list', 'merge-base', 'symbolic-ref'].includes(sub[0] ?? '') || (sub[0] === 'worktree' && sub[1] === 'list') || (sub[0] === 'rev-parse' && sub.includes('--verify')) || (sub[0] === 'remote' && sub[1] === 'get-url')
}

// The Session page of a session in the worktree, opened as the person does, with the page's own git reads done and drawn.
export const openTree = async ($: Engine, on: On, o: { session?: SessionRecord; extra?: Partial<Snapshot>; repo?: Partial<Repo>; setup?: (w: World, r: Repo) => void; row?: string; columns?: number } = {}) => {
  let repo!: Repo
  const h = await open($, on, o.session ?? inTree(), o.extra ?? { listing: LISTED }, {
    ...(o.row === undefined ? {} : { row: o.row }),
    ...(o.columns === undefined ? {} : { columns: o.columns }),
    setup: w => {
      repo = repoWorld(w, o.repo)
      o.setup?.(w, repo)
    },
  })
  await settle()
  await h.ui.redraw()
  return { ...h, repo }
}
