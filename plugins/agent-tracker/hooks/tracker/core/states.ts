import type { AgentRow, Ask, Lease, Reason, SessionRecord, SessionState } from '../types'
import { clean } from './format'
import { LEASE_FRESH_MS, PERMISSION_WAITING_FOR } from './types'

type Engine = Pick<AgentRow, 'kind' | 'status' | 'state' | 'waitingFor'>
export type Derived = { state: SessionState; reason: Reason | null; unknownValue: string | null }

const text = (v: unknown) => (typeof v === 'string' ? v : undefined)

// The list `claude agents --json` prints, pinned to the 2.1.323 fields. null: not a list, so a failed read.
export const parseAgents = (json: string): AgentRow[] | null => {
  let list: unknown
  try {
    list = JSON.parse(json)
  } catch {
    return null
  }
  if (!Array.isArray(list)) return null
  const out: AgentRow[] = []
  for (const a of list as Record<string, unknown>[]) {
    const sessionId = text(a?.sessionId)
    if (sessionId === undefined) continue
    out.push({
      sessionId,
      cwd: text(a.cwd) ?? '',
      name: clean(a.name, 200),
      startedAt: typeof a.startedAt === 'number' ? a.startedAt : 0,
      kind: a.kind === 'background' ? 'background' : 'interactive',
      status: text(a.status),
      state: text(a.state),
      waitingFor: text(a.waitingFor) ?? null,
    })
  }
  return out
}

const none = { reason: null, unknownValue: null } as const
const waits = (e: Engine, permission: string | null): Derived => ({
  state: 'needs-you',
  reason: permission !== null && e.waitingFor === permission ? 'permission' : 'waiting',
  unknownValue: null,
})
const unknown = (raw: string | undefined): Derived => ({ state: 'needs-you', reason: 'unknown', unknownValue: raw ?? '' })

// A background session reads `state`, an interactive one `status` (a background row carries both).
export const deriveState = (e: Engine, flagged: boolean, permission: string | null = PERMISSION_WAITING_FOR): Derived => {
  if (e.kind === 'background') {
    if (e.state === 'working') return { state: 'running', ...none }
    if (e.state === 'blocked') return waits(e, permission)
    if (e.state === 'done') return { state: 'ended', ...none }
    return unknown(e.state)
  }
  if (e.status === 'busy') return { state: 'running', ...none }
  if (e.status === 'waiting') return waits(e, permission)
  if (e.status === 'idle') return flagged ? { state: 'needs-you', reason: 'question', unknownValue: null } : { state: 'done', ...none }
  return unknown(e.status)
}

// The session's state from its record and the list. Absent from a good list is ended (F6); a failed read, or the
// session this mod runs in (it is live by definition), keeps the last state.
export const resolveState = (r: SessionRecord, agent: AgentRow | undefined, agentsOk: boolean, isSelf: boolean): Derived => {
  if (r.endedAt !== null) return { state: 'ended', ...none }
  if (agent) return deriveState(agent, r.questionFlag !== null)
  if (agentsOk && !isSelf) return { state: 'ended', ...none }
  return { state: r.state, reason: r.reason, unknownValue: r.unknownValue }
}

const isFresh = (at: number, now: number) => now - at < LEASE_FRESH_MS

// Who holds the poller lease: nobody fresh, this session, or another (F127).
export const leaseState = (lease: Lease | null, sessionId: string, now: number): 'free' | 'mine' | 'other' =>
  lease === null || !isFresh(lease.heartbeat, now) ? 'free' : lease.sessionId === sessionId ? 'mine' : 'other'

// An agents.json older than 15 s counts as a failed read (F129).
export const agentsFresh = (readAt: number, now: number) => isFresh(readAt, now)

// Only a "?" in the final paragraph makes a message worth the model check (F17, F132).
export const finalParagraphHasQuestion = (message: string) => {
  const paragraphs = message.split(/\n\s*\n/).map(p => p.trim()).filter(Boolean)
  return paragraphs.length > 0 && paragraphs[paragraphs.length - 1]!.includes('?')
}

// Ask status is derived, never set by hand (F16): earlier asks are replied; the last follows the turn and the state.
export const askStatuses = (asks: Ask[], state: SessionState, turnOpen: boolean): Ask[] =>
  asks.map((a, i) => {
    if (i < asks.length - 1) return { ...a, status: 'replied' as const }
    return { ...a, status: state === 'needs-you' ? ('needs-you' as const) : turnOpen ? ('in-progress' as const) : ('replied' as const) }
  })
