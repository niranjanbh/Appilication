import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, FileText, Flag } from 'lucide-react';
import { apiFetch } from '../../lib/api';

interface PatientDetail {
  patient_id: string;
  kyros_patient_id: string;
  name: string;
  phone: string | null;
  email: string | null;
  primary_conditions: string[];
  allergies: string | null;
  chronic_conditions: string | null;
  current_medications: string | null;
  consultation_counts: Record<string, number>;
}

interface LabReportSummary {
  id: string;
  lab_name: string | null;
  report_date: string | null;
  status: string;
  original_filename: string;
  doctor_reviewed_by_id: string | null;
  patient_attention_flags: string[] | null;
}

interface PatientAdherence {
  patient_id: string;
  adherence_rate_30d: number;
  current_streak: number;
  longest_streak: number;
  last_missed_at: string | null;
  active_prescription_reminders: number;
}

function formatCategory(s: string) {
  return s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

// Colour the headline rate by adherence band (PDC convention): strong ≥90%,
// watch 70–89%, concern below 70%. Uses high-contrast tokens for WCAG AA.
function adherenceColor(rate: number): string {
  if (rate >= 0.9) return 'text-forest';
  if (rate >= 0.7) return 'text-saffron';
  return 'text-alert';
}

function days(n: number): string {
  return `${n} day${n !== 1 ? 's' : ''}`;
}

function InfoRow({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="flex gap-4 py-2.5 border-b border-stone/10 last:border-0">
      <dt className="font-body text-caption text-stone w-40 shrink-0">{label}</dt>
      <dd className="font-body text-body text-ink">{value || '—'}</dd>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="py-1">
      <dt className="font-body text-caption text-stone">{label}</dt>
      <dd className="font-body text-body text-ink font-semibold">{value}</dd>
    </div>
  );
}

export function PatientDetail() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['patient', id],
    queryFn: () => apiFetch<PatientDetail>(`/v1/doctor/patients/${id}`),
    enabled: !!id,
  });

  const { data: labReports } = useQuery({
    queryKey: ['patient-lab-reports', id],
    queryFn: () => apiFetch<LabReportSummary[]>(`/v1/doctor/patients/${id}/lab-reports`),
    enabled: !!id,
  });

  const { data: adherence, isLoading: adherenceLoading } = useQuery({
    queryKey: ['patient-adherence', id],
    queryFn: () => apiFetch<PatientAdherence>(`/v1/doctor/patients/${id}/adherence`),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="px-8 py-8">
        <p className="font-body text-body text-stone">Loading patient…</p>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="px-8 py-8">
        <Link to="/patients" className="inline-flex items-center gap-2 font-body text-caption text-stone hover:text-forest mb-6">
          <ArrowLeft size={14} /> Back to patients
        </Link>
        <p className="font-body text-body text-alert">Patient not found or access denied.</p>
      </div>
    );
  }

  const totalConsults = Object.values(data.consultation_counts).reduce((a, b) => a + b, 0);

  return (
    <div className="px-8 py-8 max-w-3xl">
      <Link to="/patients" className="inline-flex items-center gap-2 font-body text-caption text-stone hover:text-forest mb-6">
        <ArrowLeft size={14} /> Back to patients
      </Link>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="font-display text-h2 text-forest font-medium">{data.name}</h1>
          <p className="font-body text-caption text-stone mt-0.5">{data.kyros_patient_id}</p>
        </div>
        <div className="bg-forest text-ivory px-3 py-1.5 rounded-full font-body text-caption font-medium">
          {totalConsults} consultation{totalConsults !== 1 ? 's' : ''}
        </div>
      </div>

      {/* Conditions */}
      {data.primary_conditions.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-6">
          {data.primary_conditions.map(c => (
            <span key={c} className="bg-sage/20 text-forest font-body text-caption px-3 py-1 rounded-full">
              {formatCategory(c)}
            </span>
          ))}
        </div>
      )}

      {/* Demographics */}
      <div className="bg-white rounded-card p-5 mb-6">
        <h2 className="font-display text-h3 text-forest font-medium mb-3">Contact</h2>
        <dl>
          <InfoRow label="Phone" value={data.phone} />
          <InfoRow label="Email" value={data.email} />
        </dl>
      </div>

      {/* Clinical */}
      <div className="bg-white rounded-card p-5 mb-6">
        <h2 className="font-display text-h3 text-forest font-medium mb-3">Clinical summary</h2>
        <dl>
          <InfoRow label="Allergies" value={data.allergies} />
          <InfoRow label="Chronic conditions" value={data.chronic_conditions} />
          <InfoRow label="Current medications" value={data.current_medications} />
        </dl>
      </div>

      {/* Adherence */}
      <div className="bg-white rounded-card p-5 mb-6">
        <h2 className="font-display text-h3 text-forest font-medium mb-3">Adherence</h2>
        {adherenceLoading ? (
          <p className="font-body text-body text-stone">Loading…</p>
        ) : !adherence ||
          (adherence.active_prescription_reminders === 0 &&
            adherence.adherence_rate_30d === 0 &&
            adherence.current_streak === 0 &&
            adherence.longest_streak === 0 &&
            !adherence.last_missed_at) ? (
          <p className="font-body text-body text-stone">No reminders set up yet.</p>
        ) : (
          <>
            <div className="flex items-baseline gap-2 mb-4">
              <span className={`font-display text-h2 font-medium ${adherenceColor(adherence.adherence_rate_30d)}`}>
                {Math.round(adherence.adherence_rate_30d * 100)}%
              </span>
              <span className="font-body text-caption text-stone">30-day adherence</span>
            </div>
            <dl className="grid grid-cols-2 gap-x-6">
              <Stat label="Current streak" value={days(adherence.current_streak)} />
              <Stat label="Longest streak" value={days(adherence.longest_streak)} />
              <Stat label="Active Rx reminders" value={String(adherence.active_prescription_reminders)} />
              <Stat
                label="Last missed"
                value={
                  adherence.last_missed_at
                    ? new Date(adherence.last_missed_at).toLocaleDateString('en-IN')
                    : 'None'
                }
              />
            </dl>
          </>
        )}
      </div>

      {/* Consultation breakdown */}
      {Object.keys(data.consultation_counts).length > 0 && (
        <div className="bg-white rounded-card p-5 mb-6">
          <h2 className="font-display text-h3 text-forest font-medium mb-3">Consultations</h2>
          <dl className="space-y-1">
            {Object.entries(data.consultation_counts).map(([status, count]) => (
              <div key={status} className="flex justify-between font-body text-body text-ink py-1 border-b border-stone/10 last:border-0">
                <dt className="text-stone capitalize">{status.replace('_', ' ')}</dt>
                <dd className="font-semibold">{count}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {/* Lab reports */}
      <div className="bg-white rounded-card p-5">
        <h2 className="font-display text-h3 text-forest font-medium mb-3">Lab Reports</h2>
        {!labReports || labReports.length === 0 ? (
          <p className="font-body text-body text-stone">No lab reports uploaded yet.</p>
        ) : (
          <div className="divide-y divide-stone/10">
            {labReports.map(report => (
              <div key={report.id} className="flex items-center justify-between py-3">
                <div className="flex items-center gap-3">
                  <FileText size={16} className="text-stone shrink-0" />
                  <div>
                    <p className="font-body text-body text-ink">
                      {report.lab_name ?? report.original_filename}
                    </p>
                    <p className="font-body text-caption text-stone">
                      {report.report_date
                        ? new Date(report.report_date).toLocaleDateString('en-IN')
                        : 'Date unknown'}
                      {' · '}
                      <span className="capitalize">{report.status.replace('_', ' ')}</span>
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {report.patient_attention_flags && report.patient_attention_flags.length > 0 && (
                    <span className="flex items-center gap-1 font-body text-caption text-saffron">
                      <Flag size={12} />
                      {report.patient_attention_flags.length} flagged
                    </span>
                  )}
                  {report.doctor_reviewed_by_id && (
                    <span className="font-body text-caption text-sage">Reviewed</span>
                  )}
                  <Link
                    to={`/patients/${id}/lab-reports/${report.id}`}
                    className="font-body text-caption text-forest hover:underline"
                  >
                    {report.doctor_reviewed_by_id ? 'Edit annotations' : 'Annotate'}
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
