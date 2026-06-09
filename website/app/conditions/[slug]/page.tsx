import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import { CONDITIONS, getCondition, CONDITION_SLUGS } from '../../../lib/conditions';
import { JsonLD } from '../../../components/schema/JsonLD';
import { PullQuote } from '../../../components/ui/PullQuote';
import { CTASection } from '../../../components/marketing/CTASection';
import { StatBlock } from '../../../components/marketing/StatBlock';

const CONDITION_SPECIALTY: Record<string, string> = {
  thyroid: 'Endocrinology',
  pcos: 'Endocrinology',
  'weight-management': 'Internal Medicine',
  'skin-and-hair': 'Dermatology',
  'mens-intimate-health': 'Urology',
  'hormones-trt': 'Endocrinology',
  longevity: 'Preventive Medicine',
};

interface Params {
  params: { slug: string };
}

export function generateStaticParams() {
  return CONDITION_SLUGS.map((slug) => ({ slug }));
}

export function generateMetadata({ params }: Params): Metadata {
  const condition = getCondition(params.slug);
  if (!condition) return {};
  return {
    title: `${condition.name} Specialist Consultation`,
    description: condition.heroSubline,
    alternates: {
      canonical: `https://kyrosclinic.com/conditions/${condition.slug}`,
    },
    openGraph: {
      title: `${condition.name} — Kyros Clinic`,
      description: condition.heroSubline,
      url: `https://kyrosclinic.com/conditions/${condition.slug}`,
      images: [{ url: condition.image, width: 1200, height: 630, alt: condition.name }],
    },
    twitter: {
      card: 'summary_large_image',
      images: [condition.image],
    },
  };
}

export default function ConditionPage({ params }: Params) {
  const condition = getCondition(params.slug);
  if (!condition) notFound();

  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://kyrosclinic.com' },
          { '@type': 'ListItem', position: 2, name: 'Conditions', item: 'https://kyrosclinic.com/conditions' },
          { '@type': 'ListItem', position: 3, name: condition.name, item: `https://kyrosclinic.com/conditions/${condition.slug}` },
        ],
      },
      {
        '@type': 'MedicalWebPage',
        '@id': `https://kyrosclinic.com/conditions/${condition.slug}`,
        name: `${condition.name} — Kyros Clinic`,
        url: `https://kyrosclinic.com/conditions/${condition.slug}`,
        description: condition.heroSubline,
        specialty: CONDITION_SPECIALTY[condition.slug] ?? 'Endocrinology',
        mainEntity: {
          '@id': `https://kyrosclinic.com/conditions/${condition.slug}#condition`,
        },
      },
      {
        '@type': 'MedicalCondition',
        '@id': `https://kyrosclinic.com/conditions/${condition.slug}#condition`,
        name: condition.schemaName,
        description: condition.schemaDescription,
        url: `https://kyrosclinic.com/conditions/${condition.slug}`,
        epidemiology: condition.stats[0]
          ? `${condition.stats[0].numeral} ${condition.stats[0].caption}`
          : undefined,
        possibleTreatment: condition.whatWeOffer.map((offer) => ({
          '@type': 'MedicalTherapy',
          name: offer,
        })),
        signOrSymptom: condition.symptoms.map((s) => ({
          '@type': 'MedicalSymptom',
          name: s,
        })),
      },
      condition.faqs.length > 0
        ? {
            '@type': 'FAQPage',
            '@id': `https://kyrosclinic.com/conditions/${condition.slug}#faq`,
            mainEntity: condition.faqs.map((faq) => ({
              '@type': 'Question',
              name: faq.question,
              acceptedAnswer: {
                '@type': 'Answer',
                text: faq.answer,
              },
            })),
          }
        : null,
    ].filter(Boolean),
  };

  const heroBg = condition.sensitiveCategory ? 'bg-peach-mist' : 'bg-ivory';
  const pullAccent = condition.sensitiveCategory ? 'terracotta' : 'saffron';

  return (
    <>
      <JsonLD data={schema} />

      {/* 1. Hero */}
      <section className={`${heroBg} py-20 px-6`}>
        {/* Condition navigation pills */}
        <div className="max-w-7xl mx-auto mb-10 overflow-x-auto">
          <div className="flex gap-2 pb-1 min-w-max">
            {CONDITIONS.map((c) => (
              <Link
                key={c.slug}
                href={`/conditions/${c.slug}`}
                className={`px-4 py-1.5 rounded-full font-body text-caption font-medium whitespace-nowrap transition-colors duration-micro
                  ${c.slug === condition.slug
                    ? 'bg-forest text-ivory'
                    : 'border border-forest/30 text-forest hover:bg-forest/8'
                  }`}
              >
                {c.name}
              </Link>
            ))}
          </div>
        </div>

        <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-10 items-center">
          <div>
            <p className="font-body text-caption text-stone uppercase tracking-widest mb-4">
              Kyros Clinic · {condition.name}
            </p>
            <h1 className="font-display text-h1 font-medium text-forest leading-tight mb-4">
              {condition.hook}
            </h1>
            <p className="font-body text-body-lg text-ink max-w-2xl mb-8 leading-relaxed">
              {condition.heroSubline}
            </p>
            <div className="flex flex-wrap gap-4">
              <a
                href="/book"
                className="inline-flex items-center justify-center px-7 py-3 rounded-button
                           bg-forest text-ivory font-body font-medium text-body-lg
                           hover:bg-jade transition-colors duration-micro"
              >
                Talk to a doctor
              </a>
              <a
                href="/how-it-works"
                className="inline-flex items-center justify-center px-7 py-3 rounded-button
                           border-2 border-forest text-forest font-body font-medium text-body-lg
                           hover:bg-forest/8 transition-colors duration-micro"
              >
                How it works
              </a>
            </div>
          </div>
          <div className="relative h-72 md:h-96 w-full">
            <Image
              src={condition.image}
              alt={condition.name}
              fill
              sizes="(max-width: 768px) 100vw, 50vw"
              className="object-contain"
              priority
            />
          </div>
        </div>
      </section>

      {/* 2. Pillar: symptoms */}
      <section className="bg-peach-mist py-16 px-6">
        <div className="max-w-7xl mx-auto">
          <h2 className="font-display text-h2 font-medium text-forest mb-8">
            Recognising {condition.name.toLowerCase()}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {condition.symptoms.map((symptom) => (
              <div key={symptom} className="bg-ivory rounded-card px-6 py-4 flex items-start gap-3">
                <span
                  className="w-2 h-2 rounded-full bg-saffron flex-shrink-0 mt-2"
                  aria-hidden="true"
                />
                <p className="font-body text-body text-ink">{symptom}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 3. Pull quote */}
      <section className="bg-ivory py-12 px-6">
        <div className="max-w-3xl mx-auto">
          <PullQuote accent={pullAccent}>{condition.hook}</PullQuote>
        </div>
      </section>

      {/* 4. What we offer */}
      <section className="bg-white py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="font-display text-h2 font-medium text-forest mb-8">
            What Kyros offers for {condition.name.toLowerCase()}
          </h2>
          <ol className="space-y-4" role="list">
            {condition.whatWeOffer.map((item, i) => (
              <li key={item} className="flex gap-4">
                <span
                  className="flex-shrink-0 w-7 h-7 rounded-full bg-saffron flex items-center justify-center font-display text-caption font-medium text-forest"
                  aria-hidden="true"
                >
                  {i + 1}
                </span>
                <p className="font-body text-body text-ink pt-1 leading-relaxed">{item}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* 6. Stats */}
      <StatBlock stats={condition.stats.map((s) => ({ ...s, color: 'forest' as const }))} />

      {/* 7. Process */}
      <section className="bg-ivory py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="font-display text-h2 font-medium text-forest mb-8">
            How a Kyros {condition.name.toLowerCase()} consultation works
          </h2>
          <ol className="space-y-8" role="list">
            {[
              {
                title: 'Complete a short intake.',
                body: 'Before your consultation, you fill in a brief symptom and history form. Your doctor reads it before the call — not during.',
              },
              {
                title: 'Consult with a specialist.',
                body: `Your Kyros doctor is a specialist in ${condition.name.toLowerCase()}. The consultation is 20 minutes, video-based, private.`,
              },
              {
                title: 'Receive a plan you can follow.',
                body: 'After the consultation: a prescription if indicated, lab orders if needed, a follow-up date, and a written note from your doctor.',
              },
              {
                title: 'Track and adjust over time.',
                body: 'Labs, biomarkers, dosage changes, and doctor notes accumulate in one place. Your doctor adjusts the plan at every follow-up.',
              },
            ].map((step, i) => (
              <li key={step.title} className="flex gap-6">
                <div
                  className="flex-shrink-0 w-10 h-10 rounded-full bg-saffron flex items-center justify-center"
                  aria-hidden="true"
                >
                  <span className="font-display text-h3 font-medium text-forest">{i + 1}</span>
                </div>
                <div className="pt-1">
                  <h3 className="font-display text-h3 font-medium text-forest mb-1">
                    {step.title}
                  </h3>
                  <p className="font-body text-body text-ink leading-relaxed">{step.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* 8. FAQ */}
      {condition.faqs.length > 0 && (
        <section className="bg-peach-mist py-16 px-6">
          <div className="max-w-3xl mx-auto">
            <h2 className="font-display text-h2 font-medium text-forest mb-8">
              Common questions
            </h2>
            <div className="space-y-6">
              {condition.faqs.map((faq) => (
                <div key={faq.question} className="bg-ivory rounded-card p-7">
                  <h3 className="font-display text-h3 font-medium text-forest mb-3">
                    {faq.question}
                  </h3>
                  <p className="font-body text-body text-ink leading-relaxed">{faq.answer}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* 9. Reflective close */}
      <section className="bg-ivory py-12 px-6 border-t-2 border-terracotta">
        <div className="max-w-3xl mx-auto">
          <p className="font-display text-h2 italic font-medium text-forest text-center">
            {condition.reflectiveClose}
          </p>
        </div>
      </section>

      {/* 10. CTA */}
      <CTASection
        headline={`Begin with a ${condition.name.toLowerCase()} consultation.`}
        subline="Consultations start at ₹400. A specialist will review your intake before your call."
        primaryCta={{ label: 'Talk to a doctor', href: '/book' }}
        secondaryCta={{ label: 'See pricing', href: '/pricing' }}
        variant="forest"
      />
    </>
  );
}
