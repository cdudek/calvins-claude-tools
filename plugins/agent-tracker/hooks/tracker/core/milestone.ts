import type { SessionRecord } from '../types'

export type Milestone = NonNullable<SessionRecord['milestone']> & { branch: string }

const front = (text: string, key: string) => new RegExp(`^${key}:\\s*(.+?)\\s*$`, 'm').exec(/^---\n([\s\S]*?)\n---/.exec(text)?.[1] ?? '')?.[1]

// An sdlc-run milestone.md: `milestone:` and `branch:` in the frontmatter, the first "> " line as the sentence,
// and the Features table (# | Change | Feature | PR or commit | State).
export const parseMilestone = (text: string): Milestone | null => {
  const slug = front(text, 'milestone')
  const branch = front(text, 'branch')
  if (!slug || !branch) return null
  const sentence = /^>\s*(.+)$/m.exec(text)?.[1] ?? ''
  const features: Milestone['features'] = []
  for (const line of text.split('\n')) {
    const cells = line.split('|').map(c => c.trim())
    if (cells.length >= 6 && /^\d+$/.test(cells[1]!)) features.push({ n: Number(cells[1]), name: cells[3]!, state: cells[5]! })
  }
  return { slug, branch, sentence, features }
}

// A feature is complete when its state is `done` (one go: `done <sha>`) or `merged` (F71).
export const isComplete = (state: string) => /^(done|merged)\b/.test(state)
export const completeCount = (features: { state: string }[]) => features.filter(f => isComplete(f.state)).length
