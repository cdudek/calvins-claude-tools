export type Snapshot = { at: number }

declare module 'claude-code' {
  interface PluginState {
    'agent-tracker': { snapshot: Snapshot }
  }
}
