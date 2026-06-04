import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Data Deletion',
  description: 'How to request deletion of your data from Kyros Clinic under the Digital Personal Data Protection Act (DPDP) 2023.',
  alternates: { canonical: 'https://kyrosclinic.com/legal/data-deletion' },
};

const LAST_UPDATED = '2 June 2026';

export default function DataDeletionPage() {
  return (
    <article className="bg-ivory py-16 px-6">
      <div className="max-w-3xl mx-auto">
        <p className="font-body text-caption text-stone uppercase tracking-widest mb-4">
          Legal · Data Rights
        </p>
        <h1 className="font-display text-h1 font-medium text-forest mb-3">
          Data Deletion and Your Rights
        </h1>
        <p className="font-body text-caption text-stone mb-10">
          Last updated: {LAST_UPDATED} · Under the Digital Personal Data Protection Act 2023
        </p>

        <div className="bg-white rounded-card p-8 space-y-10 font-body text-body text-ink leading-relaxed">

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">Your rights under DPDP</h2>
            <p>
              The Digital Personal Data Protection Act, 2023 (DPDP Act) gives you the following
              rights over your personal data held by Kyros Clinic:
            </p>
            <ul className="space-y-3 list-disc pl-5 mt-4">
              <li>
                <strong>Right to access:</strong> request a complete copy of all personal data
                we hold about you.
              </li>
              <li>
                <strong>Right to correction:</strong> request correction of inaccurate or
                outdated personal data.
              </li>
              <li>
                <strong>Right to erasure:</strong> request deletion of your account and personal
                data, subject to legal retention requirements.
              </li>
              <li>
                <strong>Right to grievance redressal:</strong> raise a complaint with our Data
                Protection Officer.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">
              How to request data deletion
            </h2>
            <div className="space-y-6">
              <div className="bg-ivory rounded-card p-6">
                <h3 className="font-display text-h3 font-medium text-forest mb-3">Option 1: From the Kyros app</h3>
                <ol className="space-y-2 list-decimal pl-5">
                  <li>Open the Kyros app and go to Profile.</li>
                  <li>Tap Privacy &amp; Data.</li>
                  <li>Tap "Delete my account and data".</li>
                  <li>Confirm with your OTP.</li>
                </ol>
                <p className="mt-3 text-stone">
                  Your account will be deactivated immediately. Data deletion completes within 30
                  days.
                </p>
              </div>

              <div className="bg-ivory rounded-card p-6">
                <h3 className="font-display text-h3 font-medium text-forest mb-3">
                  Option 2: By email
                </h3>
                <p>
                  Email{' '}
                  <a href="mailto:dpo@kyrosclinic.com" className="text-forest underline">
                    dpo@kyrosclinic.com
                  </a>{' '}
                  from the email address registered on your account, with the subject line
                  "Data deletion request".
                </p>
                <p className="mt-3 text-stone">
                  We will verify your identity and confirm receipt within 3 business days.
                  Deletion completes within 30 days of verification.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">What is deleted</h2>
            <ul className="space-y-2 list-disc pl-5">
              <li>Your account and login credentials.</li>
              <li>Profile information (name, contact details, date of birth).</li>
              <li>Health profile (conditions, allergies, medications).</li>
              <li>Consultation history, notes, prescriptions, and lab reports stored on Kyros.</li>
              <li>Uploaded files (lab reports, documents) stored in Kyros's S3 storage.</li>
              <li>Notification preferences and app settings.</li>
            </ul>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">
              What is retained after deletion
            </h2>
            <p>
              The following data is retained after account deletion for the legally required
              retention periods:
            </p>
            <ul className="space-y-2 list-disc pl-5 mt-3">
              <li>
                <strong>Medical records:</strong> retained for 7 years under Indian healthcare
                law. Retained in anonymised form where possible.
              </li>
              <li>
                <strong>Payment records:</strong> retained for 7 years as required under the
                Companies Act and GST law.
              </li>
              <li>
                <strong>Consent records:</strong> retained for the duration of the legal
                retention requirement to demonstrate regulatory compliance.
              </li>
              <li>
                <strong>Audit logs:</strong> retained for 3 years for security and fraud
                prevention purposes.
              </li>
            </ul>
            <p className="mt-4">
              Where data must be retained by law, it is retained in anonymised form where
              possible and is not used for any purpose other than the legally required one.
            </p>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">
              Data access and correction requests
            </h2>
            <p>
              To request a copy of your data or to correct inaccurate data, email{' '}
              <a href="mailto:dpo@kyrosclinic.com" className="text-forest underline">
                dpo@kyrosclinic.com
              </a>{' '}
              with the subject line "Data access request" or "Data correction request". We
              will respond within 7 business days.
            </p>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">Grievance redressal</h2>
            <p>
              If you believe your rights under the DPDP Act have not been honoured, you may:
            </p>
            <ol className="space-y-2 list-decimal pl-5 mt-3">
              <li>
                First, contact our DPO at{' '}
                <a href="mailto:dpo@kyrosclinic.com" className="text-forest underline">
                  dpo@kyrosclinic.com
                </a>
                .
              </li>
              <li>
                If not resolved within 30 days, you may escalate to the Data Protection Board
                of India at{' '}
                <a
                  href="https://dpb.gov.in"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-forest underline"
                >
                  dpb.gov.in
                </a>
                .
              </li>
            </ol>
          </section>

        </div>
      </div>
    </article>
  );
}
