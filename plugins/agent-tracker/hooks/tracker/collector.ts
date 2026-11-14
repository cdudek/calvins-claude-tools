// The collector: the one poller (by lease), this session's record from the list, and the merge into `snapshot`.
import { atom, read, update } from 'claude-code'
import type { EngineInterface, On } from 'claude-code'

import { startBackfill } from './backfill'
import { LEASE_GEN, POLL_MS, agentsFresh, clean, deriveState, leaseState, mergeSessions, noteTool, parseAgents } from './core'
import { startScan } from './scan'
import type { AgentRow, Lease, SessionRecord, Snapshot } from './types'
import { dir, initOwn, readAgentsFile, readEntrypoints, readFolder, readLateChecks, readLease, saveOwn, where, writeJson } from './store'
import type { State } from './store'

type Engine = EngineInterface
// What the band and the pane read. The engine's source scan wants this declared where it is updated.
const snapshot = atom({ plugin: 'agent-tracker', key: 'snapshot' } as const, { at: 0, agentsOk: true, okAt: 0, failedReads: 0, sessions: [] } as Snapshot)
const RESCAN_MS = 60_000 // branch and milestone are read again about once a minute
const GOAL_END = /^(clear|off|stop|cancel)\b/i

// One poll: take or keep the lease and run `claude agents --json`, or read the holder's agents.json (F127 to F129).
async function readAgents($: Engine, base: string, me: string, now: number): Promise<AgentRow[] | null> {
  if (leaseState(await readLease($, base), me, now) === 'other') {
    const f = await readAgentsFile($, base)
    return f !== null && agentsFresh(f.readAt, now) ? f.agents : null // old or unreadable counts as failed
  }
  // No fresh lease, or this session's own: write it (taking it when free) and poll. The API has no rename, so the
  // files are written whole and a reader keeps its last good copy (questions.md Q2).
  await writeJson($, `${base}/poller.json`, { v: 1, sessionId: me, heartbeat: now, gen: LEASE_GEN } satisfies Lease).catch(() => undefined)
  const run = await $.process.run(['claude', 'agents', '--json'], { timeoutMs: 10_000 }).catch(() => null)
  const agents = run !== null && run.exitCode === 0 ? parseAgents(run.stdout) : null
  if (agents !== null) await writeJson($, `${base}/agents.json`, { v: 1, readAt: now, agents }).catch(() => undefined)
  return agents
}

async function tick($: Engine, s: State) {
  if (s.isTicking) return
  s.isTicking = true
  try {
    await initOwn($, s)
    const first = s.mine
    if (first === null) return
    const now = await $.clock.now()
    const base = await dir($)
    const agents = await readAgents($, base, first.sessionId, now)
    const subagents = (await $.agent.list().catch(() => [])).map(a => ({ id: a.id, name: clean(a.description, 200), status: String(a.status) }))
    const scan = now - s.scannedAt >= RESCAN_MS ? await where($, first.cwd) : null
    if (scan !== null) s.scannedAt = now

    await saveOwn($, s, r => {
      if (r.endedAt !== null) return r
      const row = agents?.find(a => a.sessionId === r.sessionId)
      let next: SessionRecord = { ...r, ...(scan ?? {}), runs: { ...r.runs, subagents } }
      if (agents !== null) {
        const background = agents.filter(a => a.kind === 'background' && a.state !== 'done' && a.cwd === r.cwd)
        next.runs = { ...next.runs, background: background.map(a => ({ id: a.sessionId, name: a.name, since: a.startedAt })) }
      }
      if (row) {
        const same = r.engine.status === row.status && r.engine.state === row.state && r.engine.waitingFor === row.waitingFor
        next = {
          ...next,
          kind: row.kind,
          title: row.name || r.title,
          engine: { status: row.status, state: row.state, waitingFor: row.waitingFor, since: same ? r.engine.since : now },
          ...deriveState(row, r.questionFlag !== null),
        }
      }
      return next
    })

    const own = s.mine
    if (own === null) return
    const files = (await readFolder($, s, `${base}/sessions`)).filter(f => f.sessionId !== own.sessionId)
    const transcripts = await readFolder($, s, `${base}/transcripts`)
    const sessions = mergeSessions({ files: [...files, own], transcripts, agents, now, selfId: own.sessionId, seen: s.seen, entrypoints: (await readEntrypoints($, base)).by, late: (await readLateChecks($, base)).by })
    s.failedReads = agents !== null ? 0 : s.failedReads + 1
    if (agents !== null) {
      s.okAt = now
      s.seen = new Set(agents.map(a => a.sessionId))
    }
    await update($, snapshot, () => ({ at: now, agentsOk: agents !== null, okAt: s.okAt, failedReads: s.failedReads, sessions }))
  } finally {
    s.isTicking = false
  }
}

// The first poll now, then one every 5 seconds; the backfill and the repo scan run beside it, each on its own timer.
async function begin($: Engine, s: State) {
  await tick($, s).catch(() => undefined)
  if (!s.hasTimer) {
    s.hasTimer = true
    $.clock.every(POLL_MS, () => void tick($, s).catch(() => undefined))
    startBackfill($, s)
    startScan($, s)
  }
}

// A mod installed or reloaded mid-session never gets session.start, so its snapshot would stay empty: the first draw
// of the band or the pane starts the collector instead. Once per session, and the draw does not wait for the poll.
export async function ensureCollector($: Engine, s: State) {
  if (s.hasCollector || (await read($, snapshot)).at !== 0 || s.hasCollector) return
  s.hasCollector = true
  void begin($, s).catch(() => undefined)
}

export const registerCollector = (on: On, s: State) => {
  on('session.start', async ($, e, next) => {
    const r = await next(e)
    s.headless = e.isInteractive === false
    s.hasCollector = true
    void begin($, s).catch(() => undefined) // the first poll runs on; the session does not wait for `claude agents --json`
    return r
  })

  on('session.end', async ($, e, next) => {
    const r = await next(e)
    try {
      const now = await $.clock.now()
      await saveOwn($, s, m => ({ ...m, endedAt: now, state: 'ended', reason: null }))
      // A /clear goes on under a new session id with no session.start: the next poll starts a record for it.
      if (e.reason === 'clear') s.mine = null
    } catch {
      // an observer never fails the session
    }
    return r
  })

  // Tool errors and retries (F21), and a goal the model proposes. Tokens come at turn.complete, in asks.ts: the
  // engine's scan allows one hook per event without a matcher.
  on('tool.call', async ($, e, next) => {
    const r = await next(e)
    try {
      const failed = !('deny' in r) && r.isError === true
      // The call's name and input, without the ids that differ between two identical calls.
      const { tool_use_id: _id, agentId: _agent, ...input } = e as unknown as Record<string, unknown>
      const before = s.mine?.usage ?? { tokensIn: 0, tokensOut: 0, toolErrors: 0, retries: 0 }
      const step = noteTool(before, s.lastCall, JSON.stringify(input), failed)
      s.lastCall = step.last
      if (String(e.tool) === 'ProposeGoal' && !failed && !('deny' in r)) {
        const now = await $.clock.now()
        await saveOwn($, s, m => ({ ...m, runs: { ...m.runs, goalSince: now } }))
      } else if (step.usage.toolErrors !== before.toolErrors || step.usage.retries !== before.retries) {
        await saveOwn($, s, m => ({ ...m, usage: step.usage }))
      }
    } catch {
      // an observer never fails the call
    }
    return r
  })

  on('command.run', { command: 'goal' }, async ($, e, next) => {
    const r = await next(e)
    const args = e.args.trim()
    if (args !== '') {
      const now = await $.clock.now()
      await saveOwn($, s, m => ({ ...m, runs: { ...m.runs, goalSince: GOAL_END.test(args) ? null : now } })).catch(() => undefined)
    }
    return r
  })
}
