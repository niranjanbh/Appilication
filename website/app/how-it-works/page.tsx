import type { Metadata } from 'next';
import { JsonLD } from '../../components/schema/JsonLD';
import { PullQuote } from '../../components/ui/PullQuote';
import { CTASection } from '../../components/marketing/CTASection';

export const metadata: Metadata = {
  title: 'How to Consult a Specialist',
  description:
    'Choose your condition, complete a short intake, consult a specialist, receive a plan. One doctor who stays with you across follow-ups.',
  alternates: { canonical: 'https://kyrosclinic.com/how-it-works' },
  openGraph: {
    title: 'How to Consult a Specialist at Kyros Clinic',
    description: 'A 20-minute video consultation with a specialist who has already read your intake. From anywhere in India.',
    url: 'https://kyrosclinic.com/how-it-works',
    images: [{ url: '/treatments/HeroDashboard.png', width: 1200, height: 630, alt: 'How Kyros Clinic works' }],
  },
  twitter: {
    card: 'summary_large_image',
    images: ['/treatments/HeroDashboard.png'],
  },
};

const schema = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://kyrosclinic.com' },
        { '@type': 'ListItem', position: 2, name: 'How It Works', item: 'https://kyrosclinic.com/how-it-works' },
      ],
    },
    {
      '@type': 'HowTo',
      '@id': 'https://kyrosclinic.com/how-it-works',
      name: 'How to get a Kyros Clinic consultation',
      description:
        'Step-by-step guide to consulting a specialist doctor at Kyros Clinic for hormonal health conditions.',
      totalTime: 'PT48H',
      estimatedCost: {
        '@type': 'MonetaryAmount',
        currency: 'INR',
        value: '600',
      },
      step: [
        {
          '@type': 'HowToStep',
          position: 1,
          name: 'Choose your condition',
          text: 'Select the clinical vertical closest to your symptoms. A care coordinator reviews your intake.',
        },
        {
          '@type': 'HowToStep',
          position: 2,
          name: 'Complete a short intake',
          text: 'Answer 4–6 questions about your symptoms and history. Your doctor reads this before the call.',
        },
        {
          '@type': 'HowToStep',
          position: 3,
          name: 'Book and pay',
          text: 'Choose a time that suits you. Pay ₹400–600 via UPI, card, or wallet. Cancel up to 2 hours before for a full refund.',
        },
        {
          '@type': 'HowToStep',
          position: 4,
          name: 'Consult with your doctor',
          text: 'A 20-minute video consultation with a specialist. No waiting room, no commute.',
        },
        {
          '@type': 'HowToStep',
          position: 5,
          name: 'Receive a plan',
          text: 'After the consultation: a prescription if indicated, lab orders, follow-up date, and a written note from your doctor within 24 hours.',
        },
        {
          '@type': 'HowToStep',
          position: 6,
          name: 'Follow up and adjust',
          text: 'Your health data, labs, and doctor notes accumulate in one place. Your doctor adjusts the plan at every follow-up.',
        },
      ],
    },
  ],
};

const STEPS = [
  {
    n: 1,
    title: 'Choose your condition.',
    body: 'Select the clinical vertical closest to your symptoms — thyroid, PCOS, weight management, skin and hair, sexual and intimate health, hormones and TRT, diabetes, or longevity. If you are unsure, our care team will guide you.',
  },
  {
    n: 2,
    title: 'Complete a short intake.',
    body: 'You answer 4–6 questions about your symptoms, history, and what you\'d like to discuss. Your doctor reads this before the call — so the consultation starts from your context, not from scratch.',
  },
  {
    n: 3,
    title: 'Book a time that suits you.',
    body: 'Choose from available slots across our specialist panel. Consultations are 20 minutes, video-based, available morning through evening. Pay ₹400–600 by UPI, card, or wallet.',
  },
  {
    n: 4,
    title: 'Consult with your doctor.',
    body: 'A private video consultation with a specialist who has reviewed your intake. No waiting room. No "the doctor will be with you shortly" for 45 minutes.',
  },
  {
    n: 5,
    title: 'Receive a plan.',
    body: 'Within 24 hours of your consultation: a written note from your doctor, a prescription if clinically indicated, lab orders if needed, and a follow-up date.',
  },
  {
    n: 6,
    title: 'Track, adjust, continue.',
    body: 'Your labs, prescriptions, biomarker trends, and doctor notes accumulate in one place. At every follow-up, your doctor adjusts the plan based on what the data says. This is not a single transaction — it is continuous care.',
  },
];

export default function HowItWorksPage() {
  return (
    <>
      <JsonLD data={schema} />

      {/* Hero */}
      <section className="bg-ivory py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <h1 className="font-display text-h1 font-medium text-forest mb-4">
            How Kyros Clinic works
          </h1>
          <p className="font-body text-body-lg text-ink max-w-2xl leading-relaxed">
            From your first question to a plan you follow for months. Kyros is designed for
            the patient who wants a doctor, not a product.
          </p>
        </div>
      </section>

      {/* Steps */}
      <section className="bg-white py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <ol className="space-y-14" role="list">
            {STEPS.map((step) => (
              <li key={step.n} className="flex gap-8">
                <div
                  className="flex-shrink-0 w-12 h-12 rounded-full bg-saffron flex items-center justify-center"
                  aria-hidden="true"
                >
                  <span className="font-display text-h2 font-medium text-forest">{step.n}</span>
                </div>
                <div className="pt-2">
                  <h2 className="font-display text-h2 font-medium text-forest mb-3">
                    {step.title}
                  </h2>
                  <p className="font-body text-body-lg text-ink leading-relaxed">{step.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Pull quote */}
      <section className="bg-peach-mist py-12 px-6">
        <div className="max-w-3xl mx-auto">
          <PullQuote accent="terracotta">
            "This is not a single transaction — it is continuous care."
          </PullQuote>
        </div>
      </section>

      {/* What to expect */}
      <section className="bg-ivory py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="font-display text-h2 font-medium text-forest mb-8">
            What to expect at each stage
          </h2>
          <div className="space-y-6">
            {[
              { stage: 'Before your consultation', items: ['Your intake is read by your doctor', 'You receive a reminder 1 hour before', 'Your pre-consultation notes are waiting for you to add context'] },
              { stage: 'During your consultation', items: ['20 minutes with a specialist who knows your intake', 'Video-based, from anywhere in India', 'No condition names in any notification'] },
              { stage: 'After your consultation', items: ['Written doctor\'s note within 24 hours', 'Prescription delivered digitally if prescribed', 'Lab orders with guidance on where to test', 'Follow-up scheduled, not suggested'] },
            ].map(({ stage, items }) => (
              <div key={stage} className="bg-white rounded-card p-7">
                <h3 className="font-display text-h3 font-medium text-forest mb-4">{stage}</h3>
                <ul className="space-y-2" role="list">
                  {items.map((item) => (
                    <li key={item} className="flex gap-3 items-start">
                      <span className="w-2 h-2 rounded-full bg-saffron flex-shrink-0 mt-2" aria-hidden="true" />
                      <p className="font-body text-body text-ink">{item}</p>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      <CTASection
        headline="Ready to begin?"
        subline="Choose your condition and request a consultation. A coordinator will reach out within 4 hours."
        primaryCta={{ label: 'Talk to a doctor', href: '/book' }}
        secondaryCta={{ label: 'See pricing', href: '/pricing' }}
        variant="forest"
      />
    </>
  );
}
