import type { HTMLAttributes } from 'react';

type StatColor = 'forest' | 'saffron';

const numeralColor: Record<StatColor, string> = {
  forest:  'text-forest',
  saffron: 'text-saffron',
};

interface StatProps extends HTMLAttributes<HTMLDivElement> {
  numeral: string;
  caption: string;
  color?: StatColor;
}

export function Stat({ numeral, caption, color = 'forest', className = '', ...props }: StatProps) {
  return (
    <div {...props} className={['flex flex-col items-start gap-1', className].join(' ')}>
      <span className={['font-display text-h1 leading-none font-medium', numeralColor[color]].join(' ')}>
        {numeral}
      </span>
      <span className="font-body text-caption text-stone leading-caption">
        {caption}
      </span>
    </div>
  );
}
