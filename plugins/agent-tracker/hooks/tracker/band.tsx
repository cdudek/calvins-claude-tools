// The band: one row above every prompt (compact), the details view, Copy and the /tracker band commands.
// It only reads: the snapshot, settings.json and the clock. It never writes to a session.
// `$` is passed only to plain top-level functions: the engine's source scan reads no other spelling.
import { atom, read } from 'claude-code'
import type { EngineInterface, On } from 'claude-code'

import { BUTTON_LABELS, COMMAND_DESCRIPTION, COMMAND_HINT, COPIED, PANE_ID, REDRAW_MS, SEP, bandData, columnsAlt, columnsSvg, compactLayout, copyFailed, detailsLayout, stateMarkdown } from './core'
import type { Chunk, Column } from './core'
import { readSettings, writeSettings } from './store'
import type { State } from './store'
import type { Snapshot } from './types'

type Engine = EngineInterface
type Surface = Parameters<Engine['ui']['copy']>[0]['surface']
// The collector writes it; the band and the pane read it. The same literal, declared where it is read.
const snapshot = atom({ plugin: 'agent-tracker', key: 'snapshot' } as const, { at: 0, agentsOk: true, okAt: 0, failedReads: 0, sessions: [] } as Snapshot)

// Once per session, at the first draw: the /tracker command and the one-minute redraw. The collector holds the one
// unmatched session.start, so the band starts here; a mod loaded mid-session draws at once too.
async function startBand($: Engine, s: State) {
  if (s.hasBand) return
  s.hasBand = true
  $.clock.every(REDRAW_MS, () => $.ui.invalidate('ui.render'))
  await $.command.register({ name: 'tracker', description: COMMAND_DESCRIPTION, argumentHint: COMMAND_HINT, immediate: true }).catch(() => undefined)
}

async function current($: Engine) {
  return bandData(await read($, snapshot), await $.session.id(), await $.clock.now())
}

// Copy the state as Markdown. The toast says whether it worked (F36, F86).
async function copyState($: Engine, surface: Surface) {
  const done = await $.ui.copy({ text: stateMarkdown(await current($)), ...(surface === undefined ? {} : { surface }) })
  $.ui.toast(done.isCopied ? COPIED : copyFailed(done.reason))
}

async function toggleView($: Engine, s: State) {
  await writeSettings($, s, { view: (await readSettings($, s)).view === 'details' ? 'compact' : 'details' })
}

async function openPane($: Engine) {
  await $.ui.open({ id: PANE_ID, title: 'Tracker' }).catch(() => undefined)
}

// The band's `/tracker` words. The text to answer with, or null when the words are not the band's (the pane's).
export async function bandCommand($: Engine, s: State, args: string): Promise<string | null> {
  const [first, second, ...rest] = args.trim().toLowerCase().split(/\s+/).filter(Boolean)
  if (rest.length > 0 || first === undefined) return null
  if (second === undefined && (first === 'details' || first === 'compact')) await writeSettings($, s, { view: first })
  else if (second === undefined && first === 'copy') await copyState($, undefined)
  else if (first === 'band' && (second === 'on' || second === 'off')) await writeSettings($, s, { bandHidden: second === 'off' })
  else return null
  return ''
}

export const registerBand = (on: On, s: State) => {
  on('command.run', { command: 'tracker' }, async ($, e, next) => {
    const text = await bandCommand($, s, e.args)
    return text === null ? next(e) : { text }
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)
    await startBand($, s)
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
    const stack = (mine: NonNullable<typeof below>) => (below ? <Box flexDirection="column">{mine}{below}</Box> : mine)
    const view = () => toggleView($, s)
    const pane = <Button key="pane" plain label={BUTTON_LABELS.pane} hotkey="p" onPress={() => openPane($)} />

    if (settings.view !== 'details') {
      const chunk = (c: Chunk, i: number) => (
        <Text key={`c${i}`} color={c.tone === 'warning' || c.tone === 'error' ? c.tone : undefined} dimColor={c.tone === 'dim'}>
          {c.text}
        </Text>
      )
      return stack(
        <Box flexDirection="row" alignItems="center" width={width}>
          {compactLayout(data, columns).segments.map((seg, i) => (
            <Box key={seg.id} flexDirection="row">
              {i > 0 && <Text dimColor>{SEP}</Text>}
              {seg.chunks.map(chunk)}
            </Box>
          ))}
          <Box flexGrow={1} />
          {pane}
          <Button key="details" plain label={BUTTON_LABELS.details} hotkey="d" onPress={view} />
        </Box>,
      )
    }

    const d = detailsLayout(data, columns)
    const cols = d.rows.flat()
    const cell = (c: Column) => (
      <Box key={c.key} flexDirection="column" {...(isTerminal ? { width: d.colWidth } : { flexGrow: 1 })}>
        <Text dimColor>{c.label}</Text>
        <Text bold dimColor={c.tone === 'dim' && data.stale !== null}>
          {c.count}
        </Text>
        {c.line !== '' && (
          <Text dimColor={c.tone === 'dim'} wrap="truncate-end">
            {c.line}
          </Text>
        )}
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
          <Box key={`row-${i}`} flexDirection="row" gap={2}>
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
          <Text wrap="truncate-end">{d.header[0]}</Text>
          <Box flexGrow={1} />
          <Button key="copy" plain label={BUTTON_LABELS.copy} hotkey="c" onPress={() => copyState($, e.surface)} />
          {pane}
          <Button key="details" plain label={BUTTON_LABELS.compact} hotkey="d" onPress={view} />
        </Box>
        {d.header[1] !== undefined && <Text>{d.header[1]}</Text>}
        {d.note !== null && <Text dimColor>{d.note}</Text>}
        {cols.length > 0 && table}
      </Box>,
    )
  })
}
