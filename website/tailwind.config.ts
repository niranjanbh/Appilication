import type { Config } from 'tailwindcss';
// eslint-disable-next-line @typescript-eslint/no-require-imports
const kyrosPreset = require('@kyros/design-tokens/tailwind-preset');

export default {
  presets: [kyrosPreset],
  content: ['./app/**/*.{ts,tsx}', './src/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      // Override preset fontFamily to use CSS variables set by next/font/google
      // in layout.tsx (--font-display, --font-body).  Tiro Devanagari Hindi is
      // loaded via a Google Fonts <link> so we keep its name directly.
      fontFamily: {
        display: ['var(--font-display)', 'Georgia', 'serif'],
        body:    ['var(--font-body)', 'system-ui', 'sans-serif'],
        hindi:   ['Tiro Devanagari Hindi', 'serif'],
      },
    },
  },
  plugins: [],
} satisfies Config;
