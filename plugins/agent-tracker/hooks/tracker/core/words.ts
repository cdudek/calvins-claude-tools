// Every on-screen string of the band, from spec/screens.md "Words". The pane's words join them in feature 4.
export const LOADING = 'Reading sessions…'
export const ALONE = 'only this session is running'
export const THIS_SESSION = 'this session'
export const UNTITLED = 'untitled session'
export const DETACHED = 'detached HEAD'
export const SEP = ' │ '

export const COPIED = 'Tracker state copied as Markdown'
export const copyFailed = (reason: string) => `Copy failed: ${reason}. Press Copy again or run /tracker copy.`

// gh missing or signed out: the band drops its PR segment and the details view says why (F54).
export const PRS_NOT_SHOWN = 'PRs not shown: gh is not installed or not signed in. Run gh auth login to see them.'

// The session list could not be read twice in a row (F52). `age` is "2m", or null when no read ever worked.
// Longest first: the band takes the first one that fits.
export const staleWords = (age: string | null, columns: number): string[] => {
  if (columns < 60) return [age === null ? 'stale' : `stale ${age}`]
  return age === null ? ['session list unavailable'] : [`session list unavailable · counts from ${age} ago`, `counts from ${age} ago`]
}

export const BUTTON_LABELS = { pane: 'Pane', details: 'Details', copy: 'Copy', compact: 'Compact' } as const
export const COMMAND_DESCRIPTION = "Show each session's repo, work and state"
export const COMMAND_HINT = 'details | compact | copy | repo <name> | session <text> | band on | band off'
