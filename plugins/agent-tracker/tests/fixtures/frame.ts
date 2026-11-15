// A text frame of a drawn Pane, for the render check (N1). The test kit gives the element tree (`ui.drawn()`), not cells, so this lays
// out the part of Ink's flexbox the pane uses: columns that stack, rows that wrap and grow, Text that word-wraps or truncates, a Button
// that is its label or its lines. It is a model of the layout, not the engine's own render: no terminal screenshot comes out of it.
export type Node = { type?: string; props?: Record<string, unknown>; children?: (Node | string)[] }

const cells = (s: string) => [...s].length
const text = (n: Node | string): string =>
  typeof n === 'string' ? n : (n.type === 'Button' || n.type === 'Link') && (n.children ?? []).length === 0 ? String(n.props?.label ?? '') : (n.children ?? []).map(text).join('')

// Word wrap at `w` cells; a word longer than `w` is split (a button or word cut like that is reported by `clipped`).
const wrap = (s: string, w: number): string[] =>
  s.split('\n').flatMap(para => {
    if (cells(para) <= w) return [para] // fits as it is, spaces and all
    const out: string[] = []
    let line = ''
    for (const word of para.split(/(?<=\s)/)) {
      if (cells(line + word.trimEnd()) <= w) line += word
      else {
        if (line.trim() !== '') out.push(line.trimEnd())
        let rest = word
        while (cells(rest.trimEnd()) > w) {
          out.push([...rest].slice(0, w).join(''))
          rest = [...rest].slice(w).join('')
        }
        line = rest
      }
    }
    out.push(line.trimEnd())
    return out
  })

// The width a child asks for on one line.
const natural = (n: Node | string): number =>
  typeof n !== 'string' && n.type === 'Box' && n.props?.width !== undefined && (n.children ?? []).length === 0 ? Number(n.props.width) : Math.max(0, ...lay(n, 1000).map(cells))

// The lines of one node at width `w`.
export function lay(n: Node | string, w: number): string[] {
  if (typeof n === 'string') return wrap(n, w)
  if (n.type === 'Box') return n.props?.flexDirection === 'column' ? (n.children ?? []).flatMap(c => lay(c, w)) : row(n, w)
  if (n.props?.wrap === 'truncate-end') return text(n).split('\n').map(l => (cells(l) <= w ? l : `${[...l].slice(0, Math.max(0, w - 1)).join('')}…`))
  return wrap(text(n), w)
}

// A row: children side by side with the gap; a child with `flexGrow` takes what is left; with `flexWrap` a child that no longer fits
// starts the next row. A Text that truncates gives way when the row is too wide. Every child of the pane's rows is one line.
function row(n: Node, w: number): string[] {
  const gap = Number(n.props?.gap ?? 0)
  const rows: (Node | string)[][] = [[]]
  let used = 0
  for (const c of n.children ?? []) {
    const here = rows[rows.length - 1]!
    if (n.props?.flexWrap === 'wrap' && here.length > 0 && used + gap + natural(c) > w) {
      rows.push([])
      used = 0
    }
    const placed = rows[rows.length - 1]!
    used += (placed.length > 0 ? gap : 0) + natural(c)
    placed.push(c)
  }
  return rows.map(r => {
    const widths = r.map(natural)
    const free = w - widths.reduce((a, b) => a + b, 0) - gap * Math.max(0, r.length - 1)
    const grow = r.findIndex(c => typeof c !== 'string' && Number(c.props?.flexGrow ?? 0) > 0)
    const give = r.findIndex(c => typeof c !== 'string' && c.props?.wrap === 'truncate-end')
    if (free > 0 && grow >= 0) widths[grow] = widths[grow]! + free
    if (free < 0 && give >= 0) widths[give] = Math.max(1, widths[give]! + free)
    return r.map((c, i) => (lay(c, widths[i]!)[0] ?? '').padEnd(widths[i]!)).join(' '.repeat(gap)).trimEnd()
  })
}

// The whole pane at `columns` cells (its own `paddingLeft` of one cell is inside them).
export const frame = (tree: Node, columns: number): string[] => {
  const pad = Number(tree.props?.paddingLeft ?? 0)
  return lay({ ...tree, props: { ...tree.props, paddingLeft: 0 } }, columns - pad).map(l => `${' '.repeat(pad)}${l}`)
}

// Is every button's label whole on one line, and no line wider than the window?
export const clipped = (lines: string[], labels: string[], columns: number): string[] => [
  ...labels.filter(l => !lines.some(line => line.includes(l))).map(l => `button split or cut: ${l}`),
  ...lines.filter(l => cells(l) > columns).map(l => `line over ${columns} cells: ${l}`),
]
