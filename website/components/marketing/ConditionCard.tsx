'use client';

import { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';

interface ConditionCardProps {
  slug: string;
  name: string;
  shortDescription: string;
  image: string;
}

export function ConditionCard({ slug, name, shortDescription, image }: ConditionCardProps) {
  const [loaded, setLoaded] = useState(false);

  return (
    <Link
      href={`/conditions/${slug}`}
      className="group block bg-white rounded-card border border-forest/8
                 hover:border-forest/30 hover:shadow-sm transition-all duration-entrance overflow-hidden"
    >
      <div className="relative w-full h-44 overflow-hidden">
        {!loaded && <div className="absolute inset-0 shimmer-bg" aria-hidden="true" />}
        <Image
          src={image}
          alt={name}
          fill
          sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
          className={`object-cover transition-opacity duration-500 ${loaded ? 'opacity-100' : 'opacity-0'}`}
          onLoad={() => setLoaded(true)}
        />
      </div>
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
