import type { MetadataRoute } from 'next';
import { CONDITION_SLUGS } from '../lib/conditions';
import { getAllArticles } from '../lib/mdx';

const BASE_URL = 'https://kyrosclinic.com';

// Static pages have real dates; article routes use doctor_reviewed_at from frontmatter.
const SITE_BUILT = '2026-06-01';

export default function sitemap(): MetadataRoute.Sitemap {
  const staticRoutes: MetadataRoute.Sitemap = [
    { url: BASE_URL, lastModified: SITE_BUILT, changeFrequency: 'weekly', priority: 1.0 },
    { url: `${BASE_URL}/conditions`, lastModified: SITE_BUILT, changeFrequency: 'monthly', priority: 0.9 },
    { url: `${BASE_URL}/learn`, lastModified: SITE_BUILT, changeFrequency: 'weekly', priority: 0.9 },
    { url: `${BASE_URL}/how-it-works`, lastModified: SITE_BUILT, changeFrequency: 'monthly', priority: 0.8 },
    { url: `${BASE_URL}/pricing`, lastModified: SITE_BUILT, changeFrequency: 'monthly', priority: 0.8 },
    { url: `${BASE_URL}/faq`, lastModified: SITE_BUILT, changeFrequency: 'monthly', priority: 0.8 },
    { url: `${BASE_URL}/about`, lastModified: SITE_BUILT, changeFrequency: 'monthly', priority: 0.7 },
    { url: `${BASE_URL}/our-doctors`, lastModified: SITE_BUILT, changeFrequency: 'monthly', priority: 0.7 },
    { url: `${BASE_URL}/for-doctors`, lastModified: SITE_BUILT, changeFrequency: 'monthly', priority: 0.6 },
    { url: `${BASE_URL}/contact`, lastModified: SITE_BUILT, changeFrequency: 'monthly', priority: 0.6 },
    { url: `${BASE_URL}/advisory-board`, lastModified: SITE_BUILT, changeFrequency: 'monthly', priority: 0.5 },
    { url: `${BASE_URL}/legal/privacy`, lastModified: SITE_BUILT, changeFrequency: 'yearly', priority: 0.4 },
    { url: `${BASE_URL}/legal/terms`, lastModified: SITE_BUILT, changeFrequency: 'yearly', priority: 0.4 },
    { url: `${BASE_URL}/legal/telemedicine-consent`, lastModified: SITE_BUILT, changeFrequency: 'yearly', priority: 0.4 },
    { url: `${BASE_URL}/legal/data-deletion`, lastModified: SITE_BUILT, changeFrequency: 'yearly', priority: 0.4 },
  ];

  const conditionRoutes: MetadataRoute.Sitemap = CONDITION_SLUGS.map((slug) => ({
    url: `${BASE_URL}/conditions/${slug}`,
    lastModified: SITE_BUILT,
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
        lastModified: new Date(a.doctor_reviewed_at).toISOString(),
        changeFrequency: 'weekly' as const,
        priority: 0.8,
      });
    }
  }

  const articleRoutes: MetadataRoute.Sitemap = articles.map((a) => ({
    url: `${BASE_URL}/learn/${a.vertical}/${a.slug}`,
    lastModified: new Date(a.doctor_reviewed_at).toISOString(),
    changeFrequency: 'monthly' as const,
    priority: 0.85,
  }));

  return [...staticRoutes, ...conditionRoutes, ...learnVerticalRoutes, ...articleRoutes];
}
