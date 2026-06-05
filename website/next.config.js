/** @type {import('next').NextConfig} */
const nextConfig = {
  // Three.js WebGL contexts accumulate and crash with strict mode's double-mount in dev.
  reactStrictMode: false,
  transpilePackages: ['@kyros/design-tokens'],
  // Remove X-Powered-By header — no information leakage.
  poweredByHeader: false,
  // Gzip/Brotli for any non-Cloudflare responses (dev server, preview builds).
  compress: true,
  output: 'export',
  images: {
    // next/image optimisation requires a server; switch to Cloudflare Images loader once backend deploys.
    unoptimized: true,
  },
  experimental: {
    // Tree-shake R3F + three.js — only import the pieces actually used.
    // Prevents the full 600 kB three.js bundle from landing in the main chunk.
    optimizePackageImports: ['@react-three/fiber', '@react-three/drei', 'three'],
  },
};

module.exports = nextConfig;
