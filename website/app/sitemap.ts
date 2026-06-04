import type { MetadataRoute } from 'next';
import { CONDITION_SLUGS } from '../lib/conditions';
import { getAllArticleParams } from '../lib/mdx';

const BASE_URL = 'https://kyrosclinic.com';

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date().toISOString();

  const staticRoutes: MetadataRoute.Sitemap = [
    { url: BASE_URL, lastModified: now, changeFrequency: 'weekly', priority: 1.0 },
    { url: `${BASE_URL}/conditions`, lastModified: now, changeFrequency: 'monthly', priority: 0.9 },
    { url: `${BASE_URL}/learn`, lastModified: now, changeFrequency: 'weekly', priority: 0.9 },
    { url: `${BASE_URL}/how-it-works`, lastModified: now, changeFrequency: 'monthly', priority: 0.8 },
    { url: `${BASE_URL}/pricing`, lastModified: now, changeFrequency: 'monthly', priority: 0.8 },
    { url: `${BASE_URL}/faq`, lastModified: now, changeFrequency: 'monthly', priority: 0.8 },
    { url: `${BASE_URL}/about`, lastModified: now, changeFrequency: 'monthly', priority: 0.7 },
    { url: `${BASE_URL}/our-doctors`, lastModified: now, changeFrequency: 'monthly', priority: 0.7 },
    { url: `${BASE_URL}/for-doctors`, lastModified: now, changeFrequency: 'monthly', priority: 0.6 },
    { url: `${BASE_URL}/contact`, lastModified: now, changeFrequency: 'monthly', priority: 0.6 },
    { url: `${BASE_URL}/advisory-board`, lastModified: now, changeFrequency: 'monthly', priority: 0.5 },
    { url: `${BASE_URL}/legal/privacy`, lastModified: now, changeFrequency: 'yearly', priority: 0.4 },
    { url: `${BASE_URL}/legal/terms`, lastModified: now, changeFrequency: 'yearly', priority: 0.4 },
    { url: `${BASE_URL}/legal/telemedicine-consent`, lastModified: now, changeFrequency: 'yearly', priority: 0.4 },
    { url: `${BASE_URL}/legal/data-deletion`, lastModified: now, changeFrequency: 'yearly', priority: 0.4 },
  ];

  const conditionRoutes: MetadataRoute.Sitemap = CONDITION_SLUGS.map((slug) => ({
    url: `${BASE_URL}/conditions/${slug}`,
    lastModified: now,
    changeFrequency: 'monthly' as const,
    priority: 0.9,
  }));

  const articleParams = getAllArticleParams();

  const learnVerticalRoutes: MetadataRoute.Sitemap = [
    ...new Set(articleParams.map((p) => p.vertical)),
  ].map((vertical) => ({
    url: `${BASE_URL}/learn/${vertical}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: 0.8,
  }));

  const articleRoutes: MetadataRoute.Sitemap = articleParams.map(({ vertical, slug }) => ({
    url: `${BASE_URL}/learn/${vertical}/${slug}`,
    lastModified: now,
    changeFrequency: 'monthly' as const,
    priority: 0.85,
  }));

  return [...staticRoutes, ...conditionRoutes, ...learnVerticalRoutes, ...articleRoutes];
}
