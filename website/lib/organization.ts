export const ORG = {
  name: 'Kyros Clinic',
  legalName: 'Kyros Health Technologies Pvt. Ltd.',
  url: 'https://kyrosclinic.com',
  foundingDate: '2026',
  email: 'hello@kyrosclinic.com',
  dpoEmail: 'dpo@kyrosclinic.com',
  logoUrl: 'https://kyrosclinic.com/kyros-logo.png',
  logoWidth: 512,
  logoHeight: 512,
  ogImage: 'https://kyrosclinic.com/opengraph-image.png',
  address: {
    locality: 'Bengaluru',
    region: 'Karnataka',
    country: 'IN',
    countryName: 'India',
  },
  geo: {
    latitude: 12.9716,
    longitude: 77.5946,
  },
  hours: {
    days: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
    opens: '09:00',
    closes: '21:00',
    display: 'Monday to Saturday, 9 AM to 9 PM IST',
  },
  sameAs: ['https://x.com/kyrosclinic'],
  twitterHandle: '@kyrosclinic',
  languages: ['English', 'Hindi'],
  description:
    'India-first doctor-first telemedicine clinic covering hormonal health, PCOS, thyroid, weight management, skin and hair, sexual and intimate health, TRT, diabetes, and longevity.',
} as const;

export const ORG_ID = 'https://kyrosclinic.com/#organization';
export const BIZ_ID = 'https://kyrosclinic.com/#medical-business';

export function organizationSchema() {
  return {
    '@type': 'MedicalOrganization',
    '@id': ORG_ID,
    name: ORG.name,
    legalName: ORG.legalName,
    url: ORG.url,
    foundingDate: ORG.foundingDate,
    logo: {
      '@type': 'ImageObject',
      url: ORG.logoUrl,
      width: ORG.logoWidth,
      height: ORG.logoHeight,
    },
    image: ORG.ogImage,
    areaServed: { '@type': 'Country', name: ORG.address.countryName },
    address: {
      '@type': 'PostalAddress',
      addressLocality: ORG.address.locality,
      addressRegion: ORG.address.region,
      addressCountry: ORG.address.country,
    },
    geo: {
      '@type': 'GeoCoordinates',
      latitude: ORG.geo.latitude,
      longitude: ORG.geo.longitude,
    },
    description: ORG.description,
    contactPoint: {
      '@type': 'ContactPoint',
      contactType: 'customer support',
      email: ORG.email,
      availableLanguage: [...ORG.languages],
      hoursAvailable: {
        '@type': 'OpeningHoursSpecification',
        dayOfWeek: [...ORG.hours.days],
        opens: ORG.hours.opens,
        closes: ORG.hours.closes,
      },
    },
    sameAs: [...ORG.sameAs],
  };
}
