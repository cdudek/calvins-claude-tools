// Home, the triage queue: Needs you, Running, Done, Ended today and the Repos line (spec/screens.md "Pane, Home").
import { HEADINGS, LOADING, NOTHING_NEEDS, NO_REPOS, ONLY_THIS, PRS_NOT_SHOWN } from '../core'
import type { Group, HomeModel, Row } from '../core'
import { repoHeading, sessionRow, titleRow } from './chrome'
import type { Actions, Ui } from './chrome'

// The first session row is where the ring starts, unless the person already moved it (a Back returns to its row).
const firstRow = (m: HomeModel) => [...m.needs, ...m.running.flatMap(g => g.rows), ...m.done.flatMap(g => g.rows), ...m.ended][0]?.id ?? null

export function homeView(ui: Ui, m: HomeModel, a: Actions, columns: number) {
  const { Box, Text, Button } = ui
  if (m.loading)
    return (
      <Box flexDirection="column">
        {titleRow(ui, a, null)}
        <Text dimColor>{LOADING}</Text>
      </Box>
    )

  const dim = m.stale !== null // the last good list, dimmed
  const first = firstRow(m)
  const ring = a.ring ?? (first === null ? null : `session:${first}`)
  const row = (r: Row) => sessionRow(ui, r, columns, { key: `session:${r.id}`, dim, autoFocus: ring === `session:${r.id}`, onPress: () => a.open(`session:${r.id}`, { kind: 'session', id: r.id }) })
  // A repo with running and done sessions has a heading in each section: the Done one takes a suffix then, so key and focus id stay unique.
  const group = (section: 'running' | 'done') => (g: Group) => {
    const id = `${g.path === null ? 'folder' : 'repo'}:${g.path ?? g.key}${section === 'done' && m.running.some(x => x.key === g.key) ? ':done' : ''}`
    return (
      <Box key={`${section}:${g.key}`} flexDirection="column">
        {repoHeading(ui, g, columns, { key: id, dim, autoFocus: ring === id, onPress: () => a.open(id, { kind: 'repo', path: g.path ?? '' }) })}
        {g.rows.map(row)}
      </Box>
    )
  }

  return (
    <Box flexDirection="column">
      {titleRow(ui, a, m.updated)}
      {m.stale !== null && <Text color="warning">{m.stale}</Text>}
      {m.partial && <Text dimColor>{PRS_NOT_SHOWN}</Text>}
      {m.withoutTracker !== null && <Text dimColor>{m.withoutTracker}</Text>}
      <Box key="needs" flexDirection="column">
        <Text bold>{HEADINGS.needs}</Text>
        {m.needs.length > 0 ? m.needs.map(row) : <Text dimColor={dim}>{m.alone ? ONLY_THIS : NOTHING_NEEDS}</Text>}
      </Box>
      {m.running.length > 0 && (
        <Box key="running" flexDirection="column">
          <Text bold>{HEADINGS.running}</Text>
          {m.running.map(group('running'))}
        </Box>
      )}
      {m.done.length > 0 && (
        <Box key="done" flexDirection="column">
          <Text bold>{HEADINGS.done}</Text>
          {m.done.map(group('done'))}
          {m.doneMore !== null && <Text dimColor>{m.doneMore}</Text>}
        </Box>
      )}
      {m.ended.length > 0 && (
        <Box key="ended" flexDirection="column">
          <Text bold>{HEADINGS.ended}</Text>
          {m.ended.map(row)}
          {m.endedMore !== null && <Text dimColor>{m.endedMore}</Text>}
        </Box>
      )}
      {m.repos.length === 0 ? (
        <Text dimColor={dim}>{NO_REPOS}</Text>
      ) : (
        <Box key="repos" flexDirection="row" flexWrap="wrap">
          <Text>Repos:</Text>
          {m.repos.map((r, i) => (
            <Box key={r.path} flexDirection="row">
              <Text dimColor>{i === 0 ? ' ' : ' · '}</Text>
              <Button key={`repos:${r.path}`} plain autoFocus={ring === `repos:${r.path}` ? true : undefined} label={[r.label, ...r.counts].join(' ')} onPress={() => a.open(`repos:${r.path}`, { kind: 'repo', path: r.path })} />
            </Box>
          ))}
        </Box>
      )}
    </Box>
  )
}
