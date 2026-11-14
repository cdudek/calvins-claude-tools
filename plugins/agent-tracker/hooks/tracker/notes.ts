// The items of "You should know" and "Decided without you": the notes in the snapshot, and the open questions and plan
// revisions of each live repo's change folders, read as files. It only reads. `$` is passed only to plain top-level functions.
import type { EngineInterface } from 'claude-code'

import { isLive, isMerged, isNumbered, mergedKey, noteItems, taskItems } from './core'
import type { Change, NoteItem, TaskItem } from './core'
import { changesOf } from './changes'
import { readSettings } from './store'
import type { State } from './store'
import type { Snapshot } from './types'

type Engine = EngineInterface
const REPOS_MAX = 6 // the repos with a live session whose change folders are read

export async function itemsOf($: Engine, s: State, snap: Snapshot, now: number): Promise<NoteItem[]> {
  const seen = new Set((await readSettings($, s)).seen)
  const paths = [...new Set(snap.sessions.filter(r => r.repo !== null && isLive(r) && !isNumbered(r)).map(r => r.repo!.path))].slice(0, REPOS_MAX)
  const changes = new Map<string, Change[]>()
  for (const path of paths) changes.set(path, await changesOf($, s, snap, path, now).catch(() => []))
  return noteItems(snap, changes, seen, now)
}

// The tasks not done. A task whose session's branch is a merged change is done, so the repos of the open ones are read for that.
export async function tasksOf($: Engine, s: State, snap: Snapshot, now: number): Promise<TaskItem[]> {
  const { kept, closed } = await readSettings($, s)
  const marks = { kept: new Set(kept), closed: new Set(closed), merged: new Set<string>() }
  const open = taskItems(snap, now, marks)
  const paths = [...new Set(open.flatMap(t => snap.sessions.find(r => r.sessionId === t.sessionId)?.repo?.path ?? []))].slice(0, REPOS_MAX)
  for (const path of paths) for (const c of await changesOf($, s, snap, path, now).catch(() => [])) if (isMerged(c)) marks.merged.add(mergedKey(path, c.branch))
  return marks.merged.size === 0 ? open : taskItems(snap, now, marks)
}
