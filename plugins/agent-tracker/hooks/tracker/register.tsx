import type { Register } from 'claude-code'

import { registerAsks } from './asks'
import { registerBand } from './band'
import { registerCollector } from './collector'
import { registerPane } from './pane'
import { newState } from './store'

export const register: Register = on => {
  const s = newState()
  registerCollector(on, s)
  registerAsks(on, s)
  registerBand(on, s)
  registerPane(on, s)
}
