import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Terms of Use',
  description: 'Kyros Clinic terms of use. Governing conditions for the use of the Kyros telemedicine platform.',
  alternates: { canonical: 'https://kyros.clinic/legal/terms' },
};

const LAST_UPDATED = '2 June 2026';

export default function TermsPage() {
  return (
    <article className="bg-ivory py-16 px-6">
      <div className="max-w-3xl mx-auto">
        <p className="font-body text-caption text-stone uppercase tracking-widest mb-4">
          Legal · Terms
        </p>
        <h1 className="font-display text-h1 font-medium text-forest mb-3">Terms of Use</h1>
        <p className="font-body text-caption text-stone mb-10">
          Last updated: {LAST_UPDATED} · Version 1.0
        </p>

        <div className="bg-white rounded-card p-8 space-y-10 font-body text-body text-ink leading-relaxed">

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">1. Agreement</h2>
            <p>
              By using the Kyros Clinic platform ("Platform"), you agree to these Terms of Use.
              If you do not agree, do not use the Platform. These terms are governed by the laws
              of India.
            </p>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">2. The service</h2>
            <p>
              Kyros Clinic is a telemedicine platform that connects patients with licensed
              doctors for video consultations. Kyros is not a hospital, not an emergency care
              service, and not a substitute for in-person care where in-person care is clinically
              indicated.
            </p>
            <p className="mt-3">
              If you are experiencing a medical emergency, call 112 or go to the nearest
              hospital.
            </p>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">3. Eligibility</h2>
            <ul className="space-y-2 list-disc pl-5">
              <li>You must be 18 years or older to register and use the Platform independently.</li>
              <li>Minors may use the Platform only with the consent and supervision of a parent or legal guardian.</li>
              <li>You must provide accurate information at registration and keep it up to date.</li>
            </ul>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">
              4. Medical consultations
            </h2>
            <p>
              Consultations on Kyros are conducted by licensed doctors registered under the
              National Medical Commission. Doctors practise independently and are responsible for
              their own clinical judgement.
            </p>
            <p className="mt-3">
              Kyros does not guarantee clinical outcomes. Medical decisions are made by your
              assigned doctor based on the information you provide. You are responsible for the
              accuracy of health information you share.
            </p>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">
              5. Payments and refunds
            </h2>
            <p>
              Consultation fees are charged at the time of booking. Cancel up to 2 hours before
              your scheduled consultation for a full refund. Cancellations within 2 hours are
              not refunded unless the cancellation is initiated by Kyros.
            </p>
            <p className="mt-3">
              Refunds are processed within 5–7 business days to the original payment method.
            </p>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">
              6. Prohibited use
            </h2>
            <ul className="space-y-2 list-disc pl-5">
              <li>Using the Platform to request prescriptions without a genuine consultation.</li>
              <li>Sharing your account with another person.</li>
              <li>Providing false information to obtain a prescription.</li>
              <li>Recording consultations without the doctor's consent.</li>
              <li>Using the Platform for any purpose other than medical consultation.</li>
            </ul>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">
              7. Limitation of liability
            </h2>
            <p>
              To the maximum extent permitted by law, Kyros's liability is limited to the amount
              paid for the specific consultation in question. Kyros is not liable for indirect,
              consequential, or incidental damages.
            </p>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">
              8. Changes to terms
            </h2>
            <p>
              We may update these terms from time to time. Material changes will be communicated
              to you via email or in-app notification at least 30 days before they take effect.
              Continued use of the Platform after that date constitutes acceptance of the updated
              terms.
            </p>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">9. Governing law</h2>
            <p>
              These terms are governed by the laws of India. Disputes shall be subject to the
              exclusive jurisdiction of the courts of Bengaluru, Karnataka.
            </p>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">10. Contact</h2>
            <p>
              Legal enquiries: <a href="mailto:legal@kyros.clinic" className="text-forest underline">legal@kyros.clinic</a>
            </p>
          </section>

        </div>
      </div>
    </article>
  );
}
