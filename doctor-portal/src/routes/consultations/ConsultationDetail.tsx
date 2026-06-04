import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { apiFetch } from '../../lib/api';
import { ConsultationVideoLayout } from '../../components/ConsultationVideoLayout';
import { PreConsultReport } from '../../components/PreConsultReport';

interface ConsultationDetail {
  id: string;
  patient_id: string;
  patient_name: string;
  kyros_patient_id: string;
  condition_category: string;
  consultation_type: string;
  scheduled_start_at: string;
  scheduled_end_at: string;
  actual_start_at: string | null;
  actual_end_at: string | null;
  status: string;
  video_room_id: string | null;
  consultation_fee_paise: number;
  cancellation_reason: string | null;
  recording_consent: boolean;
}

const LAYOUT_STATUSES = new Set(['scheduled', 'confirmed', 'in_progress', 'completed']);

function formatIST(iso: string) {
  return new Date(iso).toLocaleString('en-IN', {
    day: 'numeric', month: 'long', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: true,
    timeZone: 'Asia/Kolkata',
  });
}

function formatCategory(s: string) {
  return s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function InfoRow({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="flex gap-4 py-2.5 border-b border-stone/10 last:border-0">
      <dt className="font-body text-caption text-stone w-44 shrink-0">{label}</dt>
      <dd className="font-body text-body text-ink">{value || '—'}</dd>
    </div>
  );
}

const STATUS_PILL: Record<string, string> = {
  scheduled: 'bg-sage/20 text-forest',
  confirmed: 'bg-jade/20 text-jade',
  in_progress: 'bg-saffron/20 text-saffron',
  completed: 'bg-stone/20 text-stone',
  cancelled: 'bg-alert/10 text-alert',
};

export function ConsultationDetail() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['consultation', id],
    queryFn: () => apiFetch<ConsultationDetail>(`/v1/doctor/consultations/${id}`),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="px-8 py-8">
        <p className="font-body text-body text-stone">Loading…</p>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="px-8 py-8">
        <Link to="/consultations/today" className="inline-flex items-center gap-2 font-body text-caption text-stone hover:text-forest mb-6">
          <ArrowLeft size={14} /> Back to consultations
        </Link>
        <p className="font-body text-body text-alert">Consultation not found or access denied.</p>
      </div>
    );
  }

  // Active and completed consultations get the full consultation room layout.
  if (LAYOUT_STATUSES.has(data.status)) {
    return (
      <div>
        <div className="flex items-center gap-4 px-6 py-3 border-b border-stone/10 bg-white">
          <Link to="/consultations/today" className="inline-flex items-center gap-2 font-body text-caption text-stone hover:text-forest">
            <ArrowLeft size={14} /> Back
          </Link>
          <div className="flex items-center gap-2">
            <span className="font-body text-body font-semibold text-forest">{data.patient_name}</span>
            <span className="font-body text-caption text-stone">·</span>
            <span className="font-body text-caption text-stone">{formatCategory(data.condition_category)}</span>
            <span className={`ml-1 px-2.5 py-0.5 rounded-full font-body text-caption font-medium ${STATUS_PILL[data.status] ?? 'bg-stone/10 text-stone'}`}>
              {data.status.replace('_', ' ')}
            </span>
          </div>
          <span className="ml-auto font-body text-caption text-stone">
            {formatIST(data.scheduled_start_at)}
          </span>
        </div>
        <ConsultationVideoLayout consultation={data} />
      </div>
    );
  }

  // Cancelled / no-show: simple info card.
  return (
    <div className="px-8 py-8 max-w-3xl">
      <Link to="/consultations/today" className="inline-flex items-center gap-2 font-body text-caption text-stone hover:text-forest mb-6">
        <ArrowLeft size={14} /> Back
      </Link>

      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="font-display text-h2 text-forest font-medium">{data.patient_name}</h1>
            <span className={`px-2.5 py-0.5 rounded-full font-body text-caption font-medium ${STATUS_PILL[data.status] ?? 'bg-stone/10 text-stone'}`}>
              {data.status.replace('_', ' ')}
            </span>
          </div>
          <Link
            to={`/patients/${data.patient_id}`}
            className="font-body text-caption text-stone hover:text-forest transition-colors"
          >
            {data.kyros_patient_id} · View patient profile →
          </Link>
        </div>
      </div>

      <div className="bg-white rounded-card p-5 mb-5">
        <h2 className="font-display text-h3 text-forest font-medium mb-3">Consultation details</h2>
        <dl>
          <InfoRow label="Condition" value={formatCategory(data.condition_category)} />
          <InfoRow label="Type" value={data.consultation_type === 'initial' ? 'Initial consultation' : 'Follow-up'} />
          <InfoRow label="Scheduled" value={formatIST(data.scheduled_start_at)} />
          <InfoRow label="Fee" value={`₹${Math.round(data.consultation_fee_paise / 100)}`} />
          {data.actual_start_at && <InfoRow label="Started at" value={formatIST(data.actual_start_at)} />}
          {data.actual_end_at && <InfoRow label="Ended at" value={formatIST(data.actual_end_at)} />}
          {data.cancellation_reason && <InfoRow label="Cancellation reason" value={data.cancellation_reason} />}
        </dl>
      </div>

      <div className="bg-white rounded-card p-5">
        <h2 className="font-display text-h3 text-forest font-medium mb-4">Pre-Consultation Report</h2>
        <PreConsultReport consultationId={data.id} />
      </div>
    </div>
  );
}
