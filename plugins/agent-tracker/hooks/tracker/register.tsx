import type { Register } from 'claude-code'

import { registerCollector } from './collector'
import { newState } from './store'

export const register: Register = on => {
  const s = newState()
  registerCollector(on, s)
}
