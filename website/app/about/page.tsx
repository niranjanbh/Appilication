import type { Metadata } from 'next';
import { JsonLD } from '../../components/schema/JsonLD';
import { PullQuote } from '../../components/ui/PullQuote';
import { CTASection } from '../../components/marketing/CTASection';
import { ORG, ORG_ID } from '../../lib/organization';

export const metadata: Metadata = {
  title: 'About Kyros Clinic',
  description:
    'Kyros Clinic is a doctor-first telemedicine clinic built for India\'s hormonal health gap. Founded by Niranjan Bhimanadham.',
  alternates: { canonical: 'https://kyrosclinic.com/about' },
  openGraph: {
    title: 'About Kyros Clinic',
    description:
      "Kyros Clinic is a doctor-first telemedicine clinic built for India's hormonal health gap. Founded by Niranjan Bhimanadham.",
    url: 'https://kyrosclinic.com/about',
    images: [{ url: '/treatments/HeroDashboard.png', width: 1200, height: 630, alt: 'About Kyros Clinic' }],
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
        { '@type': 'ListItem', position: 2, name: 'About', item: 'https://kyrosclinic.com/about' },
      ],
    },
    {
      '@type': 'AboutPage',
      '@id': 'https://kyrosclinic.com/about',
      url: 'https://kyrosclinic.com/about',
      name: 'About Kyros Clinic',
      description: 'Doctor-first telemedicine clinic for hormonal health in India.',
      mainEntity: { '@id': ORG_ID },
    },
    {
      '@type': 'Person',
      '@id': 'https://kyrosclinic.com/about#founder',
      name: 'Niranjan Bhimanadham',
      jobTitle: 'Founder & CEO',
      worksFor: { '@id': ORG_ID },
      description:
        'Founder of Kyros Clinic. Building India\'s first doctor-first telemedicine clinic for hormonal health.',
    },
  ],
};

export default function AboutPage() {
  return (
    <>
      <JsonLD data={schema} />

      {/* Hero */}
      <section className="bg-ivory py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <h1 className="font-display text-h1 font-medium text-forest mb-6">About Kyros</h1>
          <p className="font-body text-body-lg text-ink max-w-2xl leading-relaxed">
            Kyros Clinic is a doctor-first telemedicine clinic built for the chronic hormonal
            health gap in India. We are at the beginning — and we are being honest about that.
          </p>
        </div>
      </section>

      {/* The problem */}
      <section className="bg-peach-mist py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="font-display text-h2 font-medium text-forest mb-6">The problem we are solving</h2>
          <div className="space-y-5 max-w-3xl">
            <p className="font-body text-body-lg text-ink leading-relaxed">
              Hormonal conditions — thyroid, PCOS, low testosterone, insulin resistance — are
              among the most prevalent chronic diseases in India. An estimated 10.95% of Indian
              adults have hypothyroidism. Roughly 1 in 5 Indian women of reproductive age has
              PCOS. Nearly half of Indian men over 40 have symptomatic low testosterone.
            </p>
            <p className="font-body text-body-lg text-ink leading-relaxed">
              These conditions are managed across months and years, not single visits. But
              India's healthcare system is built around episodic care — a GP who sees you once,
              an endocrinologist who manages your TSH without ever asking about your symptoms, a
              diagnosis but no plan.
            </p>
            <p className="font-body text-body-lg text-ink leading-relaxed">
              Kyros is built to fill the gap: a doctor who stays with you, who reads your labs,
              who adjusts your plan, and who is reachable without a 2-hour commute and a
              45-minute wait.
            </p>
          </div>
        </div>
      </section>

      {/* Pull quote */}
      <section className="bg-ivory py-12 px-6">
        <div className="max-w-3xl mx-auto">
          <PullQuote accent="terracotta">
            "A doctor who stays with you is not a luxury. It is the minimum standard of care
            for a chronic condition."
          </PullQuote>
        </div>
      </section>

      {/* Three pillars */}
      <section className="bg-white py-16 px-6">
        <div className="max-w-7xl mx-auto">
          <h2 className="font-display text-h2 font-medium text-forest mb-8 text-center">
            What we stand for
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                title: 'Doctor-first.',
                body: 'Every product decision starts with the doctor-patient relationship. The platform exists to support that relationship, not to replace it.',
              },
              {
                title: 'Privacy is structural.',
                body: 'Your health data stays in India. No condition names in notifications. You can export or delete your data at any time. Privacy is not a feature — it is how we built the system.',
              },
              {
                title: 'Honest at every stage.',
                body: 'We are a startup. Our advisory board page has placeholders. Our doctors page reflects who is actually on our panel. We will not add names to pages before they have confirmed in writing.',
              },
            ].map((item) => (
              <div key={item.title} className="bg-ivory rounded-card p-8">
                <h3 className="font-display text-h3 font-medium text-forest mb-3">
                  {item.title}
                </h3>
                <p className="font-body text-body text-ink leading-relaxed">{item.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Founder */}
      <section className="bg-ivory py-16 px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="font-display text-h2 font-medium text-forest mb-8">The founder</h2>
          <div className="bg-white rounded-card p-8">
            <div className="flex items-start gap-6">
              <div
                className="w-16 h-16 rounded-full bg-sage/20 flex-shrink-0 flex items-center justify-center"
                aria-hidden="true"
              >
                <span className="font-display text-h2 font-medium text-forest">N</span>
              </div>
              <div>
                <h3 className="font-display text-h3 font-medium text-forest mb-1">
                  Niranjan Bhimanadham
                </h3>
                <p className="font-body text-caption text-stone mb-4">Founder & CEO</p>
                <p className="font-body text-body text-ink leading-relaxed">
                  Building Kyros from the conviction that hormonal health in India deserves the
                  same clinical rigour and continuity of care that patients in other markets take
                  for granted. The product is being built in public, honestly, with doctors who
                  share this conviction.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Company info */}
      <section className="bg-peach-mist py-12 px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="font-display text-h2 font-medium text-forest mb-6">Company details</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { label: 'Legal name', value: ORG.legalName },
              { label: 'Founded', value: ORG.foundingDate },
              { label: 'Headquarters', value: `${ORG.address.locality}, ${ORG.address.region}, ${ORG.address.countryName}` },
              { label: 'Data Protection Officer', value: ORG.dpoEmail },
              { label: 'Stage', value: 'Early-stage startup' },
              { label: 'Data residency', value: 'All data in ap-south-1 (Mumbai)' },
            ].map(({ label, value }) => (
              <div key={label} className="bg-ivory rounded-card px-6 py-4">
                <p className="font-body text-caption text-stone mb-1">{label}</p>
                <p className="font-body text-body font-medium text-ink">{value}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <CTASection
        headline="Ready to begin?"
        subline="Request a consultation. A coordinator will reach out within 4 hours."
        primaryCta={{ label: 'Talk to a doctor', href: '/book' }}
        secondaryCta={{ label: 'Contact us', href: '/contact' }}
        variant="forest"
      />
    </>
  );
}
