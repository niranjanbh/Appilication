import type { AnchorHTMLAttributes, BlockquoteHTMLAttributes, HTMLAttributes } from "react";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type MDXComponents = Record<string, React.ComponentType<any>>;

export const mdxComponents: MDXComponents = {
  h2: ({ children, ...props }: HTMLAttributes<HTMLHeadingElement>) => (
    <h2
      {...props}
      className="font-display text-h2 font-medium text-forest mt-10 mb-4 leading-snug"
    >
      {children}
    </h2>
  ),
  h3: ({ children, ...props }: HTMLAttributes<HTMLHeadingElement>) => (
    <h3
      {...props}
      className="font-display text-h3 font-medium text-forest mt-8 mb-3 leading-snug"
    >
      {children}
    </h3>
  ),
  p: ({ children, ...props }: HTMLAttributes<HTMLParagraphElement>) => (
    <p {...props} className="font-body text-body text-ink leading-relaxed mb-5">
      {children}
    </p>
  ),
  ul: ({ children, ...props }: HTMLAttributes<HTMLUListElement>) => (
    <ul {...props} className="space-y-2 mb-5 pl-5 list-disc font-body text-body text-ink">
      {children}
    </ul>
  ),
  ol: ({ children, ...props }: HTMLAttributes<HTMLOListElement>) => (
    <ol {...props} className="space-y-2 mb-5 pl-5 list-decimal font-body text-body text-ink">
      {children}
    </ol>
  ),
  li: ({ children, ...props }: HTMLAttributes<HTMLLIElement>) => (
    <li {...props} className="leading-relaxed">
      {children}
    </li>
  ),
  blockquote: ({ children, ...props }: BlockquoteHTMLAttributes<HTMLQuoteElement>) => (
    <blockquote
      {...props}
      className="border-l-4 border-saffron pl-6 py-1 my-6 bg-ivory rounded-r-card"
    >
      <p className="font-display text-h3 italic font-medium text-forest">{children}</p>
    </blockquote>
  ),
  a: ({ children, href, ...props }: AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a
      {...props}
      href={href}
      className="text-forest underline hover:text-jade transition-colors duration-micro"
      {...(href?.startsWith("http") ? { target: "_blank", rel: "noopener noreferrer" } : {})}
    >
      {children}
    </a>
  ),
  strong: ({ children, ...props }: HTMLAttributes<HTMLElement>) => (
    <strong {...props} className="font-semibold text-ink">
      {children}
    </strong>
  ),
  em: ({ children, ...props }: HTMLAttributes<HTMLElement>) => (
    <em {...props} className="italic">
      {children}
    </em>
  ),
  hr: () => <hr className="border-forest/15 my-8" />,
  table: ({ children, ...props }: HTMLAttributes<HTMLTableElement>) => (
    <div className="overflow-x-auto mb-6">
      <table {...props} className="w-full font-body text-body text-ink border-collapse">
        {children}
      </table>
    </div>
  ),
  thead: ({ children, ...props }: HTMLAttributes<HTMLTableSectionElement>) => (
    <thead {...props} className="bg-forest/5">
      {children}
    </thead>
  ),
  th: ({ children, ...props }: HTMLAttributes<HTMLTableCellElement>) => (
    <th
      {...props}
      className="px-4 py-2 text-left font-body text-caption font-semibold text-forest border border-forest/15"
    >
      {children}
    </th>
  ),
  td: ({ children, ...props }: HTMLAttributes<HTMLTableCellElement>) => (
    <td {...props} className="px-4 py-2 border border-forest/15 align-top">
      {children}
    </td>
  ),
};
