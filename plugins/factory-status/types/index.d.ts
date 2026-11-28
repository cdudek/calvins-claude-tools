export type FactoryStatusItem = { id: string; state: string }

export type FactoryStatusBoard = {
  /** The change's slug. */
  change: string
  title: string
  /** needs-you | building | ready | backlog | done */
  column: string
  milestones: FactoryStatusItem[]
  /** Tasks of the current milestone; empty when none runs. */
  tasks: FactoryStatusItem[]
  /** The needs-you text, or '' when nothing waits on the owner. */
  needs: string
  /** Where the owner acts on the needs text, or ''. */
  where: string
}

declare module 'claude-code' {
  interface PluginState {
    'factory-status': {
      /** Repo root holding .factory/factory-status.py, or '' when none. */
      root: string
      /** The last status line, '' when no run is active. */
      line: string
      /** The band is hidden ([–] button); persisted in $.store. */
      hidden: boolean
      board: Shaped<FactoryStatusBoard | null>
    }
  }
}
