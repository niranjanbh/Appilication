import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { compileMDX } from "next-mdx-remote/rsc";
import { getAllArticleParams, getArticle } from "../../../../lib/mdx";
import { getCondition } from "../../../../lib/conditions";
import { CONDITION_DISPLAY_NAMES } from "../../../../lib/conditionDisplay";
import { JsonLD } from "../../../../components/schema/JsonLD";
import { ArticleHeader } from "../../../../components/article/ArticleHeader";
import { DoctorByline } from "../../../../components/article/DoctorByline";
import { ArticleFaqSection } from "../../../../components/article/ArticleFaq";
import { References } from "../../../../components/article/References";
import { mdxComponents } from "../../../../components/article/MdxComponents";
import { CTASection } from "../../../../components/marketing/CTASection";

// ISR: revalidate once per hour so content updates without a full rebuild
export const revalidate = 3600;

interface Params {
  params: { vertical: string; slug: string };
}

const PLACEHOLDER_NAME = "TO BE ADDED AT PUBLISH";

function safeIso(value: string | undefined): string | undefined {
  if (!value) return undefined;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? undefined : d.toISOString();
}

export function generateStaticParams() {
  return getAllArticleParams();
}

export function generateMetadata({ params }: Params): Metadata {
  const article = getArticle(params.vertical, params.slug);
  if (!article) return {};
  const verticalLabel = CONDITION_DISPLAY_NAMES[params.vertical] ?? params.vertical;
  const reviewedAt = safeIso(article.lastReviewed);
  const ogImage = getCondition(params.vertical)?.ogImage ?? "/treatments/HeroDashboard.png";
  const url = `https://kyrosclinic.com/learn/${params.vertical}/${params.slug}`;
  const reviewerName =
    article.reviewer?.name && article.reviewer.name !== PLACEHOLDER_NAME
      ? article.reviewer.name
      : undefined;

  return {
    title: article.metaTitle ?? article.title,
    description: article.metaDescription,
    keywords: article.secondaryKeywords,
    alternates: { canonical: url },
    openGraph: {
      title: `${article.title} — Kyros Clinic`,
      description: article.metaDescription,
      url,
      type: "article",
      ...(reviewedAt ? { publishedTime: reviewedAt, modifiedTime: reviewedAt } : {}),
      images: [{ url: ogImage, width: 1200, height: 630, alt: article.title }],
      ...(reviewerName ? { authors: [reviewerName] } : {}),
    },
    twitter: {
      card: "summary_large_image",
      images: [ogImage],
    },
    other: {
      "article:section": verticalLabel,
      ...(reviewedAt
        ? { "article:published_time": reviewedAt, "article:modified_time": reviewedAt }
        : {}),
    },
  };
}

export default async function ArticlePage({ params }: Params) {
  const article = getArticle(params.vertical, params.slug);
  if (!article) notFound();

  const verticalLabel = CONDITION_DISPLAY_NAMES[params.vertical] ?? params.vertical;

  const { content } = await compileMDX({
    source: article.content,
    components: mdxComponents,
    options: { parseFrontmatter: false },
  });

  const url = `https://kyrosclinic.com/learn/${params.vertical}/${params.slug}`;
  const reviewedAt = safeIso(article.lastReviewed);
  const reviewer = article.reviewer;
  const reviewerNamed = Boolean(reviewer?.name) && reviewer!.name !== PLACEHOLDER_NAME;
  const conditionImage = getCondition(params.vertical)?.image
    ? `https://kyrosclinic.com${getCondition(params.vertical)!.image}`
    : "https://kyrosclinic.com/treatments/HeroDashboard.png";

  const physician = reviewerNamed
    ? {
        "@type": "Physician",
        name: reviewer!.name,
        ...(reviewer!.specialty ? { jobTitle: reviewer!.specialty } : {}),
        ...(reviewer!.nmcRegNo
          ? {
              hasCredential: {
                "@type": "EducationalOccupationalCredential",
                credentialCategory: "NMC Registration",
                name: `NMC Reg. ${reviewer!.nmcRegNo}`,
              },
            }
          : {}),
      }
    : null;

  const organization = {
    "@type": "Organization",
    name: "Kyros Clinic",
    url: "https://kyrosclinic.com",
  };

  const graph: Record<string, unknown>[] = [
    {
      "@type": "BreadcrumbList",
      itemListElement: [
        { "@type": "ListItem", position: 1, name: "Home", item: "https://kyrosclinic.com" },
        { "@type": "ListItem", position: 2, name: "Learn", item: "https://kyrosclinic.com/learn" },
        { "@type": "ListItem", position: 3, name: verticalLabel, item: `https://kyrosclinic.com/learn/${params.vertical}` },
        { "@type": "ListItem", position: 4, name: article.title, item: url },
      ],
    },
    {
      "@type": "MedicalWebPage",
      "@id": `${url}#page`,
      url,
      name: article.title,
      description: article.metaDescription,
      specialty: verticalLabel,
      inLanguage: "en-IN",
      isPartOf: { "@type": "WebSite", name: "Kyros Clinic", url: "https://kyrosclinic.com" },
      ...(physician ? { reviewedBy: physician } : {}),
    },
    {
      "@type": "Article",
      "@id": url,
      headline: article.title,
      description: article.metaDescription,
      image: conditionImage,
      url,
      ...(reviewedAt ? { datePublished: reviewedAt, dateModified: reviewedAt } : {}),
      publisher: organization,
      author: physician ?? organization,
      ...(physician ? { reviewedBy: physician } : {}),
      about: {
        "@type": "MedicalCondition",
        name: article.about ?? verticalLabel,
        url: `https://kyrosclinic.com/conditions/${params.vertical}`,
      },
      medicalAudience: { "@type": "Patient" },
      inLanguage: "en-IN",
      isPartOf: { "@id": `${url}#page` },
    },
  ];

  if (article.faq && article.faq.length > 0) {
    graph.push({
      "@type": "FAQPage",
      "@id": `${url}#faq`,
      mainEntity: article.faq.map((item) => ({
        "@type": "Question",
        name: item.q,
        acceptedAnswer: { "@type": "Answer", text: item.a },
      })),
    });
  }

  const schema = { "@context": "https://schema.org", "@graph": graph };

  return (
    <>
      <JsonLD data={schema} />

      {/* Article layout */}
      <div className="bg-ivory min-h-screen">
        <div className="max-w-3xl mx-auto px-6 py-12">
          {/* Header */}
          <ArticleHeader
            title={article.title}
            deck={article.deck}
            vertical={params.vertical}
            readingTimeMinutes={article.readingTimeMinutes}
          />

          {/* Reviewer byline — above the fold, mandatory per clinical-compliance */}
          <div className="mb-8">
            <DoctorByline reviewer={reviewer} reviewedAt={article.lastReviewed} />
          </div>

          {/* MDX body */}
          <article className="prose-kyros">{content}</article>

          {/* FAQ */}
          <ArticleFaqSection faqs={article.faq} />

          {/* References */}
          <References sources={article.sources} />

          {/* Footer byline repeat */}
          <div className="mt-8">
            <DoctorByline reviewer={reviewer} reviewedAt={article.lastReviewed} compact />
          </div>

          {/* Condition link */}
          <div className="mt-8 p-6 bg-white rounded-card border border-forest/8">
            <p className="font-body text-body text-stone mb-3">
              Want to understand your own {verticalLabel.toLowerCase()} picture? A Kyros
              specialist can review your labs, symptoms, and history in a 20-minute consultation.
            </p>
            <Link
              href={article.conversionPage ?? "/book"}
              className="inline-flex items-center justify-center px-6 py-3 rounded-button
                         bg-forest text-ivory font-body font-medium text-body-lg
                         hover:bg-jade transition-colors duration-micro"
            >
              Talk to a {verticalLabel.toLowerCase()} doctor
            </Link>
          </div>
        </div>
      </div>

      <CTASection
        headline={`More on ${verticalLabel}`}
        subline={`Read all ${verticalLabel.toLowerCase()} articles from our specialist doctors.`}
        primaryCta={{ label: `All ${verticalLabel} articles`, href: `/learn/${params.vertical}` }}
        secondaryCta={{ label: "All conditions", href: "/conditions" }}
        variant="ivory"
      />
    </>
  );
}
