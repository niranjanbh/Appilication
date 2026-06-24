import type { Metadata } from 'next';
import { JsonLD } from '../../components/schema/JsonLD';
import { CTASection } from '../../components/marketing/CTASection';

export const metadata: Metadata = {
  title: 'Consultation Fees & Pricing',
  description:
    'Kyros Clinic consultations start at ₹400. No hidden fees. Transparent pricing for initial and follow-up consultations across all eight conditions.',
  alternates: { canonical: 'https://kyrosclinic.com/pricing' },
  openGraph: {
    title: 'Consultation Fees & Pricing — Kyros Clinic',
    description: 'Initial consultations ₹600. Follow-ups ₹400–₹500. No platform fees or hidden charges.',
    url: 'https://kyrosclinic.com/pricing',
    images: [{ url: '/treatments/HeroDashboard.png', width: 1200, height: 630, alt: 'Kyros Clinic pricing' }],
  },
  twitter: {
    card: 'summary_large_image',
    images: ['/treatments/HeroDashboard.png'],
  },
};

const FAQS = [
  {
    q: 'Is there a platform fee on top of the consultation fee?',
    a: 'No. The consultation fee is what you pay. No platform fee, no booking fee, no GST added at checkout beyond what is legally required.',
  },
  {
    q: 'What is the cancellation and refund policy?',
    a: 'Cancel up to 2 hours before your scheduled consultation for a full refund. Cancellations within 2 hours are not refunded unless the cancellation is initiated by the clinic.',
  },
  {
    q: 'Are lab tests included in the consultation fee?',
    a: 'No. Lab tests are ordered by your doctor and performed at a lab of your choice (Redcliffe, Dr Lal PathLabs, Thyrocare, Metropolis, or a local lab). The cost of lab tests is separate and paid directly to the lab.',
  },
  {
    q: 'Are prescriptions included?',
    a: 'Yes. If your doctor issues a prescription during the consultation, it is included in the consultation fee. You pay the pharmacy separately for medications.',
  },
  {
    q: 'Is there a discount for follow-up consultations?',
    a: 'Follow-up consultations with the same doctor are priced between ₹400–₹500. The exact fee is shown at the time of booking.',
  },
];

const schema = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://kyrosclinic.com' },
        { '@type': 'ListItem', position: 2, name: 'Pricing', item: 'https://kyrosclinic.com/pricing' },
      ],
    },
    {
      '@type': 'MedicalWebPage',
      '@id': 'https://kyrosclinic.com/pricing',
      name: 'Kyros Clinic Pricing',
      url: 'https://kyrosclinic.com/pricing',
      description: 'Transparent consultation pricing at Kyros Clinic. Initial and follow-up consultations for hormonal health conditions.',
    },
    {
      '@type': 'FAQPage',
      '@id': 'https://kyrosclinic.com/pricing#faq',
      mainEntity: FAQS.map((faq) => ({
        '@type': 'Question',
        name: faq.q,
        acceptedAnswer: { '@type': 'Answer', text: faq.a },
      })),
    },
  ],
};

export default function PricingPage() {
  return (
    <>
      <JsonLD data={schema} />

      {/* Hero */}
      <section className="bg-ivory py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <h1 className="font-display text-h1 font-medium text-forest mb-4">
            Transparent pricing
          </h1>
          <p className="font-body text-body-lg text-ink max-w-2xl leading-relaxed">
            No hidden platform fees. No asterisks. The price you see is the price you pay.
          </p>
        </div>
      </section>

      {/* Pricing tiers */}
      <section className="bg-white py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Initial */}
            <div className="bg-ivory rounded-card p-8 border-2 border-forest/15">
              <p className="font-body text-caption text-stone uppercase tracking-widest mb-4">
                Initial consultation
              </p>
              <p className="font-display text-display font-medium text-forest mb-1">₹600</p>
              <p className="font-body text-caption text-stone mb-6">One-time fee, no subscription</p>
              <ul className="space-y-3 mb-8" role="list">
                {[
                  '20-minute video consultation with a specialist',
                  'Pre-consultation intake reviewed by your doctor',
                  'Written doctor\'s note within 24 hours',
                  'Prescription if clinically indicated',
                  'Lab orders with guidance on testing',
                  'Follow-up scheduling',
                ].map((item) => (
                  <li key={item} className="flex gap-3 items-start">
                    <span className="w-2 h-2 rounded-full bg-saffron flex-shrink-0 mt-2" aria-hidden="true" />
                    <p className="font-body text-body text-ink">{item}</p>
                  </li>
                ))}
              </ul>
              <a
                href="/book"
                className="block w-full text-center px-6 py-3 rounded-button
                           bg-forest text-ivory font-body font-medium text-body-lg
                           hover:bg-jade transition-colors duration-micro"
              >
                Book initial consultation
              </a>
            </div>

            {/* Follow-up */}
            <div className="bg-ivory rounded-card p-8 border border-forest/8">
              <p className="font-body text-caption text-stone uppercase tracking-widest mb-4">
                Follow-up consultation
              </p>
              <p className="font-display text-display font-medium text-forest mb-1">₹400–₹500</p>
              <p className="font-body text-caption text-stone mb-6">With the same doctor</p>
              <ul className="space-y-3 mb-8" role="list">
                {[
                  'Continuation with your existing doctor',
                  'Lab result review and interpretation',
                  'Prescription adjustment if needed',
                  'Plan review based on progress',
                  'Priority scheduling with your doctor',
                ].map((item) => (
                  <li key={item} className="flex gap-3 items-start">
                    <span className="w-2 h-2 rounded-full bg-sage flex-shrink-0 mt-2" aria-hidden="true" />
                    <p className="font-body text-body text-ink">{item}</p>
                  </li>
                ))}
              </ul>
              <p className="font-body text-caption text-stone">
                Follow-up consultations are booked after your first consultation, from within the
                Kyros app.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* What is not included */}
      <section className="bg-peach-mist py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="font-display text-h2 font-medium text-forest mb-6">
            What the consultation fee does not include
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { item: 'Lab tests', note: 'Ordered by your doctor, paid directly to the lab of your choice.' },
              { item: 'Medications', note: 'Prescribed by your doctor, filled at any pharmacy.' },
              { item: 'In-clinic procedures', note: 'Kyros is a telemedicine clinic. PRP, laser, surgeries are not offered.' },
              { item: 'Supplements', note: 'Kyros does not sell or recommend specific supplement brands.' },
            ].map(({ item, note }) => (
              <div key={item} className="bg-ivory rounded-card p-6">
                <p className="font-display text-h3 font-medium text-forest mb-1">{item}</p>
                <p className="font-body text-body text-stone">{note}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="bg-ivory py-16 px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="font-display text-h2 font-medium text-forest mb-8">
            Pricing questions
          </h2>
          <div className="space-y-6">
            {FAQS.map((faq) => (
              <div key={faq.q} className="bg-white rounded-card p-7">
                <h3 className="font-display text-h3 font-medium text-forest mb-3">{faq.q}</h3>
                <p className="font-body text-body text-ink leading-relaxed">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <CTASection
        headline="Start with an initial consultation."
        subline="₹600. No subscription. Cancel up to 2 hours before for a full refund."
        primaryCta={{ label: 'Book a consultation', href: '/book' }}
        secondaryCta={{ label: 'How it works', href: '/how-it-works' }}
        variant="forest"
      />
    </>
  );
}
