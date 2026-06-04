import Link from 'next/link';

interface ConditionCardProps {
  slug: string;
  name: string;
  shortDescription: string;
  icon: string;
}

export function ConditionCard({ slug, name, shortDescription, icon }: ConditionCardProps) {
  return (
    <Link
      href={`/conditions/${slug}`}
      className="group block bg-white rounded-card p-6 border border-forest/8
                 hover:border-forest/30 hover:shadow-sm transition-all duration-entrance"
    >
      <span className="text-3xl mb-4 block" aria-hidden="true">
        {icon}
      </span>
      <h3 className="font-display text-h3 font-medium text-forest mb-2 group-hover:text-jade transition-colors duration-micro">
        {name}
      </h3>
      <p className="font-body text-body text-stone leading-relaxed">{shortDescription}</p>
      <p className="font-body text-caption text-forest mt-4 font-medium">
        Learn more →
      </p>
    </Link>
  );
}
