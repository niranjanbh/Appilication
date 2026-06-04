import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Telemedicine Consent',
  description: 'Kyros Clinic telemedicine consent document, aligned with NMC Telemedicine Practice Guidelines 2020.',
  alternates: { canonical: 'https://kyrosclinic.com/legal/telemedicine-consent' },
};

const LAST_UPDATED = '2 June 2026';
const CONSENT_VERSION = 'v1.0';

export default function TelemedicineConsentPage() {
  return (
    <article className="bg-ivory py-16 px-6">
      <div className="max-w-3xl mx-auto">
        <p className="font-body text-caption text-stone uppercase tracking-widest mb-4">
          Legal · Consent
        </p>
        <h1 className="font-display text-h1 font-medium text-forest mb-3">
          Telemedicine Consent
        </h1>
        <p className="font-body text-caption text-stone mb-10">
          Last updated: {LAST_UPDATED} · Version {CONSENT_VERSION}
        </p>

        <div className="bg-white rounded-card p-8 space-y-10 font-body text-body text-ink leading-relaxed">

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">1. Nature of telemedicine</h2>
            <p>
              Telemedicine involves the delivery of healthcare services using electronic
              communications. A telemedicine consultation is not equivalent to an in-person
              consultation in all circumstances. Your doctor will inform you if your condition
              requires in-person examination.
            </p>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">
              2. Regulatory framework
            </h2>
            <p>
              This consent is issued in accordance with the Telemedicine Practice Guidelines
              (2020) issued jointly by the Board of Governors of the Medical Council of India
              (now the National Medical Commission) and NITI Aayog, and amended by subsequent
              NMC circulars.
            </p>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">
              3. What you are consenting to
            </h2>
            <ul className="space-y-3 list-disc pl-5">
              <li>
                <strong>Video consultation:</strong> a live video consultation with a licensed
                doctor on the Kyros platform.
              </li>
              <li>
                <strong>Data sharing with your doctor:</strong> health information you provide
                (intake responses, lab reports, medical history) will be shared with your
                assigned doctor before and during the consultation.
              </li>
              <li>
                <strong>Prescription via telemedicine:</strong> if clinically appropriate, your
                doctor may issue a prescription valid under the Drugs and Cosmetics Act.
              </li>
              <li>
                <strong>Consultation notes:</strong> your doctor will record a clinical note
                after the consultation. This note is visible to you and stored in your Kyros
                record.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">4. Limitations</h2>
            <ul className="space-y-3 list-disc pl-5">
              <li>
                Telemedicine does not allow physical examination. Diagnoses made via telemedicine
                are based solely on information provided digitally.
              </li>
              <li>
                Certain conditions require in-person examination and cannot be managed via
                telemedicine. Your doctor will refer you to in-person care when indicated.
              </li>
              <li>
                Telemedicine is not appropriate for emergency conditions. In an emergency, call
                112 or go to the nearest hospital.
              </li>
              <li>
                Prescriptions issued via telemedicine are subject to the restrictions in the
                Telemedicine Practice Guidelines. Certain Schedule H and Schedule X drugs may
                not be prescribed via telemedicine.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">
              5. Your responsibilities
            </h2>
            <ul className="space-y-2 list-disc pl-5">
              <li>Provide accurate and complete health information to your doctor.</li>
              <li>Inform your doctor of all current medications, allergies, and existing conditions.</li>
              <li>Attend your scheduled consultation on time.</li>
              <li>Follow your doctor's instructions and inform them of any adverse reactions to treatment.</li>
            </ul>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">6. Recording</h2>
            <p>
              Consultations are not recorded by default. Recording requires explicit opt-in
              consent from both the patient and the doctor before the consultation begins.
              Recorded consultations are stored encrypted in India and accessible only to the
              patient and doctor.
            </p>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">
              7. Withdrawal of consent
            </h2>
            <p>
              You may withdraw consent to telemedicine at any time before a consultation begins.
              Withdrawal of consent does not affect existing records or your right to access your
              health data.
            </p>
          </section>

          <section>
            <h2 className="font-display text-h2 font-medium text-forest mb-4">
              8. Consent version tracking
            </h2>
            <p>
              The version and hash of the consent text you accepted are stored with your account
              record as required by the Digital Personal Data Protection Act (2023).
            </p>
            <p className="mt-3">
              Version {CONSENT_VERSION} · SHA-256 hash is generated and stored at the time of
              consent capture in the Kyros system.
            </p>
          </section>

        </div>
      </div>
    </article>
  );
}
