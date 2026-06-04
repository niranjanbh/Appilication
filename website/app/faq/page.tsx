import type { Metadata } from 'next';
import FaqClient from './FaqClient';
import { FAQ_DATA } from '../../lib/faq-data';

export const metadata: Metadata = {
  title: 'Frequently Asked Questions | Kyros Clinic',
  description:
      'Questions about consultations, specialists, privacy, prescriptions, pricing, and how Kyros Clinic works.',
  alternates: {
    canonical: 'https://kyros.clinic/faq',
  },
  openGraph: {
    title: 'FAQ | Kyros Clinic',
    description:
        'Questions about consultations, specialists, privacy, prescriptions, pricing, and how Kyros Clinic works.',
    url: 'https://kyros.clinic/faq',
  },
};

const schema = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: FAQ_DATA.flatMap((section) =>
      section.items.map((faq) => ({
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
        <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{
              __html: JSON.stringify(schema),
            }}
        />

        <FaqClient />
      </>
  );
}