// Draws any page: the breadcrumb header, then the blocks of the model (coloured lines, rows that are Buttons, inline
// lists), then the key words. Pure drawing: the handlers come in as closures, so no `$` is passed here.
import type { EngineInterface } from 'claude-code'

import { PANE_BUTTONS, paint, rule } from '../core'
import type { Block, Item, PaneModel, Page, Spans } from '../core'

export type Ui = ReturnType<EngineInterface['ui']['resolve']>
export type Actions = {
  open: (key: string, page: Page) => void
  jump: (page: Page) => void
  close: () => void
  resume: () => void
  ring: string | null // the element holding the focus ring, as `ui.focus` last said (null: none moved it yet)
}

// `autoFocus` follows the ring, so a redraw leaves it where the person put it, and Back returns it to its row.
const ringOn = (ring: string | null, key: string) => (ring === key ? (true as const) : undefined)

export function paneView(ui: Ui, m: PaneModel, a: Actions, columns: number) {
  const { Box, Text, Button, Link } = ui
  const ring = a.ring ?? m.first
  const spans = (list: Spans, key: string) =>
    list.map((s, i) => (
      <Text key={`${key}:${i}`} {...paint(s)}>
        {s.text}
      </Text>
    ))
  // A line of spans as one Text, so a long one wraps or is cut as a paragraph.
  const line = (list: Spans, key: string, wrap: boolean) => (
    <Text key={key} wrap={wrap ? 'wrap' : 'truncate-end'}>
      {spans(list, key)}
    </Text>
  )

  const crumbs = m.crumbs.flatMap((c, i) => {
    const text = (
      <Text key={`crumb-text:${i}`} bold={c.bold} dimColor={c.to !== null}>
        {c.text}
      </Text>
    )
    const sep = i > 0 ? [<Text key={`crumb-sep:${i}`} dimColor>{' › '}</Text>] : []
    const to = c.to
    return [...sep, to === null ? text : <Button key={`crumb:${i}`} plain autoFocus={ringOn(ring, `crumb:${i}`)} onPress={() => a.jump(to)}>{text}</Button>]
  })

  const item = (b: Extract<Block, { kind: 'inline' }>, it: Item, i: number) => {
    const sep = i > 0 && b.sep !== null && it.joined !== true ? [<Text key={`${it.key}:sep`} dimColor>{b.sep.text}</Text>] : []
    const label = it.spans.map(s => s.text).join('')
    const to = it.to
    const body =
      it.href !== undefined && it.href !== '' ? (
        <Link key={it.key} href={it.href} label={label} />
      ) : to !== undefined ? (
        <Button key={it.key} plain autoFocus={ringOn(ring, it.key)} onPress={() => a.open(it.key, to)}>
          {spans(it.spans, it.key)}
        </Button>
      ) : (
        <Box key={it.key} flexDirection="row">
          {spans(it.spans, it.key)}
        </Box>
      )
    return [...sep, body]
  }

  const block = (b: Block, i: number) => {
    switch (b.kind) {
      case 'rule':
        return (
          <Text key={`rule:${i}`} dimColor>
            {rule(columns).text}
          </Text>
        )
      case 'lines':
        return (
          <Box key={b.key} flexDirection="column">
            {b.lines.map((l, j) => line(l, `${b.key}:${j}`, b.wrap === true))}
          </Box>
        )
      case 'row':
        return (
          <Button key={b.key} plain autoFocus={ringOn(ring, b.key)} onPress={() => a.open(b.key, b.to)}>
            {b.lines.flatMap((l, j) => [...(j > 0 ? [<Text key={`${b.key}:nl${j}`}>{'\n'}</Text>] : []), ...spans(l, `${b.key}:${j}`)])}
          </Button>
        )
      case 'inline':
        return (
          <Box key={b.key} flexDirection="row" flexWrap="wrap">
            {spans(b.head, `${b.key}:head`)}
            {b.items.flatMap((it, j) => item(b, it, j))}
          </Box>
        )
      case 'copy':
        return <Button key={b.key} plain autoFocus={ringOn(ring, b.key)} label={b.label} onPress={a.resume} />
    }
  }

  return (
    <Box flexDirection="column" paddingLeft={1}>
      <Box key="header" flexDirection="row" flexWrap="wrap">
        {crumbs}
        <Box flexGrow={1} width={2} />
        {spans(m.right, 'right')}
      </Box>
      {m.blocks.map(block)}
      <Box key="footer" flexDirection="row">
        {m.footer !== null && <Text wrap="truncate-end">{spans(m.footer, 'footer')}</Text>}
        <Box flexGrow={1} width={2} />
        <Button key="close" plain dimColor autoFocus={ringOn(ring, 'close')} label={PANE_BUTTONS.close} onPress={a.close} />
      </Box>
    </Box>
  )
}
