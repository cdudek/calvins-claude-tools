import type { FactoryStatusBoard, FactoryStatusItem } from '../types/index'

/** The reader ships inside this plugin (bin/), a byte copy of the factory plugin's. A repo's own copy is never run: its files are untrusted. */
export const SCRIPT = 'bin/factory-status.py'

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

export const join = (root: string, rel: string) => (root === '/' ? '' : root) + '/' + rel

export const scriptPath = (pluginRoot: string) => join(pluginRoot, SCRIPT)

// -I: isolated mode, no PYTHONPATH, no user site, no script directory on sys.path.
export const lineArgv = (pluginRoot: string, root: string) => [
  'python3', '-I', scriptPath(pluginRoot), '--repo', root, '--line',
]

export const jsonArgv = (pluginRoot: string, root: string) => [
  'python3', '-I', scriptPath(pluginRoot), '--json', '--roots', root,
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
