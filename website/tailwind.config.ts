import type { Config } from 'tailwindcss';
// eslint-disable-next-line @typescript-eslint/no-require-imports
const kyrosPreset = require('@kyros/design-tokens/tailwind-preset');

export default {
  presets: [kyrosPreset],
  content: ['./app/**/*.{ts,tsx}', './src/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['var(--font-display)', 'Georgia', 'serif'],
        body:    ['var(--font-body)', 'system-ui', 'sans-serif'],
        hindi:   ['Tiro Devanagari Hindi', 'serif'],
      },
      animation: {
        kyros:   'kyros 1.8s ease-in-out infinite',
        shimmer: 'shimmer 1.6s ease-in-out infinite',
        'fade-up': 'fade-up 0.55s ease-out forwards',
      },
    },
  },
  plugins: [],
} satisfies Config;
