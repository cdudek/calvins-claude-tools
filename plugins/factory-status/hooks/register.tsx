import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { FactoryStatusBoard } from '../types/index'
import { ancestors, jsonArgv, lineArgv, parseBoard, parseLine, scriptPath } from './status'

const PANE = 'factory-status'
const EVERY_MS = 20_000
const TIMEOUT_MS = 5_000

const root = atom({ plugin: 'factory-status', key: 'root' } as const, '')
const line = atom({ plugin: 'factory-status', key: 'line' } as const, '')
const board = atom(
  { plugin: 'factory-status', key: 'board' } as const,
  null as FactoryStatusBoard | null,
  { shape: 'board-1' },
)

async function findRoot($: EngineInterface, cwd: string): Promise<string> {
  for (const dir of ancestors(cwd)) {
    const { exitCode } = await $.process.run(['test', '-f', scriptPath(dir)], {
      timeoutMs: TIMEOUT_MS,
    })
    if (exitCode === 0) return dir
  }
  return ''
}

/** Runs the repo's script; any failure leaves the status as it was. */
async function refresh($: EngineInterface, cwd?: string): Promise<void> {
  try {
    let dir = await read($, root)
    if (!dir && cwd) {
      dir = await findRoot($, cwd)
      await update($, root, () => dir)
    }
    if (!dir) return

    const run = await $.process.run(lineArgv(dir), { cwd: dir, timeoutMs: TIMEOUT_MS })
    if (run.exitCode !== 0) return
    const text = parseLine(run.stdout)
    $.ui.status(text || undefined)
    await update($, line, () => text)

    const json = await $.process.run(jsonArgv(dir), { cwd: dir, timeoutMs: TIMEOUT_MS })
    if (json.exitCode === 0) await update($, board, () => parseBoard(json.stdout))
  } catch {
    // keep the last status
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    try {
      await $.command.register({
        name: 'factory-status',
        description: 'Show where the factory run in this repo stands, in a pane',
      })
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

  on('command.run', { command: 'factory-status' }, async $ => {
    await refresh($)
    await $.ui.open({ id: PANE, title: 'Factory' })
    return { text: 'Factory pane opened.' }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const b = await read($, board)
    const l = await read($, line)

    if (!b) return <Text dimColor>No factory run found in this repo.</Text>

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
