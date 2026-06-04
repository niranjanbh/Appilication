interface Stat {
  numeral: string;
  caption: string;
  color?: 'forest' | 'saffron';
}

interface StatBlockProps {
  stats: Stat[];
  heading?: string;
}

export function StatBlock({ stats, heading }: StatBlockProps) {
  return (
    <section className="bg-peach-mist py-16 px-6">
      <div className="max-w-7xl mx-auto">
        {heading && (
          <h2 className="font-display text-h2 font-medium text-forest mb-10 text-center">
            {heading}
          </h2>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
          {stats.map((stat) => (
            <div key={stat.caption} className="bg-ivory rounded-card p-8 text-center">
              <p
                className={`font-display text-display font-medium ${
                  stat.color === 'saffron' ? 'text-saffron' : 'text-forest'
                } mb-2`}
              >
                {stat.numeral}
              </p>
              <p className="font-body text-body text-stone">{stat.caption}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
