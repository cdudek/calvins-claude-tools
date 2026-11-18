# Questions

Asked during the build; the build never stops on them. Each has the default taken.

- **Q1 (2026-11-18) When to lock the tests?** The plan says lock after feature 1's failing tests, but features 2-4 also add tests, and the lock refuses every test file edit on the milestone branch. **Default taken:** one test-first commit with the failing tests for all facts (F1-F15, N1) and the fixture updates, then `testLocked: true`, then features 1-4 build code only. If a locked test proves wrong, the build records it here and asks for `testEdit`.
