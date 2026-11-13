import { expect, mock, test } from 'claude-code/testing'

test('the mod loads', async ($, on) => {
  const clock = mock.clock(on)
  expect(clock.now()).toBe(0)
})
