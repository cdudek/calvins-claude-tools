import type { AgentRow, Ask, Entrypoints, LateChecks, SessionRecord } from '../types'
import { labelRepos } from './repo'
import { resolveState } from './states'
import { WEEK_MS, emptyRecord } from './types'

type In = {
  files: SessionRecord[] // sessions/ files, one per session whose mod wrote it
  transcripts: SessionRecord[] // transcripts/ files, used only when no sessions/ file has the id
  agents: AgentRow[] | null // null: the list read failed or is old
  now: number
  selfId: string
  entrypoints?: Entrypoints['by'] // how each session was started; an sdk-* run is automated and left out
  late?: LateChecks['by'] // the one late verdict of a session, given to the asks no turn judged
  seen?: ReadonlySet<string> // the sessions the last good list read showed; a failed read restores only these
}

// The engine refuses a state value over 4 MiB, and the snapshot is one: with thousands of transcripts in a week the
// write failed and the band stayed on "Reading sessions…" for good. This session first, then sessions the mod or the list
// knows, then the latest history, until 3 million characters.
export const SNAPSHOT_MAX_CHARS = 3_000_000
const fitSnapshot = (sessions: SessionRecord[], selfId: string) => {
  const first = (r: SessionRecord) => Number(r.sessionId === selfId) * 2 + Number(r.source !== 'transcript')
  const ranked = [...sessions].sort((a, b) => first(b) - first(a) || b.lastActivityAt - a.lastActivityAt)
  const keep = new Set<SessionRecord>()
  let size = 0
  for (const r of ranked) {
    size += JSON.stringify(r).length + 1
    if (size > SNAPSHOT_MAX_CHARS && keep.size > 0) break
    keep.add(r)
  }
  return sessions.filter(r => keep.has(r))
}

// Every record merged into one list (F68). A sessions/ file wins over a transcripts/ file; a session the list
// shows and no file has appears from the list alone (source 'engine'); only the last 7 days show.
export const isAutomated = (entrypoint: string | undefined) => entrypoint !== undefined && entrypoint.startsWith('sdk')

export const mergeSessions = ({ files, transcripts, agents, now, selfId, seen, entrypoints = {}, late = {} }: In): SessionRecord[] => {
  const byId = new Map<string, SessionRecord>()
  for (const r of [...transcripts, ...files]) byId.set(r.sessionId, r)
  for (const a of agents ?? []) {
    if (byId.has(a.sessionId)) continue
    byId.set(a.sessionId, { ...emptyRecord(a.sessionId, a.cwd, a.startedAt), source: 'engine', kind: a.kind, title: a.name || null, engine: { since: null } })
  }
  const live = new Map((agents ?? []).map(a => [a.sessionId, a]))
  const merged = [...byId.values()].map(r => {
    const agent = live.get(r.sessionId)
    const d = resolveState(r, agent, agents !== null, r.sessionId === selfId, seen)
    const entrypoint = entrypoints[r.sessionId] || r.entrypoint
    const verdicts = late[r.sessionId]?.verdicts ?? []
    const asks: Ask[] = verdicts.length === 0 ? r.asks : r.asks.map(a => { const v = a.kind === 'task' && a.verdict === undefined ? verdicts.find(x => x.n === a.n) : undefined; return v ? { ...a, verdict: v.verdict, ...(v.by !== undefined ? { replacedBy: v.by } : {}), source: 'late' as const } : a })
    return {
      ...r,
      asks,
      ...(entrypoint ? { entrypoint } : {}),
      ...(isAutomated(entrypoint) ? { headless: true } : {}),
      title: agent?.name || r.title,
      kind: agent?.kind ?? r.kind,
      engine: agent ? { status: agent.status, state: agent.state, waitingFor: agent.waitingFor, since: r.source === 'mod' ? r.engine.since : null } : r.engine,
      ...d,
    }
  })
  // A headless or sdk-* run is nobody's work: it never reaches the snapshot, so no list, count or band sees it.
  return fitSnapshot(labelRepos(merged.filter(r => r.headless !== true && (r.state !== 'ended' || now - r.lastActivityAt <= WEEK_MS))), selfId)
}
