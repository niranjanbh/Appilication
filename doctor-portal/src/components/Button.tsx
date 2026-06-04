import type { ButtonHTMLAttributes, ReactNode } from 'react';

type ButtonVariant = 'forest' | 'saffron' | 'outline' | 'ghost';

const variantClasses: Record<ButtonVariant, string> = {
  forest:  'bg-forest text-ivory hover:bg-jade active:bg-jade/90',
  saffron: 'bg-saffron text-forest hover:bg-saffron/90 active:bg-saffron/80',
  outline: 'border-2 border-forest text-forest hover:bg-forest/8 active:bg-forest/12',
  ghost:   'text-forest hover:bg-forest/8 active:bg-forest/12',
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  children: ReactNode;
}

export function Button({ variant = 'forest', children, className = '', ...props }: ButtonProps) {
  return (
    <button
      {...props}
      className={[
        'inline-flex items-center justify-center px-6 py-3 rounded-button',
        'font-body font-medium text-body-lg',
        'transition-colors duration-micro ease-out',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        variantClasses[variant],
        className,
      ].join(' ')}
    >
      {children}
    </button>
  );
}
