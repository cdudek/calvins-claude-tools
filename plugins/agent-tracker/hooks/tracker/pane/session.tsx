// The Session page (spec/screens.md "Pane, Session").
import { navRow } from './chrome'
import type { Actions, Ui } from './chrome'

export function sessionView(ui: Ui, title: string, a: Actions) {
  const { Box, Text } = ui
  return (
    <Box flexDirection="column">
      {navRow(ui, a)}
      <Text bold>{title}</Text>
    </Box>
  )
}
