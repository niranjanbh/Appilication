import type { Metadata } from 'next';
import { HonestPlaceholder } from '../../components/marketing/HonestPlaceholder';
import { CTASection } from '../../components/marketing/CTASection';
import { JsonLD } from '../../components/schema/JsonLD';

export const metadata: Metadata = {
  title: 'Advisory Board',
  description:
    'Kyros Clinic advisory board — being formed carefully. We list advisors only after they have publicly confirmed their role in writing.',
  alternates: { canonical: 'https://kyrosclinic.com/advisory-board' },
  openGraph: {
    title: 'Advisory Board — Kyros Clinic',
    description:
      'Kyros Clinic advisory board — being formed carefully. Clinical, regulatory, and operational expertise. Listed only after written confirmation.',
    url: 'https://kyrosclinic.com/advisory-board',
  },
};

const schema = {
  '@context': 'https://schema.org',
  '@type': 'AboutPage',
  '@id': 'https://kyrosclinic.com/advisory-board',
  name: 'Advisory Board — Kyros Clinic',
  url: 'https://kyrosclinic.com/advisory-board',
  description: 'Kyros Clinic advisory board — clinical, regulatory, and operational expertise.',
  breadcrumb: {
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://kyrosclinic.com' },
      { '@type': 'ListItem', position: 2, name: 'Advisory Board', item: 'https://kyrosclinic.com/advisory-board' },
    ],
  },
};

export default function AdvisoryBoardPage() {
  return (
    <>
      <JsonLD data={schema} />
      {/* Hero */}
      <section className="bg-ivory py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <h1 className="font-display text-h1 font-medium text-forest mb-4">Advisory board</h1>
          <p className="font-body text-body-lg text-stone max-w-2xl leading-relaxed">
            Kyros's advisory board brings clinical, regulatory, and operational expertise to
            the platform. We are forming it carefully.
          </p>
        </div>
      </section>

      {/* Honest placeholder */}
      <HonestPlaceholder type="advisor" count={3} />

      {/* Why we do this honestly */}
      <section className="bg-white py-16 px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="font-display text-h2 font-medium text-forest mb-6">
            Why this page looks this way
          </h2>
          <div className="space-y-4">
            <p className="font-body text-body text-ink leading-relaxed">
              Many early-stage health startups list impressive names on advisory pages before
              those advisors have reviewed the platform, signed an agreement, or contributed
              meaningfully. We think that is misleading.
            </p>
            <p className="font-body text-body text-ink leading-relaxed">
              Every advisor will be listed here only after they have reviewed the platform in
              detail, confirmed their role in writing, and disclosed any relevant relationships.
              We will introduce each advisor with their full credentials and specific areas of
              contribution.
            </p>
            <p className="font-body text-body text-ink leading-relaxed">
              If you are a clinician, researcher, or operator who wants to contribute to
              building the clinical standard for hormonal health in India, we'd like to hear from
              you.
            </p>
          </div>
          <div className="mt-8">
            <a
              href="/contact"
              className="inline-flex items-center justify-center px-6 py-3 rounded-button
                         border-2 border-forest text-forest font-body font-medium text-body-lg
                         hover:bg-forest/8 transition-colors duration-micro"
            >
              Get in touch
            </a>
          </div>
        </div>
      </section>

      <CTASection
        headline="Questions about Kyros?"
        subline="Talk to the founding team."
        primaryCta={{ label: 'Contact us', href: '/contact' }}
        variant="ivory"
      />
    </>
  );
}
