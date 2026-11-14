// "You should know" and "Decided without you": the lines a finished turn's last message gives (one haiku call), and the
// open questions and plan revisions of an sdlc-run change, read as files. Pure: the I/O layer reads and calls the model.
import type { Note, SessionRecord, Snapshot } from '../types'
import type { Change } from './change'
import { isMerged } from './change'
import { clean } from './format'
import { isLive, repoLabel, sessionLabel } from './rank'
import { WEEK_MS } from './types'

export const NOTES_MIN_CHARS = 200 // a shorter last message is skipped: no model call
export const NOTES_MAX = 50 // per session, newest kept
export const NOTES_EACH = 3 // per kind and turn
export const NOTE_TEXT_MAX = 160
export const SEEN_MAX = 500 // the seen keys settings.json keeps, newest last
export const FILE_REVISIONS = 3 // the newest revisions of a change that count, and only the last week's

export const NOTES_PROMPT = `Read the message an AI coding agent wrote at the end of its turn. Reply with JSON only, no other words, in the form {"know":["..."],"decided":["..."]}.
"know": what the person should know: a side effect, a risk, an odd finding, a skipped step.
"decided": a call the agent made itself without asking: a library chosen, a default taken, a change to the plan's order.
Each item is one short line (under 120 characters). At most 3 per list. An empty list when there is none. Do not invent items.

Message:
`

export const notesPrompt = (message: string) => `${NOTES_PROMPT}${message}`

const list = (v: unknown): string[] | null => {
  if (v === undefined) return []
  if (!Array.isArray(v) || !v.every(x => typeof x === 'string')) return null
  return (v as string[])
    .map(x => clean(x, NOTE_TEXT_MAX).replace(/\s+/g, ' ').trim())
    .filter(Boolean)
    .slice(0, NOTES_EACH)
}

// The model's reply as the two lists. A code fence or words around the JSON are tolerated; anything that is not an object
// of string lists is null, and nothing is stored.
export const parseNotes = (reply: string): { know: string[]; decided: string[] } | null => {
  const from = reply.indexOf('{')
  const to = reply.lastIndexOf('}')
  if (from < 0 || to < from) return null
  let v: unknown
  try {
    v = JSON.parse(reply.slice(from, to + 1))
  } catch {
    return null
  }
  if (typeof v !== 'object' || v === null || Array.isArray(v)) return null
  const o = v as Record<string, unknown>
  if (o.know === undefined && o.decided === undefined) return null
  const know = list(o.know)
  const decided = list(o.decided)
  return know === null || decided === null ? null : { know, decided }
}

// The session's notes with the found ones added, ids n1, n2, ...; at most NOTES_MAX, the newest kept.
export const addNotes = (existing: Note[] | undefined, found: { know: string[]; decided: string[] }, at: number): Note[] => {
  const have = existing ?? []
  let n = Math.max(0, ...have.map(x => Number(/^n(\d+)$/.exec(x.id)?.[1] ?? 0)))
  const fresh = [...found.know.map(text => ({ kind: 'know' as const, text })), ...found.decided.map(text => ({ kind: 'decided' as const, text }))]
  return [...have, ...fresh.map((x): Note => ({ id: `n${++n}`, kind: x.kind, text: x.text, at, seen: false }))].slice(-NOTES_MAX)
}

// ---- the items the pane and the band show ----

export type NoteItem = {
  key: string // what seen is kept under
  kind: Note['kind']
  text: string
  at: number
  dayOnly: boolean // a plan revision has a date and no clock time
  seen: boolean
  repo: string // the repo name, "other" for a scratch folder
  label: string // "api/retry-bug"
  session: string | null // the session's own name
  sessionId: string | null // the session it came from, or that works the change
  source: string | null // the file it came from: changes/<dir>/questions.md; null for a turn's last message
  ref: string | null // Q7 or the revision's label
  question: string | null // the question asked, for a questions.md item
}

export const turnKey = (sessionId: string, id: string) => `${sessionId}:${id}`

const sentence = (text: string) => clean((/^(.+?[.!?])(\s|$)/.exec(text)?.[1] ?? text).replace(/\s+/g, ' ').trim(), NOTE_TEXT_MAX)

// All the items, newest first. `changes` are the change folders by repo path; a merged change adds nothing.
export const noteItems = (snap: Snapshot, changes: ReadonlyMap<string, Change[]>, seen: ReadonlySet<string>, now: number): NoteItem[] => {
  const out: NoteItem[] = []
  for (const r of snap.sessions as SessionRecord[]) {
    for (const n of r.notes ?? []) {
      const key = turnKey(r.sessionId, n.id)
      out.push({ key, kind: n.kind, text: n.text, at: n.at, dayOnly: false, seen: n.seen || seen.has(key), repo: repoLabel(r), label: sessionLabel(r), session: r.title ?? r.branch, sessionId: r.sessionId, source: null, ref: null, question: null })
    }
  }
  for (const [path, list] of changes) {
    const inRepo = snap.sessions.filter(r => r.repo?.path === path)
    const name = inRepo[0] ? repoLabel(inRepo[0]) : (path.split('/').pop() ?? path)
    for (const c of list.filter(x => !isMerged(x))) {
      const session = inRepo.filter(r => r.milestone?.slug === c.slug).sort((a, b) => Number(isLive(b)) - Number(isLive(a)) || b.lastActivityAt - a.lastActivityAt)[0]
      const base = { repo: name, label: `${name}/${c.slug}`, session: session ? (session.title ?? session.branch) : null, sessionId: session?.sessionId ?? null }
      for (const q of c.questions) {
        const key = `q:${c.dir}:${q.id}`
        out.push({ ...base, key, kind: 'decided', text: q.fallback !== '' ? `${sentence(q.fallback).replace(/\.+$/, '')} (default taken, ${q.id})` : `${q.title} (open, ${q.id})`, at: c.questionsAt, dayOnly: false, seen: seen.has(key), source: `changes/${c.dir}/questions.md`, ref: q.id, question: q.title })
      }
      for (const rev of c.revisions.filter(x => now - x.at <= WEEK_MS).slice(-FILE_REVISIONS)) {
        const key = `r:${c.dir}:${rev.at}:${rev.text.length}`
        out.push({ ...base, key, kind: 'decided', text: sentence(rev.text), at: rev.at, dayOnly: true, seen: seen.has(key), source: `changes/${c.dir}/plan.md`, ref: rev.ref === '' ? 'Revisions' : rev.ref, question: null })
      }
    }
  }
  return out.sort((a, b) => Number(a.seen) - Number(b.seen) || b.at - a.at || a.key.localeCompare(b.key))
}

export const unseenCount = (items: NoteItem[], kind: Note['kind']) => items.filter(i => i.kind === kind && !i.seen).length

// What to paste into the session to overrule an item.
export const overruleText = (i: NoteItem): string => {
  const where = i.source !== null ? `${i.source.split('/').pop()}${i.ref !== null ? `, ${i.ref}` : ''}` : i.label
  return `Overruling "${i.text}"\n(${where}). Instead: <your call>`
}
