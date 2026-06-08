import type { Metadata } from 'next';
import { CONDITIONS } from '../../lib/conditions';
import { JsonLD } from '../../components/schema/JsonLD';
import { ConditionCard } from '../../components/marketing/ConditionCard';
import { CTASection } from '../../components/marketing/CTASection';

export const metadata: Metadata = {
  title: 'Conditions We Treat',
  description:
    'Kyros Clinic covers eight chronic hormonal and metabolic conditions: thyroid, PCOS, weight management, skin & hair, men\'s intimate health, hormones & TRT, diabetes, and longevity.',
  alternates: { canonical: 'https://kyrosclinic.com/conditions' },
  openGraph: {
    title: 'Conditions We Treat — Kyros Clinic',
    url: 'https://kyrosclinic.com/conditions',
  },
};


const schema = {
  '@context': 'https://schema.org',
  '@type': 'MedicalWebPage',
  '@id': 'https://kyrosclinic.com/conditions',
  name: 'Conditions We Treat — Kyros Clinic',
  url: 'https://kyrosclinic.com/conditions',
  description:
    'Overview of the eight clinical verticals at Kyros Clinic: thyroid, PCOS, weight management, skin & hair, men\'s intimate health, hormones & TRT, diabetes, and longevity.',
  specialty: 'Endocrinology',
};

export default function ConditionsPage() {
  return (
    <>
      <JsonLD data={schema} />

      <section className="bg-ivory py-16 px-6">
        <div className="max-w-4xl mx-auto mb-12">
          <h1 className="font-display text-h1 font-medium text-forest mb-4">
            Conditions we treat
          </h1>
          <p className="font-body text-body-lg text-ink max-w-2xl leading-relaxed">
            Each Kyros vertical is staffed by specialist doctors. Choose the condition closest
            to your concern — you can discuss anything with your doctor during the consultation.
          </p>
        </div>
      </section>

      <section className="bg-white py-12 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {CONDITIONS.map((c) => (
              <ConditionCard
                key={c.slug}
                slug={c.slug}
                name={c.name}
                shortDescription={c.shortDescription}
                image={c.image}
              />
            ))}
          </div>
        </div>
      </section>

      <CTASection
        headline="Not sure which condition applies to you?"
        subline="Describe your symptoms to a care coordinator and we'll guide you to the right specialist."
        primaryCta={{ label: 'Request a consultation', href: '/book' }}
        secondaryCta={{ label: 'Contact us', href: '/contact' }}
        variant="ivory"
      />
    </>
  );
}
