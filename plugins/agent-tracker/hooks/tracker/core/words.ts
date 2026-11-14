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

// The pane's words, from spec/screens.md "Pane, Home", "Pane, Session" and "Pane, Repo".
export const PANE_TITLE = 'Tracker'
export const NOTHING_NEEDS = 'Nothing needs you.'
export const ONLY_THIS = 'Only this session is running. Sessions in other terminals show up here when they start.'
export const NO_REPOS = 'No repos yet.'
export const HEADINGS = { needs: 'Needs you', running: 'Running', done: 'Done', ended: 'Ended today' } as const
export const PANE_BUTTONS = { close: 'Close', back: 'Back', home: 'Home', resume: 'Copy resume command' } as const
export const NEW_MARK = 'new'
export const moreLine = (n: number) => `and ${n} more on the Repo pages`
export const updatedWords = (age: string) => (age === '<1m' ? 'updated just now' : `updated ${age} ago`)
// The session list failed twice (F123). `age` is "2m", or null when no read ever worked.
export const staleTop = (age: string | null) =>
  `Session list unavailable. ${age === null ? '' : `Showing what was read ${age} ago. `}Retrying every 5 seconds; if it keeps failing, update Claude Code.`
export const withoutTracker = (n: number) =>
  n === 1
    ? '1 session runs without the tracker. Questions it asks in text are not detected.'
    : `${n} sessions run without the tracker. Questions they ask in text are not detected.`
export const RESUME_COPIED = 'Resume command copied'
export const resumeFailed = (reason: string) => `Copy failed: ${reason}. Press Copy resume command again.`
export const NO_ASKS = 'No asks yet.'
export const FROM_TRANSCRIPT = 'Not classified: this session ran without the tracker.'
export const SECTION_WORDS = { running: 'Running now', usage: 'Usage', milestone: 'Milestone', asks: 'Asks' } as const
export const ASK_KIND = { task: 'task', question: 'question', 'not-classified': 'not classified' } as const
export const ASK_STATUS = { 'in-progress': 'in progress', 'needs-you': 'needs you', replied: 'replied' } as const
export const CHECKS_WORDS = { pass: '✓ checks pass', failing: '✗ checks failing', running: 'checks running' } as const
export const REVIEW_WORDS = { approved: 'approved', changes: 'changes requested', requested: 'review requested', none: 'no review' } as const
export const MERGE_WORDS = { mergeable: '↓ mergeable', conflicts: 'conflicts', unknown: 'mergeable unknown' } as const
export const sessionNotFound = (text: string) => `No session matches "${text}". Pick one on Home.`
export const NO_PRS = 'No open PRs.'
export const NO_WORKTREES = 'No worktrees found.'
export const repoNotFound = (text: string) => `No repo named "${text}" has had a session. Pick one on Home.`
export const COMMAND_HELP = 'Try /tracker, details, compact, copy, repo, session, band on, band off.'
export const REASON_WORDS = { permission: 'asks permission', question: 'asks a question', waiting: 'waiting', unknown: 'state unknown' } as const

export const BUTTON_LABELS = { pane: 'Pane', details: 'Details', copy: 'Copy', compact: 'Compact' } as const
export const COMMAND_DESCRIPTION = "Show each session's repo, work and state"
export const COMMAND_HINT = 'details | compact | copy | repo <name> | session <text> | band on | band off'

// What a /tracker command answers in the transcript, one short line each. A copy answers with its toast.
export const BAND_REPLY = { details: 'Band switched to details.', compact: 'Band switched to compact.', hidden: 'Band hidden. /tracker band on shows it again.', shown: 'Band shown.' } as const
export const PANE_OPENED = 'Tracker pane opened.'
