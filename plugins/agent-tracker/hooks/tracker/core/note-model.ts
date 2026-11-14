// One item, opened, as the owner's "One item, opened" mockup draws it (2026-11-14): what it is, when, from which session and
// file, the question and the default for a questions.md item, then the reply to paste into that session to overrule it.
import type { SessionRecord, Snapshot } from '../types'
import { resumeCommand } from './format'
import type { NoteItem } from './notes'
import { overruleText } from './notes'
import { dim, sp } from './paint'
import type { Spans } from './paint'
import { firstKey, hint, noteWhen, tidy } from './pane-model'
import type { ActionItem, Block, Local, PaneModel } from './pane-model'
import { HEADINGS } from './words'

export const noteNotFound = 'That item is gone. Pick one on Home.'

const kindStyle = { know: { glyph: '!', tone: 'cyan', head: HEADINGS.know }, decided: { glyph: '◆', tone: 'magenta', head: HEADINGS.decided } } as const

export const noteModel = (item: NoteItem, snap: Snapshot, local: Local, columns: number): PaneModel => {
  const st = kindStyle[item.kind]
  const session: SessionRecord | undefined = item.sessionId === null ? undefined : snap.sessions.find(r => r.sessionId === item.sessionId)
  const where: Spans[] = [
    [dim('when '), sp(noteWhen(item, local)), ...(item.session !== null ? [sp('   '), dim('session '), sp(item.session)] : [])],
    ...(item.source !== null ? [[dim('source '), sp(item.source)] as Spans] : []),
  ]
  const blocks: Block[] = [
    { kind: 'lines', key: 'what', wrap: true, lines: [[sp(`${st.glyph} ${item.text}`, st.tone, { bold: true })]] },
    { kind: 'lines', key: 'where', lines: where },
    { kind: 'rule' },
  ]
  if (item.question !== null) {
    const fallback = /\(default taken, [^)]*\)$/.test(item.text) ? item.text.replace(/\s*\(default taken, [^)]*\)$/, '') : null
    blocks.push({ kind: 'lines', key: 'question', wrap: true, lines: [[dim('The question:')], [sp(`"${item.question}"`)], ...(fallback !== null ? [[dim('Default taken: '), sp(fallback)] as Spans] : [])] }, { kind: 'rule' })
  }
  const actions: ActionItem[] = []
  if (item.kind === 'decided') {
    // The reply, as it will be pasted: the line starting each is a dim bar, the placeholder is yellow.
    const reply = overruleText(item).split('\n').map((l): Spans => [dim('┆ '), ...l.split('<your call>').flatMap((part, i) => (i === 0 ? [sp(part)] : [sp('<your call>', 'yellow'), sp(part)]))])
    blocks.push({ kind: 'lines', key: 'reply', wrap: true, lines: [[dim('Copy this, to paste into that session:')], ...reply] })
    actions.push({ key: 'overrule', label: 'Copy overrule', action: 'overrule' })
  }
  if (!item.seen) actions.push({ key: 'seen', label: 'Mark seen', action: 'seen', keys: [item.key] })
  if (session !== undefined && resumeCommand(session.cwd, session.sessionId) !== null) actions.push({ key: 'resume', label: 'Copy resume command', action: 'resume' })
  if (actions.length > 0) blocks.push({ kind: 'actions', key: 'note-actions', items: actions })
  return {
    crumbs: [{ text: 'Home', to: { kind: 'home' } }, { text: st.head.toLowerCase(), to: null }, { text: item.label, to: null, bold: true }],
    right: item.seen ? [dim('seen')] : [],
    blocks: tidy(blocks),
    footer: hint(),
    first: firstKey(blocks),
  }
}
