# Controlled e2e diagnosis

Read this before reproducing an e2e failure in a fresh worktree, on new fixture data or on
a shared machine. The shared rules live in
`../../test-e2e-policy/references/suite-speed-and-reliability.md`: establish a clean base-branch
control and environment parity (C), and control machine load and suite concurrency (F).
Record those inputs before attributing a failure to a code change.

## E. Classify every synthetic-fixture failure

Run the failing specs on both the synthetic fixture and the opt-in real-data fixture,
with the same build and controlled environment. Use this comparison to narrow the cause:

| Result | Classification |
|---|---|
| Fails on both | Existing defect; investigate the failing mechanism. |
| Fails only on synthetic | Fixture gap or newly exposed product bug; check data validity. |

If the synthetic data could not exist in a real dataset, fix the fixture. Impossible field
combinations and missing fields that the importer always writes are fixture gaps. If valid
data exposes a product bug, file and fix the product bug in the authorized workflow. Never
shape valid fixture data to hide it. “Synthetic only” does not mean “test problem”.

A different valid dataset can reveal ordinary values clipped in cells, stale disabled
menu state, a hover timer surviving Escape, a reflow race, a stale read-back or a navigation
race. Each is a product defect even if a familiar dataset never exposes it.

## H. Prove the mechanism with a temporary probe

When the error does not explain the cause, write a short-lived probe spec. Record the
mechanism directly: element geometry and running animations, native input events versus
renderer key events, or which dialogs are open when a request arrives. Compare the probe
under the failing and control conditions. Use the observation to choose the minimal fix.

Delete the probe before the fix lands. Keep the finding and evidence in the report, and
retain the regression test that proves intended behaviour. Instrumentation that only
records today's mechanism is not a new permanent journey test. Follow the shared reference's
section J when choosing a repair; report whether code, harness or fixture was responsible.
