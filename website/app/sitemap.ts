import type { MetadataRoute } from 'next';
import { CONDITION_SLUGS } from '../lib/conditions';
import { getAllArticles } from '../lib/mdx';

const BASE_URL = 'https://kyrosclinic.com';

const BUILD_TIME = new Date().toISOString();

function safeIso(value: string | undefined): string {
  if (!value) return BUILD_TIME;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? BUILD_TIME : d.toISOString();
}

export default function sitemap(): MetadataRoute.Sitemap {
  const staticRoutes: MetadataRoute.Sitemap = [
    { url: BASE_URL, lastModified: BUILD_TIME, changeFrequency: 'weekly', priority: 1.0 },
    { url: `${BASE_URL}/conditions`, lastModified: BUILD_TIME, changeFrequency: 'weekly', priority: 0.9 },
    { url: `${BASE_URL}/learn`, lastModified: BUILD_TIME, changeFrequency: 'weekly', priority: 0.9 },
    { url: `${BASE_URL}/how-it-works`, lastModified: BUILD_TIME, changeFrequency: 'monthly', priority: 0.8 },
    { url: `${BASE_URL}/pricing`, lastModified: BUILD_TIME, changeFrequency: 'monthly', priority: 0.8 },
    { url: `${BASE_URL}/faq`, lastModified: BUILD_TIME, changeFrequency: 'monthly', priority: 0.8 },
    { url: `${BASE_URL}/about`, lastModified: BUILD_TIME, changeFrequency: 'monthly', priority: 0.7 },
    { url: `${BASE_URL}/our-doctors`, lastModified: BUILD_TIME, changeFrequency: 'monthly', priority: 0.7 },
    { url: `${BASE_URL}/for-doctors`, lastModified: BUILD_TIME, changeFrequency: 'monthly', priority: 0.6 },
    { url: `${BASE_URL}/contact`, lastModified: BUILD_TIME, changeFrequency: 'monthly', priority: 0.6 },
    { url: `${BASE_URL}/advisory-board`, lastModified: BUILD_TIME, changeFrequency: 'monthly', priority: 0.5 },
    { url: `${BASE_URL}/legal/privacy`, lastModified: BUILD_TIME, changeFrequency: 'yearly', priority: 0.4 },
    { url: `${BASE_URL}/legal/terms`, lastModified: BUILD_TIME, changeFrequency: 'yearly', priority: 0.4 },
    { url: `${BASE_URL}/legal/telemedicine-consent`, lastModified: BUILD_TIME, changeFrequency: 'yearly', priority: 0.4 },
    { url: `${BASE_URL}/legal/data-deletion`, lastModified: BUILD_TIME, changeFrequency: 'yearly', priority: 0.4 },
  ];

  const conditionRoutes: MetadataRoute.Sitemap = CONDITION_SLUGS.map((slug) => ({
    url: `${BASE_URL}/conditions/${slug}`,
    lastModified: BUILD_TIME,
    changeFrequency: 'monthly' as const,
    priority: 0.9,
  }));

  const articles = getAllArticles();

  const seenVerticals = new Set<string>();
  const learnVerticalRoutes: MetadataRoute.Sitemap = [];
  for (const a of articles) {
    if (!seenVerticals.has(a.vertical)) {
      seenVerticals.add(a.vertical);
      learnVerticalRoutes.push({
        url: `${BASE_URL}/learn/${a.vertical}`,
        lastModified: safeIso(a.lastReviewed),
        changeFrequency: 'weekly' as const,
        priority: 0.8,
      });
    }
  }

  const articleRoutes: MetadataRoute.Sitemap = articles.map((a) => ({
    url: `${BASE_URL}/learn/${a.vertical}/${a.slug}`,
    lastModified: safeIso(a.lastReviewed),
    changeFrequency: 'monthly' as const,
    priority: 0.85,
  }));

  return [...staticRoutes, ...conditionRoutes, ...learnVerticalRoutes, ...articleRoutes];
}
