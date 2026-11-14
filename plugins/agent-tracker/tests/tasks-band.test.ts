import { describe, expect, test } from 'claude-code/testing'

import { bandData, compactLayout, detailsLayout, plain, taskItems } from '../hooks/tracker/core'
import { NOON, SELF, paneTown, snapAt } from './fixtures/pane'
import { taskTown } from './fixtures/tasks'

const TAG = '@2026-11-13-agent-tracker'

describe('the band count', () => {
  test(`${TAG} "N not done" in the compact row, red with a forgotten or waiting task; no sixth column`, () => {
    const tasks = taskItems(snapAt(taskTown()), NOON)
    const data = bandData(snapAt(paneTown()), SELF, NOON, [], tasks)
    expect(data.tasks).toEqual({ notDone: 7, needsYou: 1, alarm: true })
    const seg = compactLayout(data, 120).segments.find(s => s.id === 'tasks')!
    expect(plain(seg.chunks).trim()).toBe('7 not done')
    expect(seg.chunks.at(-1)).toMatchObject({ tone: 'red' })
    const calm = bandData(snapAt(paneTown()), SELF, NOON, [], tasks.filter(t => t.status === 'in-progress'))
    expect(compactLayout(calm, 120).segments.find(s => s.id === 'tasks')!.chunks.at(-1)).toMatchObject({ text: '3 not done', tone: 'yellow' })
    expect(compactLayout(bandData(snapAt(paneTown()), SELF, NOON), 120).segments.some(s => s.id === 'tasks')).toBe(false) // none: no segment
    // The details view carries the count on its header line, and still has five columns.
    const d = detailsLayout(data, 120)
    expect(plain(d.header[1]!)).toContain('7 not done')
    expect(d.rows.flat().map(c => c.key)).toEqual(['needs', 'running', 'know', 'decided', 'prs'])
    // The count outlives the work and the counts that drop first; the need-you count and the buttons never drop.
    const narrow = compactLayout(data, 60).segments.map(s => s.id)
    expect(narrow).toContain('needs')
    expect(narrow).toContain('tasks')
    expect(compactLayout(data, 30).segments.map(s => s.id)).not.toContain('label') // below 40 columns only the need-you count is left
  })
})
