// The repo scan: this session's own repo, every 2 minutes, by `git worktree list` and `gh pr list`. Both only read.
// The result goes into this session's own file as its `scan` block; the pane takes the latest one per repo.
import type { EngineInterface } from 'claude-code'

import { GH_FIELDS, parsePrs, parseWorktrees } from './core'
import { saveOwn } from './store'
import type { State } from './store'
import type { SessionRecord } from './types'

type Engine = EngineInterface
type Scan = NonNullable<SessionRecord['scan']>

const SCAN_MS = 120_000

// stdout of a command that exits 0, else null. A command that cannot start (no gh installed) is null too.
async function out($: Engine, argv: string[], cwd: string) {
  const r = await $.process.run(argv, { cwd, timeoutMs: 30_000 }).catch(() => null)
  return r !== null && r.exitCode === 0 ? r.stdout : null
}

export async function scanPass($: Engine, s: State) {
  const r = s.mine
  if (s.isScanning || r === null || r.repo === null || r.endedAt !== null) return // no repo: nothing to scan
  s.isScanning = true
  try {
    const now = await $.clock.now()
    const worktrees = parseWorktrees((await out($, ['git', 'worktree', 'list', '--porcelain'], r.cwd)) ?? '')
    const prs = parsePrs((await out($, ['gh', 'pr', 'list', '--state', 'open', '--limit', '100', '--json', GH_FIELDS], r.cwd)) ?? '')
    const before = r.scan
    // gh missing or signed out: keep the last PRs and their time, so the pane can show their age (F54, F69).
    const scan: Scan =
      prs !== null
        ? { at: now, ghOk: true, worktrees, prs }
        : { at: before?.at ?? now, ghOk: false, worktrees: worktrees.length ? worktrees : (before?.worktrees ?? []), prs: before?.prs ?? [] }
    await saveOwn($, s, m => ({ ...m, scan }))
  } finally {
    s.isScanning = false
  }
}

// One scan now and one every 2 minutes, never two at once. The 5-second poll does not wait on it.
export function startScan($: Engine, s: State) {
  void scanPass($, s).catch(() => undefined)
  $.clock.every(SCAN_MS, () => void scanPass($, s).catch(() => undefined))
}
