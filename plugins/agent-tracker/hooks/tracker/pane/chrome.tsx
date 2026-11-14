// What every page shares: the title row, the Back, Home and Close buttons, and a session row as one Button.
// Pure drawing: the handlers come in as closures, so no `$` is passed here.
import type { EngineInterface } from 'claude-code'

import { PANE_BUTTONS, PANE_TITLE, headingText, rowLayout } from '../core'
import type { Group, Page, Part, Row } from '../core'

export type Ui = ReturnType<EngineInterface['ui']['resolve']>
export type Actions = {
  open: (key: string, page: Page) => void
  back: () => void
  home: () => void
  close: () => void
  resume: () => void
  ring: string | null // the element holding the focus ring, as `ui.focus` last said (null: none moved it yet)
}

// `autoFocus` follows the ring, so a redraw leaves it where the person put it, and Back returns it to its row.
export const ringOn = (a: Actions, key: string) => (a.ring === key ? (true as const) : undefined)

const partProps = (p: Part, dim: boolean) => ({ dimColor: dim || p.tone === 'dim', color: p.tone === 'error' ? ('error' as const) : undefined })

// The title row of Home: "Tracker", when it was read, and Close.
export function titleRow(ui: Ui, a: Actions, updated: string | null) {
  const { Box, Text, Button } = ui
  return (
    <Box key="title" flexDirection="row" flexWrap="wrap" gap={2}>
      <Text bold>{PANE_TITLE}</Text>
      {updated !== null && <Text dimColor>{updated}</Text>}
      <Box flexGrow={1} />
      <Button key="close" plain label={PANE_BUTTONS.close} autoFocus={ringOn(a, 'close')} onPress={a.close} />
    </Box>
  )
}

// Session and Repo: Back, Home and Close in a row.
export function navRow(ui: Ui, a: Actions, withBack = true) {
  const { Box, Button } = ui
  return (
    <Box key="nav" flexDirection="row" flexWrap="wrap" gap={2}>
      {withBack && <Button key="back" plain label={PANE_BUTTONS.back} autoFocus={ringOn(a, 'back')} onPress={a.back} />}
      <Button key="home" plain label={PANE_BUTTONS.home} autoFocus={ringOn(a, 'home')} onPress={a.home} />
      <Button key="close" plain label={PANE_BUTTONS.close} autoFocus={ringOn(a, 'close')} onPress={a.close} />
    </Box>
  )
}

// A session as one focusable row. One line from 70 columns; below, the title and a second line of details.
export function sessionRow(ui: Ui, row: Row, columns: number, o: { key: string; dim: boolean; autoFocus: boolean; onPress: () => void }) {
  const { Text, Button } = ui
  const layout = rowLayout(row, columns)
  const parts = layout.details.map((p, i) => (
    <Text key={`p${i}`} {...partProps(p, o.dim)}>
      {i === 0 ? '' : ' · '}
      {p.text}
    </Text>
  ))
  return (
    <Button key={o.key} plain autoFocus={o.autoFocus ? true : undefined} onPress={o.onPress}>
      <Text dimColor={o.dim}>{layout.first}</Text>
      <Text>{layout.inline ? '   ' : '\n  '}</Text>
      {parts}
    </Button>
  )
}

// A repo heading: a button that opens the Repo page, its label cut and its counts whole.
export function repoHeading(ui: Ui, g: Group, columns: number, o: { key: string; dim: boolean; autoFocus: boolean; onPress: () => void }) {
  const { Text, Button } = ui
  const text = headingText(g, columns)
  if (g.path === null) return <Text key={o.key} bold dimColor={o.dim}>{text}</Text>
  return (
    <Button key={o.key} plain autoFocus={o.autoFocus ? true : undefined} onPress={o.onPress}>
      <Text bold dimColor={o.dim}>{text}</Text>
    </Button>
  )
}
