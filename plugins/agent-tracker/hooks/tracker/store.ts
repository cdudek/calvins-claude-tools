// The store, `~/.claude/agent-tracker/`: the only folder the mod writes. This file holds the one record this
// session's mod owns and reads the others. It is the only place the collector and the asks meet.
// `$` is passed only to plain top-level functions: the engine's source scan reads no other spelling.
import type { EngineInterface } from 'claude-code'

import { COMMAND_DESCRIPTION, COMMAND_HINT, PANE_ID, PANE_TITLE, REDRAW_MS, askStatuses, emptyRecord, gitArgv, parseMilestone, repoFromCommonDir } from './core'
import type { Frozen, Page } from './core'
import type { AgentsFile, Lease, SessionRecord, Settings } from './types'

type Engine = EngineInterface

export const WRITE_FAILED =
  "Tracker could not save this session's record. Asks from now on are not kept. Check that the agent-tracker folder in your Claude folder can be written."

// The pane's own state: the page shown, where Back goes, the row holding the ring, and the order Home froze.
export type PaneState = { page: Page; history: { page: Page; focus: string | null }[]; focus: string | null; frozen: Frozen | null }
export const newPane = (page: Page = { kind: 'home' }): PaneState => ({ page, history: [], focus: null, frozen: null })

// All the mod's changing state, one object per registration, so a reload or a test starts clean.
export type State = {
  mine: SessionRecord | null // this session's record; every change goes through saveOwn
  turn: { open: boolean } // true from prompt.submit to turn.complete, for the ask status
  lastCall: { key: string; failed: boolean } | null // the previous tool call, for retries
  lastSaved: string
  hasFailed: boolean
  queue: Promise<void>
  caches: Map<string, Map<string, { mtimeMs: number; record: SessionRecord }>>
  initializing: Promise<void> | null
  isTicking: boolean
  hasTimer: boolean
  scannedAt: number
  isBackfilling: boolean // a backfill pass or a repo scan is running: the next timer fire skips
  isScanning: boolean
  seen: Set<string> // the sessions the last good list read showed (R11)
  okAt: number // time of the last good list read, and the failed reads since (F52)
  failedReads: number
  settings: Settings // the last good read of settings.json
  hasBand: boolean // the band or the pane started: its command is registered and the one-minute redraw runs (F126)
  pane: PaneState
}

export const newState = (): State => ({
  mine: null,
  turn: { open: false },
  lastCall: null,
  lastSaved: '',
  hasFailed: false,
  queue: Promise.resolve(),
  caches: new Map(),
  initializing: null,
  isTicking: false,
  hasTimer: false,
  scannedAt: 0,
  isBackfilling: false,
  isScanning: false,
  seen: new Set(),
  okAt: 0,
  failedReads: 0,
  settings: { v: 1, view: 'compact', bandHidden: false },
  hasBand: false,
  pane: newPane(),
})

export async function claudeDir($: Engine) {
  return `${(await $.env.get('HOME')) ?? ''}/.claude`
}

export async function dir($: Engine) {
  return `${await claudeDir($)}/agent-tracker`
}

export async function readJson($: Engine, path: string): Promise<unknown> {
  try {
    return JSON.parse((await $.fs.read(path)) as string)
  } catch {
    return undefined // missing, or torn: the caller keeps its last good copy
  }
}

export function writeJson($: Engine, path: string, value: unknown) {
  return $.fs.write(path, JSON.stringify(value))
}

// The view and the hidden flag, one file for every session (F22, F29). A torn or missing file keeps the last good copy.
export async function readSettings($: Engine, s: State): Promise<Settings> {
  const f = (await readJson($, `${await dir($)}/settings.json`)) as Partial<Settings> | undefined
  if (f?.v === 1) s.settings = { v: 1, view: f.view === 'details' ? 'details' : 'compact', bandHidden: f.bandHidden === true }
  return s.settings
}

export async function writeSettings($: Engine, s: State, change: Partial<Settings>) {
  const next = { ...(await readSettings($, s)), ...change }
  s.settings = next
  await writeJson($, `${await dir($)}/settings.json`, next).catch(() => undefined) // not kept: the choice holds for this session
  $.ui.invalidate('ui.render')
}

// Once per session, at the first draw of the band or the pane: the /tracker command and the one-minute redraw.
export async function startUi($: Engine, s: State) {
  if (s.hasBand) return
  s.hasBand = true
  $.clock.every(REDRAW_MS, () => $.ui.invalidate('ui.render'))
  await $.command.register({ name: 'tracker', description: COMMAND_DESCRIPTION, argumentHint: COMMAND_HINT, immediate: true }).catch(() => undefined)
}

// Open the pane on a page, with the keys. No closeOnEscape: Escape only hands the keys back; Close and `ctrl+x x` close it (F92).
export async function openPane($: Engine, s: State, page: Page = { kind: 'home' }) {
  s.pane = newPane(page)
  $.ui.invalidate('ui.render')
  await $.ui.open({ id: PANE_ID, title: PANE_TITLE, focus: true }).catch(() => undefined)
}

export async function readLease($: Engine, base: string): Promise<Lease | null> {
  const l = (await readJson($, `${base}/poller.json`)) as Partial<Lease> | undefined
  return l?.v === 1 && typeof l.sessionId === 'string' && typeof l.heartbeat === 'number' ? (l as Lease) : null
}

export async function readAgentsFile($: Engine, base: string): Promise<AgentsFile | null> {
  const f = (await readJson($, `${base}/agents.json`)) as Partial<AgentsFile> | undefined
  return f?.v === 1 && typeof f.readAt === 'number' && Array.isArray(f.agents) ? (f as AgentsFile) : null
}

// Each folder is listed every poll, and only a file whose mtime changed is read again.
export async function readFolder($: Engine, s: State, folder: string): Promise<SessionRecord[]> {
  const cache = s.caches.get(folder) ?? new Map<string, { mtimeMs: number; record: SessionRecord }>()
  s.caches.set(folder, cache)
  const entries = await $.fs.list(folder).catch(() => [])
  const names = new Set<string>()
  for (const e of entries) {
    if (e.kind !== 'file' || !e.name.endsWith('.json')) continue
    names.add(e.name)
    if (cache.get(e.name)?.mtimeMs === e.mtimeMs) continue
    const r = (await readJson($, `${folder}/${e.name}`)) as Partial<SessionRecord> | undefined
    // A file whose v we do not know, or that will not parse, is skipped; the last good copy stays.
    if (r?.v === 1 && typeof r.sessionId === 'string') cache.set(e.name, { mtimeMs: e.mtimeMs, record: r as SessionRecord })
  }
  for (const name of [...cache.keys()]) if (!names.has(name)) cache.delete(name)
  return [...cache.values()].map(c => c.record)
}

async function write($: Engine, s: State) {
  if (!s.mine) return
  s.mine = { ...s.mine, asks: askStatuses(s.mine.asks, s.mine.state, s.turn.open), writtenAt: await $.clock.now() }
  const body = JSON.stringify({ ...s.mine, writtenAt: 0 })
  if (body === s.lastSaved && !s.hasFailed) return // nothing but the time changed
  try {
    await writeJson($, `${await dir($)}/sessions/${s.mine.sessionId}.json`, s.mine)
    s.lastSaved = body
    if (s.hasFailed) $.ui.status(undefined)
    s.hasFailed = false
  } catch {
    s.hasFailed = true
    $.ui.status(WRITE_FAILED)
  }
}

// Apply a change to this session's record and write the whole file, one write at a time.
export function saveOwn($: Engine, s: State, change?: (r: SessionRecord) => SessionRecord) {
  if (s.mine && change) s.mine = change(s.mine)
  s.queue = s.queue.then(() => write($, s)).catch(() => undefined)
  return s.queue
}

async function git($: Engine, cwd: string, args: string[]) {
  const r = await $.process.run(gitArgv(...args), { cwd }).catch(() => null)
  return r !== null && r.exitCode === 0 ? r.stdout.trim() : null
}

// The first changes/*/milestone.md whose branch equals the session's branch; a changes folder alone is none (F9, F10).
async function readMilestone($: Engine, cwd: string, branch: string | null): Promise<SessionRecord['milestone']> {
  if (branch === null) return null
  const entries = await $.fs.list(`${cwd}/changes`).catch(() => [])
  for (const e of entries.filter(e => e.kind === 'dir')) {
    const text = await $.fs.read(`${cwd}/changes/${e.name}/milestone.md`).catch(() => null)
    const m = typeof text === 'string' ? parseMilestone(text) : null
    if (m !== null && m.branch === branch) return { slug: m.slug, sentence: m.sentence, features: m.features }
  }
  return null
}

// The repo a folder belongs to, or null (F7).
export async function repoOf($: Engine, cwd: string) {
  const common = await git($, cwd, ['rev-parse', '--path-format=absolute', '--git-common-dir'])
  return common === null ? null : repoFromCommonDir(common)
}

// Repo, branch and milestone of a folder; read at the start and again about once a minute.
export async function where($: Engine, cwd: string) {
  const branch = (await git($, cwd, ['branch', '--show-current'])) || null // empty: a detached HEAD
  return { repo: await repoOf($, cwd), branch, milestone: await readMilestone($, cwd, branch) }
}

// Start this session's record, once. A /clear goes on under a new id with no session.start, so a later hook
// that finds no record calls this too.
export function initOwn($: Engine, s: State) {
  s.initializing ??= (async () => {
    if (s.mine) return
    const now = await $.clock.now()
    const cwd = await $.session.cwd()
    s.mine = { ...emptyRecord(await $.session.id(), cwd, now), ...(await where($, cwd)) }
    s.lastSaved = ''
    s.scannedAt = now
    await saveOwn($, s)
  })().finally(() => {
    s.initializing = null
  })
  return s.initializing
}
