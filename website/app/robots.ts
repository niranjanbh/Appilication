import type { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: ['/api/', '/design', '/book'],
    },
    sitemap: 'https://kyrosclinic.com/sitemap.xml',
  };
}
