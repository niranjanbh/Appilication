interface Reference {
  citation: string;
  url?: string;
}

interface ReferencesProps {
  references: Reference[];
}

export function References({ references }: ReferencesProps) {
  if (!references || references.length === 0) return null;

  return (
    <section
      aria-label="References"
      className="mt-12 pt-8 border-t border-forest/15"
    >
      <h2 className="font-display text-h3 font-medium text-forest mb-4">References</h2>
      <ol className="space-y-3" role="list">
        {references.map((ref, i) => (
          <li key={i} className="flex gap-3">
            <span
              className="flex-shrink-0 font-body text-caption text-stone font-medium w-6 text-right pt-0.5"
              aria-hidden="true"
            >
              {i + 1}.
            </span>
            <p className="font-body text-caption text-stone leading-relaxed">
              {ref.url ? (
                <>
                  {ref.citation}{" "}
                  <a
                    href={ref.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-forest underline hover:text-jade transition-colors duration-micro break-all"
                  >
                    {ref.url}
                  </a>
                </>
              ) : (
                ref.citation
              )}
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}
