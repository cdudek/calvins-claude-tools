import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'wxt';

// The public half of the pinned key pair (ADR 2026-10-28-adr-pinned-extension-id). It fixes the extension id for every checkout:
// pgiiilhkollimekpinhmfjllamhlpkhb. The private half is never committed.
export const EXTENSION_KEY =
  'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAud2hAdx9zdhC/rhld86gGxqw4hGvWCv0fZauow+wGYTfpxwIcUFwGEXZCzagZwMY2q3AXB3457TvZoT6NJKKCjCJvgGBuzeHUwzwG0iGTvY+pVNHfr1G8jWW4SlbWceCRiIXX8IWx8OHIse4pZt9BuQbuZe7Vdwyjv1Xum2f9bVmFCclYira6IQEUo5jeqKZQtW2kJ4uaBlePvOX0AFK5HHM6Lc5dCYmBPiWxnniEiGA2DV27kGAHE6u+pVNlMgGfvilIC74ICru9L1GBhZGaZMxUsKc1IwBN09Weoo8xyyzs65xvo/I+ZNbZNn22y+lsZXvMBKl65DoikT+Jrng8QIDAQAB';

export default defineConfig({
  srcDir: 'src',
  manifestVersion: 3,
  vite: () => ({ plugins: [tailwindcss()] }),
  manifest: {
    name: 'HeyDiff',
    description: 'HeyDiff turns team feedback into agent-ready software changes.',
    key: EXTENSION_KEY,
    // No host permissions yet: milestone 3 adds what the toolbar needs.
    permissions: [],
  },
});
