// The world beneath the mod in a test: an in-memory disk, a scripted `claude agents --json`, git, and a recorder of
// every write, process, model and network call. Nothing here is a test; the test files import it.
import { mock } from 'claude-code/testing'
import type { Engine, MockClock } from 'claude-code/testing'
import type { AgentInfo, On, SessionMessage } from 'claude-code'

import type { Snapshot } from '../../hooks/tracker/types'

export const HOME = '/u'
export const DIR = `${HOME}/.claude/agent-tracker`

type Git = { commonDir: string | null; branch: string | null }

export type World = {
  clock: MockClock
  files: Map<string, string>
  writes: string[]
  procs: { argv: readonly string[]; cwd?: string }[]
  models: { op: 'classify' | 'complete'; text: string; labels?: readonly string[]; model?: string }[]
  net: string[]
  statuses: (string | undefined)[]
  states: Map<string, unknown>
  snapshot: () => Snapshot
  failWrite: (path: string) => boolean
  agents: { json: string | null }
  git: Record<string, Git>
  messages: SessionMessage[]
  subagents: AgentInfo[]
  tool: (e: unknown) => { result: object; isError?: boolean }
  classify: (text: string, labels: readonly string[]) => string | undefined | Error
  id: string
  cwd: string
  put: (path: string, value: unknown) => void
  json: (path: string) => unknown
}

const RUN = { stderr: '', isStdoutTruncated: false, isStderrTruncated: false } as const

export function world(on: On, o: { id?: string; cwd?: string; now?: number } = {}): World {
  const clock = mock.clock(on, { now: o.now ?? 0 })
  mock.store(on)
  const mtimes = new Map<string, number>()
  const w: World = {
    clock,
    files: new Map(),
    writes: [],
    procs: [],
    models: [],
    net: [],
    statuses: [],
    states: new Map(),
    snapshot: () => w.states.get('agent-tracker/snapshot') as Snapshot,
    failWrite: () => false,
    agents: { json: '[]' },
    git: {},
    messages: [],
    subagents: [],
    tool: () => ({ result: {} }),
    classify: () => 'task',
    id: o.id ?? 'self-0000',
    cwd: o.cwd ?? '/work/repo-self',
    put: (path, value) => {
      w.files.set(path, typeof value === 'string' ? value : JSON.stringify(value))
      mtimes.set(path, clock.now())
    },
    json: path => JSON.parse(w.files.get(path) ?? 'null'),
  }
  w.git[w.cwd] = { commonDir: `${w.cwd}/.git`, branch: 'main' }

  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('session.end', (_, e) => ({ sessionId: e.sessionId }))
  on('env.get', (_, e) => ({ value: e.name === 'HOME' ? HOME : undefined }))
  on('session.id', () => ({ value: w.id }))
  on('session.cwd', () => ({ value: w.cwd }))
  on('session.messages', () => ({ value: w.messages }))
  on('agent.list', () => ({ value: w.subagents }))
  on('command.register', (_, e) => ({ value: { command: e.name } }))
  on('prompt.submit', (_, e) => ({ text: e.text }))
  on('turn.complete', (_, e) => ({ text: e.answer }))
  on('tool.call', (_, e) => w.tool(e) as never)
  on('command.run', () => ({}))

  on('fs.read', (_, e) => (w.files.has(e.path) ? { value: w.files.get(e.path)! } : { deny: `ENOENT ${e.path}` }))
  on('fs.exists', (_, e) => ({ value: w.files.has(e.path) }))
  on('fs.write', (_, e) => {
    w.writes.push(e.path)
    if (w.failWrite(e.path)) return { deny: `EACCES ${e.path}` }
    w.put(e.path, e.text)
    return { value: undefined }
  })
  on('fs.list', (_, e) => {
    const prefix = e.path.replace(/\/$/, '') + '/'
    const seen = new Map<string, { name: string; kind: 'file' | 'dir'; size: number; mtimeMs: number; isLink: false }>()
    for (const [path, text] of w.files) {
      if (!path.startsWith(prefix)) continue
      const rest = path.slice(prefix.length)
      const name = rest.split('/')[0]!
      const isFile = !rest.includes('/')
      seen.set(name, { name, kind: isFile ? 'file' : 'dir', size: text.length, mtimeMs: isFile ? (mtimes.get(path) ?? 0) : 0, isLink: false })
    }
    return seen.size === 0 ? { deny: `ENOENT ${e.path}` } : { value: [...seen.values()] }
  })

  on('process.run', (_, e) => {
    const { argv, init } = e
    w.procs.push({ argv, cwd: init?.cwd })
    if (argv[0] === 'claude' && argv[1] === 'agents') {
      return w.agents.json === null ? { value: { exitCode: 1, stdout: '', ...RUN, stderr: 'failed' } } : { value: { exitCode: 0, stdout: w.agents.json, ...RUN } }
    }
    if (argv[0] === 'git') {
      const g = w.git[init?.cwd ?? w.cwd]
      if (!g) return { value: { exitCode: 128, stdout: '', ...RUN, stderr: 'not a git repository' } }
      if (argv.includes('--git-common-dir')) return g.commonDir === null ? { value: { exitCode: 128, stdout: '', ...RUN } } : { value: { exitCode: 0, stdout: `${g.commonDir}\n`, ...RUN } }
      if (argv.includes('--show-current')) return { value: { exitCode: 0, stdout: g.branch === null ? '\n' : `${g.branch}\n`, ...RUN } }
    }
    return { value: { exitCode: 1, stdout: '', ...RUN, stderr: 'unscripted' } }
  })
  // A spawn streams, so its hook is a generator: it records the call and ends the stream with a refusal.
  on('process.spawn', async function* (_, e) {
    w.net.push(`spawn ${e.argv.join(' ')}`)
    yield { stream: 'stderr', text: 'no spawn in tests' } as never
  })
  on('http.fetch', (_, e) => {
    w.net.push(`fetch ${e.url}`)
    return { deny: 'no network in tests' }
  })

  // The newest value the mod wrote to each named state value: the band and the pane will read the snapshot.
  on('state.set', (_, e, next) => {
    w.states.set(`${e.plugin}/${e.key}`, e.value)
    return next(e)
  })
  on('ui.status', (_, e) => {
    w.statuses.push(e.text)
    return { value: undefined }
  })
  on('ui.log', () => ({ value: undefined }))
  on('ui.toast', () => ({ value: undefined }))
  on('ui.invalidate', () => ({ value: undefined }))

  on('model.classify', (_, e) => {
    w.models.push({ op: 'classify', text: e.text, labels: e.labels, model: e.options?.model })
    const r = w.classify(e.text, e.labels)
    return r instanceof Error ? { deny: r.message } : { value: r }
  })
  on('model.complete', (_, e) => {
    w.models.push({ op: 'complete', text: JSON.stringify(e), model: (e as { model?: string }).model })
    return { deny: 'no complete in tests' }
  })
  return w
}

export const start = ($: Engine, w: World) =>
  $.session.start({ cwd: w.cwd, surface: 'terminal', isInteractive: true })
