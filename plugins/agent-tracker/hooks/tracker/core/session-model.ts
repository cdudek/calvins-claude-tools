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
import { REASON, TASK_STYLE, hint, tidy } from './pane-model'
import type { ActionItem, Block, Local, PaneModel } from './pane-model'
import { clearGate, confirmLines, hasProcess, onlyWorktree, outcomeLines, workOf, wtLines } from './clear'
import type { ClearState } from './clear'
import { offerLines, staysLine } from './worktree'
import type { WorktreeFact } from './worktree'
import { TASK_LABEL } from './tasks'
import type { TaskItem } from './tasks'
import { checksGlyph } from './repo-model'
import { lastActivity, startedWords } from './activity'
import { CHECKS_WORDS, CLEAR_WORDS, DETACHED, FROM_TRANSCRIPT, MERGE_WORDS, PANE_BUTTONS, REVIEW_WORDS, UNKNOWN_ACTIVITY, UNTITLED, WORKTREE_WORDS, endedWords } from './words'

export const SESSION_ASKS_SHOWN = 6

// What the page needs beyond the snapshot: the tasks Home lists, whether the session's folder exists (the resume command needs it),
// the page's own Clear state, and the worktree the session ran in (null: no linked worktree, or git has not said yet).
export type SessionCtx = { tasks: TaskItem[]; folder: boolean; clear: ClearState | null; worktree: WorktreeFact | null }
const NO_CTX: SessionCtx = { tasks: [], folder: false, clear: null, worktree: null }


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
    default: {
      const at = r.endedAt ?? lastActivity(r)
      return [dim(endedWords(at === null ? null : duration(now - at)))]
    }
  }
}

const line = (label: string, ...rest: Spans): Spans => [dim(`${label} `), ...rest]

export const sessionModel = (snap: Snapshot, id: string, now: number, local: Local, columns: number, ctx: SessionCtx = NO_CTX): PaneModel | null => {
  const r = snap.sessions.find(x => x.sessionId === id)
  if (r === undefined) return null
  const title = r.title ?? UNTITLED
  const prs = r.repo ? repoPrs(snap.sessions, r.repo.path, now) : null
  const pr = prs !== null && prs.ghOk && r.branch !== null ? prs.prs.find(p => p.branch === r.branch) : undefined
  const lines: Spans[] = []

  const branch = r.branch ?? (r.repo ? DETACHED : null)
  const active = lastActivity(r)
  lines.push([...(branch !== null ? [...line('branch', sp(branch)), sp('  ')] : []), ...line('started', sp(startedWords(r.startedAt, now, local))), sp('  '), ...(active === null ? [dim(UNKNOWN_ACTIVITY)] : line('last activity', sp(`${duration(now - active)} ago`)))])
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

  // tasks: the session's task asks, newest first, each with its state; a question is not a task. An ended session shows only the
  // tasks Home lists for it, with Home's glyph and word: those are the tasks Clear closes (F15).
  const ended = !hasProcess(r, snap)
  const tasks = [...r.asks].filter(x => x.kind === 'task').sort((x, y) => y.at - x.at)
  const homeTasks = [...ctx.tasks].filter(t => t.sessionId === r.sessionId && r.source !== 'transcript')
  const shown = ended ? homeTasks.length : tasks.length
  if (shown > 0 || r.source === 'transcript') {
    const glyph = (st: Ask['status']) => (st === 'needs-you' ? sp('●', 'red') : st === 'in-progress' ? sp('◐', 'yellow') : sp('✓', 'green'))
    const items: Spans[] = ended
      ? homeTasks.slice(0, SESSION_ASKS_SHOWN).map((t): Spans => [sp(cut(t.text.replace(/\s+/g, ' ').trim(), 40)), sp(' '), sp(`${TASK_STYLE[t.status].glyph} ${TASK_LABEL[t.status].toLowerCase()}`, TASK_STYLE[t.status].tone)])
      : tasks.slice(0, SESSION_ASKS_SHOWN).map((t): Spans => [sp(cut(t.text.replace(/\s+/g, ' ').trim(), 40)), sp(' '), glyph(t.status)])
    blocks.push({
      kind: 'lines',
      key: 'asks',
      wrap: true,
      lines: [
        ...(r.source === 'transcript' ? [[dim(FROM_TRANSCRIPT)] as Spans] : []),
        ...(shown === 0 ? [] : [line('tasks', ...join(items))]),
        ...(shown > SESSION_ASKS_SHOWN ? [[dim(`and ${shown - SESSION_ASKS_SHOWN} more`)] as Spans] : []),
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

  // Clear: for an ended session with work left, behind a confirm. A live session, or a list that says nothing about processes, gets one line instead.
  const clear = ctx.clear
  const wt = ctx.worktree
  const work = workOf(r, snap, ctx.tasks, wt, clear?.left === true)
  const gate = clearGate(r, snap, work)
  // The worktree: its label and branch, or why it stays (the first failed condition). Clear mentions it only when Clear is drawn.
  if (wt !== null) {
    const stays = ended ? staysLine(wt) : null
    blocks.push({ kind: 'lines', key: 'worktree', wrap: true, lines: [stays !== null ? [sp(stays)] : [dim(WORKTREE_WORDS.line(wt.label, wt.branch)), ...(gate === 'clear' && wt.removable ? [sp(`  ${WORKTREE_WORDS.offersRemoval}`)] : [])]] })
  }
  const gone = clear?.wt?.kind === 'removed' || clear?.wt?.kind === 'claude-removed' // no folder to resume in
  const resume = ended && ctx.folder && !gone && resumeCommand(r.cwd, r.sessionId) !== null
  const note = gate === 'live' ? (r.kind === 'background' ? CLEAR_WORDS.liveBackground : CLEAR_WORDS.liveInteractive) : gate === 'unreadable' ? CLEAR_WORDS.waitsUnreadable : gate === 'pid-unknown' ? CLEAR_WORDS.waitsNoPid : null
  if (note !== null) blocks.push({ kind: 'lines', key: 'clear-note', wrap: true, lines: [[sp(note)]] })
  let first = resume ? 'resume' : 'crumb:0'
  const offer = clear?.offer === true && wt?.removable === true && gate === 'clear' && clear.step === 'idle'
  if (clear?.step === 'clearing') {
    blocks.push({ kind: 'lines', key: 'clearing', lines: [[dim(CLEAR_WORDS.clearing)]] })
    first = 'crumb:0'
  }
  else if (clear?.step === 'confirm' && gate === 'clear') {
    blocks.push({ kind: 'lines', key: 'confirm', wrap: true, lines: [[sp(CLEAR_WORDS.question)], ...confirmLines(work).map((l): Spans => [sp(l)])] })
    blocks.push({ kind: 'actions', key: 'confirm-actions', items: [{ key: 'confirm-clear', label: PANE_BUTTONS.confirmClear, action: 'confirm-clear' }, { key: 'cancel-clear', label: PANE_BUTTONS.cancelClear, action: 'cancel-clear' }] })
    first = 'cancel-clear'
  } else {
    const asking = gate === 'clear' && !offer && clear?.step !== 'removing' // Clear is drawn: the offer is its own confirm while it is open
    const items: ActionItem[] = [
      ...(resume ? [{ key: 'resume', label: PANE_BUTTONS.resume, action: 'resume' as const }] : []),
      ...(asking ? [{ key: 'clear', label: PANE_BUTTONS.clear, action: 'clear' as const }] : []),
      ...(clear?.outcome?.kind === 'cleared' && clear.outcome.closed.length > 0 ? [{ key: 'reopen', label: PANE_BUTTONS.reopen, action: 'reopen' as const, keys: clear.outcome.closed }] : []),
    ]
    if (asking && onlyWorktree(work)) blocks.push({ kind: 'lines', key: 'clear-hint', wrap: true, lines: [[sp(WORKTREE_WORDS.onlyWorktree)]] })
    if (items.length > 0) blocks.push({ kind: 'actions', key: 'session-actions', items })
    if (clear?.step === 'removing') {
      blocks.push({ kind: 'lines', key: 'removing', lines: [[dim(WORKTREE_WORDS.removing)]] })
      first = 'crumb:0'
    } else if (offer) {
      blocks.push({ kind: 'lines', key: 'offer', wrap: true, lines: offerLines(wt).map((l): Spans => [sp(l)]) })
      blocks.push({ kind: 'actions', key: 'offer-actions', items: [{ key: 'remove-worktree', label: PANE_BUTTONS.removeWorktree, action: 'remove-worktree' }, { key: 'keep-worktree', label: PANE_BUTTONS.keepWorktree, action: 'keep-worktree' }] })
      first = 'keep-worktree'
    }
  }
  // What the last Clear and the offer did, or that there is nothing to clear. The lines stay until the owner leaves the page.
  const done = [...(clear?.outcome != null ? outcomeLines(clear.outcome) : []), ...(clear?.wt != null ? wtLines(clear.wt) : [])]
  const result = clear?.step === 'clearing' ? [] : done.length > 0 ? done : gate === 'nothing' ? [{ glyph: null, text: CLEAR_WORDS.nothing }] : []
  if (result.length > 0)
    blocks.push({ kind: 'lines', key: 'clear-result', wrap: true, lines: result.map((l): Spans => [...(l.glyph === null ? [] : [sp(l.glyph, l.glyph === '✓' ? 'green' : 'red'), sp(' ')]), sp(l.text)]) })
  const crumbs = [{ text: 'Home', to: { kind: 'home' } as const }, ...(r.repo ? [{ text: repoLabel(r), to: { kind: 'repo', path: r.repo.path } as const }] : []), { text: title, to: null, bold: true }]
  return { crumbs, right: stateSpans(r, now), blocks: tidy(blocks), footer: hint(), first }
}

// A page that a command's argument, or a row that went away, could not find: one line under Home.
export const missingModel = (line: string): PaneModel => ({
  crumbs: [{ text: 'Home', to: { kind: 'home' } }, { text: 'Not found', to: null, bold: true }],
  right: [],
  blocks: [{ kind: 'rule' }, { kind: 'lines', key: 'missing', wrap: true, lines: [[sp(line)]] }],
  footer: hint(),
  first: null,
})
