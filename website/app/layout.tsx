import type { Metadata } from 'next';
import { Cormorant_Garamond, DM_Sans } from 'next/font/google';
import { Navigation } from '../components/layout/Navigation';
import { Footer } from '../components/layout/Footer';
import './globals.css';

const cormorant = Cormorant_Garamond({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  style: ['normal', 'italic'],
  variable: '--font-display',
  display: 'swap',
});

const dmSans = DM_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-body',
  display: 'swap',
});

export const metadata: Metadata = {
  title: {
    default: 'Kyros Clinic — Doctor-first hormonal health',
    template: '%s — Kyros Clinic',
  },
  description:
    'India-first telemedicine clinic for hormonal health, PCOS, thyroid, weight management, skin & hair, and longevity. Consult real doctors, track your labs, follow a plan that fits you.',
  metadataBase: new URL('https://kyrosclinic.com'),
  openGraph: {
    siteName: 'Kyros Clinic',
    type: 'website',
    locale: 'en_IN',
  },
  twitter: {
    card: 'summary_large_image',
    site: '@kyrosclinic',
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${cormorant.variable} ${dmSans.variable}`}>
      {/*
        Tiro Devanagari Hindi is not available via next/font/google.
        Loaded via preconnect + stylesheet for zero layout-shift on Hindi text.
      */}
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Tiro+Devanagari+Hindi&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-ivory font-body text-ink flex flex-col min-h-screen">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4
                     bg-forest text-ivory px-4 py-2 rounded-button z-50 font-body text-body"
        >
          Skip to main content
        </a>
        <Navigation />
        <main id="main-content" className="flex-1">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
