import Link from 'next/link';
import { MobileMenu } from './MobileMenu';

const NAV_LINKS = [
  { href: '/conditions', label: 'Conditions' },
  { href: '/how-it-works', label: 'How it works' },
  { href: '/pricing', label: 'Pricing' },
  { href: '/our-doctors', label: 'Our doctors' },
  { href: '/faq', label: 'FAQ' },
];

export function Navigation() {
  return (
    <header className="bg-forest text-ivory sticky top-0 z-50 shadow-sm">
      <nav
        className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between"
        aria-label="Main navigation"
      >
        {/* Logo */}
        <Link href="/" aria-label="Kyros Clinic — home" className="flex font-serif flex-col items-center hover:opacity-90 transition-opacity duration-micro">
          {/* <Image src="/kyros-logo.png" alt="Kyros Clinic" width={120} height={36} priority /> */}
          <p>Kyros Clinic</p>
          
        </Link>

        {/* Desktop nav */}
        <ul className="hidden md:flex items-center gap-6" role="list">
          {NAV_LINKS.map(({ href, label }) => (
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

        {/* Right side: desktop CTA + mobile Book link + hamburger */}
        <div className="flex items-center gap-3">
          <Link
            href="/book"
            className="hidden md:inline-flex items-center justify-center px-5 py-2 rounded-button
                       bg-saffron text-forest font-body font-medium text-body-lg
                       hover:bg-saffron/90 transition-colors duration-micro"
          >
            Book consultation
          </Link>
          {/* Mobile: compact book link */}
          <Link
            href="/book"
            className="md:hidden font-body text-body-lg font-medium text-saffron"
          >
            Book
          </Link>
          {/* Mobile: hamburger menu — renders button + panel */}
          <MobileMenu />
        </div>
      </nav>
    </header>
  );
}
