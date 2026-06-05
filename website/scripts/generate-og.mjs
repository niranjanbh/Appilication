/**
 * Generates website/public/og-default.png (1200x630) from an inline SVG.
 * Run once: node scripts/generate-og.mjs
 * Re-run any time the brand identity changes.
 */
import sharp from 'sharp';
import { fileURLToPath } from 'url';
import { join, dirname } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, '..', 'public', 'og-default.png');

// Design tokens
const FOREST      = '#0F3D2E';
const JADE        = '#2D7A5F';
const SAGE        = '#8FA88E';
const SAFFRON     = '#E08E3C';
const IVORY       = '#FAF1E4';
const PEACH_MIST  = '#FCE4CC';
const STONE       = '#6B6B68';

const svg = `
<svg width="1200" height="630" viewBox="0 0 1200 630" xmlns="http://www.w3.org/2000/svg">
  <!-- Forest background -->
  <rect width="1200" height="630" fill="${FOREST}"/>

  <!-- Warm right-panel tint -->
  <rect x="820" y="0" width="380" height="630" fill="${JADE}" opacity="0.18"/>

  <!-- Peach-mist warm glow bottom-right -->
  <ellipse cx="1050" cy="540" rx="260" ry="180" fill="${PEACH_MIST}" opacity="0.07"/>

  <!-- Saffron vertical accent bar -->
  <rect x="80" y="110" width="3" height="300" fill="${SAFFRON}" opacity="0.9"/>

  <!-- Brand name: Kyros -->
  <text
    x="108" y="230"
    font-family="Georgia, 'Times New Roman', serif"
    font-size="108"
    font-weight="500"
    letter-spacing="-2"
    fill="${IVORY}">Kyros</text>

  <!-- Brand name: Clinic (smaller, sage) -->
  <text
    x="113" y="288"
    font-family="Georgia, 'Times New Roman', serif"
    font-size="44"
    font-weight="400"
    letter-spacing="8"
    fill="${SAGE}">CLINIC</text>

  <!-- Saffron divider line -->
  <rect x="108" y="310" width="120" height="2" fill="${SAFFRON}" opacity="0.8"/>

  <!-- Tagline -->
  <text
    x="108" y="356"
    font-family="Arial, Helvetica, sans-serif"
    font-size="22"
    font-weight="400"
    letter-spacing="0.5"
    fill="${IVORY}" opacity="0.85">Doctor-first hormonal health</text>

  <!-- Verticals row -->
  <text
    x="108" y="398"
    font-family="Arial, Helvetica, sans-serif"
    font-size="16"
    fill="${STONE}"
    letter-spacing="0.3">PCOS · Thyroid · Weight · Skin &amp; Hair · Men's Health · Longevity</text>

  <!-- India badge -->
  <rect x="108" y="430" width="210" height="32" rx="4" fill="${SAFFRON}" opacity="0.12"/>
  <text
    x="122" y="451"
    font-family="Arial, Helvetica, sans-serif"
    font-size="15"
    fill="${SAFFRON}"
    letter-spacing="1">India-first telemedicine clinic</text>

  <!-- Domain -->
  <text
    x="108" y="530"
    font-family="Arial, Helvetica, sans-serif"
    font-size="18"
    fill="${SAGE}" opacity="0.7"
    letter-spacing="0.5">kyrosclinic.com</text>

  <!-- Right-side decorative cross mark -->
  <g transform="translate(980, 200)" opacity="0.15">
    <rect x="-1" y="-40" width="2" height="80" fill="${IVORY}"/>
    <rect x="-40" y="-1" width="80" height="2" fill="${IVORY}"/>
  </g>

  <!-- Bottom saffron accent line -->
  <rect x="0" y="624" width="1200" height="6" fill="${SAFFRON}" opacity="0.6"/>
</svg>
`.trim();

const png = await sharp(Buffer.from(svg))
  .png({ compressionLevel: 9 })
  .toFile(OUT);

console.log(`✓ og-default.png — ${png.width}×${png.height}px → ${OUT}`);
