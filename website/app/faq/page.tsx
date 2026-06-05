import type { Metadata } from 'next';
import FaqClient from './FaqClient';
import { FAQ_DATA } from '../../lib/faq-data';
import { JsonLD } from '../../components/schema/JsonLD';

export const metadata: Metadata = {
  title: 'Frequently Asked Questions | Kyros Clinic',
  description:
      'Questions about consultations, specialists, privacy, prescriptions, pricing, and how Kyros Clinic works.',
  alternates: {
    canonical: 'https://kyrosclinic.com/faq',
  },
  openGraph: {
    title: 'FAQ | Kyros Clinic',
    description:
        'Questions about consultations, specialists, privacy, prescriptions, pricing, and how Kyros Clinic works.',
    url: 'https://kyrosclinic.com/faq',
    images: [{ url: '/treatments/HeroDashboard.png', width: 1200, height: 630, alt: 'Kyros Clinic FAQ' }],
  },
  twitter: {
    card: 'summary_large_image',
    images: ['/treatments/HeroDashboard.png'],
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
      <JsonLD data={schema} />
      <FaqClient />
    </>
  );
}