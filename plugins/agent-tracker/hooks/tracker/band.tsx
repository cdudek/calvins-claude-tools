// The band: one row above every prompt (compact), the details view, Copy and the /tracker band commands.
// It only reads: the snapshot, settings.json and the clock. It never writes to a session.
// `$` is passed only to plain top-level functions: the engine's source scan reads no other spelling.
import { atom, read } from 'claude-code'
import type { EngineInterface, On } from 'claude-code'

import { BAND_REPLY, BUTTON_LABELS, COPIED, bandData, columnsAlt, columnsSvg, compactLayout, copyFailed, detailsLayout, paint, rule, stateMarkdown } from './core'
import type { Column, Spans } from './core'
import { ensureCollector } from './collector'
import { openPane, readSettings, startUi, writeSettings } from './store'
import type { State } from './store'
import type { Snapshot } from './types'

type Engine = EngineInterface
type Surface = Parameters<Engine['ui']['copy']>[0]['surface']
// The collector writes it; the band and the pane read it. The same literal, declared where it is read.
const snapshot = atom({ plugin: 'agent-tracker', key: 'snapshot' } as const, { at: 0, agentsOk: true, okAt: 0, failedReads: 0, sessions: [] } as Snapshot)

async function current($: Engine) {
  return bandData(await read($, snapshot), await $.session.id(), await $.clock.now())
}

// Copy the state as Markdown. The toast says whether it worked (F36, F86).
async function copyState($: Engine, surface: Surface) {
  const done = await $.ui.copy({ text: stateMarkdown(await current($)), ...(surface === undefined ? {} : { surface }) })
  const said = done.isCopied ? COPIED : copyFailed(done.reason)
  $.ui.toast(said)
  return said
}

async function toggleView($: Engine, s: State) {
  await writeSettings($, s, { view: (await readSettings($, s)).view === 'details' ? 'compact' : 'details' })
}

// The band's `/tracker` words. The text to answer with, or null when the words are not the band's (the pane's).
export async function bandCommand($: Engine, s: State, args: string): Promise<string | null> {
  const [first, second, ...rest] = args.trim().toLowerCase().split(/\s+/).filter(Boolean)
  if (rest.length > 0 || first === undefined) return null
  if (second === undefined && (first === 'details' || first === 'compact')) await writeSettings($, s, { view: first })
  else if (second === undefined && first === 'copy') return copyState($, undefined)
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
    const data = await current($)
    const { Box, Text, Button } = $.ui.resolve(e)
    // bodyColumns counts terminal cells; a graphical surface draws Buttons wider than their cells, so a row sized to it wraps there.
    const isTerminal = e.surface === 'terminal'
    const width = isTerminal ? columns : undefined
    // One blank line above our row, and a rule between it and the next mod's row, so the mods do not run together.
    const stack = (mine: NonNullable<typeof below>) => (
      <Box flexDirection="column" marginTop={1}>
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
            <Button key="details" plain label={BUTTON_LABELS.details} onPress={view} />
          </Box>
        </Box>,
      )
    }

    const d = detailsLayout(data, columns)
    const cols = d.rows.flat()
    const cell = (c: Column) => (
      <Box key={c.key} flexDirection="column" width={d.colWidth}>
        <Text dimColor>{c.label}</Text>
        <Text bold dimColor={data.stale !== null} color={c.countTone === 'red' ? paint({ text: '', tone: 'red' }).color : undefined}>
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
            <Button key="copy" plain label={BUTTON_LABELS.copy} onPress={() => void copyState($, e.surface)} />
            {pane}
            <Button key="details" plain label={BUTTON_LABELS.compact} onPress={view} />
          </Box>
        </Box>
        {d.header[1] !== undefined && <Text wrap="truncate-end">{run(d.header[1], 'h1')}</Text>}
        {d.note !== null && <Text dimColor>{d.note}</Text>}
        {cols.length > 0 && table}
      </Box>,
    )
  })
}
