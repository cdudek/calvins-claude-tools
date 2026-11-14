// The Repo page: Open PRs, Worktrees and Ended (spec/screens.md "Pane, Repo"), and the not-found line of a page
// a `/tracker` word could not match.
import { WIDE, prTitle } from '../core'
import type { PrView, RepoModel } from '../core'
import { navRow, ringOn, sessionRow } from './chrome'
import type { Actions, Ui } from './chrome'

const SEP = ' · '

// One PR. From 70 columns one line: the number as a link, the title up to 30 cells, then the words. Below, the number,
// title and checks, then review, mergeable and the session button. Failing checks are in the error colour, never dim.
function prRow(ui: Ui, p: PrView, columns: number, a: Actions) {
  const { Box, Text, Button, Link } = ui
  const checks = <Text color={p.failing ? 'error' : undefined}>{p.checks}</Text>
  const session = p.session && <Button key={`pr-session:${p.number}`} plain autoFocus={ringOn(a, `pr-session:${p.number}`)} label={`session: ${p.session.title}`} onPress={() => a.open(`pr-session:${p.number}`, { kind: 'session', id: p.session?.id ?? '' })} />
  const link = <Link href={p.url} label={`#${p.number}`} />
  const title = <Text>{` ${prTitle(p, columns)}`}</Text>
  if (columns >= WIDE)
    return (
      <Box key={`pr:${p.number}`} flexDirection="row" flexWrap="wrap">
        {link}
        {title}
        <Text>{SEP}</Text>
        {checks}
        <Text>{`${SEP}${p.review}${SEP}${p.mergeable}`}</Text>
        {session && <Text>{SEP}</Text>}
        {session}
      </Box>
    )
  return (
    <Box key={`pr:${p.number}`} flexDirection="column">
      <Box flexDirection="row">
        {link}
        {title}
        <Text> </Text>
        {checks}
      </Box>
      <Box flexDirection="row" flexWrap="wrap">
        <Text>{`${p.review}${SEP}${p.mergeable}`}</Text>
        {session && <Text>{SEP}</Text>}
        {session}
      </Box>
    </Box>
  )
}

export function repoView(ui: Ui, m: RepoModel, a: Actions, columns: number) {
  const { Box, Text } = ui
  const row = (r: RepoModel['ended'][number]) => sessionRow(ui, r, columns, { key: `session:${r.id}`, dim: false, autoFocus: a.ring === `session:${r.id}`, onPress: () => a.open(`session:${r.id}`, { kind: 'session', id: r.id }) })
  return (
    <Box flexDirection="column">
      {navRow(ui, a)}
      <Text dimColor>{m.crumbs}</Text>
      <Text bold>{m.label}</Text>
      <Box key="prs" flexDirection="column">
        <Text bold>Open PRs</Text>
        {m.stored !== null && <Text dimColor>{m.stored}</Text>}
        {m.prsNote !== null && <Text dimColor>{m.prsNote}</Text>}
        {m.prs.map(p => prRow(ui, p, columns, a))}
      </Box>
      <Box key="worktrees" flexDirection="column">
        <Text bold>Worktrees</Text>
        {m.worktreesNote !== null && <Text dimColor>{m.worktreesNote}</Text>}
        {m.worktrees.map(w => (
          <Box key={`tree:${w.label}`} flexDirection="column">
            <Text>{`${w.label}${SEP}${w.branch}`}</Text>
            {w.rows.map(row)}
          </Box>
        ))}
      </Box>
      {m.ended.length > 0 && (
        <Box key="ended" flexDirection="column">
          <Text bold>Ended</Text>
          {m.ended.map(row)}
        </Box>
      )}
    </Box>
  )
}

// A page a command argument could not find: one line, Home and Close.
export function missingView(ui: Ui, line: string, a: Actions) {
  const { Box, Text } = ui
  return (
    <Box flexDirection="column">
      {navRow(ui, a, false)}
      <Text>{line}</Text>
    </Box>
  )
}
