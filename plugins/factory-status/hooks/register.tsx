import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { FactoryStatusBoard } from '../types/index'
import {
  BOARD_URL,
  ancestors,
  installArgv,
  join,
  jsonArgv,
  lineArgv,
  parseBoard,
  parseLine,
  probeArgv,
} from './status'

const PANE = 'factory-status'
const HIDDEN_KEY = 'bandHidden'
const EVERY_MS = 20_000
const TIMEOUT_MS = 5_000

const root = atom({ plugin: 'factory-status', key: 'root' } as const, '')
const line = atom({ plugin: 'factory-status', key: 'line' } as const, '')
const board = atom(
  { plugin: 'factory-status', key: 'board' } as const,
  null as FactoryStatusBoard | null,
  { shape: 'board-1' },
)

const hidden = atom({ plugin: 'factory-status', key: 'hidden' } as const, false)

/** The nearest git root at or above cwd (never past it) that holds `.factory/` or `changes/`; '' otherwise. Only existence is tested, nothing in the repo runs. */
async function findRoot($: EngineInterface, cwd: string): Promise<string> {
  const test = async (flag: string, path: string) =>
    (await $.process.run(['test', flag, path], { timeoutMs: TIMEOUT_MS })).exitCode === 0
  for (const dir of ancestors(cwd)) {
    if (!(await test('-e', join(dir, '.git')))) continue
    return (await test('-d', join(dir, '.factory'))) || (await test('-d', join(dir, 'changes'))) ? dir : ''
  }
  return ''
}

/** Runs the plugin's own bundled reader on the repo; any failure leaves the status as it was. */
async function refresh($: EngineInterface, cwd?: string): Promise<void> {
  try {
    let dir = await read($, root)
    if (!dir && cwd) {
      dir = await findRoot($, cwd)
      await update($, root, () => dir)
    }
    if (!dir) return

    const run = await $.process.run(lineArgv($.plugin.root, dir), { timeoutMs: TIMEOUT_MS })
    if (run.exitCode !== 0) return
    const text = parseLine(run.stdout)
    await update($, line, () => text)

    const json = await $.process.run(jsonArgv($.plugin.root, dir), { timeoutMs: TIMEOUT_MS })
    if (json.exitCode === 0) await update($, board, () => parseBoard(json.stdout))
  } catch {
    // keep the last status
  }
}

const answers = async ($: EngineInterface): Promise<boolean> => {
  const r = await $.process.run(probeArgv(), { timeoutMs: TIMEOUT_MS }).catch(() => null)
  return r !== null && r.exitCode === 0 && r.stdout.trim().startsWith('2')
}

/** Starts the board (the bundled copy installs a launchd agent) when nothing answers on its port, then opens it in the browser. Returns the sentence to show. */
async function openBoard($: EngineInterface): Promise<string> {
  try {
    if (!(await answers($))) {
      const install = await $.process.run(installArgv($.plugin.root), { timeoutMs: 30_000 })
      if (install.exitCode !== 0) return `Board install failed: ${install.stderr.trim().split('\n').pop() || 'exit ' + install.exitCode}`
      // the agent needs a moment to bind the port
      await $.process.run(probeArgv(true), { timeoutMs: 15_000 })
      if (!(await answers($))) return `Board installed but nothing answers at ${BOARD_URL} yet. Try again in a moment.`
    }
    const system = await $.process.run(['uname', '-s'], { timeoutMs: TIMEOUT_MS }).catch(() => null)
    const opener = system !== null && system.stdout.trim() === 'Darwin' ? 'open' : 'xdg-open'
    const opened = await $.process.run([opener, BOARD_URL], { timeoutMs: 10_000 })
    return opened.exitCode === 0 ? `Board opened at ${BOARD_URL.replace(/\/$/, '')}` : `Board is up at ${BOARD_URL} but no browser could be opened.`
  } catch (err) {
    return `Board could not be opened: ${err instanceof Error ? err.message : String(err)}`
  }
}

async function setHidden($: EngineInterface, value: boolean): Promise<void> {
  await update($, hidden, () => value)
  await $.store.set(HIDDEN_KEY, value).catch(() => undefined)
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    try {
      await $.command.register({
        name: 'factory-status',
        description: 'Factory status: pane (default), web (open the board), band on|off',
      })
      const wasHidden = (await $.store.get(HIDDEN_KEY).catch(() => false)) === true
      await update($, hidden, () => wasHidden)
      await refresh($, e.cwd)
      $.clock.every(EVERY_MS, () => void refresh($, e.cwd))
    } catch {
      // never throw out of a hook
    }
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    void refresh($)
    return next(e)
  })

  on('command.run', { command: 'factory-status' }, async ($, e) => {
    const [first, second] = e.args.trim().toLowerCase().split(/\s+/)
    if (first === 'web') return { text: await openBoard($) }
    if (first === 'band' && (second === 'on' || second === 'off')) {
      await setHidden($, second === 'off')
      return { text: second === 'off' ? 'Band hidden. /factory-status band on shows it again.' : 'Band shown.' }
    }
    await refresh($)
    await $.ui.open({ id: PANE, title: 'Factory' })
    return { text: 'Factory pane opened.' }
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey || (await read($, hidden)) || !(await read($, root))) return next(e)
    const text = await read($, line)
    const b = await read($, board)
    const needs = b && b.column === 'needs-you' ? b.needs : ''
    if (!text && !needs) return next(e)

    const { Box, Text, Button } = $.ui.resolve(e)
    return (
      <Box flexDirection="row" alignItems="center" width={e.surface === 'terminal' ? e.props.bodyColumns : undefined}>
        <Text wrap="truncate-end">
          <Text bold>factory</Text>
          {needs && <Text color="red">{`  needs you: ${needs}`}</Text>}
          {text && <Text dimColor={needs !== ''}>{`  ${text}`}</Text>}
        </Text>
        <Box flexGrow={1} width={2} />
        <Box flexDirection="row" gap={2}>
          <Button key="pane" plain label="[pane]" onPress={() => void $.ui.open({ id: PANE, title: 'Factory', focus: true }).catch(() => undefined)} />
          <Button key="board" plain label="[board]" onPress={() => void openBoard($).then(t => $.ui.toast(t))} />
          <Button key="hide" plain dimColor label="[–]" onPress={() => void setHidden($, true).then(() => $.ui.toast('Band hidden. /factory-status band on shows it again.'))} />
        </Box>
      </Box>
    )
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const b = await read($, board)
    const l = await read($, line)

    if (!b) return <Text dimColor>No factory change in this repo.</Text>

    return (
      <Box flexDirection="column">
        <Text bold>{b.change}{b.title ? ` · ${b.title}` : ''} [{b.column}]</Text>
        {l && <Text>{l}</Text>}
        {b.needs && <Text color="yellow">Needs you: {b.needs}{b.where ? ` (${b.where})` : ''}</Text>}
        <Text bold>Milestones</Text>
        {b.milestones.map(m => (
          <Text>{m.id} {m.state}</Text>
        ))}
        {b.tasks.length > 0 && <Text bold>Tasks</Text>}
        {b.tasks.map(t => (
          <Text>{t.id} {t.state}</Text>
        ))}
      </Box>
    )
  })
}
