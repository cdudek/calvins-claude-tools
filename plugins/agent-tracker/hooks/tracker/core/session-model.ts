// The Session page, as the owner's "Session detail" mockup draws it (2026-11-14): the state at the top right, then one
// line each for the branch, the tokens, the struggles, what runs, the milestone, the asks and the PR. A line with no data
// behind it is not drawn (no model, context or cost: the collector does not have them).
import type { Ask, SessionRecord, Snapshot } from '../types'
import { cut, duration, plural, resumeCommand, tokens } from './format'
import { repoPrs } from './git'
import { featureKind } from './change'
import { completeCount } from './milestone'
import { repoLabel } from './rank'
import { DOT, bar, dim, join, sp } from './paint'
import type { Spans } from './paint'
import { REASON, endedAt, firstKey, hint, tidy } from './pane-model'
import type { Block, Local, PaneModel } from './pane-model'
import { checksGlyph } from './repo-model'
import { CHECKS_WORDS, DETACHED, FROM_TRANSCRIPT, MERGE_WORDS, PANE_BUTTONS, REVIEW_WORDS, UNTITLED } from './words'

export const SESSION_ASKS_SHOWN = 6


// "● permission 4m", "◐ running 3m", "✓ done 3m ago", "○ ended 2h ago", in the state's colour.
const stateSpans = (r: SessionRecord, now: number): Spans => {
  const since = r.engine.since === null ? null : duration(now - r.engine.since)
  switch (r.state) {
    case 'needs-you':
      return [sp(`● ${[r.reason === 'unknown' ? `state unknown (${r.unknownValue ?? ''})` : REASON[r.reason ?? 'waiting'], since].filter(Boolean).join(' ')}`, 'red')]
    case 'running':
      return [sp(`◐ ${['running', since].filter(Boolean).join(' ')}`, 'yellow')]
    case 'done':
      return [sp(`✓ ${['done', since === null ? null : `${since} ago`].filter(Boolean).join(' ')}`, 'green')]
    default:
      return [dim(`○ ended ${duration(now - endedAt(r))} ago`)]
  }
}

const line = (label: string, ...rest: Spans): Spans => [dim(`${label} `), ...rest]

export const sessionModel = (snap: Snapshot, id: string, now: number, local: Local, columns: number): PaneModel | null => {
  const r = snap.sessions.find(x => x.sessionId === id)
  if (r === undefined) return null
  const title = r.title ?? UNTITLED
  const prs = r.repo ? repoPrs(snap.sessions, r.repo.path, now) : null
  const pr = prs !== null && prs.ghOk && r.branch !== null ? prs.prs.find(p => p.branch === r.branch) : undefined
  const lines: Spans[] = []

  const branch = r.branch ?? (r.repo ? DETACHED : null)
  lines.push([...(branch !== null ? [...line('branch', sp(branch)), sp('  ')] : []), ...line('since', sp(local.clock(r.startedAt))), sp('  '), ...line('last activity', sp(`${duration(now - r.lastActivityAt)} ago`))])
  const u = r.usage
  lines.push(line('tokens', sp(`in ${tokens(u.tokensIn)}`), sp(' '), sp(`out ${tokens(u.tokensOut)}`)))
  lines.push(line('struggles', u.retries > 0 ? sp(plural(u.retries, 'retry', 'retries'), 'yellow') : dim('0 retries'), DOT, u.toolErrors > 0 ? sp(plural(u.toolErrors, 'tool error', 'tool errors'), 'yellow') : dim('0 tool errors')))

  const running: Spans[] = [
    ...(r.runs.goalSince !== null && (r.state === 'running' || r.state === 'needs-you') ? [[sp(`/goal ${duration(now - r.runs.goalSince)}`, 'cyan')]] : []),
    ...r.runs.subagents.map((a): Spans => [dim(`subagent ${a.name} ${a.status}`)]),
    ...r.runs.background.map((b): Spans => [dim(`background ${b.name} ${duration(now - b.since)}`)]),
  ]
  if (running.length > 0) lines.push(line('running', ...join(running)))

  const blocks: Block[] = [{ kind: 'rule' }, { kind: 'lines', key: 'facts', wrap: true, lines }]

  const m = r.milestone
  if (m !== null) {
    const done = completeCount(m.features)
    const marks = m.features.flatMap((f, i): Spans => {
      const kind = featureKind(f.state)
      const glyph = kind === 'done' || kind === 'merged' ? sp('✓', 'green') : kind === 'building' ? sp('◐', 'yellow') : kind === 'blocked' ? sp('✗', 'red') : sp('☐', 'dim')
      return [...(i > 0 ? [sp(' ')] : []), glyph, kind === 'todo' ? dim(` ${f.n}`) : sp(` ${f.n}`)]
    })
    blocks.push({ kind: 'lines', key: 'milestone', wrap: true, lines: [line('milestone', sp(m.slug), sp(' '), ...bar(done, m.features.length, 6), sp(` ${done}/${m.features.length}`)), [sp('  '), ...marks]] })
  }

  // tasks: the session's task asks, newest first, each with its state; a question is not a task.
  const tasks = [...r.asks].filter(x => x.kind === 'task').sort((x, y) => y.at - x.at)
  if (tasks.length > 0 || r.source === 'transcript') {
    const glyph = (st: Ask['status']) => (st === 'needs-you' ? sp('●', 'red') : st === 'in-progress' ? sp('◐', 'yellow') : sp('✓', 'green'))
    blocks.push({
      kind: 'lines',
      key: 'asks',
      wrap: true,
      lines: [
        ...(r.source === 'transcript' ? [[dim(FROM_TRANSCRIPT)] as Spans] : []),
        ...(tasks.length === 0 ? [] : [line('tasks', ...join(tasks.slice(0, SESSION_ASKS_SHOWN).map((t): Spans => [sp(cut(t.text.replace(/\s+/g, ' ').trim(), 40)), sp(' '), glyph(t.status)])))]),
        ...(tasks.length > SESSION_ASKS_SHOWN ? [[dim(`and ${tasks.length - SESSION_ASKS_SHOWN} more`)] as Spans] : []),
      ],
    })
  }

  if (pr !== undefined)
    blocks.push({
      kind: 'inline',
      key: 'pr',
      head: [dim('PR ')],
      sep: null,
      items: [
        { key: 'pr:link', href: pr.url, spans: [sp(`#${pr.number}`, 'cyan')] },
        { key: 'pr:words', joined: true, spans: [sp(' open · checks '), checksGlyph(pr.checks), dim(` ${CHECKS_WORDS[pr.checks].replace(/^[✓✗] /, '')} · ${REVIEW_WORDS[pr.review]} · `), pr.behind === true ? sp('BEHIND', 'yellow') : pr.mergeable === 'conflicts' ? sp(MERGE_WORDS.conflicts, 'red') : pr.mergeable === 'mergeable' ? sp(MERGE_WORDS.mergeable, 'green') : dim(MERGE_WORDS.unknown)] },
      ],
    })

  if (resumeCommand(r.cwd, r.sessionId) !== null) blocks.push({ kind: 'actions', key: 'session-actions', items: [{ key: 'resume', label: PANE_BUTTONS.resume, action: 'resume' }] })
  const crumbs = [{ text: 'Home', to: { kind: 'home' } as const }, ...(r.repo ? [{ text: repoLabel(r), to: { kind: 'repo', path: r.repo.path } as const }] : []), { text: title, to: null, bold: true }]
  return { crumbs, right: stateSpans(r, now), blocks: tidy(blocks), footer: hint(), first: firstKey(blocks) }
}

// A page that a command's argument, or a row that went away, could not find: one line under Home.
export const missingModel = (line: string): PaneModel => ({
  crumbs: [{ text: 'Home', to: { kind: 'home' } }, { text: 'Not found', to: null, bold: true }],
  right: [],
  blocks: [{ kind: 'rule' }, { kind: 'lines', key: 'missing', wrap: true, lines: [[sp(line)]] }],
  footer: hint(),
  first: null,
})
