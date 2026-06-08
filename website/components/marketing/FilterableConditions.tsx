'use client';

import { useState } from 'react';
import { CONDITIONS } from '../../lib/conditions';
import type { ConditionAudience } from '../../lib/conditions';
import { ConditionCard } from './ConditionCard';

const FILTERS: [ConditionAudience, string][] = [
  ['all', 'All'],
  ['women', 'Women'],
  ['men', 'Men'],
];

export function FilterableConditions() {
  const [filter, setFilter] = useState<ConditionAudience>('all');
  const [animKey, setAnimKey] = useState(0);

  const visible = CONDITIONS.filter(
    (c) => filter === 'all' || c.audience === 'all' || c.audience === filter,
  );

  function handleFilter(next: ConditionAudience) {
    setFilter(next);
    setAnimKey((k) => k + 1);
  }

  return (
    <section className="bg-white py-16 px-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
          <div>
            <h2 className="font-display text-h2 font-medium text-forest mb-3">
              Eight conditions. One clinical home.
            </h2>
            <p className="font-body text-body text-stone max-w-2xl">
              Kyros doctors specialise in chronic hormonal conditions that are common,
              underdiagnosed, and undertreated in India.
            </p>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <span className="font-body text-caption text-stone">Show:</span>
            {FILTERS.map(([key, label]) => (
              <button
                key={key}
                onClick={() => handleFilter(key)}
                className={`px-4 py-1.5 rounded-full font-body text-caption font-medium transition-all duration-micro
                  ${filter === key
                    ? 'bg-forest text-ivory'
                    : 'border border-forest/30 text-stone hover:border-forest/60'
                  }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {visible.map((c, idx) => (
            <div
              key={`${animKey}-${c.slug}`}
              style={{ animation: `fade-up 0.45s ease-out ${idx * 50}ms both` }}
            >
              <ConditionCard
                slug={c.slug}
                name={c.name}
                shortDescription={c.shortDescription}
                image={c.image}
              />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
