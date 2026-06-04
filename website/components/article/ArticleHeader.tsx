import Link from "next/link";
import { CONDITION_DISPLAY_NAMES } from "../../lib/conditionDisplay";

interface ArticleHeaderProps {
  title: string;
  deck: string;
  vertical: string;
  readingTimeMinutes: number;
}

export function ArticleHeader({ title, deck, vertical, readingTimeMinutes }: ArticleHeaderProps) {
  const verticalLabel = CONDITION_DISPLAY_NAMES[vertical] ?? vertical;

  return (
    <header className="mb-8">
      <nav aria-label="Breadcrumb" className="mb-4">
        <ol className="flex items-center gap-2 font-body text-caption text-stone" role="list">
          <li>
            <Link href="/learn" className="hover:text-forest transition-colors duration-micro">
              Learn
            </Link>
          </li>
          <li aria-hidden="true">·</li>
          <li>
            <Link
              href={`/learn/${vertical}`}
              className="hover:text-forest transition-colors duration-micro"
            >
              {verticalLabel}
            </Link>
          </li>
        </ol>
      </nav>

      <div className="inline-block bg-saffron/15 text-forest font-body text-caption font-medium px-3 py-1 rounded-button mb-4">
        {verticalLabel}
      </div>

      <h1 className="font-display text-h1 font-medium text-forest leading-tight mb-4">
        {title}
      </h1>

      <p className="font-body text-body-lg text-stone leading-relaxed mb-4">{deck}</p>

      <p className="font-body text-caption text-stone">
        {readingTimeMinutes} min read
      </p>
    </header>
  );
}
