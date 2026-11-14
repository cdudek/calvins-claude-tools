import type { SessionRecord } from '../types'

type Usage = SessionRecord['usage']
type TurnTokens = { input_tokens: number; output_tokens: number; cache_read_input_tokens: number; cache_creation_input_tokens: number }

// Tokens in are everything the model read: fresh input plus cache reads and writes (questions.md Q3).
export const addTokens = (u: Usage, t: TurnTokens): Usage => ({
  ...u,
  tokensIn: u.tokensIn + t.input_tokens + t.cache_read_input_tokens + t.cache_creation_input_tokens,
  tokensOut: u.tokensOut + t.output_tokens,
})

// A tool call: an error counts, and so does a call that repeats the one straight before it that failed (F21).
// `key` is the call's name and input; `last` is the previous call, or null.
export const noteTool = (u: Usage, last: { key: string; failed: boolean } | null, key: string, failed: boolean) => {
  const isRetry = last !== null && last.failed && last.key === key
  return {
    usage: { ...u, toolErrors: u.toolErrors + (failed ? 1 : 0), retries: u.retries + (isRetry ? 1 : 0) },
    last: { key, failed },
  }
}
