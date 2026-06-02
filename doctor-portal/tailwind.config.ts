import type { Config } from 'tailwindcss';
import kyrosPreset from '@kyros/design-tokens/tailwind-preset';

export default {
  presets: [kyrosPreset],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {},
  },
  plugins: [],
} satisfies Config;
