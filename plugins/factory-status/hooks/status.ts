import type { FactoryStatusBoard, FactoryStatusItem } from '../types/index'

export const SCRIPT = '.factory/factory-status.py'

/** The directory and each parent up to the root, nearest first. */
export function ancestors(cwd: string): string[] {
  const out: string[] = []
  let dir = cwd.replace(/\/+$/, '') || '/'
  for (;;) {
    out.push(dir)
    if (dir === '/') return out
    dir = dir.slice(0, dir.lastIndexOf('/')) || '/'
  }
}

const join = (root: string, rel: string) => (root === '/' ? '' : root) + '/' + rel

export const scriptPath = (root: string) => join(root, SCRIPT)

export const lineArgv = (root: string) => [
  'python3', scriptPath(root), '--repo', root, '--line',
]

export const jsonArgv = (root: string) => [
  'python3', scriptPath(root), '--json', '--roots', root,
]

/** First non-empty line of the script's output: the status line, or ''. */
export const parseLine = (stdout: string): string =>
  stdout.split('\n').map(l => l.trim()).find(l => l !== '') ?? ''

const isObj = (v: unknown): v is Record<string, unknown> =>
  typeof v === 'object' && v !== null && !Array.isArray(v)

const arr = (v: unknown): Record<string, unknown>[] => (Array.isArray(v) ? v.filter(isObj) : [])

const items = (v: unknown): FactoryStatusItem[] =>
  arr(v).map(o => ({ id: String(o.id), state: String(o.state) }))

/**
 * Reads `--json` output: {projects: [{changes: [...]}]}. Picks the change with
 * `current` set, else a `needs-you` one, else the last listed (the newest).
 */
export function parseBoard(stdout: string): FactoryStatusBoard | null {
  let data: unknown
  try {
    data = JSON.parse(stdout)
  } catch {
    return null
  }
  if (!isObj(data)) return null
  const changes = arr(data.projects).flatMap(p => arr(p.changes))
  const change =
    changes.find(c => c.current != null) ??
    changes.find(c => c.column === 'needs-you') ??
    changes[changes.length - 1]
  if (!change) return null

  const milestones = arr(change.milestones)
  const cur = isObj(change.current) ? change.current : null
  const running = cur && milestones.find(m => m.id === cur.milestone)
  const needs = isObj(change.needs) ? change.needs : null

  return {
    change: String(change.slug),
    title: String(change.title ?? ''),
    column: String(change.column ?? ''),
    milestones: items(milestones),
    tasks: items(running?.tasks),
    needs: needs ? String(needs.text ?? '') : '',
    where: needs ? String(needs.where ?? '') : '',
  }
}
