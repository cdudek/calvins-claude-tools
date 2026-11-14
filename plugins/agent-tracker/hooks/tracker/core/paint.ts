// Colour and weight as data, from the owner's mockups (2026-11-14): .r red, .y yellow, .g green, .c cyan, .m magenta,
// .d dim, bold. The drawing layer turns a tone into a Text prop; nothing here touches the engine.
import { cells } from './format'

export type Tone = 'red' | 'yellow' | 'green' | 'cyan' | 'magenta' | 'dim' | 'label'
export type Span = { text: string; tone?: Tone; bold?: boolean; strike?: boolean }
export type Spans = Span[]

export const sp = (text: string, tone?: Tone, o: { bold?: boolean; strike?: boolean } = {}): Span => ({ text, ...(tone ? { tone } : {}), ...o })
export const spanCells = (spans: Spans) => spans.reduce((n, s) => n + cells(s.text), 0)
export const plain = (spans: Spans) => spans.map(s => s.text).join('')
export const dim = (text: string) => sp(text, 'dim')
export const DOT: Span = dim(' · ')

// Theme keys where one fits (red, yellow, green, cyan follow the person's theme); magenta is the theme's purple (merged); no raw hex is needed.
export const TONE_COLOR = { red: 'error', yellow: 'warning', green: 'success', cyan: 'suggestion', magenta: 'merged', label: 'claude' } as const
export type Paint = { color?: string; dimColor?: boolean; bold?: boolean; strikethrough?: boolean }
export const paint = (s: Span): Paint => ({
  ...(s.tone === undefined || s.tone === 'dim' ? {} : { color: TONE_COLOR[s.tone] }),
  ...(s.tone === 'dim' ? { dimColor: true } : {}),
  ...(s.bold ? { bold: true } : {}),
  ...(s.strike ? { strikethrough: true } : {}),
})

// The spans of a list joined by a separator.
export const join = (parts: Spans[], sep: Span = DOT): Spans => parts.flatMap((p, i) => (i === 0 ? p : [sep, ...p]))
// The spans cut to `max` cells, "…" in place of the last one.
export const cutSpans = (spans: Spans, max: number): Spans => {
  if (spanCells(spans) <= max) return spans
  const out: Spans = []
  let room = Math.max(0, max - 1)
  for (const s of spans) {
    const chars = [...s.text]
    if (chars.length <= room) {
      out.push(s)
      room -= chars.length
    } else {
      out.push({ ...s, text: `${chars.slice(0, room).join('')}…` })
      return out
    }
  }
  return out
}
// A stale list dims what it last read.
export const dimmed = (spans: Spans): Spans => spans.map(s => ({ ...s, tone: 'dim' as const }))

// A bar as the mockups draw it: green ▓ for what is done, dim ░ for the rest.
export const bar = (done: number, total: number, width = 10): Spans => {
  const filled = total <= 0 ? 0 : Math.min(width, Math.round((width * done) / total))
  return [sp('▓'.repeat(filled), 'green'), dim('░'.repeat(width - filled))]
}
export const percent = (done: number, total: number) => (total <= 0 ? 0 : Math.round((100 * done) / total))

export const rule = (columns: number): Span => dim('─'.repeat(Math.max(1, columns)))
