// The time of the last line of a session's transcript (F71): the one source of a last activity for a session that no
// mod file or transcript record describes. Read with `tail` (an argument list, no shell) from the end of the file, so a
// transcript of any size costs the same. The transcript is found by listing the project folders for `<session id>.jsonl`.
import type { EngineInterface } from 'claude-code'

import { claudeDir } from './store'
import type { State } from './store'
import type { AgentRow } from './types'

type Engine = EngineInterface
type Cache = { paths: Map<string, string>; times: Map<string, { readAt: number; time: number | null }>; listedAt: number }

const TAIL_BYTES = 65_536 // a last line can be huge; its time is near its end, and the lines before it often have none
const LIST_MS = 60_000 // the project folders are listed again at most once a minute for a transcript not found yet
const REFRESH_MS = 60_000 // a row with a process is read again after this; a row with none is final
const BUDGET = 20 // transcripts read in one poll; the rest wait for the next
const caches = new WeakMap<State, Cache>()

async function findPaths($: Engine, root: string, ids: ReadonlySet<string>, into: Map<string, string>) {
  for (const folder of (await $.fs.list(root).catch(() => [])).filter(e => e.kind === 'dir')) {
    for (const f of await $.fs.list(`${root}/${folder.name}`).catch(() => [])) {
      const id = f.name.slice(0, -'.jsonl'.length)
      if (f.kind === 'file' && f.name.endsWith('.jsonl') && ids.has(id)) into.set(id, `${root}/${folder.name}/${f.name}`)
    }
  }
}

// The time of the last line that has one, from the end of the transcript; null when none is found.
async function readTime($: Engine, path: string): Promise<number | null> {
  const run = await $.process.run(['tail', '-c', String(TAIL_BYTES), path], { timeoutMs: 10_000 }).catch(() => null)
  if (run === null || run.exitCode !== 0) return null
  const stamps = [...run.stdout.matchAll(/"timestamp":"([^"]*)"/g)].map(m => Date.parse(m[1]!)).filter(t => !Number.isNaN(t))
  return stamps.length === 0 ? null : Math.max(...stamps)
}

// The last line time of every row that has no process, and of every row `skip` does not hold (no record of its own), by
// session id. Only a time that was found is in the answer.
export async function lastLines($: Engine, s: State, rows: AgentRow[], skip: ReadonlySet<string>, now: number): Promise<Record<string, number>> {
  const cache = caches.get(s) ?? { paths: new Map(), times: new Map(), listedAt: 0 }
  caches.set(s, cache)
  const wanted = rows.filter(a => (a.pid === undefined || !skip.has(a.sessionId)) && !(a.pid === undefined && cache.times.has(a.sessionId)))
  const lost = new Set(wanted.filter(a => !cache.paths.has(a.sessionId)).map(a => a.sessionId))
  if (lost.size > 0 && now - cache.listedAt >= LIST_MS) {
    cache.listedAt = now
    await findPaths($, `${await claudeDir($)}/projects`, lost, cache.paths)
  }
  let budget = BUDGET
  for (const a of wanted) {
    const path = cache.paths.get(a.sessionId)
    const seen = cache.times.get(a.sessionId)
    if (path === undefined || (seen !== undefined && now - seen.readAt < REFRESH_MS)) continue
    if (budget-- <= 0) break
    cache.times.set(a.sessionId, { readAt: now, time: await readTime($, path) })
  }
  const out: Record<string, number> = {}
  for (const a of rows) {
    const t = cache.times.get(a.sessionId)?.time
    if (t !== undefined && t !== null) out[a.sessionId] = t
  }
  return out
}
