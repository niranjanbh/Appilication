import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { apiFetch } from '../../lib/api';
import { useBulkSelect } from '../../hooks/useBulkSelect';
import { downloadCSV } from '../../lib/csv-export';
import { BulkActionBar } from '../../components/BulkActionBar';

interface Consultation {
  id: string;
  patient_name: string;
  kyros_patient_id: string;
  condition_category: string;
  consultation_type: string;
  scheduled_start_at: string;
  status: string;
  video_room_id: string | null;
}

interface ConsultationListResponse {
  items: Consultation[];
  total: number;
  page: number;
  pages: number;
}

export type FilterType = 'today' | 'upcoming' | 'history';

function formatIST(iso: string) {
  return new Date(iso).toLocaleString('en-IN', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
    hour12: true, timeZone: 'Asia/Kolkata',
  });
}

function formatCategory(s: string) {
  return s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

const STATUS_PILL: Record<string, string> = {
  scheduled: 'bg-sage/20 text-forest',
  confirmed: 'bg-jade/20 text-jade',
  in_progress: 'bg-saffron/20 text-saffron',
  completed: 'bg-stone/20 text-stone',
  cancelled: 'bg-alert/10 text-alert',
  no_show: 'bg-terracotta/10 text-terracotta',
};

const TITLES: Record<FilterType, string> = {
  today: "Today's consultations",
  upcoming: 'Upcoming consultations',
  history: 'Consultation history',
};

const CONSULTATION_CSV_HEADERS = ['Patient', 'Kyros ID', 'Condition', 'Type', 'Status', 'Scheduled (IST)'];

function consultationToRow(c: Consultation): string[] {
  return [
    c.patient_name,
    c.kyros_patient_id,
    formatCategory(c.condition_category),
    formatCategory(c.consultation_type),
    c.status.replace(/_/g, ' '),
    formatIST(c.scheduled_start_at),
  ];
}

export function ConsultationList({ filter }: { filter: FilterType }) {
  const { selected, toggle, toggleAll, clear, count } = useBulkSelect<string>();

  const { data, isLoading } = useQuery({
    queryKey: ['consultations', filter],
    queryFn: () =>
      apiFetch<ConsultationListResponse>(`/v1/doctor/consultations?filter=${filter}&page_size=50`),
    refetchInterval: filter === 'today' ? 30000 : undefined,
  });

  // Clear selection when switching tabs (today/upcoming/history).
  useEffect(() => {
    clear();
  }, [filter, clear]);

  const items = data?.items ?? [];
  const ids = items.map(c => c.id);
  const allSelected = items.length > 0 && count === items.length;

  const exportRows = (consultations: Consultation[], suffix: string) => {
    downloadCSV(
      `consultations-${filter}-${suffix}.csv`,
      CONSULTATION_CSV_HEADERS,
      consultations.map(consultationToRow),
    );
  };

  const handleExportSelected = () => {
    exportRows(items.filter(c => selected.has(c.id)), 'selected');
  };

  const handleExportAll = () => {
    exportRows(items, 'all');
  };

  return (
    <div className="px-8 py-8 max-w-4xl">
      <div className="flex items-center justify-between mb-2">
        <h1 className="font-display text-h2 text-forest font-medium">{TITLES[filter]}</h1>
        <button
          onClick={handleExportAll}
          disabled={items.length === 0}
          className="px-3 py-1.5 rounded border border-forest/30 font-body text-caption text-forest hover:bg-forest/5 disabled:opacity-40 transition-colors"
        >
          Export All CSV
        </button>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-1 mb-6 bg-white rounded-card p-1 w-fit">
        {(['today', 'upcoming', 'history'] as FilterType[]).map(f => (
          <Link
            key={f}
            to={`/consultations/${f}`}
            className={`px-4 py-1.5 rounded font-body text-caption font-medium transition-colors ${
              f === filter
                ? 'bg-forest text-ivory'
                : 'text-stone hover:text-ink'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </Link>
        ))}
      </div>

      <BulkActionBar count={count} onClear={clear} onExport={handleExportSelected} />

      <div className="bg-white rounded-card overflow-hidden">
        {isLoading ? (
          <p className="px-5 py-10 text-center font-body text-body text-stone">Loading…</p>
        ) : items.length === 0 ? (
          <p className="px-5 py-10 text-center font-body text-body text-stone">
            No {filter} consultations.
          </p>
        ) : (
          <ul className="divide-y divide-stone/10">
            <li className="flex items-center gap-3 px-5 py-3 bg-ivory border-b border-stone/10">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={() => toggleAll(ids)}
                aria-label="Select all consultations"
                className="w-4 h-4 rounded border-stone/30 text-forest focus:ring-forest accent-forest"
              />
              <span className="font-body text-caption text-stone font-semibold">Select all</span>
            </li>
            {items.map(c => (
              <li
                key={c.id}
                className={`flex items-center gap-3 px-5 ${selected.has(c.id) ? 'bg-sage/5' : 'hover:bg-ivory'} transition-colors`}
              >
                <input
                  type="checkbox"
                  checked={selected.has(c.id)}
                  onChange={() => toggle(c.id)}
                  aria-label={`Select consultation with ${c.patient_name}`}
                  className="w-4 h-4 rounded border-stone/30 text-forest focus:ring-forest accent-forest"
                />
                <Link
                  to={`/consultations/${c.id}`}
                  className="flex flex-1 items-center justify-between py-4"
                >
                  <div>
                    <p className="font-body text-body text-ink font-medium">{c.patient_name}</p>
                    <p className="font-body text-caption text-stone">
                      {formatCategory(c.condition_category)} · {c.kyros_patient_id}
                    </p>
                  </div>
                  <div className="text-right flex items-center gap-3">
                    <span
                      className={`px-2 py-0.5 rounded-full font-body text-caption font-medium ${STATUS_PILL[c.status] ?? 'bg-stone/10 text-stone'}`}
                    >
                      {c.status.replace('_', ' ')}
                    </span>
                    <p className="font-body text-caption text-stone whitespace-nowrap">
                      {formatIST(c.scheduled_start_at)}
                    </p>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
