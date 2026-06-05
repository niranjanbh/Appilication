import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { compileMDX } from "next-mdx-remote/rsc";
import { getAllArticleParams, getArticle } from "../../../../lib/mdx";
import { getDoctor } from "../../../../lib/doctors";
import { getCondition } from "../../../../lib/conditions";
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
  const reviewedAt = new Date(article.doctor_reviewed_at).toISOString();
  const ogImage = getCondition(params.vertical)?.image ?? '/treatments/HeroDashboard.png';

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
      publishedTime: reviewedAt,
      modifiedTime: reviewedAt,
      images: [{ url: ogImage, width: 1200, height: 630, alt: article.title }],
      ...(doctor ? { authors: [doctor.name] } : {}),
    },
    twitter: {
      card: 'summary_large_image',
      images: [ogImage],
    },
    other: {
      "article:section": verticalLabel,
      "article:published_time": reviewedAt,
      "article:modified_time": reviewedAt,
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

  const reviewedAt = new Date(article.doctor_reviewed_at).toISOString();

  const schema = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Home", item: "https://kyrosclinic.com" },
          { "@type": "ListItem", position: 2, name: "Learn", item: "https://kyrosclinic.com/learn" },
          { "@type": "ListItem", position: 3, name: verticalLabel, item: `https://kyrosclinic.com/learn/${params.vertical}` },
          { "@type": "ListItem", position: 4, name: article.title, item: `https://kyrosclinic.com/learn/${params.vertical}/${params.slug}` },
        ],
      },
      {
        "@type": "MedicalWebPage",
        "@id": `https://kyrosclinic.com/learn/${params.vertical}/${params.slug}#page`,
        url: `https://kyrosclinic.com/learn/${params.vertical}/${params.slug}`,
        name: article.title,
        description: article.deck,
        specialty: verticalLabel,
        inLanguage: "en-IN",
        isPartOf: { "@type": "WebSite", name: "Kyros Clinic", url: "https://kyrosclinic.com" },
        ...(doctor ? {
          reviewedBy: {
            "@type": "Physician",
            name: doctor.name,
            jobTitle: doctor.specialty,
            hasCredential: {
              "@type": "EducationalOccupationalCredential",
              credentialCategory: "NMC Registration",
              name: `NMC Reg. ${doctor.nmcRegistration}`,
            },
          },
        } : {}),
      },
      {
        "@type": "Article",
        "@id": `https://kyrosclinic.com/learn/${params.vertical}/${params.slug}`,
        headline: article.title,
        description: article.deck,
        image: getCondition(params.vertical)?.image
          ? `https://kyrosclinic.com${getCondition(params.vertical)!.image}`
          : `https://kyrosclinic.com/treatments/HeroDashboard.png`,
        url: `https://kyrosclinic.com/learn/${params.vertical}/${params.slug}`,
        datePublished: reviewedAt,
        dateModified: reviewedAt,
        publisher: {
          "@type": "Organization",
          name: "Kyros Clinic",
          url: "https://kyrosclinic.com",
        },
        ...(doctor
          ? {
              author: {
                "@type": "Physician",
                name: doctor.name,
                jobTitle: doctor.specialty,
                hasCredential: {
                  "@type": "EducationalOccupationalCredential",
                  credentialCategory: "NMC Registration",
                  name: `NMC Reg. ${doctor.nmcRegistration}`,
                },
              },
              reviewedBy: {
                "@type": "Physician",
                name: doctor.name,
                jobTitle: doctor.specialty,
                hasCredential: {
                  "@type": "EducationalOccupationalCredential",
                  credentialCategory: "NMC Registration",
                  name: `NMC Reg. ${doctor.nmcRegistration}`,
                },
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
          "@id": `https://kyrosclinic.com/learn/${params.vertical}/${params.slug}#page`,
        },
      },
    ],
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
