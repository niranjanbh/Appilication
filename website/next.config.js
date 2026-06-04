/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['@kyros/design-tokens'],
  output: 'export',
  images: {
    // next/image optimisation requires a server; use unoptimized for static export.
    // Switch back to a loader (e.g. Cloudflare Images) once the backend is deployed.
    unoptimized: true,
  },
};

module.exports = nextConfig;
