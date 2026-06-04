interface Pillar {
  title: string;
  body: string;
  icon?: string;
}

interface PillarBlockProps {
  pillars: Pillar[];
  variant?: 'peach' | 'sage';
}

export function PillarBlock({ pillars, variant = 'peach' }: PillarBlockProps) {
  const sectionBg = variant === 'sage' ? 'bg-sage/15' : 'bg-peach-mist';

  return (
    <section className={`${sectionBg} py-16 px-6`}>
      <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6">
        {pillars.map((pillar) => (
          <div key={pillar.title} className="bg-ivory rounded-card p-8">
            {pillar.icon && (
              <span className="text-2xl mb-4 block" aria-hidden="true">
                {pillar.icon}
              </span>
            )}
            <h3 className="font-display text-h3 font-medium text-forest mb-3">{pillar.title}</h3>
            <p className="font-body text-body text-ink leading-relaxed">{pillar.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
