import type { Metadata } from "next";
import Link from "next/link";
import { getAllArticles } from "../../lib/mdx";
import { getDoctor } from "../../lib/doctors";
import { CONDITION_DISPLAY_NAMES } from "../../lib/conditionDisplay";
import { JsonLD } from "../../components/schema/JsonLD";

export const metadata: Metadata = {
  title: "Learn — Hormonal Health Guides",
  description:
    "Doctor-reviewed articles on thyroid, PCOS, weight management, skin and hair, men's intimate health, hormones, and longevity — written by NMC-registered specialists.",
  alternates: { canonical: "https://kyros.clinic/learn" },
  openGraph: {
    title: "Learn — Kyros Clinic",
    description: "Clinical articles reviewed by NMC-registered specialist doctors.",
    url: "https://kyros.clinic/learn",
  },
};

const schema = {
  "@context": "https://schema.org",
  "@type": "CollectionPage",
  name: "Kyros Clinic — Learn",
  url: "https://kyros.clinic/learn",
  description:
    "Doctor-reviewed clinical articles on hormonal health conditions for Indian patients.",
};

function ArticleCard({
  article,
}: {
  article: ReturnType<typeof getAllArticles>[number];
}) {
  const doctor = getDoctor(article.doctor_author_id);
  const verticalLabel = CONDITION_DISPLAY_NAMES[article.vertical] ?? article.vertical;

  return (
    <Link
      href={`/learn/${article.vertical}/${article.slug}`}
      className="group block bg-white rounded-card p-6 border border-forest/8
                 hover:border-forest/30 hover:shadow-sm transition-all duration-entrance"
    >
      <span className="inline-block bg-saffron/15 text-forest font-body text-caption font-medium px-2 py-0.5 rounded-button mb-3">
        {verticalLabel}
      </span>
      <h2 className="font-display text-h3 font-medium text-forest mb-2 group-hover:text-jade transition-colors duration-micro">
        {article.title}
      </h2>
      <p className="font-body text-body text-stone leading-relaxed mb-4">{article.deck}</p>
      <div className="flex items-center justify-between">
        <p className="font-body text-caption text-stone">
          {doctor ? `Reviewed by ${doctor.name}` : "Doctor-reviewed"}{" "}
          · {article.readingTimeMinutes} min
        </p>
        <span className="font-body text-caption text-forest font-medium">Read →</span>
      </div>
    </Link>
  );
}

export default function LearnPage() {
  const articles = getAllArticles();

  const byVertical: Record<string, typeof articles> = {};
  for (const article of articles) {
    if (!byVertical[article.vertical]) byVertical[article.vertical] = [];
    byVertical[article.vertical].push(article);
  }

  return (
    <>
      <JsonLD data={schema} />

      <section className="bg-ivory py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <h1 className="font-display text-h1 font-medium text-forest mb-4">Learn</h1>
          <p className="font-body text-body-lg text-stone max-w-2xl leading-relaxed">
            Clinical articles written and reviewed by NMC-registered specialist doctors.
            Every claim is sourced. Every article carries its reviewer's name and registration
            number.
          </p>
        </div>
      </section>

      <section className="bg-white py-12 px-6">
        <div className="max-w-7xl mx-auto space-y-14">
          {Object.entries(byVertical).map(([vertical, arts]) => (
            <div key={vertical}>
              <div className="flex items-baseline justify-between mb-6">
                <h2 className="font-display text-h2 font-medium text-forest">
                  {CONDITION_DISPLAY_NAMES[vertical] ?? vertical}
                </h2>
                <Link
                  href={`/learn/${vertical}`}
                  className="font-body text-caption text-forest hover:text-jade transition-colors duration-micro"
                >
                  All {CONDITION_DISPLAY_NAMES[vertical]} articles →
                </Link>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {arts.map((article) => (
                  <ArticleCard key={`${vertical}/${article.slug}`} article={article} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
