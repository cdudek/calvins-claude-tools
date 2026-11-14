// The web page, `~/.claude/agent-tracker/board.html`: one self-contained file, no server and no port. `/tracker web`
// builds it fresh and opens it; the session holding the poller lease rewrites it every 10 seconds, and the page
// reloads itself, so it stays live. It reads the snapshot the band and the pane read, plus a few files of the change
// folders; it writes only that one file. `$` is passed only to plain top-level functions.
import { atom, read } from 'claude-code'
import type { EngineInterface, On } from 'claude-code'

import { ensureCollector } from './collector'
import { boardHtml } from './board-page'
import { BOARD_FILE, BOARD_PATH_TEXT, BOARD_WRITE_MS, boardData } from './core/board-html'
import type { ChangeFiles } from './core/board-html'
import { leaseState } from './core/states'
import { dir, readLease } from './store'
import type { State } from './store'
import type { Snapshot } from './types'

type Engine = EngineInterface
// The collector writes it; the band, the pane and the board read it. The same literal, declared where it is read.
const snapshot = atom({ plugin: 'agent-tracker', key: 'snapshot' } as const, { at: 0, agentsOk: true, okAt: 0, failedReads: 0, sessions: [] } as Snapshot)

export const BOARD_OPENED = `Board opened: ${BOARD_PATH_TEXT}`
export const BOARD_NOT_OPENED = `Board written to ${BOARD_PATH_TEXT}, but no browser could be opened. Open that file yourself.`

const CHANGES_EVERY_MS = 60_000 // the change folders are read again at most once a minute
const REPOS_MAX = 30
const WEEK_MS = 7 * 24 * 3600 * 1000
// Per mod registration (a reload or a test starts clean): the timer is running, a write is in flight, the last read of the change folders.
const timers = new WeakSet<State>()
const writing = new WeakSet<State>()
const changeCache = new WeakMap<State, { at: number; list: ChangeFiles[] }>()

async function text($: Engine, path: string) {
  const t = await $.fs.read(path).catch(() => null)
  return typeof t === 'string' ? t : undefined
}

// Every changes/*/milestone.md of the repos the sessions of the last week work in, with the files the pages read.
async function readChanges($: Engine, snap: Snapshot, now: number): Promise<ChangeFiles[]> {
  const places = new Map<string, string>() // folder holding changes/ -> its repo
  for (const r of snap.sessions) {
    if (r.repo === null || (r.state === 'ended' && Math.max(r.lastActivityAt, r.endedAt ?? 0) < now - WEEK_MS)) continue
    places.set(r.repo.path, r.repo.path)
    if (r.milestone !== null) places.set(r.cwd, r.repo.path) // a worktree holds its own copy of the change folders
  }
  const out: ChangeFiles[] = []
  const seen = new Set<string>()
  for (const [folder, repoPath] of [...places].slice(0, REPOS_MAX)) {
    const entries = await $.fs.list(`${folder}/changes`).catch(() => [])
    for (const e of entries.filter(e => e.kind === 'dir' && e.name !== 'archive')) {
      const base = `${folder}/changes/${e.name}`
      const milestone = await text($, `${base}/milestone.md`)
      if (milestone === undefined || seen.has(`${repoPath}|${e.name}`)) continue
      seen.add(`${repoPath}|${e.name}`)
      out.push({
        repoPath,
        folder: e.name,
        milestone,
        facts: await text($, `${base}/facts.md`),
        validation: await text($, `${base}/validation.md`),
        questions: await text($, `${base}/questions.md`),
        findings: await text($, `${base}/findings.md`),
        done: await text($, `${base}/done.json`),
      })
    }
  }
  return out
}

async function boardPath($: Engine) {
  return `${await dir($)}/${BOARD_FILE}`
}

async function writeBoard($: Engine, s: State, fresh: boolean) {
  const snap = await read($, snapshot)
  const now = await $.clock.now()
  let cached = changeCache.get(s)
  if (fresh || cached === undefined || now - cached.at >= CHANGES_EVERY_MS) {
    cached = { at: now, list: await readChanges($, snap, now) }
    changeCache.set(s, cached)
  }
  await $.fs.write(await boardPath($), boardHtml(boardData(snap, cached.list, now)))
}

// Only the session holding the poller lease writes on the timer, so one mod writes the file; and only once a board
// exists, so a machine that never asked for the page never gets the file.
async function rewrite($: Engine, s: State) {
  if (writing.has(s)) return
  writing.add(s)
  try {
    const me = await $.session.id()
    if (leaseState(await readLease($, await dir($)), me, await $.clock.now()) !== 'mine') return
    if (!(await $.fs.exists(await boardPath($)).catch(() => false))) return
    await writeBoard($, s, false)
  } finally {
    writing.delete(s)
  }
}

// shortcut: the timer starts at the first turn of a session or at `/tracker web`, so an idle session that holds the lease and never gets a turn leaves the file as it was; start it from session.start in collector.ts if that shows up.
function startTimer($: Engine, s: State) {
  if (timers.has(s)) return
  timers.add(s)
  $.clock.every(BOARD_WRITE_MS, () => void rewrite($, s).catch(() => undefined))
}

// Build the page fresh, write it and open it in the browser; the text for the command's answer.
export async function openBoard($: Engine, s: State): Promise<string> {
  await ensureCollector($, s)
  startTimer($, s)
  try {
    await writeBoard($, s, true)
  } catch {
    return `Board could not be written to ${BOARD_PATH_TEXT}. Check that the agent-tracker folder in your Claude folder can be written.`
  }
  const system = await $.process.run(['uname', '-s'], { timeoutMs: 5000 }).catch(() => null)
  const opener = system !== null && system.stdout.trim() === 'Darwin' ? 'open' : 'xdg-open'
  const run = await $.process.run([opener, await boardPath($)], { timeoutMs: 10_000 }).catch(() => null)
  return run !== null && run.exitCode === 0 ? BOARD_OPENED : BOARD_NOT_OPENED
}

export const registerBoard = (on: On, s: State) => {
  // `/tracker web` only; every other word goes on (the band's and the pane's).
  on('command.run', { command: 'tracker' }, async ($, e, next) => {
    if (e.args.trim().toLowerCase() !== 'web') return next(e)
    return { text: await openBoard($, s) }
  })

  on('turn.start', async ($, e, next) => {
    startTimer($, s)
    return next(e)
  })
}
