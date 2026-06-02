import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Kyros Clinic — Doctor-first hormonal health',
  description: 'India-first telemedicine clinic for hormonal health, PCOS, thyroid, and more.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-ivory font-body text-ink">{children}</body>
    </html>
  );
}
