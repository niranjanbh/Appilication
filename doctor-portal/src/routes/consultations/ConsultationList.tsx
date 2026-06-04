import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { apiFetch } from '../../lib/api';

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

export function ConsultationList({ filter }: { filter: FilterType }) {
  const { data, isLoading } = useQuery({
    queryKey: ['consultations', filter],
    queryFn: () =>
      apiFetch<ConsultationListResponse>(`/v1/doctor/consultations?filter=${filter}&page_size=50`),
    refetchInterval: filter === 'today' ? 30000 : undefined,
  });

  return (
    <div className="px-8 py-8 max-w-4xl">
      <h1 className="font-display text-h2 text-forest font-medium mb-2">{TITLES[filter]}</h1>

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

      <div className="bg-white rounded-card overflow-hidden">
        {isLoading ? (
          <p className="px-5 py-10 text-center font-body text-body text-stone">Loading…</p>
        ) : !data || data.items.length === 0 ? (
          <p className="px-5 py-10 text-center font-body text-body text-stone">
            No {filter} consultations.
          </p>
        ) : (
          <ul className="divide-y divide-stone/10">
            {data.items.map(c => (
              <li key={c.id}>
                <Link
                  to={`/consultations/${c.id}`}
                  className="flex items-center justify-between px-5 py-4 hover:bg-ivory transition-colors"
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
