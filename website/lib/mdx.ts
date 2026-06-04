import fs from "fs";
import path from "path";
import matter from "gray-matter";

const CONTENT_DIR = path.join(process.cwd(), "content", "learn");

export interface ArticleFrontmatter {
  title: string;
  slug: string;
  vertical: string;
  deck: string;
  doctor_author_id: string;
  doctor_reviewed_at: string;
  references: Array<{ citation: string; url?: string }>;
}

export interface ArticleMeta extends ArticleFrontmatter {
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

export function getArticle(vertical: string, slug: string): ArticleWithContent | null {
  const filePath = path.join(getVerticalDir(vertical), `${slug}.mdx`);
  if (!fs.existsSync(filePath)) return null;

  const raw = fs.readFileSync(filePath, "utf-8");
  const { data, content } = matter(raw);
  const fm = data as ArticleFrontmatter;

  return {
    ...fm,
    slug,
    vertical,
    readingTimeMinutes: estimateReadingTime(content),
    content,
  };
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
      const fm = data as ArticleFrontmatter;
      return { ...fm, slug, vertical, readingTimeMinutes: estimateReadingTime(content) };
    })
    .sort((a, b) =>
      new Date(b.doctor_reviewed_at).getTime() - new Date(a.doctor_reviewed_at).getTime()
    );
}

export function getAllArticles(): ArticleMeta[] {
  if (!fs.existsSync(CONTENT_DIR)) return [];

  return fs
    .readdirSync(CONTENT_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .flatMap((d) => getArticlesByVertical(d.name));
}

export function getAllArticleParams(): Array<{ vertical: string; slug: string }> {
  if (!fs.existsSync(CONTENT_DIR)) return [];

  return fs
    .readdirSync(CONTENT_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory())
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
    .filter((d) => d.isDirectory())
    .map((d) => d.name);
}
