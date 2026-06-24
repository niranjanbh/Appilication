import type { Metadata } from 'next';
import Link from 'next/link';
import Image from 'next/image';
import { CONDITIONS } from '../lib/conditions';
import { ORG, ORG_ID, BIZ_ID } from '../lib/organization';
import { JsonLD } from '../components/schema/JsonLD';
import { PullQuote } from '../components/ui/PullQuote';
import { FadeIn } from '../components/ui/FadeIn';
import { FilterableConditions } from '../components/marketing/FilterableConditions';
import { PillarBlock } from '../components/marketing/PillarBlock';
import { StatBlock } from '../components/marketing/StatBlock';
import { CTASection } from '../components/marketing/CTASection';
import { DashboardSection } from '../components/dashboard/DashboardSection';
import { HomeFAQ } from '../components/marketing/HomeFAQ';

export const metadata: Metadata = {
  title: 'Kyros Clinic | Doctor-first care for hormonal, metabolic, and preventive health.',
  description:
    'Consult specialist doctors for thyroid, PCOS, weight management, skin & hair, sexual health, hormones, diabetes, and longevity. Track labs, follow a plan, stay with one doctor.',
  alternates: { canonical: 'https://kyrosclinic.com' },
  openGraph: {
    title: 'Kyros Clinic | Doctor-first care for hormonal, metabolic, and preventive health.',
    description:
      'India-first telemedicine clinic. One doctor. One place. A platform where privacy is the point.',
    url: 'https://kyrosclinic.com',
    images: [{ url: '/treatments/HeroDashboard.png', width: 1200, height: 630, alt: 'Kyros Clinic telehealth dashboard' }],
  },
};

const HOME_FAQS = [
  {
    q: 'How is Kyros different from other Indian telemedicine platforms?',
    a: 'Most Indian telemedicine platforms connect you to any available doctor for a single visit. Kyros assigns you to one specialist who stays with you — reading your labs, adjusting your plan, and building a clinical record over time.',
  },
  {
    q: 'How long does it take from filling the form to seeing a doctor?',
    a: 'The intake form takes 5–10 minutes. Same-day and next-day slots are typically available. Most patients see their doctor within 24–48 hours of booking.',
  },
  {
    q: 'Do I have to know which specialist I need before signing up?',
    a: 'No. Choose the condition closest to your concern. If you are unsure, a care coordinator can help match you to the right specialist before your consultation.',
  },
  {
    q: 'Is my health data private?',
    a: "Yes. Kyros operates under India's Digital Personal Data Protection Act. Your health data stays on servers in India, condition names never appear in notifications, and you can export or delete your data at any time.",
  },
  {
    q: 'Can my parents, partner, or child use my Kyros account?',
    a: 'No. Every adult must have their own individual account to ensure clinical safety and data privacy.',
  },
];

const schema = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'MedicalBusiness',
      '@id': BIZ_ID,
      name: ORG.name,
      url: ORG.url,
      logo: ORG.logoUrl,
      image: ORG.ogImage,
      priceRange: '₹400–₹600',
      currenciesAccepted: 'INR',
      paymentAccepted: 'UPI, Credit Card, Debit Card, Wallet',
      address: {
        '@type': 'PostalAddress',
        addressLocality: ORG.address.locality,
        addressRegion: ORG.address.region,
        addressCountry: ORG.address.country,
      },
      geo: {
        '@type': 'GeoCoordinates',
        latitude: ORG.geo.latitude,
        longitude: ORG.geo.longitude,
      },
      openingHoursSpecification: {
        '@type': 'OpeningHoursSpecification',
        dayOfWeek: [...ORG.hours.days],
        opens: ORG.hours.opens,
        closes: ORG.hours.closes,
      },
      contactPoint: {
        '@type': 'ContactPoint',
        contactType: 'customer support',
        email: ORG.email,
        availableLanguage: [...ORG.languages],
      },
      isAcceptingNewPatients: true,
      medicalSpecialty: [
        'Endocrinology',
        'Dermatology',
        'Urology',
        'Preventive Medicine',
      ],
      availableService: CONDITIONS.map((c) => ({
        '@type': 'MedicalTherapy',
        name: c.name,
        url: `https://kyrosclinic.com/conditions/${c.slug}`,
      })),
      sameAs: [...ORG.sameAs],
      parentOrganization: { '@id': ORG_ID },
    },
    {
      '@type': 'FAQPage',
      '@id': 'https://kyrosclinic.com/#faq',
      mainEntity: HOME_FAQS.map((faq) => ({
        '@type': 'Question',
        name: faq.q,
        acceptedAnswer: { '@type': 'Answer', text: faq.a },
      })),
    },
  ],
};

export default function HomePage() {
  return (
    <>
      <JsonLD data={schema} />

      {/* 1. Hero */}
      <section className="bg-ivory py-14 md:py-20 px-6">
        <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-[1.2fr_1fr] gap-10 md:gap-14 items-center">
          <div>
            <p className="font-body text-caption text-stone uppercase tracking-widest mb-4">
              India-first · Doctor-first · Telemedicine
            </p>
            <h1 className="font-display text-h1 md:text-[86px]] font-medium text-forest leading-tight mb-6 max-w-[620px]">
              Whatever&apos;s been bothering you, start with a doctor.
            </h1>
            <p className="font-body text-body-lg text-ink max-w-[480px] mb-6 leading-relaxed">
              NMC-registered specialists for thyroid, weight, hormonal health, skin, and
              longevity care — from home, in your language, without the waiting room.
            </p>
            <div className="border-l-2 border-forest/30 pl-4 mb-8">
              <p className="font-display italic text-body-lg text-ink leading-relaxed">
                &ldquo;In Indian healthcare, you see a different specialist every visit. No one
                keeps your story.&rdquo;
              </p>
            </div>
            <div className="flex flex-wrap gap-4">
              <Link
                href="/book"
                className="inline-flex items-center justify-center px-7 py-3 rounded-button
                           bg-forest text-ivory font-body font-medium text-body-lg
                           hover:bg-jade transition-colors duration-micro"
              >
                Talk to a doctor
              </Link>
              <Link
                href="/how-it-works"
                className="inline-flex items-center justify-center px-7 py-3 rounded-button
                           border-2 border-forest text-forest font-body font-medium text-body-lg
                           hover:bg-forest/8 transition-colors duration-micro"
              >
                How it works
              </Link>
            </div>
          </div>
          <div className="relative w-full h-[300px] lg:h-[400px]">
            <Image
              src="/treatments/HeroDashboard.webp"
              alt="Personalised doctor consultation on Kyros telehealth platform"
              fill
              sizes="(max-width: 768px) 100vw, 50vw"
              className="object-cover rounded-card"
              priority
            />
          </div>
        </div>
      </section>

      {/* 2. Three Pillars */}
      <FadeIn>
      <PillarBlock
        pillars={[
          {
            title: 'A doctor who stays with you.',
            body:
              'Not a different doctor every visit. Not a rotation. The same specialist who knows your history, your labs, and your plan.',
          },
          {
            title: 'A place where your health lives.',
            body:
              'Lab results, prescriptions, dosage history, doctor notes — all in one place, visible to you and your doctor, accumulating over time.',
          },
          {
            title: 'A platform where privacy is the point.',
            body:
              "No condition names in notifications. No data shared without your consent. Built under India’s Digital Personal Data Protection Act.",
          },
        ]}
      />
      </FadeIn>

      {/* 3. Pull quote */}
      <FadeIn>
      <section className="bg-ivory py-12 px-6">
        <div className="max-w-3xl mx-auto">
          <PullQuote accent="terracotta">
            "The first honest conversation about your health should be with someone who
            measures, not someone who sells."
          </PullQuote>
        </div>
      </section>
      </FadeIn>

      {/* 4. Conditions — filterable by audience */}
      <FilterableConditions />

      {/* 5. Dashboard with 3D body model */}
      <DashboardSection />

      {/* 7. Process steps */}
      <FadeIn>
      <section className="bg-sage/10 py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="font-display text-h2 font-medium text-forest mb-10 text-center">
            How Kyros works
          </h2>
          <ol className="space-y-8" role="list">
            {[
              {
                n: 1,
                title: 'Choose your concern.',
                body: 'Select the condition closest to your symptoms. A care coordinator reviews your intake before matching you with the right specialist.',
              },
              {
                n: 2,
                title: 'Book a consultation.',
                body: 'Pick a time that suits you. Consultations are video-based, from anywhere in India. Initial consultations are ₹400–600.',
              },
              {
                n: 3,
                title: 'Follow a plan that adjusts.',
                body: 'Your doctor builds a plan — labs, prescriptions, follow-ups — that changes as your results change. Not a one-time visit.',
              },
            ].map((step) => (
              <li key={step.n} className="flex gap-6">
                <div
                  className="flex-shrink-0 w-10 h-10 rounded-full bg-saffron flex items-center justify-center"
                  aria-hidden="true"
                >
                  <span className="font-display text-h3 font-medium text-forest">
                    {step.n}
                  </span>
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
          <div className="mt-10 text-center">
            <Link
              href="/how-it-works"
              className="font-body text-body text-forest underline hover:text-jade transition-colors duration-micro"
            >
              Read the full how-it-works →
            </Link>
          </div>
        </div>
      </section>
      </FadeIn>

      {/* 8. Stats */}
      <FadeIn>
      <StatBlock
        stats={[
          { numeral: '₹400', caption: 'starting consultation fee', color: 'forest' },
          { numeral: '7', caption: 'clinical verticals covered', color: 'forest' },
          { numeral: '1', caption: 'doctor who stays with you', color: 'saffron' },
        ]}
      />
      </FadeIn>

      {/* 7. Trust signals */}
      <FadeIn>
      <section className="bg-white py-16 px-6">
        <div className="max-w-7xl mx-auto">
          <h2 className="font-display text-h2 font-medium text-forest mb-8 text-center">
            Built for the Indian patient
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
            {[
              {
                title: 'NMC-registered doctors only',
                body: 'Every Kyros doctor is verified against the National Medical Commission registry. You will always see your doctor\'s NMC registration number.',
              },
              {
                title: 'DPDP-aligned data privacy',
                body: 'Your health data stays in India. We operate under the Digital Personal Data Protection Act and you can export or delete your data at any time.',
              },
              {
                title: 'No condition names in notifications',
                body: 'Notifications say "Your consultation is confirmed" — not the condition you booked for. Privacy is structural, not aspirational.',
              },
              {
                title: 'Transparent pricing',
                body: 'Consultations start at ₹400. No hidden platform fees. Refund policy stated clearly before you pay.',
              },
            ].map((item) => (
              <div key={item.title} className="bg-ivory rounded-card p-7">
                <h3 className="font-display text-h3 font-medium text-forest mb-2">
                  {item.title}
                </h3>
                <p className="font-body text-body text-ink">{item.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
      </FadeIn>

      {/* FAQ */}
      <FadeIn>
        <HomeFAQ />
      </FadeIn>

      {/* 8. Reflective close */}
      <FadeIn>
      <section className="bg-ivory py-12 px-6 border-t-2 border-terracotta">
        <div className="max-w-3xl mx-auto">
          <p className="font-display text-h2 italic font-medium text-forest text-center">
            The first consultation is the beginning of a record that accumulates.
          </p>
        </div>
      </section>
      </FadeIn>

      {/* 9-10. CTA */}
      <CTASection
        headline="Begin with a doctor."
        subline="Consultations start at ₹400. No account required to request a consultation."
        primaryCta={{ label: 'Talk to a doctor', href: '/book' }}
        secondaryCta={{ label: 'How it works', href: '/how-it-works' }}
        variant="forest"
      />
    </>
  );
}
