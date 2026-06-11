import Link from 'next/link';

const VERTICALS = [
  { href: '/conditions/thyroid', label: 'Thyroid' },
  { href: '/conditions/pmos', label: 'PMOS (PCOS)' },
  { href: '/conditions/weight-management', label: 'Weight Management' },
  { href: '/conditions/skin-and-hair', label: 'Skin & Hair' },
  { href: '/conditions/sexual-health', label: 'Sexual & Intimate Health' },
  { href: '/conditions/hormones-trt', label: 'Hormones & TRT' },
  { href: '/conditions/longevity', label: 'Longevity' },
  { href: '/conditions/diabetes', label: 'Diabetes' },
];

const COMPANY = [
  { href: '/about', label: 'About' },
  { href: '/our-doctors', label: 'Our doctors' },
  { href: '/advisory-board', label: 'Advisory board' },
  { href: '/for-doctors', label: 'For doctors' },
  { href: '/how-it-works', label: 'How it works' },
  { href: '/pricing', label: 'Pricing' },
];

const SUPPORT = [
  { href: '/faq', label: 'FAQ' },
  { href: '/contact', label: 'Contact' },
];

const LEGAL = [
  { href: '/legal/privacy', label: 'Privacy notice' },
  { href: '/legal/terms', label: 'Terms of use' },
  { href: '/legal/telemedicine-consent', label: 'Telemedicine consent' },
  { href: '/legal/data-deletion', label: 'Data deletion' },
];

function FooterColumn({
  title,
  links,
}: {
  title: string;
  links: Array<{ href: string; label: string }>;
}) {
  return (
    <div>
      <h3 className="font-body text-caption font-semibold text-ivory/60 uppercase tracking-widest mb-4">
        {title}
      </h3>
      <ul className="space-y-2" role="list">
        {links.map(({ href, label }) => (
          <li key={href}>
            <Link
              href={href}
              className="font-body text-body text-ivory/80 hover:text-ivory transition-colors duration-micro"
            >
              {label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function Footer() {
  return (
    <footer className="bg-forest text-ivory mt-auto">
      <div className="max-w-7xl mx-auto px-6 py-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-10 mb-12">
          <FooterColumn title="Conditions" links={VERTICALS} />
          <FooterColumn title="Company" links={COMPANY} />
          <FooterColumn title="Support" links={SUPPORT} />
          <FooterColumn title="Legal" links={LEGAL} />
        </div>

        <div className="border-t border-ivory/15 pt-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <p className="font-display text-h3 font-medium text-ivory mb-1">Kyros Clinic</p>
            <p className="font-body text-caption text-ivory/60">
              Doctor-first hormonal health. India.
            </p>
          </div>
          <div className="text-right">
            <p className="font-body text-caption text-ivory/60">
              Kyros Health Technologies Pvt. Ltd.
            </p>
            <p className="font-body text-caption text-ivory/60">
              Data Protection Officer:{' '}
              <a
                href="mailto:dpo@kyrosclinic.com"
                className="text-ivory/80 hover:text-ivory transition-colors duration-micro"
              >
                dpo@kyrosclinic.com
              </a>
            </p>
            <p className="font-body text-caption text-ivory/60 mt-1">
              © {new Date().getFullYear()} Kyros Health Technologies Pvt. Ltd.
            </p>
          </div>
        </div>

        <p className="font-body text-caption text-ivory/40 mt-6 max-w-3xl">
          Kyros Clinic is a telemedicine platform providing medical consultations. Information
          on this website is for general awareness only and does not constitute medical advice.
          Always consult a qualified medical professional for diagnosis and treatment.
          Consultations are subject to doctor availability.
        </p>
      </div>
    </footer>
  );
}
