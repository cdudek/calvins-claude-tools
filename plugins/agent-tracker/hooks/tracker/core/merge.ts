import type { AgentRow, SessionRecord } from '../types'
import { labelRepos } from './repo'
import { resolveState } from './states'
import { WEEK_MS, emptyRecord } from './types'

type In = {
  files: SessionRecord[] // sessions/ files, one per session whose mod wrote it
  transcripts: SessionRecord[] // transcripts/ files, used only when no sessions/ file has the id
  agents: AgentRow[] | null // null: the list read failed or is old
  now: number
  selfId: string
}

// Every record merged into one list (F68). A sessions/ file wins over a transcripts/ file; a session the list
// shows and no file has appears from the list alone (source 'engine'); only the last 7 days show.
export const mergeSessions = ({ files, transcripts, agents, now, selfId }: In): SessionRecord[] => {
  const byId = new Map<string, SessionRecord>()
  for (const r of [...transcripts, ...files]) byId.set(r.sessionId, r)
  for (const a of agents ?? []) {
    if (byId.has(a.sessionId)) continue
    byId.set(a.sessionId, { ...emptyRecord(a.sessionId, a.cwd, a.startedAt), source: 'engine', kind: a.kind, title: a.name || null, engine: { since: null } })
  }
  const live = new Map((agents ?? []).map(a => [a.sessionId, a]))
  const merged = [...byId.values()].map(r => {
    const agent = live.get(r.sessionId)
    const d = resolveState(r, agent, agents !== null, r.sessionId === selfId)
    return {
      ...r,
      title: agent?.name || r.title,
      kind: agent?.kind ?? r.kind,
      engine: agent ? { status: agent.status, state: agent.state, waitingFor: agent.waitingFor, since: r.source === 'mod' ? r.engine.since : null } : r.engine,
      ...d,
    }
  })
  return labelRepos(merged.filter(r => r.state !== 'ended' || now - r.lastActivityAt <= WEEK_MS))
}
