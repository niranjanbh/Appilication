import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Search, Trash2 } from 'lucide-react';
import { apiFetch } from '../lib/api';

interface Diagnosis {
  id: string;
  icd10_code: string;
  icd10_description: string;
  is_primary: boolean;
  created_at: string;
}

interface Icd10Code {
  code: string;
  description: string;
  category: string;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
    timeZone: 'Asia/Kolkata',
  });
}

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(t);
  }, [value, delayMs]);
  return debounced;
}

interface DiagnosisPanelProps {
  consultationId: string;
}

export function DiagnosisPanel({ consultationId }: DiagnosisPanelProps) {
  const qc = useQueryClient();

  const [search, setSearch] = useState('');
  const [focused, setFocused] = useState(false);
  const [selected, setSelected] = useState<Icd10Code | null>(null);
  const [isPrimary, setIsPrimary] = useState(false);
  const debounced = useDebouncedValue(search, 250);

  const { data: diagnoses = [], isLoading } = useQuery<Diagnosis[]>({
    queryKey: ['consultation-diagnoses', consultationId],
    queryFn: () => apiFetch<Diagnosis[]>(`/v1/doctor/consultations/${consultationId}/diagnoses`),
  });

  const { data: results } = useQuery<Icd10Code[]>({
    queryKey: ['icd10-search', debounced],
    queryFn: () =>
      apiFetch<Icd10Code[]>(`/v1/doctor/icd10-codes?q=${encodeURIComponent(debounced.trim())}`),
    enabled: focused && debounced.trim().length >= 1,
    staleTime: 60_000,
  });

  const showDropdown = focused && !selected && (results?.length ?? 0) > 0;

  const addDiagnosis = useMutation({
    mutationFn: () => {
      if (!selected) throw new Error('No ICD-10 code selected');
      return apiFetch<Diagnosis>(`/v1/doctor/consultations/${consultationId}/diagnoses`, {
        method: 'POST',
        body: JSON.stringify({
          icd10_code: selected.code,
          icd10_description: selected.description,
          is_primary: isPrimary,
        }),
      });
    },
    onSuccess: () => {
      setSelected(null);
      setSearch('');
      setIsPrimary(false);
      qc.invalidateQueries({ queryKey: ['consultation-diagnoses', consultationId] });
    },
  });

  const deleteDiagnosis = useMutation({
    mutationFn: (diagnosisId: string) =>
      apiFetch<void>(`/v1/doctor/consultations/${consultationId}/diagnoses/${diagnosisId}`, {
        method: 'DELETE',
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['consultation-diagnoses', consultationId] }),
  });

  function pick(code: Icd10Code) {
    setSelected(code);
    setSearch(`${code.code} — ${code.description}`);
    setFocused(false);
  }

  function clearSelection() {
    setSelected(null);
    setSearch('');
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="bg-white rounded-card p-4">
        <h3 className="font-body text-body font-semibold text-forest mb-3">Add diagnosis (ICD-10)</h3>

        <div className="relative mb-3">
          <div className="flex items-center border border-stone/30 rounded px-3 focus-within:ring-1 focus-within:ring-forest/50">
            <Search size={14} className="text-stone shrink-0" />
            <input
              value={search}
              onChange={e => { setSearch(e.target.value); if (selected) setSelected(null); }}
              onFocus={() => setFocused(true)}
              onBlur={() => setTimeout(() => setFocused(false), 120)}
              placeholder="Search ICD-10 code or description…"
              aria-autocomplete="list"
              className="w-full font-body text-body text-ink px-2 py-1.5 focus:outline-none"
            />
            {selected && (
              <button
                type="button"
                onClick={clearSelection}
                className="text-stone hover:text-alert shrink-0"
                aria-label="Clear selection"
              >
                <Trash2 size={14} />
              </button>
            )}
          </div>

          {showDropdown && (
            <ul className="absolute z-10 mt-1 w-full bg-white border border-stone/30 rounded shadow-lg max-h-56 overflow-auto">
              {results!.map(c => (
                <li key={c.code}>
                  <button
                    type="button"
                    onMouseDown={e => e.preventDefault()}
                    onClick={() => pick(c)}
                    className="w-full text-left px-3 py-1.5 hover:bg-sage/10 flex items-start gap-2"
                  >
                    <span className="font-body text-caption font-semibold text-forest bg-sage/20 rounded px-1.5 py-0.5 shrink-0">
                      {c.code}
                    </span>
                    <span className="font-body text-caption text-ink">{c.description}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <label className="flex items-center gap-2 mb-3 cursor-pointer">
          <input
            type="checkbox"
            checked={isPrimary}
            onChange={e => setIsPrimary(e.target.checked)}
            className="accent-forest"
          />
          <span className="font-body text-caption text-stone">Mark as primary diagnosis</span>
        </label>

        <button
          onClick={() => addDiagnosis.mutate()}
          disabled={!selected || addDiagnosis.isPending}
          className="inline-flex items-center gap-1.5 bg-forest text-ivory font-body text-caption font-semibold px-3 py-2 rounded-md disabled:opacity-40 hover:bg-jade transition-colors"
        >
          <Plus size={12} /> {addDiagnosis.isPending ? 'Adding…' : 'Add diagnosis'}
        </button>

        {addDiagnosis.isError && (
          <p className="font-body text-caption text-alert mt-2">Failed to add diagnosis. Please try again.</p>
        )}
      </div>

      <div>
        <h3 className="font-body text-body font-semibold text-forest mb-2">Recorded diagnoses</h3>
        {isLoading ? (
          <p className="font-body text-caption text-stone">Loading…</p>
        ) : diagnoses.length === 0 ? (
          <p className="font-body text-caption text-stone">No diagnoses recorded yet.</p>
        ) : (
          <ul className="space-y-2">
            {diagnoses.map(d => (
              <li key={d.id} className="border border-stone/15 rounded p-2.5 flex items-start gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="font-body text-caption font-semibold text-forest bg-sage/20 rounded px-1.5 py-0.5">
                      {d.icd10_code}
                    </span>
                    {d.is_primary && (
                      <span className="font-body text-caption font-semibold text-saffron bg-saffron/15 rounded px-1.5 py-0.5">
                        Primary
                      </span>
                    )}
                  </div>
                  <p className="font-body text-caption text-ink">{d.icd10_description}</p>
                  <p className="font-body text-caption text-stone/60 mt-0.5">{formatDate(d.created_at)}</p>
                </div>
                <button
                  onClick={() => deleteDiagnosis.mutate(d.id)}
                  disabled={deleteDiagnosis.isPending}
                  className="text-stone hover:text-alert shrink-0 disabled:opacity-40"
                  aria-label="Remove diagnosis"
                >
                  <Trash2 size={14} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
