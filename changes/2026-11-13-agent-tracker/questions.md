# Questions: agent-tracker

One entry per open question: the question, the default taken, and where it lands. Written during the build; the owner reads it at the close.

## Feature 1

- **Q1 (F4, step 3): which `waitingFor` value means a permission prompt?** A session was waiting when step 3 ran, with `waitingFor: "input needed"`. Its last transcript entry was an `AskUserQuestion` tool call, so that value is what a question wait reports, not a permission prompt. **Default taken:** no permission value was recorded, so `PERMISSION_WAITING_FOR` is `null`, "asks permission" never shows, and any `waitingFor` gives "waiting" (F4's own fallback). The scrubbed row is the fixture `tests/fixtures/agents.ts`. **To change:** record `waitingFor` from a session that waits on a permission prompt and set the constant in `core/types.ts`.
