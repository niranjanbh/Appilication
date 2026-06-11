interface ReferencesProps {
  /** Plain citation strings from the article's `sources` frontmatter. */
  sources?: string[];
}

export function References({ sources }: ReferencesProps) {
  if (!sources || sources.length === 0) return null;

  return (
    <section
      aria-label="References"
      className="mt-12 pt-8 border-t border-forest/15"
    >
      <h2 className="font-display text-h3 font-medium text-forest mb-4">References</h2>
      <ol className="space-y-3" role="list">
        {sources.map((citation, i) => (
          <li key={i} className="flex gap-3">
            <span
              className="flex-shrink-0 font-body text-caption text-stone font-medium w-6 text-right pt-0.5"
              aria-hidden="true"
            >
              {i + 1}.
            </span>
            <p className="font-body text-caption text-stone leading-relaxed">{citation}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
