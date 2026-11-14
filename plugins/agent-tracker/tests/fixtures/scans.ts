// What `git worktree list --porcelain` and `gh pr list --json ...` print, in the shapes of git 2 and gh 2, written by
// hand: every folder, branch, title and address is made up.
export const WORKTREES_PORCELAIN = [
  'worktree /work/repo-9',
  'HEAD 1111111111111111111111111111111111111111',
  'branch refs/heads/main',
  '',
  'worktree /work/repo-9-login',
  'HEAD 2222222222222222222222222222222222222222',
  'branch refs/heads/feat/login',
  '',
  'worktree /work/repo-9-detached',
  'HEAD 3333333333333333333333333333333333333333',
  'detached',
  '',
].join('\n')

const run = (conclusion: string, status = 'COMPLETED') => ({ __typename: 'CheckRun', name: 'tests', status, conclusion })
const context = (state: string) => ({ __typename: 'StatusContext', context: 'lint', state })

export const GH_PRS = [
  // Every check passed, approved, mergeable.
  { number: 101, title: 'Add login form', url: 'https://example.test/pr/101', headRefName: 'feat/login', createdAt: '2026-11-09T08:00:00Z',
    statusCheckRollup: [run('SUCCESS'), context('SUCCESS'), run('SKIPPED')], reviewDecision: 'APPROVED', mergeable: 'MERGEABLE', mergeStateStatus: 'CLEAN' },
  // One check failed and one still runs: failing wins. Changes requested, conflicts.
  { number: 102, title: 'Rework the session store', url: 'https://example.test/pr/102', headRefName: 'feat/store', createdAt: '2026-11-08T08:00:00Z',
    statusCheckRollup: [run('FAILURE'), run('', 'IN_PROGRESS')], reviewDecision: 'CHANGES_REQUESTED', mergeable: 'CONFLICTING', mergeStateStatus: 'DIRTY' },
  // Checks still running, review asked, mergeable not known yet.
  { number: 103, title: 'Docs pass', url: 'https://example.test/pr/103', headRefName: 'docs/pass', createdAt: '2026-11-10T08:00:00Z',
    statusCheckRollup: [run('', 'QUEUED'), context('PENDING')], reviewDecision: 'REVIEW_REQUIRED', mergeable: 'UNKNOWN', mergeStateStatus: 'UNKNOWN' },
  // No checks and no review decision; the branch is behind the base.
  { number: 104, title: 'Fix a typo', url: 'https://example.test/pr/104', headRefName: 'fix/typo', createdAt: '2026-11-10T09:00:00Z',
    statusCheckRollup: [], reviewDecision: '', mergeable: 'MERGEABLE', mergeStateStatus: 'BEHIND' },
]

export const GH_JSON = JSON.stringify(GH_PRS)

// What the parser must make of them.
export const EXPECTED_PRS = [
  { number: 101, title: 'Add login form', url: 'https://example.test/pr/101', branch: 'feat/login', createdAt: '2026-11-09T08:00:00Z', checks: 'pass', review: 'approved', mergeable: 'mergeable', behind: false },
  { number: 102, title: 'Rework the session store', url: 'https://example.test/pr/102', branch: 'feat/store', createdAt: '2026-11-08T08:00:00Z', checks: 'failing', review: 'changes', mergeable: 'conflicts', behind: false },
  { number: 103, title: 'Docs pass', url: 'https://example.test/pr/103', branch: 'docs/pass', createdAt: '2026-11-10T08:00:00Z', checks: 'running', review: 'requested', mergeable: 'unknown', behind: false },
  { number: 104, title: 'Fix a typo', url: 'https://example.test/pr/104', branch: 'fix/typo', createdAt: '2026-11-10T09:00:00Z', checks: 'pass', review: 'none', mergeable: 'mergeable', behind: true },
]

export const EXPECTED_WORKTREES = [
  { path: '/work/repo-9', branch: 'main' },
  { path: '/work/repo-9-login', branch: 'feat/login' },
  { path: '/work/repo-9-detached', branch: null },
]
