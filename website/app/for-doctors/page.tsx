import type { Metadata } from 'next';
import { CTASection } from '../../components/marketing/CTASection';

export const metadata: Metadata = {
  title: 'For Doctors',
  description:
    'Join the Kyros Clinic specialist panel. NMC-registered endocrinologists, dermatologists, and urologists building longitudinal patient relationships in telemedicine.',
  alternates: { canonical: 'https://kyros.clinic/for-doctors' },
  openGraph: {
    title: 'For Doctors — Join Kyros Clinic',
    url: 'https://kyros.clinic/for-doctors',
  },
};

export default function ForDoctorsPage() {
  return (
    <>
      {/* Hero */}
      <section className="bg-forest py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <p className="font-body text-caption text-ivory/60 uppercase tracking-widest mb-4">
            Kyros Clinic · Doctor panel
          </p>
          <h1 className="font-display text-h1 font-medium text-ivory mb-6">
            A panel built for continuity, not volume.
          </h1>
          <p className="font-body text-body-lg text-ivory/80 max-w-2xl leading-relaxed mb-8">
            Kyros is looking for NMC-registered specialists who want to build real longitudinal
            relationships with patients — not a high-volume, low-engagement telemedicine queue.
          </p>
          <a
            href="/contact"
            className="inline-flex items-center justify-center px-7 py-3 rounded-button
                       bg-saffron text-forest font-body font-medium text-body-lg
                       hover:bg-saffron/90 transition-colors duration-micro"
          >
            Apply to join
          </a>
        </div>
      </section>

      {/* What Kyros offers doctors */}
      <section className="bg-ivory py-16 px-6">
        <div className="max-w-7xl mx-auto">
          <h2 className="font-display text-h2 font-medium text-forest mb-8">
            What Kyros offers you
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                title: 'Curated patients.',
                body: 'Patients who arrive with intake forms already completed, labs already uploaded, and a genuine commitment to following a plan. No drive-by prescriptions.',
              },
              {
                title: 'A complete clinical record.',
                body: 'Every patient\'s labs, prescriptions, dosage history, and previous consultation notes in one place before your call starts. No piecing together history from screenshots.',
              },
              {
                title: 'Longitudinal income.',
                body: 'A patient panel where follow-ups are expected and scheduled, not contingent on the patient returning independently. Predictable, repeatable income.',
              },
              {
                title: 'No administrative burden.',
                body: 'Kyros handles scheduling, payments, prescriptions, lab orders, and reminders. You consult. We handle the rest.',
              },
              {
                title: 'Your identity is yours.',
                body: 'Your NMC registration number, credentials, and clinical work are presented accurately on every artifact — consultation notes, prescriptions, education content.',
              },
              {
                title: 'Revenue share from Day 1.',
                body: 'Transparent revenue share on every consultation. No performance thresholds before you earn. Paid fortnightly.',
              },
            ].map((item) => (
              <div key={item.title} className="bg-white rounded-card p-7">
                <h3 className="font-display text-h3 font-medium text-forest mb-3">
                  {item.title}
                </h3>
                <p className="font-body text-body text-ink leading-relaxed">{item.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Specialties we're looking for */}
      <section className="bg-peach-mist py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="font-display text-h2 font-medium text-forest mb-6">
            Specialties we are building
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { specialty: 'Endocrinology', verticals: 'Thyroid, PCOS, TRT, Diabetes, Longevity' },
              { specialty: 'Dermatology', verticals: 'AGA, Adult acne, Melasma, Skin conditions' },
              { specialty: 'Urology / Andrology', verticals: "Men's intimate health, ED, TRT" },
              { specialty: 'Internal Medicine / GP', verticals: 'Weight management, Metabolic health, Longevity' },
              { specialty: 'Gynaecology', verticals: 'PCOS, hormonal health, fertility support' },
              { specialty: 'Psychiatry / Psychology', verticals: 'Hormonal mood effects, anxiety related to chronic conditions' },
            ].map(({ specialty, verticals }) => (
              <div key={specialty} className="bg-ivory rounded-card p-6">
                <p className="font-display text-h3 font-medium text-forest mb-1">{specialty}</p>
                <p className="font-body text-body text-stone">{verticals}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Requirements */}
      <section className="bg-white py-16 px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="font-display text-h2 font-medium text-forest mb-6">
            What we require
          </h2>
          <ul className="space-y-4" role="list">
            {[
              'Active NMC registration (we verify directly with NMC)',
              'MBBS minimum; MD, DM, DNB, or Fellowship strongly preferred for specialties',
              'Ability to consult in English; Hindi or a regional language is a plus',
              'Commitment to written notes within 24 hours of every consultation',
              'Availability for a minimum of 10 hours per week on the Kyros platform',
              'Alignment with evidence-based practice and Kyros clinical standards',
            ].map((req) => (
              <li key={req} className="flex gap-4 items-start">
                <span
                  className="w-2 h-2 rounded-full bg-saffron flex-shrink-0 mt-2"
                  aria-hidden="true"
                />
                <p className="font-body text-body text-ink">{req}</p>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <CTASection
        headline="Ready to join the Kyros panel?"
        subline="Send us your details and we will get back to you within 2 business days."
        primaryCta={{ label: 'Apply now', href: '/contact' }}
        variant="forest"
      />
    </>
  );
}
