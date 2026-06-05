'use client';

export function LoadingLines() {
  const letters = 'Kyros'.split('');
  return (
    <div
      className="flex items-center justify-center h-[120px] gap-[2px] text-2xl text-forest"
      aria-label="Loading"
      role="status"
    >
      {letters.map((letter, idx) => (
        <span
          key={idx}
          className="inline-block opacity-0 animate-kyros"
          style={{ animationDelay: `${idx * 0.12}s` }}
        >
          {letter}
        </span>
      ))}
    </div>
  );
}
