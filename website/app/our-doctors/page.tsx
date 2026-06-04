import type { Metadata } from 'next';
import { JsonLD } from '../../components/schema/JsonLD';
import { HonestPlaceholder } from '../../components/marketing/HonestPlaceholder';
import { CTASection } from '../../components/marketing/CTASection';

export const metadata: Metadata = {
  title: 'Our Doctors',
  description:
    'Kyros Clinic doctors — NMC-registered specialists in thyroid, PCOS, weight management, hormones, skin & hair, and longevity. Being introduced as they join the panel.',
  alternates: { canonical: 'https://kyros.clinic/our-doctors' },
};

const schema = {
  '@context': 'https://schema.org',
  '@type': 'MedicalWebPage',
  name: 'Our Doctors — Kyros Clinic',
  url: 'https://kyros.clinic/our-doctors',
  description:
    'NMC-registered specialist doctors at Kyros Clinic, covering thyroid, PCOS, weight management, hormones, skin & hair, and longevity.',
};

export default function OurDoctorsPage() {
  return (
    <>
      <JsonLD data={schema} />

      {/* Hero */}
      <section className="bg-ivory py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <h1 className="font-display text-h1 font-medium text-forest mb-4">Our doctors</h1>
          <p className="font-body text-body-lg text-ink max-w-2xl leading-relaxed">
            Kyros doctors are NMC-registered specialists. Every doctor listed here has been
            verified by registration number, interviewed in person, and agreed to the Kyros
            clinical standard.
          </p>
        </div>
      </section>

      {/* Standards */}
      <section className="bg-peach-mist py-16 px-6">
        <div className="max-w-7xl mx-auto">
          <h2 className="font-display text-h2 font-medium text-forest mb-8">
            What every Kyros doctor commits to
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            {[
              { title: 'NMC verification', body: 'Registration number verified against the National Medical Commission registry before onboarding.' },
              { title: 'Specialty match', body: 'Doctors treat only the conditions within their verified specialty. No generalists treating specialist conditions.' },
              { title: 'Written notes', body: 'A written clinical note within 24 hours of every consultation. Patients and doctors see the same note.' },
              { title: 'Continuity of care', body: 'Your doctor stays with you across follow-ups. No unexplained substitutions without direct communication to you.' },
            ].map((item) => (
              <div key={item.title} className="bg-ivory rounded-card p-6">
                <h3 className="font-display text-h3 font-medium text-forest mb-2">{item.title}</h3>
                <p className="font-body text-body text-ink">{item.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Honest placeholder */}
      <HonestPlaceholder type="doctor" count={3} />

      {/* For aspiring doctors */}
      <section className="bg-white py-16 px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="font-display text-h2 font-medium text-forest mb-4">
            Are you a specialist?
          </h2>
          <p className="font-body text-body text-ink mb-6 leading-relaxed">
            Kyros is looking for NMC-registered specialists in endocrinology, dermatology,
            urology, and internal medicine who want to build a longitudinal patient panel —
            not a high-volume click-and-prescribe model.
          </p>
          <a
            href="/for-doctors"
            className="inline-flex items-center justify-center px-6 py-3 rounded-button
                       bg-forest text-ivory font-body font-medium text-body-lg
                       hover:bg-jade transition-colors duration-micro"
          >
            Join the panel
          </a>
        </div>
      </section>

      <CTASection
        headline="Ready to consult a Kyros doctor?"
        subline="We'll match you with the right specialist for your condition."
        primaryCta={{ label: 'Book a consultation', href: '/book' }}
        variant="forest"
      />
    </>
  );
}
