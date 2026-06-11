import type { Metadata } from 'next';
import Script from 'next/script';
import { Cormorant_Garamond, DM_Sans } from 'next/font/google';
import { Navigation } from '../components/layout/Navigation';
import { Footer } from '../components/layout/Footer';
import { JsonLD } from '../components/schema/JsonLD';
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
  icons: {
    icon: [
      { url: '/icon.svg', type: 'image/svg+xml' },
    ],
    shortcut: '/icon.svg',
    apple: '/icon.svg',
  },
  description:
    'India-first telemedicine clinic for hormonal health, PCOS, thyroid, weight management, skin & hair, sexual health, diabetes, and longevity. Consult real doctors, track your labs, follow a plan that fits you.',
  metadataBase: new URL('https://kyrosclinic.com'),
  openGraph: {
    siteName: 'Kyros Clinic',
    type: 'website',
    locale: 'en_IN',
    images: [{ url: '/opengraph-image.png', width: 1200, height: 630, alt: 'Kyros Clinic — Doctor-first hormonal health' }],
  },
  twitter: {
    card: 'summary_large_image',
    site: '@kyrosclinic',
    images: ['/opengraph-image.png'],
  },
  robots: { index: true, follow: true },
  verification: {
    google: process.env.NEXT_PUBLIC_GSC_VERIFICATION || undefined,
    other: process.env.NEXT_PUBLIC_BING_VERIFICATION
      ? { 'msvalidate.01': process.env.NEXT_PUBLIC_BING_VERIFICATION }
      : undefined,
  },
};

const websiteSchema = {
  '@context': 'https://schema.org',
  '@type': 'WebSite',
  '@id': 'https://kyrosclinic.com/#website',
  name: 'Kyros Clinic',
  url: 'https://kyrosclinic.com',
  inLanguage: 'en-IN',
  publisher: { '@id': 'https://kyrosclinic.com/#organization' },
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
        <JsonLD data={websiteSchema} />
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

        {/* Cloudflare Web Analytics — cookieless, no consent banner required */}
        {process.env.NEXT_PUBLIC_CF_ANALYTICS_TOKEN && (
          <Script
            defer
            src="https://static.cloudflareinsights.com/beacon.min.js"
            data-cf-beacon={`{"token":"${process.env.NEXT_PUBLIC_CF_ANALYTICS_TOKEN}"}`}
            strategy="afterInteractive"
          />
        )}

        {/* GA4 — optional, for organic-sourced-consultation attribution */}
        {process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID && (
          <>
            <Script
              src={`https://www.googletagmanager.com/gtag/js?id=${process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID}`}
              strategy="afterInteractive"
            />
            <Script id="ga4-config" strategy="afterInteractive">
              {`window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}gtag('js',new Date());gtag('config','${process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID}')`}
            </Script>
          </>
        )}
      </body>
    </html>
  );
}
