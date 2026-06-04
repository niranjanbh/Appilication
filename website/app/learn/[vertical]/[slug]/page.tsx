import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { compileMDX } from "next-mdx-remote/rsc";
import { getAllArticleParams, getArticle } from "../../../../lib/mdx";
import { getDoctor } from "../../../../lib/doctors";
import { CONDITION_DISPLAY_NAMES } from "../../../../lib/conditionDisplay";
import { JsonLD } from "../../../../components/schema/JsonLD";
import { ArticleHeader } from "../../../../components/article/ArticleHeader";
import { DoctorByline } from "../../../../components/article/DoctorByline";
import { References } from "../../../../components/article/References";
import { mdxComponents } from "../../../../components/article/MdxComponents";
import { CTASection } from "../../../../components/marketing/CTASection";

// ISR: revalidate once per hour so content updates without a full rebuild
export const revalidate = 3600;

interface Params {
  params: { vertical: string; slug: string };
}

export function generateStaticParams() {
  return getAllArticleParams();
}

export function generateMetadata({ params }: Params): Metadata {
  const article = getArticle(params.vertical, params.slug);
  if (!article) return {};
  const doctor = getDoctor(article.doctor_author_id);
  const verticalLabel = CONDITION_DISPLAY_NAMES[params.vertical] ?? params.vertical;
  return {
    title: article.title,
    description: article.deck,
    alternates: {
      canonical: `https://kyrosclinic.com/learn/${params.vertical}/${params.slug}`,
    },
    openGraph: {
      title: `${article.title} — Kyros Clinic`,
      description: article.deck,
      url: `https://kyrosclinic.com/learn/${params.vertical}/${params.slug}`,
      type: "article",
      ...(doctor ? { authors: [doctor.name] } : {}),
    },
    other: {
      "article:section": verticalLabel,
      "article:modified_time": new Date(article.doctor_reviewed_at).toISOString(),
    },
  };
}

export default async function ArticlePage({ params }: Params) {
  const article = getArticle(params.vertical, params.slug);
  if (!article) notFound();

  const doctor = getDoctor(article.doctor_author_id);
  const verticalLabel = CONDITION_DISPLAY_NAMES[params.vertical] ?? params.vertical;

  const { content } = await compileMDX({
    source: article.content,
    components: mdxComponents,
    options: { parseFrontmatter: false },
  });

  const schema = {
    "@context": "https://schema.org",
    "@type": "Article",
    "@id": `https://kyrosclinic.com/learn/${params.vertical}/${params.slug}`,
    headline: article.title,
    description: article.deck,
    url: `https://kyrosclinic.com/learn/${params.vertical}/${params.slug}`,
    dateModified: new Date(article.doctor_reviewed_at).toISOString(),
    publisher: {
      "@type": "Organization",
      name: "Kyros Clinic",
      url: "https://kyrosclinic.com",
    },
    ...(doctor
      ? {
          author: {
            "@type": "Person",
            name: doctor.name,
            jobTitle: doctor.specialty,
            identifier: `NMC Reg. ${doctor.nmcRegistration}`,
          },
          reviewedBy: {
            "@type": "Person",
            name: doctor.name,
            jobTitle: doctor.specialty,
            identifier: `NMC Reg. ${doctor.nmcRegistration}`,
          },
        }
      : {}),
    about: {
      "@type": "MedicalCondition",
      name: verticalLabel,
      url: `https://kyrosclinic.com/conditions/${params.vertical}`,
    },
    medicalAudience: { "@type": "Patient" },
    inLanguage: "en-IN",
    isPartOf: {
      "@type": "WebSite",
      name: "Kyros Clinic",
      url: "https://kyrosclinic.com",
    },
  };

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

          {/* Doctor byline — above the fold, mandatory per clinical-compliance */}
          {doctor && (
            <div className="mb-8">
              <DoctorByline doctor={doctor} reviewedAt={article.doctor_reviewed_at} />
            </div>
          )}

          {/* MDX body */}
          <article className="prose-kyros">{content}</article>

          {/* References */}
          <References references={article.references} />

          {/* Footer byline repeat */}
          {doctor && (
            <div className="mt-8">
              <DoctorByline doctor={doctor} reviewedAt={article.doctor_reviewed_at} compact />
            </div>
          )}

          {/* Condition link */}
          <div className="mt-8 p-6 bg-white rounded-card border border-forest/8">
            <p className="font-body text-body text-stone mb-3">
              Want to understand your own {verticalLabel.toLowerCase()} picture? A Kyros
              specialist can review your labs, symptoms, and history in a 20-minute consultation.
            </p>
            <Link
              href="/book"
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
