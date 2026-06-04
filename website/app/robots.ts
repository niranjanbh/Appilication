import type { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: ['/api/', '/book'],
    },
    sitemap: 'https://kyros.clinic/sitemap.xml',
  };
}
