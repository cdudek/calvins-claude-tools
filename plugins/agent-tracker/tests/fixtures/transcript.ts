// A session transcript in the shape Claude Code 2.1.323 writes (one JSON object per line), written by hand: every
// id, folder, title and prompt is made up. Kept shapes: typed prompts, an image prompt, tool results (one an
// error), slash-command and shell expansions, a system note, an interrupt note, a meta line, a subagent line,
// one message written as two lines with one usage, and the title line.
export const TRANSCRIPT_ID = '00000000-0000-4000-8000-0000000000a1'
export const PROJECT_DIR = '-work-repo-7' // the folder name Claude Code derives from a session's folder
export const TRANSCRIPT_CWD = '/work/repo-7'
export const T_FIRST = '2026-11-10T09:00:00.000Z'
export const T_LAST = '2026-11-10T09:30:00.000Z'

let n = 0
const line = (o: Record<string, unknown>) => JSON.stringify(o)
const at = (minute: number) => `2026-11-10T09:${String(minute).padStart(2, '0')}:00.000Z`
const base = (minute: number, branch = 'feat/login') => ({ uuid: `u-${n++}`, timestamp: at(minute), cwd: TRANSCRIPT_CWD, gitBranch: branch })

const user = (content: unknown, minute: number, extra: Record<string, unknown> = {}, sidechain = false) =>
  line({ parentUuid: null, isSidechain: sidechain, type: 'user', message: { role: 'user', content }, ...base(minute), ...extra })

const usage = (input: number, created: number, read: number, output: number) => ({
  input_tokens: input,
  cache_creation_input_tokens: created,
  cache_read_input_tokens: read,
  output_tokens: output,
})

// An assistant message: one line per content block, all with the same message id and usage.
const assistant = (id: string, blocks: unknown[], u: ReturnType<typeof usage>, minute: number, sidechain = false) =>
  blocks.map(block =>
    line({
      parentUuid: null,
      isSidechain: sidechain,
      type: 'assistant',
      message: { model: 'model-x', id, type: 'message', role: 'assistant', content: [block], stop_reason: 'end_turn', usage: u },
      ...base(minute),
    }),
  )

const toolResult = (isError: boolean, minute: number) =>
  user([{ type: 'tool_result', tool_use_id: 't1', is_error: isError, content: 'output' }], minute)

// The prompts the owner typed, in order, as an ask must hold them.
export const ASK_TEXTS = ['fix the login bug', 'now add a test, with "quotes"\nand a second line', 'ship it']

export const TRANSCRIPT_LINES: string[] = [
  line({ type: 'queue-operation', operation: 'enqueue', timestamp: T_FIRST, sessionId: TRANSCRIPT_ID }),
  user(ASK_TEXTS[0], 0, { promptSource: 'typed', turnOrigin: 'human' }),
  line({ parentUuid: null, isSidechain: false, attachment: { type: 'environment' }, type: 'attachment', ...base(1) }),
  ...assistant('msg_a1', [{ type: 'thinking', thinking: 'hm' }, { type: 'text', text: 'On it.' }], usage(2, 1000, 500, 100), 2),
  ...assistant('msg_a2', [{ type: 'tool_use', id: 't1', name: 'Bash', input: { command: 'make' } }], usage(3, 0, 1500, 50), 3),
  toolResult(false, 4),
  ...assistant('msg_a3', [{ type: 'tool_use', id: 't2', name: 'Bash', input: { command: 'make' } }], usage(1, 10, 1990, 25), 5),
  toolResult(true, 6),
  // Not asks: a slash command and its expansion, shell input and output, an interrupt note, a meta line.
  user('<command-name>/clear</command-name>\n<command-message>clear</command-message>', 7, { turnOrigin: 'system' }),
  user('<bash-input>ls</bash-input>', 8),
  user('<bash-stdout>a.txt</bash-stdout><bash-stderr></bash-stderr>', 8, { turnOrigin: 'human' }),
  user([{ type: 'text', text: '[Request interrupted by user]' }], 9),
  user('Another session sent a note', 10, { promptSource: 'system', turnOrigin: 'peer' }),
  user([{ type: 'text', text: 'Caveat: generated while running local commands' }], 10, { isMeta: true }),
  user('<task-notification>a background task ended</task-notification>', 11, { promptSource: 'system' }),
  // An image first, then the text: still one ask, from the text part.
  user(
    [
      { type: 'image', source: { type: 'base64', media_type: 'image/png', data: 'AAAA' } },
      { type: 'text', text: ASK_TEXTS[1] },
    ],
    12,
    { promptSource: 'typed' },
  ),
  // A subagent's prompt and its answer: its tokens count, it is not an ask.
  user('subagent task text', 13, {}, true),
  ...assistant('msg_s1', [{ type: 'text', text: 'sub done' }], usage(5, 0, 100, 40), 14, true),
  user(ASK_TEXTS[2], 15, { promptSource: 'queued' }),
  ...assistant('msg_a4', [{ type: 'text', text: 'Shipped.' }], usage(1, 0, 2000, 10), 30),
  line({ type: 'ai-title', aiTitle: 'Fix the login bug', sessionId: TRANSCRIPT_ID }),
]

export const TRANSCRIPT_TEXT = TRANSCRIPT_LINES.join('\n') + '\n'

// What the fields of F12 read from it. In: input plus cache reads and writes of each message, once (questions.md Q3).
export const EXPECTED = {
  cwd: TRANSCRIPT_CWD,
  branch: 'feat/login',
  title: 'Fix the login bug',
  tokensIn: 2 + 1000 + 500 + (3 + 0 + 1500) + (1 + 10 + 1990) + (5 + 0 + 100) + (1 + 0 + 2000),
  tokensOut: 100 + 50 + 25 + 40 + 10,
  toolErrors: 1,
  startedAt: Date.parse(T_FIRST),
  lastActivityAt: Date.parse(T_LAST),
}
