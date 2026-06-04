import type { Metadata } from 'next';
import { JsonLD } from '../../components/schema/JsonLD';
import { CTASection } from '../../components/marketing/CTASection';

export const metadata: Metadata = {
  title: 'Frequently Asked Questions',
  description:
    'Common questions about Kyros Clinic: how consultations work, pricing, privacy, data rights, prescriptions, and more.',
  alternates: { canonical: 'https://kyros.clinic/faq' },
  openGraph: {
    title: 'FAQ — Kyros Clinic',
    url: 'https://kyros.clinic/faq',
  },
};

const FAQS = [
  {
    category: 'Consultations',
    items: [
      {
        q: 'How does a Kyros consultation work?',
        a: 'You choose a condition, complete a short intake, book a time, and consult with a specialist doctor over video. The doctor reads your intake before the call. After the consultation, you receive a written note, prescription if indicated, and lab orders within 24 hours.',
      },
      {
        q: 'How long is a consultation?',
        a: 'Initial consultations are 20 minutes. Follow-up consultations are also 20 minutes. If a complex consultation requires more time, your doctor will let you know and reschedule where needed.',
      },
      {
        q: 'Can I choose my doctor?',
        a: 'Yes. You can request a specific doctor or accept the next available specialist in your vertical. The same doctor will be assigned to your follow-up consultations unless you request a change.',
      },
      {
        q: 'What happens if my doctor cancels?',
        a: 'If a doctor cancels, you are immediately rebooked with the same or equivalent doctor at the next available slot. If Kyros initiates the cancellation, you receive a full refund regardless of the timing.',
      },
    ],
  },
  {
    category: 'Pricing and payment',
    items: [
      {
        q: 'What does a consultation cost?',
        a: 'Initial consultations are ₹600. Follow-up consultations are ₹400–₹500. There are no hidden platform fees.',
      },
      {
        q: 'What payment methods are accepted?',
        a: 'UPI (GPay, PhonePe, Paytm), debit and credit cards, and major wallets. Payment is collected at the time of booking.',
      },
      {
        q: 'What is the refund policy?',
        a: 'Cancel up to 2 hours before your consultation for a full refund. Cancellations within 2 hours are not refunded unless initiated by the clinic. Refunds are processed within 5–7 business days to the original payment method.',
      },
    ],
  },
  {
    category: 'Privacy and data',
    items: [
      {
        q: 'Will my family or employer find out what condition I am consulting for?',
        a: 'No. Kyros uses generic notification language ("Your consultation is confirmed") and never includes condition names in any push notification, SMS, or WhatsApp message. You can also set an app passcode for device-level privacy.',
      },
      {
        q: 'Where is my health data stored?',
        a: 'All health data is stored on servers in Mumbai, India (AWS ap-south-1 region). No data is transferred outside India. Kyros operates under India\'s Digital Personal Data Protection Act.',
      },
      {
        q: 'Can I export or delete my data?',
        a: 'Yes. You can request a full export of your data or request account deletion from the app at any time. Data deletion requests are processed within 30 days. See our Data Deletion page for details.',
      },
      {
        q: 'Does Kyros share my data with third parties?',
        a: 'No data is shared with third parties without your explicit consent. Kyros does not sell patient data. Lab partners and payment processors receive only the minimum information required to provide their service.',
      },
    ],
  },
  {
    category: 'Prescriptions and labs',
    items: [
      {
        q: 'Can Kyros doctors prescribe medications?',
        a: 'Yes. Kyros doctors are licensed under the Medical Practitioners Act and can issue prescriptions valid across India. Prescription medications are prescribed only after clinical evaluation — Kyros does not fill prescription requests without a consultation.',
      },
      {
        q: 'Where do I get my lab tests done?',
        a: 'Your Kyros doctor orders lab tests and you get them done at a lab of your choice — Dr Lal PathLabs, Thyrocare, Redcliffe, Metropolis, Apollo Diagnostics, or a local lab. You upload the report to the Kyros app and your doctor reviews it.',
      },
      {
        q: 'Are prescriptions available online?',
        a: 'Yes. Prescriptions are generated digitally and available in the Kyros app within minutes of being issued. You can download them as PDF or share directly with a pharmacy.',
      },
    ],
  },
  {
    category: 'Platform and technology',
    items: [
      {
        q: 'Is Kyros a Jio Health, Practo, or Apollo 24|7 competitor?',
        a: 'Kyros is a specialist telemedicine clinic for chronic hormonal conditions, not a general OPD platform. The key difference is continuity: one doctor who manages your condition over months and years, with labs and prescriptions in a single record.',
      },
      {
        q: 'Does Kyros use AI to diagnose?',
        a: 'No. Kyros doctors make all clinical decisions. The platform uses AI internally for document processing (lab report OCR) and scheduling, but no AI system diagnoses, prescribes, or makes clinical recommendations visible to patients.',
      },
    ],
  },
];

const schema = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: FAQS.flatMap((cat) =>
    cat.items.map((faq) => ({
      '@type': 'Question',
      name: faq.q,
      acceptedAnswer: {
        '@type': 'Answer',
        text: faq.a,
      },
    }))
  ),
};

export default function FAQPage() {
  return (
    <>
      <JsonLD data={schema} />

      {/* Hero */}
      <section className="bg-ivory py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <h1 className="font-display text-h1 font-medium text-forest mb-4">
            Frequently asked questions
          </h1>
          <p className="font-body text-body-lg text-stone max-w-2xl leading-relaxed">
            Questions about how Kyros works, pricing, privacy, and more. If your question
            isn't here,{' '}
            <a href="/contact" className="text-forest underline">
              contact us
            </a>
            .
          </p>
        </div>
      </section>

      {/* FAQ sections */}
      <section className="bg-white py-16 px-6">
        <div className="max-w-3xl mx-auto space-y-16">
          {FAQS.map((category) => (
            <div key={category.category}>
              <h2 className="font-display text-h2 font-medium text-forest mb-8">
                {category.category}
              </h2>
              <div className="space-y-6">
                {category.items.map((faq) => (
                  <div key={faq.q} className="bg-ivory rounded-card p-7">
                    <h3 className="font-display text-h3 font-medium text-forest mb-3">
                      {faq.q}
                    </h3>
                    <p className="font-body text-body text-ink leading-relaxed">{faq.a}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <CTASection
        headline="Still have questions?"
        subline="Our care team is available from 9 AM to 9 PM, Monday to Saturday."
        primaryCta={{ label: 'Contact us', href: '/contact' }}
        secondaryCta={{ label: 'Book a consultation', href: '/book' }}
        variant="ivory"
      />
    </>
  );
}
