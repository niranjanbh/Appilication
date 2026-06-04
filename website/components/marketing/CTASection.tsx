import Link from 'next/link';

interface CTASectionProps {
  headline: string;
  subline?: string;
  primaryCta: { label: string; href: string };
  secondaryCta?: { label: string; href: string };
  variant?: 'forest' | 'ivory';
}

export function CTASection({
  headline,
  subline,
  primaryCta,
  secondaryCta,
  variant = 'forest',
}: CTASectionProps) {
  if (variant === 'forest') {
    return (
      <section className="bg-forest py-16 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="font-display text-h2 font-medium text-ivory mb-4">{headline}</h2>
          {subline && (
            <p className="font-body text-body-lg text-ivory/80 mb-8">{subline}</p>
          )}
          <div className="flex flex-wrap justify-center gap-4">
            <Link
              href={primaryCta.href}
              className="inline-flex items-center justify-center px-8 py-3 rounded-button
                         bg-saffron text-forest font-body font-medium text-body-lg
                         hover:bg-saffron/90 transition-colors duration-micro"
            >
              {primaryCta.label}
            </Link>
            {secondaryCta && (
              <Link
                href={secondaryCta.href}
                className="inline-flex items-center justify-center px-8 py-3 rounded-button
                           border-2 border-ivory/40 text-ivory font-body font-medium text-body-lg
                           hover:border-ivory hover:bg-ivory/8 transition-colors duration-micro"
              >
                {secondaryCta.label}
              </Link>
            )}
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="bg-ivory py-16 px-6">
      <div className="max-w-7xl mx-auto">
        <div className="bg-peach-mist rounded-card p-10 md:p-14 text-center">
          <h2 className="font-display text-h2 font-medium text-forest mb-4">{headline}</h2>
          {subline && (
            <p className="font-body text-body-lg text-ink mb-8">{subline}</p>
          )}
          <div className="flex flex-wrap justify-center gap-4">
            <Link
              href={primaryCta.href}
              className="inline-flex items-center justify-center px-8 py-3 rounded-button
                         bg-forest text-ivory font-body font-medium text-body-lg
                         hover:bg-jade transition-colors duration-micro"
            >
              {primaryCta.label}
            </Link>
            {secondaryCta && (
              <Link
                href={secondaryCta.href}
                className="inline-flex items-center justify-center px-8 py-3 rounded-button
                           border-2 border-forest text-forest font-body font-medium text-body-lg
                           hover:bg-forest/8 transition-colors duration-micro"
              >
                {secondaryCta.label}
              </Link>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
