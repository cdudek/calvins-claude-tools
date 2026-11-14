// A change folder of an sdlc-run repo as plain data: `milestone.md`, `done.json`, `validation.md`, `questions.md`,
// `findings.md` and `decisions.json`, read as they are (nothing asks an agent). The I/O layer reads the files; this parses them.
import { clean } from './format'

const MAX = 200 // a repo file reaches the screen only through clean()

export type ChangeFeature = { n: number; name: string; state: string; ref: string }
export type ChangeFact = { id: string; feature: number | null; check: string }
export type Verdict = 'met' | 'unmet' | 'open' // met: green, unmet: red, open: not checked yet or not testable (dim)
export type Change = {
  dir: string // the folder name: 2026-11-13-agent-tracker
  root: string // the worktree that holds it
  slug: string
  branch: string
  sentence: string
  status: string // the milestone.md frontmatter status: building, merged, ...
  features: ChangeFeature[]
  project: string | null
  ticket: string | null
  facts: ChangeFact[]
  verdicts: Record<string, Verdict>
  questions: { id: string; title: string; fallback: string }[]
  questionsAt: number // when questions.md last changed (ms), 0 when unknown
  revisions: { at: number; ref: string; text: string }[] // the plan's `## Revisions`, oldest first
  findings: { open: number; fixed: number } | null // null: no findings.md yet
  has: { intent: boolean; ux: boolean; facts: boolean; plan: boolean; locked: boolean }
}

export type ChangeFiles = {
  dir: string
  root: string
  milestone: string
  done: string | null
  validation: string | null
  questions: string | null
  questionsAt: number
  plan: string | null
  findings: string | null
  decisions: string | null
  has: Change['has']
}

const front = (text: string, key: string) => new RegExp(`^${key}:\\s*(.+?)\\s*$`, 'm').exec(/^---\n([\s\S]*?)\n---/.exec(text)?.[1] ?? '')?.[1]

const json = (text: string | null): Record<string, unknown> | null => {
  if (text === null) return null
  try {
    const v = JSON.parse(text)
    return typeof v === 'object' && v !== null ? (v as Record<string, unknown>) : null
  } catch {
    return null
  }
}

// The Features table: # | Change | Feature | PR or commit | State.
const featuresOf = (text: string): ChangeFeature[] => {
  const out: ChangeFeature[] = []
  for (const line of text.split('\n')) {
    const c = line.split('|').map(x => x.trim())
    if (c.length >= 6 && /^\d+$/.test(c[1]!)) out.push({ n: Number(c[1]), name: clean(c[3], MAX), ref: clean(c[4], MAX), state: clean(c[5], MAX) })
  }
  return out
}

// validation.md: one row per fact, `| F12 | expected | observed | evidence | verdict |`.
export const parseVerdicts = (text: string | null): Record<string, Verdict> => {
  const out: Record<string, Verdict> = {}
  for (const line of (text ?? '').split('\n')) {
    const c = line.split('|').map(x => x.trim())
    if (c.length < 4 || !/^F\d+$/.test(c[1] ?? '')) continue
    const verdict = (c[c.length - 2] ?? '').toLowerCase()
    out[c[1]!] = /^met\b/.test(verdict) ? 'met' : /^(unmet|not met|fail)/.test(verdict) ? 'unmet' : 'open'
  }
  return out
}

// questions.md: `- **Q7 (build): the question?** ... **Default taken:** what the build did. ...`
export const parseQuestions = (text: string | null): Change['questions'] =>
  (text ?? '')
    .split('\n')
    .flatMap(line => {
      const m = /^- \*\*(Q\d+)\s*(?:\([^)]*\))?:?\s*([^*]+?)\*\*/.exec(line)
      if (!m) return []
      return [{ id: m[1]!, title: clean(m[2], MAX), fallback: clean(/\*\*Default taken:\*\*\s*([^*]*?)(?:\s*\*\*|$)/.exec(line)?.[1] ?? '', MAX) }]
    })

// `- **2026-11-14, F92:** what changed, and why`: the line's date at 12:00 UTC (no clock or zone is read here), and its text without the label.
export const parseRevisions = (plan: string | null): { at: number; ref: string; text: string }[] => {
  if (plan === null) return []
  const at = plan.search(/^##\s+Revisions\s*$/m)
  if (at < 0) return []
  const body = plan.slice(at).split('\n').slice(1)
  const end = body.findIndex(l => /^##\s/.test(l))
  const out: { at: number; ref: string; text: string }[] = []
  for (const line of end < 0 ? body : body.slice(0, end)) {
    const m = /^- \*\*(\d{4})-(\d{2})-(\d{2})\s*(?:[,—-]\s*)?([^*]*?):?\*\*:?\s*(.+)$/.exec(line)
    if (m) out.push({ at: Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]), 12), ref: clean(m[4], 40).trim(), text: clean(m[5], 400).replace(/\s+/g, ' ').trim() })
  }
  return out
}

// findings.md: the checkboxes outside "## Advisory": unchecked are open, checked are fixed.
export const parseFindings = (text: string | null): Change['findings'] => {
  if (text === null) return null
  let open = 0
  let fixed = 0
  let skip = false
  for (const line of text.split('\n')) {
    if (/^##\s/.test(line)) skip = /^##\s+Advisory\b/i.test(line)
    if (skip) continue
    if (/^- \[ \]/.test(line)) open += 1
    else if (/^- \[x\]/i.test(line)) fixed += 1
  }
  return { open, fixed }
}

export const parseChange = (f: ChangeFiles): Change | null => {
  const slug = clean(front(f.milestone, 'milestone'), MAX)
  const branch = clean(front(f.milestone, 'branch'), MAX)
  if (!slug || !branch) return null
  const done = json(f.done)
  const decisions = json(f.decisions)
  const project = (decisions?.project as { slug?: unknown } | undefined)?.slug
  const ticket = decisions?.ticket
  const facts = (Array.isArray(done?.facts) ? (done!.facts as Record<string, unknown>[]) : [])
    .filter(x => typeof x?.id === 'string' && /^F\d+$/.test(x.id as string))
    .map(x => ({ id: x.id as string, feature: typeof x.feature === 'number' ? x.feature : null, check: clean(x.check, 400) }))
  return {
    dir: f.dir,
    root: f.root,
    slug,
    branch,
    sentence: clean(/^>\s*(.+)$/m.exec(f.milestone)?.[1], MAX),
    status: clean(front(f.milestone, 'status') ?? '', 40),
    features: featuresOf(f.milestone),
    project: typeof project === 'string' ? clean(project, MAX) : null,
    ticket: typeof ticket === 'string' && ticket !== '' ? clean(ticket, MAX) : null,
    facts,
    verdicts: parseVerdicts(f.validation),
    questions: parseQuestions(f.questions),
    questionsAt: f.questionsAt,
    revisions: parseRevisions(f.plan),
    findings: parseFindings(f.findings),
    has: f.has,
  }
}

// ---- reading a feature's state ----

export type FeatureKind = 'done' | 'merged' | 'building' | 'blocked' | 'todo'
export const featureKind = (state: string): FeatureKind => (/^done\b/.test(state) ? 'done' : /^merged\b/.test(state) ? 'merged' : /^building\b/.test(state) ? 'building' : /^blocked\b/.test(state) ? 'blocked' : 'todo')
export const isFeatureComplete = (f: ChangeFeature) => featureKind(f.state) === 'done' || featureKind(f.state) === 'merged'

// The commit of a done feature: `done <sha>` in the state, else the first word of the PR or commit column when it is a sha.
export const featureSha = (f: ChangeFeature): string | null => /^done\s+([0-9a-f]{7,40})\b/.exec(f.state)?.[1]?.slice(0, 7) ?? (/^([0-9a-f]{7,40})\b/.exec(f.ref)?.[1]?.slice(0, 7) ?? null)
export const blockedReason = (f: ChangeFeature) => f.state.replace(/^blocked:?\s*/, '')

export const factVerdict = (c: Change, id: string): Verdict => c.verdicts[id] ?? 'open'
export const factsMet = (c: Change) => c.facts.filter(f => factVerdict(c, f.id) === 'met').length

// How far the change is: the facts the last gate report passes when there are facts, else the features done.
export const progressOf = (c: Change): { done: number; total: number; unit: 'facts' | 'features' } =>
  c.facts.length > 0 && Object.keys(c.verdicts).length > 0
    ? { done: factsMet(c), total: c.facts.length, unit: 'facts' }
    : { done: c.features.filter(isFeatureComplete).length, total: c.features.length, unit: 'features' }

export const isMerged = (c: Change) => /^(merged|released|shipped)\b/i.test(c.status)

// Stage 1 to 6 from which files exist: 1 intent, 2 UX plan, 3 facts, 4 tech plan (locked), 5 build, 6 close.
export type StageState = 'done' | 'active' | 'todo'
export const stages = (c: Change): { n: number; name: string | null; state: StageState }[] => {
  const complete = c.features.length > 0 && c.features.every(isFeatureComplete)
  const build: StageState = isMerged(c) || complete ? 'done' : c.features.some(f => featureKind(f.state) !== 'todo') || /^building\b/i.test(c.status) ? 'active' : 'todo'
  const close: StageState = isMerged(c) ? 'done' : complete ? 'active' : 'todo'
  const yes = (b: boolean): StageState => (b ? 'done' : 'todo')
  return [
    { n: 1, name: null, state: yes(c.has.intent) },
    { n: 2, name: null, state: yes(c.has.ux) },
    { n: 3, name: null, state: yes(c.has.facts) },
    { n: 4, name: null, state: c.has.plan ? (c.has.locked ? 'done' : 'active') : 'todo' },
    { n: 5, name: 'build', state: build },
    { n: 6, name: 'close', state: close },
  ]
}

// The test files a feature's facts name: "`collector.test.ts` › ..." in each fact's check, with how many facts rest on each.
export const testsOf = (c: Change, feature: number): { file: string; met: number; total: number }[] => {
  const by = new Map<string, { met: number; total: number }>()
  for (const f of c.facts.filter(x => x.feature === feature)) {
    for (const file of new Set([...f.check.matchAll(/`([\w./-]+\.test\.\w+)`/g)].map(m => m[1]!))) {
      const e = by.get(file) ?? { met: 0, total: 0 }
      by.set(file, { met: e.met + Number(factVerdict(c, f.id) === 'met'), total: e.total + 1 })
    }
  }
  return [...by.entries()].map(([file, v]) => ({ file, ...v }))
}
