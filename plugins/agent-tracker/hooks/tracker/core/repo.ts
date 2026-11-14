import type { SessionRecord } from '../types'

const base = (path: string) => path.replace(/\/+$/, '').split('/').pop() ?? path
const parent = (path: string) => path.replace(/\/+$/, '').split('/').slice(0, -1).join('/')

// The repo is the main worktree: the parent of `git rev-parse --path-format=absolute --git-common-dir` (F7).
export const repoFromCommonDir = (commonDir: string) => {
  const path = parent(commonDir.trim())
  return { path, name: base(path) }
}

// Two repos with one folder name get the parent folder added: `work/web-app`.
export const labelRepos = (sessions: SessionRecord[]): SessionRecord[] => {
  const paths = new Map<string, Set<string>>()
  for (const s of sessions) if (s.repo) paths.set(s.repo.name, (paths.get(s.repo.name) ?? new Set()).add(s.repo.path))
  return sessions.map(s =>
    s.repo && (paths.get(s.repo.name)?.size ?? 0) > 1 ? { ...s, repo: { ...s.repo, name: `${base(parent(s.repo.path))}/${s.repo.name}` } } : s,
  )
}
