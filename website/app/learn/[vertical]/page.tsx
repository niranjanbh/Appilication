import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { getArticlesByVertical, getVerticals } from "../../../lib/mdx";
import { getDoctor } from "../../../lib/doctors";
import { getCondition } from "../../../lib/conditions";
import { CONDITION_DISPLAY_NAMES } from "../../../lib/conditionDisplay";
import { JsonLD } from "../../../components/schema/JsonLD";

interface Params {
  params: { vertical: string };
}

export function generateStaticParams() {
  return getVerticals().map((vertical) => ({ vertical }));
}

export function generateMetadata({ params }: Params): Metadata {
  const label = CONDITION_DISPLAY_NAMES[params.vertical];
  if (!label) return {};
  const ogImage = getCondition(params.vertical)?.ogImage ?? '/treatments/HeroDashboard.png';
  return {
    title: `${label} — Clinical Articles`,
    description: `Doctor-reviewed clinical articles on ${label.toLowerCase()} from NMC-registered specialists at Kyros Clinic.`,
    alternates: { canonical: `https://kyrosclinic.com/learn/${params.vertical}` },
    openGraph: {
      title: `${label} Articles — Kyros Clinic`,
      description: `Doctor-reviewed articles on ${label.toLowerCase()} — sourced, specialist-reviewed, written for Indian patients.`,
      url: `https://kyrosclinic.com/learn/${params.vertical}`,
      images: [{ url: ogImage, width: 1200, height: 630, alt: `${label} health guides` }],
    },
    twitter: {
      card: 'summary_large_image' as const,
      images: [ogImage],
    },
  };
}

export default function VerticalLearnPage({ params }: Params) {
  const label = CONDITION_DISPLAY_NAMES[params.vertical];
  if (!label) notFound();

  const articles = getArticlesByVertical(params.vertical);
  if (articles.length === 0) notFound();

  const schema = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Home", item: "https://kyrosclinic.com" },
          { "@type": "ListItem", position: 2, name: "Learn", item: "https://kyrosclinic.com/learn" },
          { "@type": "ListItem", position: 3, name: label, item: `https://kyrosclinic.com/learn/${params.vertical}` },
        ],
      },
      {
        "@type": "CollectionPage",
        "@id": `https://kyrosclinic.com/learn/${params.vertical}`,
        name: `${label} — Kyros Clinic Learn`,
        url: `https://kyrosclinic.com/learn/${params.vertical}`,
        description: `Doctor-reviewed clinical articles on ${label.toLowerCase()}.`,
      },
    ],
  };

  return (
    <>
      <JsonLD data={schema} />

      <section className="bg-ivory py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <nav aria-label="Breadcrumb" className="mb-4">
            <ol className="flex items-center gap-2 font-body text-caption text-stone" role="list">
              <li>
                <Link href="/learn" className="hover:text-forest transition-colors duration-micro">
                  Learn
                </Link>
              </li>
              <li aria-hidden="true">·</li>
              <li className="text-forest">{label}</li>
            </ol>
          </nav>
          <h1 className="font-display text-h1 font-medium text-forest mb-4">{label}</h1>
          <p className="font-body text-body-lg text-stone max-w-2xl leading-relaxed">
            Clinical articles on {label.toLowerCase()}, reviewed by NMC-registered specialists.
          </p>
        </div>
      </section>

      <section className="bg-white py-12 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {articles.map((article) => {
              const doctor = getDoctor(article.doctor_author_id);
              return (
                <Link
                  key={article.slug}
                  href={`/learn/${params.vertical}/${article.slug}`}
                  className="group block bg-white rounded-card p-6 border border-forest/8
                             hover:border-forest/30 hover:shadow-sm transition-all duration-entrance"
                >
                  <h2 className="font-display text-h3 font-medium text-forest mb-2 group-hover:text-jade transition-colors duration-micro">
                    {article.title}
                  </h2>
                  <p className="font-body text-body text-stone leading-relaxed mb-4">
                    {article.deck}
                  </p>
                  <p className="font-body text-caption text-stone">
                    {doctor ? `Reviewed by ${doctor.name}` : "Doctor-reviewed"}{" "}
                    · {article.readingTimeMinutes} min read
                  </p>
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      <section className="bg-peach-mist py-12 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <p className="font-display text-h2 font-medium text-forest mb-4">
            Ready to talk to a {label.toLowerCase()} specialist?
          </p>
          <Link
            href="/book"
            className="inline-flex items-center justify-center px-7 py-3 rounded-button
                       bg-forest text-ivory font-body font-medium text-body-lg
                       hover:bg-jade transition-colors duration-micro"
          >
            Book a consultation
          </Link>
        </div>
      </section>
    </>
  );
}
