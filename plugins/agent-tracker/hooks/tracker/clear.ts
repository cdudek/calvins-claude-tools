// Clear on the Session page, the run after the owner's press of "Clear session": read `claude agents --json` again, run
// `claude rm <job id>` for a listed row with no process, then close the session's tasks. Never `claude stop`, never a flag,
// never a shell. `$` is passed only to plain top-level functions.
import type { EngineInterface } from 'claude-code'

import { decide, parseAgents, reasonOf } from './core'
import type { Outcome } from './core'
import { markTask, unmarkTask } from './store'
import type { State } from './store'
import type { AgentRow } from './types'

type Engine = EngineInterface
const RM_MS = 15_000 // a `claude rm` that asks a question or hangs ends here, as the error line

// The list as the press sees it, read now; null: it could not be read.
async function readRows($: Engine): Promise<AgentRow[] | null> {
  const run = await $.process.run(['claude', 'agents', '--json'], { timeoutMs: 10_000 }).catch(() => null)
  return run !== null && run.exitCode === 0 ? parseAgents(run.stdout) : null
}

// `keys`: the tasks Home lists for the session, from the page. The outcome says what was written, so nothing else did.
export async function clearSession($: Engine, s: State, sessionId: string, keys: string[]): Promise<{ outcome: Outcome; left: boolean }> {
  const step = decide(await readRows($), sessionId)
  if (step.do === 'refuse') return { outcome: step.outcome, left: false }
  let left = false
  if (step.do === 'rm') {
    const rm = await $.process.run(['claude', 'rm', step.id], { timeoutMs: RM_MS }).catch(() => null)
    left = rm !== null && rm.exitCode === 0
    // Whatever it said, only the list decides: a session that is gone is not an error, one that is still there is.
    if (!left && decide(await readRows($), sessionId).do !== 'skip') return { outcome: { kind: 'failed', reason: reasonOf(rm?.stderr || rm?.stdout) }, left: false }
  }
  const failed = keys.length === 0 ? null : await markTask($, s, 'closed', keys, true)
  return { outcome: failed === null ? { kind: 'cleared', left, closed: keys } : { kind: 'partly', reason: reasonOf(failed), left }, left }
}

// Reopen tasks: the closed marks of those keys go. A failed save changes nothing and says so by returning false.
export async function reopenTasks($: Engine, s: State, keys: string[]): Promise<boolean> {
  return (await unmarkTask($, s, keys)) === null
}
