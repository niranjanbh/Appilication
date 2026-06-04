import Link from 'next/link';
import type { ReactNode } from 'react';

interface HeroSectionProps {
  headline: string;
  subline: string;
  primaryCta?: { label: string; href: string };
  secondaryCta?: { label: string; href: string };
  accentLine?: ReactNode;
  variant?: 'ivory' | 'peach';
}

export function HeroSection({
  headline,
  subline,
  primaryCta,
  secondaryCta,
  accentLine,
  variant = 'ivory',
}: HeroSectionProps) {
  const bg = variant === 'peach' ? 'bg-peach-mist' : 'bg-ivory';

  return (
    <section className={`${bg} py-20 md:py-28 px-6`}>
      <div className="max-w-4xl mx-auto">
        {accentLine && (
          <p className="font-body text-caption text-stone uppercase tracking-widest mb-4">
            {accentLine}
          </p>
        )}
        <h1 className="font-display text-h1 md:text-display font-medium text-forest leading-tight mb-6 max-w-3xl">
          {headline}
        </h1>
        <p className="font-body text-body-lg text-ink max-w-2xl mb-8 leading-relaxed">
          {subline}
        </p>
        {(primaryCta || secondaryCta) && (
          <div className="flex flex-wrap gap-4">
            {primaryCta && (
              <Link
                href={primaryCta.href}
                className="inline-flex items-center justify-center px-7 py-3 rounded-button
                           bg-forest text-ivory font-body font-medium text-body-lg
                           hover:bg-jade transition-colors duration-micro"
              >
                {primaryCta.label}
              </Link>
            )}
            {secondaryCta && (
              <Link
                href={secondaryCta.href}
                className="inline-flex items-center justify-center px-7 py-3 rounded-button
                           border-2 border-forest text-forest font-body font-medium text-body-lg
                           hover:bg-forest/8 transition-colors duration-micro"
              >
                {secondaryCta.label}
              </Link>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
