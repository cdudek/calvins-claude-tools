// The backfill: a session active in the last 7 days that has no file gets a record from its transcript, in
// `transcripts/`. It makes no model call and never touches a `sessions/` file, so one mod still writes one of those.
import { atom, read } from 'claude-code'
import type { EngineInterface } from 'claude-code'

import { ASK_TEXT_MAX, MODEL, isAutomated, WEEK_MS, emptyRecord, foldTranscript, FRAGMENT, fragments, latePrompt, leaseState, parseNotes, taskLists } from './core'
import type { TranscriptFields } from './core'
import { claudeDir, dir, readEntrypoints, readFolder, readLateChecks, readLease, repoOf, writeJson } from './store'
import type { State } from './store'
import type { LateChecks, SessionRecord, Snapshot } from './types'

type Engine = EngineInterface

const BACKFILL_MS = 60_000 // the projects folder is listed once a minute
const BACKFILL_MAX = 25 // transcripts read in one pass; the rest wait for the next
const READ_MAX = 4 * 1024 * 1024 // the most one $.fs.read returns
const ENTRY_MAX = 60 // transcripts whose entrypoint is looked up in one pass
const LATE_MAX = 5 // sessions given their one late check in one pass
// The collector writes it; the late check reads the sessions from it. The same literal, declared where it is read.
const snapshot = atom({ plugin: 'agent-tracker', key: 'snapshot' } as const, { at: 0, agentsOk: true, okAt: 0, failedReads: 0, sessions: [] } as Snapshot)
type TranscriptFile = { path: string; size: number; mtimeMs: number }

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

// Every transcript of the last week, by session id.
async function transcriptFiles($: Engine, root: string, now: number) {
  const out = new Map<string, TranscriptFile>()
  for (const folder of (await $.fs.list(root).catch(() => [])).filter(e => e.kind === 'dir')) {
    for (const f of await $.fs.list(`${root}/${folder.name}`).catch(() => [])) {
      if (f.kind === 'file' && f.name.endsWith('.jsonl') && now - f.mtimeMs <= WEEK_MS) out.set(f.name.slice(0, -'.jsonl'.length), { path: `${root}/${folder.name}/${f.name}`, size: f.size, mtimeMs: f.mtimeMs })
    }
  }
  return out
}

// How a session was started, said once at the top of its transcript: `grep -m 1` stops at the first line that has it, so only
// the head of the file is read. Looked up once per session; empty when the transcript says nothing.
async function entrypointPass($: Engine, base: string, files: Map<string, TranscriptFile>) {
  const known = await readEntrypoints($, base)
  let budget = ENTRY_MAX
  let changed = false
  // Newest first: the lists show today, and a late check waits for its session's entrypoint.
  for (const [id, f] of [...files].sort((a, b) => b[1].mtimeMs - a[1].mtimeMs)) {
    if (id in known.by) continue
    if (budget-- <= 0) break
    const run = await $.process.run(['grep', '-a', '-o', '-m', '1', '-E', '"entrypoint":"[^"]*"', f.path], { timeoutMs: 10_000 }).catch(() => null)
    known.by[id] = (run !== null && run.exitCode === 0 ? /"entrypoint":"([^"]*)"/.exec(run.stdout)?.[1] : undefined) ?? ''
    changed = true
  }
  if (changed) await writeJson($, `${base}/entrypoints.json`, known).catch(() => undefined)
  return known.by
}

// What the agent wrote in a session after `from`: the text of its assistant lines, the last ASK_TEXT_MAX characters. A
// transcript over 4 MiB or unreadable gives nothing.
async function writtenSince($: Engine, f: TranscriptFile | undefined, from: number) {
  if (f === undefined || f.size > READ_MAX) return ''
  const text = await $.fs.read(f.path).catch(() => '')
  const out: string[] = []
  for (const line of String(text).split('\n')) {
    if (!line.includes('"type":"assistant"')) continue
    try {
      const o = JSON.parse(line) as { timestamp?: string; message?: { content?: { type?: string; text?: string }[] } }
      if (Date.parse(o.timestamp ?? '') < from) continue
      for (const b of o.message?.content ?? []) if (b.type === 'text' && typeof b.text === 'string') out.push(b.text)
    } catch {
      // a torn line
    }
  }
  return out.join('\n').slice(-ASK_TEXT_MAX)
}

// One late check per session whose task asks no turn judged and that is over or idle: one haiku call on the asks and what the
// agent wrote after the first of them, at most 5 sessions a pass, from the session that holds the lease. The check is marked
// done when it ran, whether or not the call answered, and never runs again. A session is not checked until its entrypoint is
// known, so an sdk-* run never costs a call.
async function latePass($: Engine, s: State, base: string, now: number, files: Map<string, TranscriptFile>, entrypoints: Record<string, string>) {
  if (s.mine === null || leaseState(await readLease($, base), s.mine.sessionId, now) !== 'mine') return
  const snap = await read($, snapshot)
  if (snap.at === 0) return
  const done = await readLateChecks($, base)
  const unchecked = new Map<string, { n: number; text: string; at: number }[]>()
  for (const u of taskLists(snap, now).unchecked) {
    if (u.sessionId in done.by || !(u.sessionId in entrypoints) || isAutomated(entrypoints[u.sessionId])) continue
    unchecked.set(u.sessionId, [...(unchecked.get(u.sessionId) ?? []), { n: u.n, text: u.text, at: u.at }])
  }
  let budget = LATE_MAX
  for (const [id, asks] of unchecked) {
    if (budget-- <= 0) return
    const record = snap.sessions.find(r => r.sessionId === id)
    const first = Math.min(...asks.map(a => a.at))
    const written = await writtenSince($, files.get(id), first)
    const open = asks.slice(-8)
    let verdicts: LateChecks['by'][string]['verdicts'] = []
    if (written !== '') {
      const r = await $.model.complete({ model: MODEL, prompt: latePrompt(open, written), maxTokens: 600, effort: 'low', timeoutMs: 30_000 }).catch(() => null)
      const found = r !== null && r.isAnswered ? parseNotes(r.text, { open: new Set(open.map(a => a.n)), all: new Set((record?.asks ?? []).map(a => a.n)) }) : null
      verdicts = found?.verdicts ?? []
    }
    done.by[id] = { at: now, verdicts }
    await writeJson($, `${base}/latechecks.json`, done).catch(() => undefined) // marked before the next session, so a stop never repeats a call
  }
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
    const files = await transcriptFiles($, root, now)
    const entrypoints = await entrypointPass($, base, files)
    await latePass($, s, base, now, files, entrypoints).catch(() => undefined)
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
