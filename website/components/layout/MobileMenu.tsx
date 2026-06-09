'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

const NAV_LINKS = [
  { href: '/conditions', label: 'Conditions' },
  { href: '/how-it-works', label: 'How it works' },
  { href: '/our-doctors', label: 'Our doctors' },
  { href: '/faq', label: 'FAQ' },
];

export function MobileMenu() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  // Close menu on route change
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  // Lock body scroll while menu is open
  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [open]);

  return (
    <>
      {/* Hamburger / close button — right side, mobile only */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="md:hidden flex items-center justify-center w-10 h-10 -mr-2 rounded-lg text-ivory hover:bg-white/10 transition-colors duration-micro"
        aria-label={open ? 'Close menu' : 'Open menu'}
        aria-expanded={open}
        aria-controls="mobile-nav-panel"
      >
        {open ? (
          /* X icon */
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <path d="M4 4L16 16M16 4L4 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        ) : (
          /* Hamburger icon */
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <path d="M3 5H17M3 10H17M3 15H17" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        )}
      </button>

      {/* Mobile nav panel — drops below the sticky header */}
      {open && (
        <div
          id="mobile-nav-panel"
          className="md:hidden fixed inset-x-0 top-16 z-40 bg-forest border-t border-white/10 shadow-lg"
        >
          <nav aria-label="Mobile navigation">
            <ul className="px-6 py-4 flex flex-col gap-1" role="list">
              {NAV_LINKS.map(({ href, label }) => (
                <li key={href}>
                  <Link
                    href={href}
                    className={`flex items-center px-3 py-3 rounded-lg font-body text-body-lg transition-colors duration-micro ${
                      pathname === href
                        ? 'bg-white/10 text-ivory font-medium'
                        : 'text-ivory/80 hover:text-ivory hover:bg-white/10'
                    }`}
                  >
                    {label}
                  </Link>
                </li>
              ))}
            </ul>

            {/* Full-width CTA */}
            <div className="px-6 pb-6 pt-2 border-t border-white/10">
              <Link
                href="/book"
                className="flex items-center justify-center w-full px-5 py-3 rounded-button
                           bg-saffron text-forest font-body font-semibold text-body-lg
                           hover:bg-saffron/90 transition-colors duration-micro"
              >
                Book consultation
              </Link>
            </div>
          </nav>
        </div>
      )}

      {/* Backdrop — tapping outside closes the menu */}
      {open && (
        <div
          className="md:hidden fixed inset-0 top-16 z-30 bg-black/30"
          aria-hidden="true"
          onClick={() => setOpen(false)}
        />
      )}
    </>
  );
}
