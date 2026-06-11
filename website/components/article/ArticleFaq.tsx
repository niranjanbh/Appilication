import type { ArticleFaq } from "../../lib/mdx";

interface ArticleFaqProps {
  faqs?: ArticleFaq[];
}

export function ArticleFaqSection({ faqs }: ArticleFaqProps) {
  if (!faqs || faqs.length === 0) return null;

  return (
    <section aria-label="Frequently asked questions" className="mt-12 pt-8 border-t border-forest/15">
      <h2 className="font-display text-h2 font-medium text-forest mb-6 leading-snug">
        Frequently asked questions
      </h2>
      <dl className="space-y-6">
        {faqs.map((item, i) => (
          <div key={i}>
            <dt className="font-body text-body-lg font-medium text-forest mb-2">{item.q}</dt>
            <dd className="font-body text-body text-ink leading-relaxed">{item.a}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
