import type { Ask, SessionRecord } from '../types'
import { clean } from './format'
import { ASKS_MAX, ASK_TEXT_MAX } from './types'
import { addTokens } from './usage'

// What the backfill takes from a transcript (JSON lines). Instead of parsing every line, one pattern pulls out the
// few pieces it needs, so the same pattern works on the text in memory and, for a file over 4 MiB, as
// `grep -o -E` (F13). Both read the same fragments and so give the same record. The pattern is written in the
// subset that JS regex and POSIX ERE share. `S` is a JSON string body, in a form that cannot backtrack badly.
const S = String.raw`[^"\\]*(\\.[^"\\]*)*`
const IMAGE = String.raw`(\{"type":"image","source":\{[^}]*\}\},)?` // an image comes before the text of a prompt
export const FRAGMENT = [
  String.raw`"(timestamp|cwd|gitBranch|aiTitle|promptSource)":"[^"]*"`,
  String.raw`"isSidechain":(true|false)`, // the first key of a message line: it starts a line
  String.raw`"isMeta":true`,
  String.raw`"is_error":true`,
  String.raw`"id":"msg_[A-Za-z0-9]+"`,
  String.raw`"usage":\{"input_tokens":[0-9]+,"cache_creation_input_tokens":[0-9]+,"cache_read_input_tokens":[0-9]+,"output_tokens":[0-9]+`,
  String.raw`"role":"user","content":"${S}"`,
  String.raw`"role":"user","content":\[${IMAGE}\{"type":"text","text":"${S}"`,
].join('|')

export const fragments = (text: string): string[] => text.match(new RegExp(FRAGMENT, 'g')) ?? []

export type TranscriptFields = Pick<SessionRecord, 'cwd' | 'branch' | 'title' | 'usage' | 'asks' | 'startedAt' | 'lastActivityAt'>

// A prompt the owner typed is not a shell line, a slash command's expansion, a notification or a system note (F70).
const NOT_AN_ASK =
  /^(<(command-name|command-message|command-args|local-command|bash-input|bash-stdout|bash-stderr|task-notification|system-reminder)|\[Request interrupted|This session is being continued)/

const decode = (f: string, close: string): unknown => {
  try {
    return JSON.parse(`{${f}${close}`)
  } catch {
    return undefined // a fragment cut short by a truncated search
  }
}
const num = (f: string, key: string) => Number(new RegExp(`"${key}":([0-9]+)`).exec(f)?.[1] ?? 0)

export const foldTranscript = (frags: string[]): TranscriptFields => {
  let first = 0
  let last = 0
  const messages = new Map<string, { input_tokens: number; output_tokens: number; cache_read_input_tokens: number; cache_creation_input_tokens: number }>()
  const asks: Ask[] = []
  let cwd = ''
  let branch: string | null = null
  let title: string | null = null
  let errors = 0
  let messageId = ''
  let isSide = false
  let pending: { text: string; at: number; isMeta: boolean; isSystem: boolean } | null = null
  let n = 0
  const flush = () => {
    if (pending && !isSide && !pending.isMeta && !pending.isSystem && pending.text.trim() !== '' && !NOT_AN_ASK.test(pending.text)) {
      asks.push({ n: ++n, text: clean(pending.text, ASK_TEXT_MAX), kind: 'not-classified', status: 'replied', at: pending.at })
    }
    pending = null
  }

  for (const f of frags) {
    if (f.startsWith('"isSidechain"')) {
      flush()
      isSide = f.endsWith('true')
    } else if (f.startsWith('"isMeta"')) {
      if (pending) pending.isMeta = true
    } else if (f.startsWith('"is_error"')) {
      errors += 1
    } else if (f.startsWith('"id"')) {
      messageId = f.slice(6, -1)
    } else if (f.startsWith('"usage"')) {
      // A message written as several lines carries the same usage on each: count it once.
      messages.set(messageId, {
        input_tokens: num(f, 'input_tokens'),
        cache_creation_input_tokens: num(f, 'cache_creation_input_tokens'),
        cache_read_input_tokens: num(f, 'cache_read_input_tokens'),
        output_tokens: num(f, 'output_tokens'),
      })
    } else if (f.startsWith('"role"')) {
      const m = decode(f, f.includes('"content":[') ? '}]}' : '}') as { content?: unknown } | undefined
      const text = typeof m?.content === 'string' ? m.content : ((m?.content as { text?: string }[] | undefined)?.at(-1)?.text ?? '')
      pending = { text, at: last, isMeta: false, isSystem: false }
    } else {
      const [key, value] = Object.entries((decode(f, '}') as Record<string, string> | undefined) ?? {})[0] ?? []
      if (key === 'timestamp') {
        const t = Date.parse(value!)
        if (!Number.isNaN(t)) {
          first = first === 0 ? t : Math.min(first, t)
          last = Math.max(last, t)
          if (pending) pending.at = t // a line's own time comes after its message
        }
      } else if (key === 'cwd') cwd = value!
      else if (key === 'gitBranch') branch = value === 'HEAD' || value === '' ? null : clean(value, 200) // HEAD: detached
      else if (key === 'aiTitle') title = clean(value, 200) || title
      else if (key === 'promptSource' && pending && value === 'system') pending.isSystem = true
    }
  }
  flush()

  let usage = { tokensIn: 0, tokensOut: 0, toolErrors: errors, retries: 0 }
  for (const t of messages.values()) usage = addTokens(usage, t)
  return { cwd, branch, title, usage, asks: asks.slice(-ASKS_MAX), startedAt: first, lastActivityAt: last }
}
