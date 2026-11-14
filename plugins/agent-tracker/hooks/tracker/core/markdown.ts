// The band's state as Markdown for the clipboard (F36, F85): the four counts, one line per session that needs you or
// runs, then the open PRs with their state. A session line holds a repo name, a title and a time; never a path.
import type { BandData } from './band-model'
import { duration } from './format'
import type { Line } from './rank'

const one = (s: string) => s.replace(/\s+/g, ' ').trim()
const session = (l: Line, verb: string) => `- ${one(l.repo)}: ${one(l.title)}, ${verb}${l.ms === null ? '' : ` ${duration(l.ms)}`}`

const REVIEW = { approved: 'approved', changes: 'changes requested', requested: 'review requested', none: 'no review' } as const
const MERGE = { mergeable: 'mergeable', conflicts: 'conflicts', unknown: 'merge state unknown' } as const

export const stateMarkdown = (d: BandData): string => {
  const out = ['## Tracker state', '']
  out.push(`- **Needs you:** ${d.needs.length}`, `- **Running:** ${d.running.length}`, `- **Done:** ${d.done.length}`)
  if (d.prs) out.push(`- **PRs:** ${d.prs.open} open, ${d.prs.failing} failing`)
  if (d.needs.length > 0) out.push('', '### Needs you', ...d.needs.map(l => session(l, l.self ? 'waiting (this session)' : 'waiting')))
  if (d.running.length > 0) out.push('', '### Running', ...d.running.map(l => session(l, 'running')))
  if (d.prs && d.prs.rows.length > 0) {
    out.push('', '### Open PRs')
    for (const { repo, pr } of d.prs.rows) out.push(`- ${one(repo)} #${pr.number} ${one(pr.title)} (checks ${pr.checks}, ${REVIEW[pr.review]}, ${MERGE[pr.mergeable]})`)
  }
  return `${out.join('\n')}\n`
}
