import type { Register } from 'claude-code'

import { registerAsks } from './asks'
import { registerBand } from './band'
import { registerBoard } from './board'
import { registerCollector } from './collector'
import { registerPane } from './pane'
import { newState } from './store'

export const register: Register = on => {
  const s = newState()
  registerCollector(on, s)
  registerAsks(on, s)
  registerBoard(on, s) // before the pane: it answers every /tracker word it does not know
  registerBand(on, s)
  registerPane(on, s)
}
