import fs from "fs";
import path from "path";
import matter from "gray-matter";

const CONTENT_DIR = path.join(process.cwd(), "content", "learn");

export interface ArticleReviewer {
  name: string;
  credentials?: string;
  nmcRegNo?: string;
  specialty?: string;
  doctorSlug?: string;
}

export interface ArticleHeroImage {
  src: string;
  alt: string;
  suggestion?: string;
}

export interface ArticleFaq {
  q: string;
  a: string;
}

export interface ArticleFrontmatter {
  title: string;
  slug: string;
  vertical: string;
  pillar?: string;
  intentLayer?: string;
  canonical?: string;
  metaTitle?: string;
  metaDescription: string;
  primaryKeyword?: string;
  secondaryKeywords?: string[];
  reviewer?: ArticleReviewer;
  lastReviewed: string;
  datePublished?: string;
  heroImage?: ArticleHeroImage;
  schemaTypes?: string[];
  about?: string;
  alternateName?: string[];
  faq?: ArticleFaq[];
  relatedLearn?: string[];
  conversionPage?: string;
  sources?: string[];
  scheduleJReviewed?: boolean;
  complianceNotes?: string;
}

export interface ArticleMeta extends ArticleFrontmatter {
  /** Convenience alias for metaDescription, used as the article deck/summary. */
  deck: string;
  readingTimeMinutes: number;
}

export interface ArticleWithContent extends ArticleMeta {
  content: string;
}

function estimateReadingTime(text: string): number {
  const WORDS_PER_MINUTE = 200;
  const words = text.trim().split(/\s+/).length;
  return Math.max(1, Math.round(words / WORDS_PER_MINUTE));
}

function getVerticalDir(vertical: string): string {
  return path.join(CONTENT_DIR, vertical);
}

/**
 * A directory is a content vertical only if it is not hidden (no leading dot)
 * and contains at least one .mdx file. This guards routing against stray dirs
 * such as an accidental `.claude/` settings folder landing under content/learn.
 */
function isVerticalDir(name: string): boolean {
  if (name.startsWith(".")) return false;
  const dir = path.join(CONTENT_DIR, name);
  if (!fs.statSync(dir).isDirectory()) return false;
  return fs.readdirSync(dir).some((f) => f.endsWith(".mdx"));
}

/**
 * Build an ArticleMeta from parsed frontmatter. The directory name (`vertical`)
 * and filename (`slug`) are the source of truth for routing — they override any
 * value declared in the frontmatter so links always resolve to a real route.
 */
function toMeta(
  data: Record<string, unknown>,
  vertical: string,
  slug: string,
  content: string,
): ArticleMeta {
  const fm = data as unknown as ArticleFrontmatter;
  return {
    ...fm,
    slug,
    vertical,
    deck: fm.metaDescription,
    readingTimeMinutes: estimateReadingTime(content),
  };
}

export function getArticle(vertical: string, slug: string): ArticleWithContent | null {
  const filePath = path.join(getVerticalDir(vertical), `${slug}.mdx`);
  if (!fs.existsSync(filePath)) return null;

  const raw = fs.readFileSync(filePath, "utf-8");
  const { data, content } = matter(raw);

  return { ...toMeta(data, vertical, slug, content), content };
}

export function getArticlesByVertical(vertical: string): ArticleMeta[] {
  const dir = getVerticalDir(vertical);
  if (!fs.existsSync(dir)) return [];

  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".mdx"))
    .map((f) => {
      const slug = f.replace(/\.mdx$/, "");
      const raw = fs.readFileSync(path.join(dir, f), "utf-8");
      const { data, content } = matter(raw);
      return toMeta(data, vertical, slug, content);
    })
    .sort((a, b) =>
      new Date(b.lastReviewed).getTime() - new Date(a.lastReviewed).getTime()
    );
}

export function getAllArticles(): ArticleMeta[] {
  if (!fs.existsSync(CONTENT_DIR)) return [];

  return fs
    .readdirSync(CONTENT_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory() && isVerticalDir(d.name))
    .flatMap((d) => getArticlesByVertical(d.name));
}

export function getAllArticleParams(): Array<{ vertical: string; slug: string }> {
  if (!fs.existsSync(CONTENT_DIR)) return [];

  return fs
    .readdirSync(CONTENT_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory() && isVerticalDir(d.name))
    .flatMap((d) => {
      const dir = path.join(CONTENT_DIR, d.name);
      return fs
        .readdirSync(dir)
        .filter((f) => f.endsWith(".mdx"))
        .map((f) => ({ vertical: d.name, slug: f.replace(/\.mdx$/, "") }));
    });
}

export function getVerticals(): string[] {
  if (!fs.existsSync(CONTENT_DIR)) return [];
  return fs
    .readdirSync(CONTENT_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory() && isVerticalDir(d.name))
    .map((d) => d.name);
}
