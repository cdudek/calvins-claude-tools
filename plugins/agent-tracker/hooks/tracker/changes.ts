// The change folders of a repo, read as they are: `changes/*/milestone.md` and the files beside it, in the main checkout and
// in each worktree. It only reads. The pane's Repo, Milestone and Feature pages draw what it finds.
// `$` is passed only to plain top-level functions: the engine's source scan reads no other spelling.
import type { EngineInterface } from 'claude-code'

import { changeRoots, parseChange, pickChanges } from './core'
import type { Change } from './core'
import type { State } from './store'
import type { Snapshot } from './types'

type Engine = EngineInterface
type Root = { path: string; branch: string | null }

const CHANGES_MAX = 20 // the newest change folders of each root
const FRESH_MS = 15_000 // a read is kept this long: a redraw does not read every file again
const NONE = { intent: false, ux: false, facts: false, plan: false, locked: false }

async function text($: Engine, path: string): Promise<string | null> {
  const t = await $.fs.read(path).catch(() => null)
  return typeof t === 'string' ? t : null
}

async function has($: Engine, path: string) {
  return $.fs.exists(path).catch(() => false)
}

// Phase one reads every milestone.md to see which change lives where; phase two reads the other files of the copy picked.
export async function readChanges($: Engine, roots: Root[]): Promise<Change[]> {
  const light: Change[] = []
  for (const root of roots) {
    const entries = await $.fs.list(`${root.path}/changes`).catch(() => [])
    const dirs = entries
      .filter(e => e.kind === 'dir' && e.name !== 'archive')
      .map(e => e.name)
      .sort()
      .reverse()
      .slice(0, CHANGES_MAX)
    for (const dir of dirs) {
      const milestone = await text($, `${root.path}/changes/${dir}/milestone.md`)
      const c = milestone === null ? null : parseChange({ dir, root: root.path, milestone, done: null, validation: null, questions: null, findings: null, decisions: null, has: NONE })
      if (c !== null) light.push(c)
    }
  }
  const out: Change[] = []
  for (const c of pickChanges(light, roots)) {
    const base = `${c.root}/changes/${c.dir}`
    const full = parseChange({
      dir: c.dir,
      root: c.root,
      milestone: (await text($, `${base}/milestone.md`)) ?? '',
      done: await text($, `${base}/done.json`),
      validation: await text($, `${base}/validation.md`),
      questions: await text($, `${base}/questions.md`),
      findings: await text($, `${base}/findings.md`),
      decisions: await text($, `${base}/decisions.json`),
      has: {
        intent: await has($, `${base}/intent.md`),
        ux: await has($, `${base}/spec`),
        facts: await has($, `${base}/facts.md`),
        plan: await has($, `${base}/plan.md`),
        locked: await has($, `${base}/lock.json`),
      },
    })
    if (full !== null) out.push(full)
  }
  return out
}

// A repo's changes, the last read kept for FRESH_MS.
export async function changesOf($: Engine, s: State, snap: Snapshot, repoPath: string, now: number): Promise<Change[]> {
  const kept = s.changes.get(repoPath)
  if (kept !== undefined && now - kept.at < FRESH_MS) return kept.changes
  const changes = await readChanges($, changeRoots(snap, repoPath))
  s.changes.set(repoPath, { at: now, changes })
  return changes
}
