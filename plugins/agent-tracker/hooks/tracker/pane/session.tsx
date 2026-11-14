// The Session page: header, Running now, Usage, Milestone and Asks (spec/screens.md "Pane, Session").
import { NO_ASKS, FROM_TRANSCRIPT, PANE_BUTTONS, SECTION_WORDS, askLines, kindWidth } from '../core'
import type { SessionModel } from '../core'
import { navRow } from './chrome'
import type { Actions, Ui } from './chrome'

export function sessionView(ui: Ui, m: SessionModel, a: Actions, columns: number) {
  const { Box, Text, Button, Link } = ui
  const kinds = kindWidth(m.asks)
  return (
    <Box flexDirection="column">
      {navRow(ui, a)}
      <Text dimColor>{m.crumbs}</Text>
      <Text bold>{m.title}</Text>
      <Text>{m.state}</Text>
      <Box key="where" flexDirection="row" flexWrap="wrap">
        {m.repo !== null && <Button key={`repo:${m.repo.path}`} plain label={m.repo.label} onPress={() => a.open(`repo:${m.repo?.path}`, { kind: 'repo', path: m.repo?.path ?? '' })} />}
        {m.branch !== null && <Text dimColor>{m.repo === null ? '' : ' · '}</Text>}
        {m.branch !== null && <Text>{m.branch}</Text>}
        {m.pr !== null && <Text dimColor> · PR </Text>}
        {m.pr !== null && <Link href={m.pr.url} label={`#${m.pr.number}`} />}
        {m.pr !== null && <Text> {m.pr.checks}</Text>}
      </Box>
      {m.resume !== null && <Button key="resume" plain label={PANE_BUTTONS.resume} hotkey="r" onPress={a.resume} />}
      {m.running.length > 0 && (
        <Box key="running" flexDirection="column">
          <Text bold>{SECTION_WORDS.running}</Text>
          {m.running.map(r => (
            <Text key={r}>{r}</Text>
          ))}
        </Box>
      )}
      <Box key="usage" flexDirection="column">
        <Text bold>{SECTION_WORDS.usage}</Text>
        <Text>{m.usage}</Text>
      </Box>
      {m.milestone !== null && (
        <Box key="milestone" flexDirection="column">
          <Text bold>{SECTION_WORDS.milestone}</Text>
          <Text>{m.milestone.sentence}</Text>
          <Text>{m.milestone.count}</Text>
          {m.milestone.rows.map(r => (
            <Text key={r}>{r}</Text>
          ))}
        </Box>
      )}
      <Box key="asks" flexDirection="column">
        <Text bold>{SECTION_WORDS.asks}</Text>
        {m.fromTranscript && <Text dimColor>{FROM_TRANSCRIPT}</Text>}
        {m.asks.length === 0 && <Text dimColor>{NO_ASKS}</Text>}
        {m.asks.map(k => (
          <Box key={`ask:${k.n}`} flexDirection="column">
            {askLines(k, columns, kinds).map((line, i) => (
              <Text key={`l${i}`}>{line}</Text>
            ))}
          </Box>
        ))}
      </Box>
    </Box>
  )
}
