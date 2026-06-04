import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Search } from 'lucide-react';
import { apiFetch } from '../../lib/api';

interface PatientSummary {
  patient_id: string;
  kyros_patient_id: string;
  name: string;
  phone: string | null;
  primary_conditions: string[];
}

interface PatientListResponse {
  items: PatientSummary[];
  total: number;
  page: number;
  pages: number;
}

function formatConditions(conditions: string[]): string {
  return conditions
    .map(c => c.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()))
    .join(', ') || '—';
}

export function PatientList() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const debouncedSearch = search.trim();

  const { data, isLoading } = useQuery({
    queryKey: ['patients', debouncedSearch, page],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), page_size: '20' });
      if (debouncedSearch) params.set('search', debouncedSearch);
      return apiFetch<PatientListResponse>(`/v1/doctor/patients?${params.toString()}`);
    },
  });

  return (
    <div className="px-8 py-8 max-w-4xl">
      <h1 className="font-display text-h2 text-forest font-medium mb-6">Patients</h1>

      {/* Search */}
      <div className="relative mb-6">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-stone" />
        <input
          type="text"
          placeholder="Search by name or phone…"
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
          className="w-full pl-9 pr-4 py-2.5 border border-stone/30 rounded-md font-body text-body text-ink focus:outline-none focus:border-forest transition-colors"
        />
      </div>

      <div className="bg-white rounded-card overflow-hidden">
        {isLoading ? (
          <p className="px-5 py-10 text-center font-body text-body text-stone">Loading…</p>
        ) : !data || data.items.length === 0 ? (
          <p className="px-5 py-10 text-center font-body text-body text-stone">
            {debouncedSearch ? 'No patients match your search.' : 'No patients in your panel yet.'}
          </p>
        ) : (
          <>
            <table className="w-full">
              <thead>
                <tr className="border-b border-stone/10 bg-ivory">
                  <th className="text-left px-5 py-3 font-body text-caption text-stone font-semibold">Patient</th>
                  <th className="text-left px-5 py-3 font-body text-caption text-stone font-semibold">Kyros ID</th>
                  <th className="text-left px-5 py-3 font-body text-caption text-stone font-semibold">Conditions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone/10">
                {data.items.map(pt => (
                  <tr key={pt.patient_id} className="hover:bg-ivory transition-colors">
                    <td className="px-5 py-4">
                      <Link
                        to={`/patients/${pt.patient_id}`}
                        className="font-body text-body text-forest hover:underline font-medium"
                      >
                        {pt.name}
                      </Link>
                      {pt.phone && (
                        <p className="font-body text-caption text-stone">{pt.phone}</p>
                      )}
                    </td>
                    <td className="px-5 py-4 font-body text-caption text-stone">{pt.kyros_patient_id}</td>
                    <td className="px-5 py-4 font-body text-caption text-stone">{formatConditions(pt.primary_conditions)}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            {data.pages > 1 && (
              <div className="flex items-center justify-between px-5 py-3 border-t border-stone/10">
                <p className="font-body text-caption text-stone">
                  {data.total} patient{data.total !== 1 ? 's' : ''}
                </p>
                <div className="flex gap-2">
                  <button
                    disabled={page <= 1}
                    onClick={() => setPage(p => p - 1)}
                    className="px-3 py-1 rounded border border-stone/30 font-body text-caption text-stone hover:bg-ivory disabled:opacity-40 transition-colors"
                  >
                    Previous
                  </button>
                  <span className="px-3 py-1 font-body text-caption text-stone">{page} / {data.pages}</span>
                  <button
                    disabled={page >= data.pages}
                    onClick={() => setPage(p => p + 1)}
                    className="px-3 py-1 rounded border border-stone/30 font-body text-caption text-stone hover:bg-ivory disabled:opacity-40 transition-colors"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
