import type { Metadata } from 'next';
import { ContactForm } from './ContactForm';
import { JsonLD } from '../../components/schema/JsonLD';
import { ORG, ORG_ID } from '../../lib/organization';

export const metadata: Metadata = {
  title: 'Contact',
  description:
    'Contact Kyros Clinic. Reach our care team for consultation enquiries, support, doctor applications, and press.',
  alternates: { canonical: 'https://kyrosclinic.com/contact' },
  openGraph: {
    title: 'Contact — Kyros Clinic',
    description: 'Reach our care team for consultation enquiries, support, doctor applications, and press.',
    url: 'https://kyrosclinic.com/contact',
    images: [{ url: '/treatments/HeroDashboard.png', width: 1200, height: 630, alt: 'Contact Kyros Clinic' }],
  },
  twitter: {
    card: 'summary_large_image',
    images: ['/treatments/HeroDashboard.png'],
  },
};

const schema = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://kyrosclinic.com' },
        { '@type': 'ListItem', position: 2, name: 'Contact', item: 'https://kyrosclinic.com/contact' },
      ],
    },
    {
      '@type': 'ContactPage',
      '@id': 'https://kyrosclinic.com/contact',
      name: 'Contact — Kyros Clinic',
      url: 'https://kyrosclinic.com/contact',
      description: 'Contact Kyros Clinic for consultation enquiries, support, doctor applications, and press.',
      mainEntity: { '@id': ORG_ID },
    },
    {
      '@type': 'Organization',
      '@id': ORG_ID,
      name: ORG.name,
      url: ORG.url,
      logo: ORG.logoUrl,
      address: {
        '@type': 'PostalAddress',
        addressLocality: ORG.address.locality,
        addressRegion: ORG.address.region,
        addressCountry: ORG.address.country,
      },
      sameAs: [...ORG.sameAs],
      contactPoint: [
        {
          '@type': 'ContactPoint',
          email: ORG.email,
          contactType: 'customer support',
          availableLanguage: [...ORG.languages],
          hoursAvailable: {
            '@type': 'OpeningHoursSpecification',
            dayOfWeek: [...ORG.hours.days],
            opens: ORG.hours.opens,
            closes: ORG.hours.closes,
          },
        },
        {
          '@type': 'ContactPoint',
          email: 'doctors@kyrosclinic.com',
          contactType: 'recruiting',
        },
        {
          '@type': 'ContactPoint',
          email: 'press@kyrosclinic.com',
          contactType: 'press',
        },
      ],
    },
  ],
};

export default function ContactPage() {
  return (
    <>
      <JsonLD data={schema} />
      {/* Hero */}
      <section className="bg-ivory py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <h1 className="font-display text-h1 font-medium text-forest mb-4">Get in touch</h1>
          <p className="font-body text-body-lg text-stone max-w-2xl leading-relaxed">
            Reach us for consultation enquiries, support, doctor applications, or press.
          </p>
        </div>
      </section>

      {/* Contact channels + form */}
      <section className="bg-white py-16 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
            {/* Channels */}
            <div>
              <h2 className="font-display text-h2 font-medium text-forest mb-8">
                How to reach us
              </h2>
              <div className="space-y-6">
                {[
                  {
                    channel: 'General enquiries',
                    value: 'hello@kyrosclinic.com',
                    href: 'mailto:hello@kyrosclinic.com',
                    note: 'We respond within 1 business day.',
                  },
                  {
                    channel: 'Doctor applications',
                    value: 'doctors@kyrosclinic.com',
                    href: 'mailto:doctors@kyrosclinic.com',
                    note: 'NMC-registered specialists only. We respond within 2 business days.',
                  },
                  {
                    channel: 'Data Protection Officer',
                    value: 'dpo@kyrosclinic.com',
                    href: 'mailto:dpo@kyrosclinic.com',
                    note: 'For DPDP rights requests, data access, correction, or deletion.',
                  },
                  {
                    channel: 'Press',
                    value: 'press@kyrosclinic.com',
                    href: 'mailto:press@kyrosclinic.com',
                    note: 'Media enquiries, interviews, data requests.',
                  },
                ].map(({ channel, value, href, note }) => (
                  <div key={channel} className="bg-ivory rounded-card p-6">
                    <p className="font-body text-caption text-stone uppercase tracking-widest mb-1">
                      {channel}
                    </p>
                    <a
                      href={href}
                      className="font-display text-h3 font-medium text-forest hover:text-jade transition-colors duration-micro"
                    >
                      {value}
                    </a>
                    <p className="font-body text-body text-stone mt-2">{note}</p>
                  </div>
                ))}
              </div>

              <div className="mt-8 bg-peach-mist rounded-card p-6">
                <p className="font-display text-h3 font-medium text-forest mb-2">Care team hours</p>
                <p className="font-body text-body text-ink">
                  {ORG.hours.display}
                </p>
                <p className="font-body text-caption text-stone mt-2">
                  For urgent medical concerns, please contact emergency services or go to the
                  nearest hospital. Kyros is not an emergency care service.
                </p>
              </div>
            </div>

            {/* Form */}
            <div>
              <h2 className="font-display text-h2 font-medium text-forest mb-8">
                Send a message
              </h2>
              <ContactForm />
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
