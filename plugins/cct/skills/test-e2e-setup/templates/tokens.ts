// e2e/tokens.ts — resolve a design token to the value the browser computes for it.
// Assert paint against the token, never a hex literal or a class name:
//   const selected = await resolveToken(page, '--background-color-selected', 'background-color')
//   await expect(row).toHaveCSS('background-color', selected)
// A renamed token fails here; a changed token value passes, because the claim still holds.
// See cct:test-e2e-policy, references/strategy.md section 5.
import type { Page } from '@playwright/test'

export async function resolveToken(page: Page, token: string, prop = 'color'): Promise<string> {
  const value = await page.evaluate(
    ([t, p]) => {
      const probe = document.createElement('div')
      probe.style.setProperty(p, `var(${t})`)
      document.body.append(probe)
      const resolved = getComputedStyle(probe).getPropertyValue(p)
      const declared = getComputedStyle(document.documentElement).getPropertyValue(t)
      probe.remove()
      return declared.trim() === '' ? '' : resolved
    },
    [token, prop] as const,
  )
  if (!value) throw new Error(`design token ${token} is not defined on this page`)
  return value
}
