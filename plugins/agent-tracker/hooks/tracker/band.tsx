// The band: one row above every prompt (compact), the details view, Copy and the /tracker band commands.
// It only reads: the snapshot, settings.json and the clock. It never writes to a session.
// `$` is passed only to plain top-level functions: the engine's source scan reads no other spelling.
import { atom, read } from 'claude-code'
import type { EngineInterface, On } from 'claude-code'

import { BAND_REPLY, BOARD_FAILED, DIVIDER_LABEL, DIVIDER_LEAD, TONE_COLOR, cells, BUTTON_LABELS, COPIED, bandData, columnsAlt, columnsSvg, compactLayout, copyFailed, detailsLayout, paint, rule, stateMarkdown } from './core'
import type { Column, Spans } from './core'
import { ensureCollector } from './collector'
import { itemsOf } from './notes'
import { openPane, readSettings, startUi, writeSettings } from './store'
import type { State } from './store'
import type { Snapshot } from './types'

type Engine = EngineInterface
type Surface = Parameters<Engine['ui']['copy']>[0]['surface']
// The collector writes it; the band and the pane read it. The same literal, declared where it is read.
const snapshot = atom({ plugin: 'agent-tracker', key: 'snapshot' } as const, { at: 0, agentsOk: true, okAt: 0, failedReads: 0, sessions: [] } as Snapshot)

async function current($: Engine, s: State) {
  const snap = await read($, snapshot)
  const now = await $.clock.now()
  return bandData(snap, await $.session.id(), now, await itemsOf($, s, snap, now))
}

// Copy the state as Markdown. The toast says whether it worked (F36, F86).
async function copyState($: Engine, s: State, surface: Surface) {
  const done = await $.ui.copy({ text: stateMarkdown(await current($, s)), ...(surface === undefined ? {} : { surface }) })
  const said = done.isCopied ? COPIED : copyFailed(done.reason)
  $.ui.toast(said)
  return said
}

// Board: the web page, which the `/tracker web` command builds and opens. A command nothing answers says so, and the toast says it.
async function openBoard($: Engine) {
  const done = await $.command.run({ command: 'tracker', args: 'web' }).catch(() => null)
  $.ui.toast(done?.text ? done.text : BOARD_FAILED)
}

// [–]: hide the band; /tracker band on brings it back.
async function hideBand($: Engine, s: State) {
  await writeSettings($, s, { bandHidden: true })
  $.ui.toast(BAND_REPLY.hidden)
}

async function toggleView($: Engine, s: State) {
  await writeSettings($, s, { view: (await readSettings($, s)).view === 'details' ? 'compact' : 'details' })
}

// The band's `/tracker` words. The text to answer with, or null when the words are not the band's (the pane's).
export async function bandCommand($: Engine, s: State, args: string): Promise<string | null> {
  const [first, second, ...rest] = args.trim().toLowerCase().split(/\s+/).filter(Boolean)
  if (rest.length > 0 || first === undefined) return null
  if (second === undefined && (first === 'details' || first === 'compact')) await writeSettings($, s, { view: first })
  else if (second === undefined && first === 'copy') return copyState($, s, undefined)
  else if (first === 'band' && (second === 'on' || second === 'off')) await writeSettings($, s, { bandHidden: second === 'off' })
  else return null
  return second === undefined ? BAND_REPLY[first as 'details' | 'compact'] : BAND_REPLY[second === 'off' ? 'hidden' : 'shown']
}

export const registerBand = (on: On, s: State) => {
  on('command.run', { command: 'tracker' }, async ($, e, next) => {
    const text = await bandCommand($, s, e.args)
    return text === null ? next(e) : { text }
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)
    await startUi($, s)
    await ensureCollector($, s)
    const settings = await readSettings($, s)
    if (settings.bandHidden) return next(e)
    // Other mods share this slot: draw theirs below ours instead of replacing it.
    // next(e) rejects only when nothing answers beneath (the test harness): the band still draws.
    const below = await next(e).catch(() => undefined)

    const columns = e.props.bodyColumns
    const data = await current($, s)
    const { Box, Text, Button } = $.ui.resolve(e)
    // bodyColumns counts terminal cells; a graphical surface draws Buttons wider than their cells, so a row sized to it wraps there.
    const isTerminal = e.surface === 'terminal'
    const width = isTerminal ? columns : undefined
    // Our row is set apart from the other mods': an empty line, then a dim rule that carries the label "tracker", then our row.
    // A rule of box characters is for the terminal; a graphical surface gets the empty line alone.
    const stack = (mine: NonNullable<typeof below>) => (
      <Box flexDirection="column">
        <Text key="gap">{' '}</Text>
        {isTerminal && (
          <Text key="divider" wrap="truncate-end">
            <Text dimColor>{DIVIDER_LEAD}</Text>
            <Text bold color={TONE_COLOR.label}>
              {DIVIDER_LABEL}
            </Text>
            <Text dimColor>{` ${'─'.repeat(Math.max(1, columns - cells(DIVIDER_LEAD) - cells(DIVIDER_LABEL) - 1))}`}</Text>
          </Text>
        )}
        {mine}
        {below && isTerminal && (
          <Text key="below-rule" dimColor>
            {rule(columns).text}
          </Text>
        )}
        {below}
      </Box>
    )
    const run = (spans: Spans, key: string) => spans.map((x, i) => <Text key={`${key}${i}`} {...paint(x)}>{x.text}</Text>)
    const view = () => toggleView($, s)
    const pane = <Button key="pane" plain label={BUTTON_LABELS.pane} onPress={() => openPane($, s)} />
    const board = <Button key="board" plain label={BUTTON_LABELS.board} onPress={() => void openBoard($)} />
    const hide = <Button key="hide" plain dimColor label={BUTTON_LABELS.hide} onPress={() => void hideBand($, s)} />

    if (settings.view !== 'details') {
      return stack(
        <Box flexDirection="row" alignItems="center" width={width}>
          {compactLayout(data, columns).segments.map(seg => (
            <Box key={seg.id} flexDirection="row">
              {run(seg.chunks, seg.id)}
            </Box>
          ))}
          <Box flexGrow={1} width={2} />
          <Box flexDirection="row" gap={2}>
            {pane}
            {board}
            <Button key="details" plain label={BUTTON_LABELS.details} onPress={view} />
            {hide}
          </Box>
        </Box>,
      )
    }

    const d = detailsLayout(data, columns)
    const cols = d.rows.flat()
    const cell = (c: Column) => (
      <Box key={c.key} flexDirection="column" width={d.colWidth}>
        <Text dimColor>{c.label}</Text>
        <Text bold {...paint({ text: '', tone: c.countTone })} dimColor={data.stale !== null ? true : undefined}>
          {c.count}
        </Text>
        {c.line !== '' && <Text wrap="truncate-end">{run(c.lineSpans, `${c.key}-line`)}</Text>}
      </Box>
    )
    let table = (
      <Box flexDirection="column">
        {isTerminal && (
          <Text dimColor wrap="truncate-end">
            {'─'.repeat(columns)}
          </Text>
        )}
        {d.rows.map((r, i) => (
          <Box key={`row-${i}`} flexDirection="row">
            {r.map(cell)}
          </Box>
        ))}
      </Box>
    )
    // Text glyphs make broken lines in the desktop's proportional font; an SVG draws real ones.
    if (e.surface === 'desktop') {
      const { Svg } = $.ui.resolve(e)
      table = <Svg source={columnsSvg(cols)} alt={columnsAlt(cols)} />
    }

    return stack(
      // The desktop's SVG draws its own line at the top, which would touch the buttons without the gap.
      <Box flexDirection="column" width={width} gap={e.surface === 'desktop' ? 1 : 0}>
        <Box flexDirection="row" alignItems="center">
          <Text wrap="truncate-end">{run(d.header[0] ?? [], 'h0')}</Text>
          <Box flexGrow={1} width={2} />
          <Box flexDirection="row" gap={2}>
            <Button key="copy" plain label={BUTTON_LABELS.copy} onPress={() => void copyState($, s, e.surface)} />
            {pane}
            {board}
            <Button key="details" plain label={BUTTON_LABELS.compact} onPress={view} />
            {hide}
          </Box>
        </Box>
        {d.header[1] !== undefined && <Text wrap="truncate-end">{run(d.header[1], 'h1')}</Text>}
        {d.note !== null && <Text dimColor>{d.note}</Text>}
        {cols.length > 0 && table}
      </Box>,
    )
  })
}
