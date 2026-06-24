import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Image as ImageIcon, Pill } from 'lucide-react';
import {
  getMedicationCatalogImageUrl,
  searchMedicationCatalog,
  type MedicationCatalogItem,
} from '../lib/medicationCatalog';

interface MedicationCatalogPickerProps {
  value: string;
  /** Fired on every change. `item` is the chosen catalog entry, or null on free text. */
  onChange: (name: string, item: MedicationCatalogItem | null) => void;
  placeholder?: string;
}

/**
 * Autocomplete over the medication catalog. The doctor types a name, picks a
 * match (with form/strength), and — when the entry has an image — a thumbnail
 * preview is shown so they can confirm the right medication. Free text is still
 * allowed for medications not yet in the catalog.
 */
export function MedicationCatalogPicker({ value, onChange, placeholder }: MedicationCatalogPickerProps) {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<MedicationCatalogItem | null>(null);
  const [debounced, setDebounced] = useState(value);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), 250);
    return () => clearTimeout(t);
  }, [value]);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const { data } = useQuery({
    queryKey: ['med-catalog-search', debounced],
    queryFn: () => searchMedicationCatalog(debounced),
    enabled: open && debounced.trim().length >= 2,
    staleTime: 60_000,
  });

  const imageQuery = useQuery({
    queryKey: ['med-catalog-image', selected?.id],
    queryFn: () => getMedicationCatalogImageUrl(selected!.id),
    enabled: !!selected?.has_image,
    staleTime: 5 * 60_000,
  });

  const results = data?.items ?? [];
  const thumbUrl = selected?.has_image ? imageQuery.data?.url : undefined;

  function pick(item: MedicationCatalogItem) {
    setSelected(item);
    onChange(item.name, item);
    setOpen(false);
  }

  return (
    <div ref={boxRef} className="relative flex-1">
      {thumbUrl && (
        <img
          src={thumbUrl}
          alt={selected?.name ?? ''}
          className="absolute left-2 top-1/2 -translate-y-1/2 w-6 h-6 rounded object-cover border border-stone/20"
        />
      )}
      <input
        value={value}
        onChange={e => {
          onChange(e.target.value, null);
          setSelected(null);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        placeholder={placeholder ?? 'Search medication…'}
        className={`w-full font-body text-body text-ink border border-stone/30 rounded py-1.5 pr-3 focus:outline-none focus:ring-1 focus:ring-forest/50 ${thumbUrl ? 'pl-10' : 'pl-3'}`}
      />
      {open && results.length > 0 && (
        <ul className="absolute z-20 mt-1 left-0 right-0 max-h-56 overflow-auto bg-white border border-stone/30 rounded shadow-card">
          {results.map(item => (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => pick(item)}
                className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-sage/10"
              >
                <Pill size={14} className="text-forest shrink-0" />
                <span className="font-body text-caption text-ink">{item.name}</span>
                {item.form && (
                  <span className="font-body text-caption text-stone">· {item.form}</span>
                )}
                {item.strength && (
                  <span className="font-body text-caption text-stone">· {item.strength}</span>
                )}
                {item.has_image && (
                  <ImageIcon size={12} className="text-stone ml-auto shrink-0" />
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}