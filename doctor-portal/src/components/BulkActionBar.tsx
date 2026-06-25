interface BulkActionBarProps {
  count: number;
  onClear: () => void;
  onExport: () => void;
  children?: React.ReactNode; // for additional action buttons if needed
}

export function BulkActionBar({ count, onClear, onExport, children }: BulkActionBarProps) {
  if (count === 0) return null;
  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-sage/10 border border-sage/30 rounded-card mb-4">
      <span className="font-body text-body text-forest font-medium">
        {count} selected
      </span>
      <div className="flex-1" />
      {children}
      <button
        onClick={onExport}
        className="px-3 py-1.5 rounded border border-forest/30 font-body text-caption text-forest hover:bg-forest/5 transition-colors"
      >
        Export CSV
      </button>
      <button
        onClick={onClear}
        className="px-3 py-1.5 rounded font-body text-caption text-stone hover:text-ink transition-colors"
      >
        Clear
      </button>
    </div>
  );
}
