import type { HTMLAttributes, ReactNode } from 'react';

type TagVariant = 'sage' | 'saffron' | 'terracotta' | 'forest';

const variantClasses: Record<TagVariant, string> = {
  sage:       'bg-sage/20 text-forest',
  saffron:    'bg-saffron/20 text-forest',
  terracotta: 'bg-terracotta/20 text-terracotta',
  forest:     'bg-forest text-ivory',
};

interface TagProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: TagVariant;
  children: ReactNode;
}

export function Tag({ variant = 'forest', children, className = '', ...props }: TagProps) {
  return (
    <span
      {...props}
      className={[
        'inline-flex items-center px-3 py-1 rounded-button',
        'font-body text-caption font-medium',
        variantClasses[variant],
        className,
      ].join(' ')}
    >
      {children}
    </span>
  );
}
