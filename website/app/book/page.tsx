import type { Metadata } from 'next';
import { BookingFlow } from '../../components/marketing/BookingFlow';

export const metadata: Metadata = {
  title: 'Request a Consultation',
  description:
    'Request a Kyros Clinic consultation. Choose your condition, answer a few questions, and a care coordinator will reach out within 4 hours.',
  alternates: { canonical: 'https://kyrosclinic.com/book' },
  robots: { index: false, follow: true },
};

export default function BookPage() {
  return (
    <>
      <section className="bg-ivory py-16 px-6">
        <div className="max-w-3xl mx-auto">
          <p className="font-body text-caption text-stone uppercase tracking-widest mb-4">
            Kyros Clinic · Consultation request
          </p>
          <div className="bg-white rounded-card p-8 md:p-12 shadow-sm">
            <BookingFlow />
          </div>
        </div>
      </section>

      {/* Trust signals */}
      <section className="bg-white py-12 px-6">
        <div className="max-w-3xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { title: 'Private', body: 'No condition names in notifications.' },
              { title: 'Transparent', body: '₹600 initial consultation. No hidden fees.' },
              { title: 'Refundable', body: 'Cancel up to 2 hours before for a full refund.' },
            ].map((item) => (
              <div key={item.title} className="bg-ivory rounded-card p-5 text-center">
                <p className="font-display text-h3 font-medium text-forest mb-1">{item.title}</p>
                <p className="font-body text-body text-stone">{item.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
