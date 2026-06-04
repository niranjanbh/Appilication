import type { HTMLAttributes, ReactNode } from 'react';

type PullQuoteAccent = 'terracotta' | 'saffron';

const accentClasses: Record<PullQuoteAccent, string> = {
  terracotta: 'border-terracotta',
  saffron:    'border-saffron',
};

interface PullQuoteProps extends HTMLAttributes<HTMLQuoteElement> {
  accent?: PullQuoteAccent;
  children: ReactNode;
}

export function PullQuote({ accent = 'terracotta', children, className = '', ...props }: PullQuoteProps) {
  return (
    <blockquote
      {...props}
      className={[
        'border-l-4 pl-6 py-1',
        'font-display italic text-h3 text-forest leading-snug',
        accentClasses[accent],
        className,
      ].join(' ')}
    >
      {children}
    </blockquote>
  );
}
