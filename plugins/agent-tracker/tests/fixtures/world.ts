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
  models: { op: 'classify' | 'complete' | 'fork'; text: string; labels?: readonly string[]; model?: string }[]
  net: string[]
  origins: string[] // who raised each prompt that reached the engine
  toolCalls: number
  commandRuns: number
  invalidations: number // each $.ui.invalidate the mod raised
  toasts: string[]
  copies: { text: string; surface?: string }[]
  failCopy: string | null // the reason $.ui.copy fails with, or null: it works
  commands: string[] // each command the mod registered
  opens: { id: string; title?: string; focus?: boolean; closeOnEscape?: boolean }[] // each pane the mod opened
  closes: string[] // each pane the mod closed
  statuses: (string | undefined)[]
  states: Map<string, unknown>
  snapshot: () => Snapshot
  failWrite: (path: string) => boolean
  agents: { json: string | null }
  git: Record<string, Git>
  worktrees: Record<string, string> // `git worktree list --porcelain` output by folder; none: exit 128
  gh: { json: string | null; missing: boolean } // `gh pr list` output; null: signed out (exit 1); missing: no gh binary
  unreadable: Set<string> // files that exist and cannot be read, by read or by grep
  sizes: Map<string, number> // a file's size as the engine reports it, when a test needs a big one
  messages: SessionMessage[]
  subagents: AgentInfo[]
  tool: (e: unknown) => { result: object; isError?: boolean }
  classify: (text: string, labels: readonly string[]) => string | undefined | Error
  id: string
  cwd: string
  mtimes: Map<string, number> // a file's modification time, set by put
  put: (path: string, value: unknown) => void
  json: (path: string) => unknown
}

const RUN = { stderr: '', isStdoutTruncated: false, isStderrTruncated: false } as const

export function world(on: On, o: { id?: string; cwd?: string; now?: number; panes?: boolean } = {}): World {
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
    origins: [],
    toolCalls: 0,
    commandRuns: 0,
    invalidations: 0,
    toasts: [],
    copies: [],
    failCopy: null,
    commands: [],
    opens: [],
    closes: [],
    statuses: [],
    states: new Map(),
    snapshot: () => w.states.get('agent-tracker/snapshot') as Snapshot,
    failWrite: () => false,
    agents: { json: '[]' },
    git: {},
    worktrees: {},
    gh: { json: null, missing: false },
    unreadable: new Set(),
    sizes: new Map(),
    messages: [],
    subagents: [],
    tool: () => ({ result: {} }),
    classify: () => 'task',
    id: o.id ?? 'self-0000',
    cwd: o.cwd ?? '/work/repo-self',
    mtimes,
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
  on('command.register', (_, e) => {
    w.commands.push(e.name)
    return { value: { command: e.name } }
  })
  on('prompt.submit', (_, e) => {
    w.origins.push(e.origin.kind)
    return { text: e.text }
  })
  on('turn.complete', (_, e) => ({ text: e.answer }))
  on('tool.call', (_, e) => {
    w.toolCalls += 1
    return w.tool(e) as never
  })
  on('command.run', () => {
    w.commandRuns += 1
    return {}
  })

  // Like the engine: a read over 4 MiB rejects.
  const MAX_READ = 4 * 1024 * 1024
  on('fs.read', (_, e) => {
    if (!w.files.has(e.path)) return { deny: `ENOENT ${e.path}` }
    if (w.unreadable.has(e.path)) return { deny: `EACCES ${e.path}` }
    return (w.sizes.get(e.path) ?? w.files.get(e.path)!.length) > MAX_READ ? { deny: `EFBIG ${e.path}` } : { value: w.files.get(e.path)! }
  })
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
      seen.set(name, { name, kind: isFile ? 'file' : 'dir', size: isFile ? (w.sizes.get(path) ?? text.length) : text.length, mtimeMs: isFile ? (mtimes.get(path) ?? 0) : 0, isLink: false })
    }
    return seen.size === 0 ? { deny: `ENOENT ${e.path}` } : { value: [...seen.values()] }
  })

  on('process.run', (_, e) => {
    const { argv, init } = e
    w.procs.push({ argv, cwd: init?.cwd })
    if (argv[0] === 'claude' && argv[1] === 'agents') {
      return w.agents.json === null ? { value: { exitCode: 1, stdout: '', ...RUN, stderr: 'failed' } } : { value: { exitCode: 0, stdout: w.agents.json, ...RUN } }
    }
    if (argv[0] === 'gh') {
      if (w.gh.missing) return { deny: 'ENOENT gh' }
      return w.gh.json === null ? { value: { exitCode: 1, stdout: '', ...RUN, stderr: 'gh auth login' } } : { value: { exitCode: 0, stdout: w.gh.json, ...RUN } }
    }
    // grep -o -E <pattern> <file>: the pattern runs as a JS regex over the file text, one match per line.
    if (argv[0] === 'grep') {
      const text = w.files.get(argv[argv.length - 1]!)
      if (text === undefined || w.unreadable.has(argv[argv.length - 1]!)) return { value: { exitCode: 2, stdout: '', ...RUN, stderr: 'No such file' } }
      const found = text.match(new RegExp(argv[argv.length - 2]!, 'g')) ?? []
      return { value: { exitCode: found.length ? 0 : 1, stdout: found.length ? `${found.join('\n')}\n` : '', ...RUN } }
    }
    if (argv[0] === 'git') {
      if (argv[1] === 'worktree') {
        const list = w.worktrees[init?.cwd ?? w.cwd]
        return list === undefined ? { value: { exitCode: 128, stdout: '', ...RUN, stderr: 'not a git repository' } } : { value: { exitCode: 0, stdout: list, ...RUN } }
      }
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
  on('ui.toast', (_, e) => {
    w.toasts.push(e.text)
    return { value: undefined }
  })
  on('ui.invalidate', () => {
    w.invalidations += 1
    return { value: undefined }
  })
  // Opt in with `panes: true`: a test that answers ui.open itself would register it twice.
  if (o.panes) {
    on('ui.open', (_, e) => {
      w.opens.push({ id: e.id, title: e.title, focus: e.focus, closeOnEscape: e.closeOnEscape })
      return { value: { isPlaced: true as const } }
    })
    on('ui.close', (_, e) => {
      w.closes.push(e.id)
      return { value: undefined }
    })
  }
  on('ui.copy', (_, e) => {
    w.copies.push({ text: e.text, surface: e.surface })
    return { value: w.failCopy === null ? { isCopied: true as const } : { isCopied: false as const, reason: w.failCopy } } as never
  })

  on('model.classify', (_, e) => {
    w.models.push({ op: 'classify', text: e.text, labels: e.labels, model: e.options?.model })
    const r = w.classify(e.text, e.labels)
    return r instanceof Error ? { deny: r.message } : { value: r }
  })
  on('model.complete', (_, e) => {
    w.models.push({ op: 'complete', text: JSON.stringify(e), model: (e as { model?: string }).model })
    return { deny: 'no complete in tests' }
  })
  on('model.fork', (_, e) => {
    w.models.push({ op: 'fork', text: JSON.stringify(e), model: (e as { model?: string }).model })
    return { deny: 'no fork in tests' }
  })
  return w
}

export const start = ($: Engine, w: World) =>
  $.session.start({ cwd: w.cwd, surface: 'terminal', isInteractive: true })
