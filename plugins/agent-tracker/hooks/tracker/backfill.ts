// The backfill: a session active in the last 7 days that has no file gets a record from its transcript, in
// `transcripts/`. It makes no model call and never touches a `sessions/` file, so one mod still writes one of those.
import type { EngineInterface } from 'claude-code'

import { WEEK_MS, emptyRecord, foldTranscript, FRAGMENT, fragments } from './core'
import type { TranscriptFields } from './core'
import { claudeDir, dir, readFolder, repoOf, writeJson } from './store'
import type { State } from './store'
import type { SessionRecord } from './types'

type Engine = EngineInterface

const BACKFILL_MS = 60_000 // the projects folder is listed once a minute
const BACKFILL_MAX = 25 // transcripts read in one pass; the rest wait for the next
const READ_MAX = 4 * 1024 * 1024 // the most one $.fs.read returns

// The fragments of a transcript, or null when it cannot be read. Over 4 MiB it is searched, not read whole.
export async function readFragments($: Engine, path: string, size: number): Promise<string[] | null> {
  try {
    if (size <= READ_MAX) return fragments((await $.fs.read(path)) as string)
    const run = await $.process.run(['grep', '-a', '-o', '-E', FRAGMENT, path], { timeoutMs: 60_000 })
    if (run.exitCode > 1) return null // 1 is "no match"
    const lines = run.stdout.split('\n').filter(Boolean)
    // Output cut at the limit ends in a half fragment: the fold skips a fragment that does not parse.
    return run.isStdoutTruncated ? lines.slice(0, -1) : lines
  } catch {
    return null
  }
}

async function transcriptRecord($: Engine, id: string, fields: TranscriptFields | null, mtimeMs: number, now: number): Promise<SessionRecord> {
  const startedAt = fields?.startedAt || mtimeMs
  const base = { ...emptyRecord(id, fields?.cwd ?? '', startedAt), source: 'transcript' as const, writtenAt: now, state: 'done' as const }
  // Unreadable: the session shows without its asks and numbers, and is read again when the file changes (F55).
  if (fields === null) return { ...base, lastActivityAt: mtimeMs }
  return { ...base, ...fields, startedAt, lastActivityAt: fields.lastActivityAt || mtimeMs, repo: fields.cwd ? await repoOf($, fields.cwd) : null }
}

export async function backfillPass($: Engine, s: State) {
  if (s.isBackfilling || s.mine === null) return
  s.isBackfilling = true
  try {
    const now = await $.clock.now()
    const base = await dir($)
    const root = `${await claudeDir($)}/projects`
    // Sessions with a file are the mod's own, and a transcripts file at least as new as the transcript is done.
    const hasFile = new Set((await readFolder($, s, `${base}/sessions`)).map(r => r.sessionId))
    const doneAt = new Map((await readFolder($, s, `${base}/transcripts`)).map(r => [r.sessionId, r.writtenAt]))
    let budget = BACKFILL_MAX
    for (const folder of (await $.fs.list(root).catch(() => [])).filter(e => e.kind === 'dir')) {
      for (const f of await $.fs.list(`${root}/${folder.name}`).catch(() => [])) {
        const id = f.name.slice(0, -'.jsonl'.length)
        if (f.kind !== 'file' || !f.name.endsWith('.jsonl') || id === s.mine.sessionId || hasFile.has(id)) continue
        if (now - f.mtimeMs > WEEK_MS || (doneAt.get(id) ?? -1) >= f.mtimeMs) continue
        if (budget-- <= 0) return
        const frags = await readFragments($, `${root}/${folder.name}/${f.name}`, f.size)
        const record = await transcriptRecord($, id, frags === null ? null : foldTranscript(frags), f.mtimeMs, now)
        await writeJson($, `${base}/transcripts/${id}.json`, record).catch(() => undefined)
      }
    }
  } finally {
    s.isBackfilling = false
  }
}

// One pass now and one a minute, never two at once. The 5-second poll does not wait on it.
export function startBackfill($: Engine, s: State) {
  void backfillPass($, s).catch(() => undefined)
  $.clock.every(BACKFILL_MS, () => void backfillPass($, s).catch(() => undefined))
}
