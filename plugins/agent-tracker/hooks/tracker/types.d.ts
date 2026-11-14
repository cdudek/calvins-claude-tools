// The data the mod keeps, one place. v is the shape tag: a reader skips a file whose v it does not know.
// `source` is 'engine' for a session only `claude agents --json` lists (no file, no mod).

export type SessionState = 'running' | 'needs-you' | 'done' | 'ended'
export type Reason = 'permission' | 'question' | 'waiting' | 'unknown'

export type Engine = { status?: string; state?: string; waitingFor?: string | null; since: number | null } // since null: unknown (no mod file saw the session change)

export type Ask = {
  n: number
  text: string
  kind: 'task' | 'question' | 'not-classified'
  status: 'in-progress' | 'needs-you' | 'replied'
  at: number
  // The haiku read at turn.complete of a task ask: done, partly done, not started, or replaced by the later ask `replacedBy`. Absent: not judged.
  verdict?: 'done' | 'partly' | 'not-started' | 'replaced'
  replacedBy?: number
  source?: 'late' // the verdict came from the one late check, not from a turn's notes call
}

// A line the agent's last message gave (haiku reads it at turn.complete): kind `know` is a side effect, a risk, an odd finding
// or a skipped step; `decided` is a call the agent made without asking. `seen` stays false here: what the owner has seen
// lives in settings.json, because a session writes only its own file.
export type Note = { id: string; kind: 'know' | 'decided'; text: string; at: number; seen: boolean }

export type Pr = {
  number: number
  title: string
  url: string
  branch: string
  createdAt: string
  checks: 'pass' | 'failing' | 'running'
  review: 'approved' | 'changes' | 'requested' | 'none'
  mergeable: 'mergeable' | 'conflicts' | 'unknown'
  behind?: boolean // gh's mergeStateStatus is BEHIND; absent in a PR stored before the field
}

export type SessionRecord = {
  v: 1
  sessionId: string
  source: 'mod' | 'transcript' | 'engine'
  writtenAt: number
  kind: 'interactive' | 'background'
  title: string | null
  cwd: string
  repo: { path: string; name: string } | null
  branch: string | null
  startedAt: number
  lastActivityAt: number
  endedAt: number | null
  engine: Engine
  state: SessionState
  reason: Reason | null
  // The engine value that made the state unknown (F66), else null.
  unknownValue: string | null
  questionFlag: { at: number } | null
  usage: { tokensIn: number; tokensOut: number; toolErrors: number; retries: number }
  entrypoint?: string // how the session was started, from its transcript; sdk-* is an automated run
  headless?: boolean // a `claude -p` or SDK run: no model call, never on a list or in a count
  asks: Ask[]
  notes?: Note[] // at most 50, newest kept; absent in a record written before the field
  runs: {
    goalSince: number | null
    subagents: { id: string; name: string; status: string }[]
    background: { id: string; name: string; since: number }[]
  }
  milestone: { slug: string; sentence: string; features: { n: number; name: string; state: string }[] } | null
  // `github: false`: the origin is not on github.com, gh was never asked, and no PR line shows (R9).
  scan: { at: number; ghOk: boolean; github?: false; worktrees: { path: string; branch: string | null }[]; prs: Pr[] } | null
}

// One row of `claude agents --json`, the 2.1.323 fields the mod reads.
export type AgentRow = {
  sessionId: string
  cwd: string
  name: string
  startedAt: number
  kind: 'interactive' | 'background'
  status?: string
  state?: string
  waitingFor?: string | null
}

// Beside the session files, for what one session reads of another's: the entrypoint of each transcript of the week (`cli`,
// `claude-desktop`, `sdk-ts`, ...; empty: not found), and the one late check of each session with unchecked tasks.
export type Entrypoints = { v: 1; by: Record<string, string> }
export type LateVerdict = { n: number; verdict: NonNullable<Ask['verdict']>; by?: number }
export type LateChecks = { v: 1; by: Record<string, { at: number; verdicts: LateVerdict[] }> }
export type Lease = { v: 1; sessionId: string; heartbeat: number; gen?: number } // gen absent: written by 0.1.x
export type AgentsFile = { v: 1; readAt: number; agents: AgentRow[] }
// seen: the notes the owner marked, `<session>:<note id>` or a file note's key, newest last. kept, closed: the owner's marks on a task
// ask, `<session>:<ask n>`, newest last; only the pane writes them.
export type Settings = { v: 1; view: 'compact' | 'details'; bandHidden: boolean; seen: string[]; kept: string[]; closed: string[] }

// What the band and the pane read: every session merged, and whether the list read was good.
// `okAt` is the time of the last good list read (0: none yet) and `failedReads` the failed reads in a row: two or
// more is stale (F52, F123). `at` 0 is the untouched value: the first read is still pending (F53).
export type Snapshot = { at: number; agentsOk: boolean; okAt: number; failedReads: number; sessions: SessionRecord[] }

declare module 'claude-code' {
  interface PluginState {
    'agent-tracker': { snapshot: Snapshot }
  }
}
