import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Privacy Notice',
  description: 'Kyros Clinic DPDP-compliant privacy notice. How we collect, use, store, and protect your personal and health data.',
  alternates: { canonical: 'https://kyrosclinic.com/legal/privacy' },
};

const LAST_UPDATED = '2 June 2026';

export default function PrivacyPage() {
  return (
    <article className="bg-ivory py-16 px-6">
      <div className="max-w-3xl mx-auto">
        <p className="font-body text-caption text-stone uppercase tracking-widest mb-4">
          Legal · Privacy
        </p>
        <h1 className="font-display text-h1 font-medium text-forest mb-3">Privacy Notice</h1>
        <p className="font-body text-caption text-stone mb-10">
          Last updated: {LAST_UPDATED} · Version 1.0
        </p>

        <div className="bg-white rounded-card p-8 space-y-10 font-body text-body text-ink leading-relaxed">

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">1. Who we are</h2>
            <p>
              Kyros Health Technologies Pvt. Ltd. ("Kyros", "we", "us", "our") operates Kyros
              Clinic, a telemedicine platform accessible at kyrosclinic.com and through the Kyros
              mobile application. We are a Data Fiduciary under the Digital Personal Data
              Protection Act, 2023 (DPDP Act).
            </p>
            <p className="mt-3">
              Data Protection Officer: <a href="mailto:dpo@kyrosclinic.com" className="text-forest underline">dpo@kyrosclinic.com</a>
            </p>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">2. Data we collect</h2>
            <div className="space-y-4">
              <div>
                <h3 className="font-display text-h3 font-medium text-forest mb-2">Identity data</h3>
                <p>Name, phone number, email address, date of birth, gender, city, and state.</p>
              </div>
              <div>
                <h3 className="font-display text-h3 font-medium text-forest mb-2">Health data</h3>
                <p>
                  Medical history, symptoms, consultation notes, prescriptions, laboratory
                  results, and any health information you voluntarily share with your doctor.
                  Health data is sensitive personal data under the DPDP Act and is processed
                  only with your explicit consent.
                </p>
              </div>
              <div>
                <h3 className="font-display text-h3 font-medium text-forest mb-2">
                  Device and usage data
                </h3>
                <p>
                  IP address, device type, browser, approximate location (city-level), and
                  app usage logs. This data is used for security, fraud prevention, and service
                  improvement.
                </p>
              </div>
              <div>
                <h3 className="font-display text-h3 font-medium text-forest mb-2">Payment data</h3>
                <p>
                  Payment method details processed by Razorpay. Kyros does not store card
                  numbers or CVV codes.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">
              3. How we use your data
            </h2>
            <ul className="space-y-2 list-disc pl-5">
              <li>To provide telemedicine consultations and clinical care.</li>
              <li>To generate and store prescriptions, lab orders, and consultation notes.</li>
              <li>To send appointment reminders and care-related communications.</li>
              <li>To comply with legal obligations under the Telemedicine Practice Guidelines (2020) and DPDP Act (2023).</li>
              <li>To improve the platform and doctor-patient experience.</li>
              <li>To detect and prevent fraud and security incidents.</li>
            </ul>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">4. Data residency</h2>
            <p>
              All personal data and health data is stored in the AWS ap-south-1 (Mumbai, India)
              region. No data is transferred outside India. Third-party services used by Kyros
              (payment processing, video consultations, SMS) operate under India data residency
              agreements.
            </p>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">5. Data sharing</h2>
            <p>We share your data only as follows:</p>
            <ul className="space-y-2 list-disc pl-5 mt-3">
              <li><strong>With your doctor:</strong> your health data is shared with the doctor assigned to your consultation.</li>
              <li><strong>With Razorpay:</strong> payment data necessary to process transactions.</li>
              <li><strong>With MSG91:</strong> your phone number to deliver OTP verification and appointment reminders.</li>
              <li><strong>With Google Document AI:</strong> uploaded lab reports for OCR processing. Processed in Asia South 1 (Mumbai) region.</li>
              <li><strong>With authorities:</strong> when required by law, court order, or regulatory requirement.</li>
            </ul>
            <p className="mt-3">We do not sell patient data. We do not share data with advertisers.</p>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">6. Your rights (DPDP Act §11–14)</h2>
            <ul className="space-y-3 list-disc pl-5">
              <li><strong>Access:</strong> request a copy of all personal data we hold about you.</li>
              <li><strong>Correction:</strong> request correction of inaccurate personal data.</li>
              <li><strong>Erasure:</strong> request deletion of your account and associated data (subject to legal retention requirements).</li>
              <li><strong>Grievance:</strong> raise a complaint with our Data Protection Officer.</li>
            </ul>
            <p className="mt-4">
              To exercise these rights:{' '}
              <a href="/legal/data-deletion" className="text-forest underline">
                see our data deletion process
              </a>{' '}
              or email{' '}
              <a href="mailto:dpo@kyrosclinic.com" className="text-forest underline">
                dpo@kyrosclinic.com
              </a>
              .
            </p>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">7. Data retention</h2>
            <p>
              Medical records are retained for a minimum of 7 years as required under Indian
              healthcare law. Account data is retained for the duration of your account plus 3
              years. Payment records are retained for 7 years as required under the Companies
              Act.
            </p>
            <p className="mt-3">
              When you request account deletion, your account is deactivated immediately and
              permanently deleted within 30 days, subject to legal retention requirements.
            </p>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">8. Security</h2>
            <p>
              All data is encrypted in transit (TLS 1.3) and at rest (AES-256 via AWS KMS).
              Health data in S3 is encrypted with a dedicated KMS key. We conduct quarterly
              security reviews and maintain an incident response plan aligned with the 72-hour
              breach notification requirement under the DPDP Act.
            </p>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">9. Cookies</h2>
            <p>
              The Kyros website uses strictly necessary cookies for session management and
              security. We do not use third-party tracking cookies or advertising cookies.
            </p>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">10. Contact</h2>
            <p>
              Questions about this notice: <a href="mailto:dpo@kyrosclinic.com" className="text-forest underline">dpo@kyrosclinic.com</a>
              <br />
              Kyros Health Technologies Pvt. Ltd., Bengaluru, Karnataka, India
            </p>
          </section>

        </div>
      </div>
    </article>
  );
}
