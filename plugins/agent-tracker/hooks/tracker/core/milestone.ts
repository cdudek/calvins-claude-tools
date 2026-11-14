import type { SessionRecord } from '../types'
import { clean } from './format'

export type Milestone = NonNullable<SessionRecord['milestone']> & { branch: string }

const MAX = 200 // a repo file reaches the screen only through clean()
const front = (text: string, key: string) => new RegExp(`^${key}:\\s*(.+?)\\s*$`, 'm').exec(/^---\n([\s\S]*?)\n---/.exec(text)?.[1] ?? '')?.[1]

// An sdlc-run milestone.md: `milestone:` and `branch:` in the frontmatter, the first "> " line as the sentence,
// and the Features table (# | Change | Feature | PR or commit | State).
export const parseMilestone = (text: string): Milestone | null => {
  const slug = clean(front(text, 'milestone'), MAX)
  const branch = front(text, 'branch')
  if (!slug || !branch) return null
  const sentence = clean(/^>\s*(.+)$/m.exec(text)?.[1], MAX)
  const features: Milestone['features'] = []
  for (const line of text.split('\n')) {
    const cells = line.split('|').map(c => c.trim())
    if (cells.length >= 6 && /^\d+$/.test(cells[1]!)) features.push({ n: Number(cells[1]), name: clean(cells[3], MAX), state: clean(cells[5], MAX) })
  }
  return { slug, branch, sentence, features }
}

// A feature is complete when its state is `done` (one go: `done <sha>`) or `merged` (F71).
export const isComplete = (state: string) => /^(done|merged)\b/.test(state)
export const completeCount = (features: { state: string }[]) => features.filter(f => isComplete(f.state)).length
