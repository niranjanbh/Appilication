import type { HTMLAttributes, ReactNode } from 'react';

type CardVariant = 'white' | 'ivory';

const variantClasses: Record<CardVariant, string> = {
  white: 'bg-white',
  ivory: 'bg-ivory',
};

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
  children: ReactNode;
}

export function Card({ variant = 'white', children, className = '', ...props }: CardProps) {
  return (
    <div
      {...props}
      className={[
        'rounded-card p-6 shadow-sm',
        variantClasses[variant],
        className,
      ].join(' ')}
    >
      {children}
    </div>
  );
}
