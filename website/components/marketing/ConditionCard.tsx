'use client';

import Link from 'next/link';
import Image from 'next/image';

interface ConditionCardProps {
  slug: string;
  name: string;
  shortDescription: string;
  image: string;
}

export function ConditionCard({ slug, name, shortDescription, image }: ConditionCardProps) {
  return (
    <Link
      href={`/conditions/${slug}`}
      className="group block bg-white rounded-card border border-forest/8
                 hover:border-forest/30 hover:shadow-md transition-all duration-entrance overflow-hidden"
    >
      <div className="p-6">
        <h3 className="font-display text-h3 font-medium text-forest mb-2 group-hover:text-jade transition-colors duration-micro">
          {name}
        </h3>
        <p className="font-body text-body text-stone leading-relaxed">{shortDescription}</p>
        <p className="font-body text-caption text-forest mt-4 font-medium">
          Learn more →
        </p>
      </div>
    </Link>
  );
}
