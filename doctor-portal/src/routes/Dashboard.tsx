import { useQuery } from '@tanstack/react-query';
import { CalendarClock, Users } from 'lucide-react';
import { Link } from 'react-router-dom';
import { apiFetch } from '../lib/api';

interface Consultation {
  id: string;
  patient_name: string;
  condition_category: string;
  scheduled_start_at: string;
  status: string;
  video_room_id: string | null;
}

interface ConsultationList {
  items: Consultation[];
  total: int;
}

type int = number;

function formatIST(iso: string) {
  return new Date(iso).toLocaleTimeString('en-IN', {
    hour: '2-digit', minute: '2-digit', hour12: true, timeZone: 'Asia/Kolkata',
  });
}

function formatCategory(s: string) {
  return s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function minutesUntil(iso: string) {
  return Math.round((new Date(iso).getTime() - Date.now()) / 60000);
}

function CountdownChip({ iso }: { iso: string }) {
  const mins = minutesUntil(iso);
  if (mins < 0) return <span className="text-stone">In progress</span>;
  if (mins < 60) return <span className="text-saffron font-semibold">in {mins} min</span>;
  return <span className="text-stone">at {formatIST(iso)}</span>;
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    scheduled: 'bg-sage/20 text-forest',
    confirmed: 'bg-jade/20 text-jade',
    in_progress: 'bg-saffron/20 text-saffron',
    completed: 'bg-stone/20 text-stone',
    cancelled: 'bg-alert/10 text-alert',
  };
  return (
    <span className={`px-2 py-0.5 rounded-full font-body text-caption font-medium ${map[status] ?? 'bg-stone/10 text-stone'}`}>
      {status.replace('_', ' ')}
    </span>
  );
}

export function Dashboard() {
  const today = useQuery({
    queryKey: ['consultations', 'today'],
    queryFn: () => apiFetch<ConsultationList>('/v1/doctor/consultations?filter=today&page_size=50'),
    refetchInterval: 30000,
  });

  const upcoming = useQuery({
    queryKey: ['consultations', 'upcoming-count'],
    queryFn: () => apiFetch<ConsultationList>('/v1/doctor/consultations?filter=upcoming&page_size=1'),
  });

  const todayList = today.data?.items ?? [];
  const nextUp = todayList.find(c => minutesUntil(c.scheduled_start_at) > -30);

  return (
    <div className="px-8 py-8 max-w-4xl">
      <h1 className="font-display text-h2 text-forest font-medium mb-1">Dashboard</h1>
      <p className="font-body text-body text-stone mb-8">
        {new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'Asia/Kolkata' })}
      </p>

      {/* Quick stats */}
      <div className="grid grid-cols-2 gap-4 mb-8">
        <div className="bg-white rounded-card p-5 flex items-center gap-4">
          <CalendarClock size={20} className="text-forest shrink-0" />
          <div>
            <p className="font-display text-h2 text-forest font-medium">{today.data?.total ?? '—'}</p>
            <p className="font-body text-caption text-stone">Today's consultations</p>
          </div>
        </div>
        <div className="bg-white rounded-card p-5 flex items-center gap-4">
          <Users size={20} className="text-jade shrink-0" />
          <div>
            <p className="font-display text-h2 text-forest font-medium">{upcoming.data?.total ?? '—'}</p>
            <p className="font-body text-caption text-stone">Upcoming scheduled</p>
          </div>
        </div>
      </div>

      {/* Next up */}
      {nextUp && (
        <div className="bg-peach-mist rounded-card p-5 mb-8 flex items-center justify-between">
          <div>
            <p className="font-body text-caption text-stone mb-0.5">Next consultation</p>
            <p className="font-display text-h3 text-forest font-medium">{nextUp.patient_name}</p>
            <p className="font-body text-body text-stone">{formatCategory(nextUp.condition_category)}</p>
          </div>
          <div className="text-right">
            <CountdownChip iso={nextUp.scheduled_start_at} />
            {nextUp.video_room_id && (
              <div className="mt-2">
                <Link
                  to={`/consultations/${nextUp.id}`}
                  className="inline-block bg-forest text-ivory font-body text-caption font-semibold px-4 py-2 rounded-md hover:bg-jade transition-colors"
                >
                  View &amp; join
                </Link>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Today's list */}
      <div className="bg-white rounded-card overflow-hidden">
        <div className="px-5 py-4 border-b border-stone/10">
          <h2 className="font-display text-h3 text-forest font-medium">Today's queue</h2>
        </div>
        {today.isLoading ? (
          <p className="px-5 py-8 font-body text-body text-stone text-center">Loading…</p>
        ) : todayList.length === 0 ? (
          <p className="px-5 py-8 font-body text-body text-stone text-center">No consultations scheduled today.</p>
        ) : (
          <ul className="divide-y divide-stone/10">
            {todayList.map(c => (
              <li key={c.id}>
                <Link
                  to={`/consultations/${c.id}`}
                  className="flex items-center justify-between px-5 py-4 hover:bg-ivory transition-colors"
                >
                  <div>
                    <p className="font-body text-body text-ink font-medium">{c.patient_name}</p>
                    <p className="font-body text-caption text-stone">{formatCategory(c.condition_category)}</p>
                  </div>
                  <div className="text-right flex items-center gap-3">
                    <StatusBadge status={c.status} />
                    <CountdownChip iso={c.scheduled_start_at} />
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
