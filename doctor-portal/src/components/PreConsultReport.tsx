/**
 * Pre-consultation report panel — doctor view.
 *
 * Displays: lab summary, adherence, wearable stats, patient flags.
 * Information symmetry: identical content to patient view.
 * Doctor-only field: editable prep notes (doctor_notes_pre_consult).
 */

import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckCircle, RefreshCw } from 'lucide-react';
import { apiFetch } from '../lib/api';

// ── Types ─────────────────────────────────────────────────────────────────────

interface BiomarkerSummary {
  name: string;
  value: string | null;
  unit: string | null;
  flag: 'high' | 'low' | null;
  ref_low: string | null;
  ref_high: string | null;
  trend: 'up' | 'down' | 'stable';
}

interface LabSummary {
  biomarkers: BiomarkerSummary[];
  window_days: number;
}

interface AdherenceSummary {
  compliance_pct: number | null;
  taken: number;
  skipped: number;
  snoozed: number;
  total: number;
  window_days: number;
}

interface WearableSummary {
  avg_steps: number | null;
  avg_resting_hr: number | null;
  avg_sleep_hours: number | null;
  window_days: number;
}

interface DoctorPreConsultReport {
  id: string;
  consultation_id: string | null;
  generated_at: string;
  lab_summary: LabSummary | null;
  adherence_summary: AdherenceSummary | null;
  wearable_summary: WearableSummary | null;
  patient_flags: { flags: string[] } | null;
  intake_responses: Record<string, unknown> | null;
  pdf_url: string | null;
  doctor_notes_pre_consult: string | null;
  doctor_reviewed_at: string | null;
}

interface GenerateResponse {
  task_id: string;
  status: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatIST(iso: string) {
  return new Date(iso).toLocaleString('en-IN', {
    day: 'numeric', month: 'long', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: true,
    timeZone: 'Asia/Kolkata',
  });
}

function trendSymbol(t: BiomarkerSummary['trend']): string {
  return t === 'up' ? '↑' : t === 'down' ? '↓' : '↔';
}

function trendClass(t: BiomarkerSummary['trend']): string {
  return t === 'up' ? 'text-terracotta' : t === 'down' ? 'text-forest' : 'text-stone';
}

// ── Sub-components ────────────────────────────────────────────────────────────

function LabSummaryTable({ summary }: { summary: LabSummary | null }) {
  if (!summary?.biomarkers?.length) {
    return <p className="font-body text-caption text-stone">No lab data in the last 90 days.</p>;
  }
  return (
    <table className="w-full text-sm border-collapse">
      <thead>
        <tr className="bg-navy/10 text-left">
          <th className="px-3 py-2 font-heading text-caption text-ink">Biomarker</th>
          <th className="px-3 py-2 font-heading text-caption text-ink">Latest Value</th>
          <th className="px-3 py-2 font-heading text-caption text-ink">Trend</th>
          <th className="px-3 py-2 font-heading text-caption text-ink">Reference</th>
        </tr>
      </thead>
      <tbody>
        {summary.biomarkers.map((bm) => (
          <tr
            key={bm.name}
            className={`border-b border-stone/10 last:border-0 ${bm.flag ? 'bg-saffron/10' : ''}`}
          >
            <td className="px-3 py-2 font-body text-body text-ink capitalize">{bm.name}</td>
            <td className={`px-3 py-2 font-body text-body ${bm.flag === 'high' ? 'text-terracotta' : bm.flag === 'low' ? 'text-forest' : 'text-ink'}`}>
              {bm.value ?? '—'} {bm.unit ?? ''}
            </td>
            <td className={`px-3 py-2 font-body text-body font-semibold ${trendClass(bm.trend)}`}>
              {trendSymbol(bm.trend)}
            </td>
            <td className="px-3 py-2 font-body text-caption text-stone">
              {bm.ref_low ?? '—'} – {bm.ref_high ?? '—'} {bm.unit ?? ''}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function AdherenceSection({ summary }: { summary: AdherenceSummary | null }) {
  if (!summary || summary.compliance_pct === null) {
    return <p className="font-body text-caption text-stone">No medication adherence data.</p>;
  }
  const pct = summary.compliance_pct;
  const barColor = pct >= 80 ? 'bg-forest' : pct >= 50 ? 'bg-saffron' : 'bg-terracotta';
  const textColor = pct >= 80 ? 'text-forest' : pct >= 50 ? 'text-saffron' : 'text-terracotta';
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3">
        <div className="flex-1 h-2.5 bg-stone/20 rounded-full overflow-hidden">
          <div className={`h-full ${barColor} rounded-full`} style={{ width: `${pct}%` }} />
        </div>
        <span className={`font-heading text-lg ${textColor}`}>{pct}%</span>
      </div>
      <div className="flex gap-4 font-body text-caption text-stone">
        <span>Taken: {summary.taken}</span>
        <span>Skipped: {summary.skipped}</span>
        <span>Snoozed: {summary.snoozed}</span>
        <span className="text-stone/60">/ {summary.total} total (last {summary.window_days}d)</span>
      </div>
    </div>
  );
}

function WearableSection({ summary }: { summary: WearableSummary | null }) {
  if (!summary) {
    return <p className="font-body text-caption text-stone">No wearable data.</p>;
  }
  const stats = [
    { label: 'Avg Steps', value: summary.avg_steps?.toLocaleString('en-IN') ?? '—' },
    { label: 'Resting HR', value: summary.avg_resting_hr ? `${summary.avg_resting_hr} bpm` : '—' },
    { label: 'Sleep', value: summary.avg_sleep_hours ? `${summary.avg_sleep_hours} hrs` : '—' },
  ];
  return (
    <div className="flex gap-3">
      {stats.map((s) => (
        <div key={s.label} className="flex-1 bg-sage/20 rounded-xl p-3 text-center">
          <p className="font-heading text-xl text-ink">{s.value}</p>
          <p className="font-body text-xs text-stone mt-1">{s.label} (last {summary.window_days}d)</p>
        </div>
      ))}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function PreConsultReport({ consultationId }: { consultationId: string }) {
  const qc = useQueryClient();
  const [notes, setNotes] = useState<string>('');
  const [notesSaved, setNotesSaved] = useState(false);

  const { data: report, isLoading, isError } = useQuery<DoctorPreConsultReport>({
    queryKey: ['pre-consult-report', consultationId],
    queryFn: () =>
      apiFetch<DoctorPreConsultReport>(
        `/v1/doctor/consultations/${consultationId}/pre-consult-report`,
      ),
    retry: false,
  });

  useEffect(() => {
    if (report?.doctor_notes_pre_consult) {
      setNotes(report.doctor_notes_pre_consult);
    }
  }, [report?.doctor_notes_pre_consult]);

  const generateMutation = useMutation<GenerateResponse>({
    mutationFn: () =>
      apiFetch<GenerateResponse>(
        `/v1/doctor/consultations/${consultationId}/pre-consult-report/generate`,
        { method: 'POST' },
      ),
    onSuccess: () => {
      // Poll until report appears (simple approach: invalidate after 6 s)
      setTimeout(() => qc.invalidateQueries({ queryKey: ['pre-consult-report', consultationId] }), 6000);
    },
  });

  const saveNotesMutation = useMutation({
    mutationFn: (notesText: string) =>
      apiFetch<DoctorPreConsultReport>(
        `/v1/doctor/consultations/${consultationId}/pre-consult-report`,
        {
          method: 'PATCH',
          body: JSON.stringify({ doctor_notes_pre_consult: notesText }),
        },
      ),
    onSuccess: () => {
      setNotesSaved(true);
      setTimeout(() => setNotesSaved(false), 3000);
      qc.invalidateQueries({ queryKey: ['pre-consult-report', consultationId] });
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-forest border-t-transparent" />
        <span className="ml-3 font-body text-caption text-stone">Loading report…</span>
      </div>
    );
  }

  if (isError || !report) {
    return (
      <div className="space-y-3 py-4">
        <p className="font-body text-caption text-stone">
          No pre-consultation report yet.
        </p>
        <button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          className="flex items-center gap-2 rounded-lg bg-forest px-4 py-2 font-body text-sm text-white hover:bg-forest/90 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${generateMutation.isPending ? 'animate-spin' : ''}`} />
          {generateMutation.isPending ? 'Generating…' : 'Generate Report'}
        </button>
        {generateMutation.isSuccess && (
          <p className="font-body text-caption text-stone">
            Report queued — refresh in a few seconds.
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <p className="font-body text-caption text-stone">
            Generated {formatIST(report.generated_at)}
            {report.doctor_reviewed_at && (
              <> · Reviewed {formatIST(report.doctor_reviewed_at)}</>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          {report.pdf_url && (
            <a
              href={`/v1/doctor/consultations/${consultationId}/pre-consult-report/download`}
              target="_blank"
              rel="noreferrer"
              className="rounded-lg border border-stone/20 px-3 py-1.5 font-body text-sm text-ink hover:bg-stone/10"
            >
              PDF
            </a>
          )}
          <button
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            className="flex items-center gap-1.5 rounded-lg border border-stone/20 px-3 py-1.5 font-body text-sm text-ink hover:bg-stone/10 disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${generateMutation.isPending ? 'animate-spin' : ''}`} />
            Regenerate
          </button>
        </div>
      </div>

      {/* Lab Summary */}
      <section>
        <h3 className="mb-3 font-heading text-base text-ink">
          Lab Summary (last {report.lab_summary?.window_days ?? 90} days)
        </h3>
        <LabSummaryTable summary={report.lab_summary} />
      </section>

      {/* Adherence */}
      <section>
        <h3 className="mb-3 font-heading text-base text-ink">Medication Adherence</h3>
        <AdherenceSection summary={report.adherence_summary} />
      </section>

      {/* Wearable */}
      <section>
        <h3 className="mb-3 font-heading text-base text-ink">Health Summary</h3>
        <WearableSection summary={report.wearable_summary} />
      </section>

      {/* Patient flags */}
      <section>
        <h3 className="mb-3 font-heading text-base text-ink">Patient-Flagged Concerns</h3>
        {(report.patient_flags?.flags?.length ?? 0) === 0 ? (
          <p className="font-body text-caption text-stone">None flagged.</p>
        ) : (
          <ul className="list-disc list-inside space-y-1">
            {report.patient_flags!.flags.map((f, i) => (
              <li key={i} className="font-body text-body text-ink">{f}</li>
            ))}
          </ul>
        )}
      </section>

      {/* Doctor prep notes — doctor-only field */}
      <section className="rounded-xl border border-jade/30 bg-jade/5 p-4">
        <h3 className="mb-2 font-heading text-base text-ink">Your Prep Notes</h3>
        <p className="mb-3 font-body text-caption text-stone">
          Private to you — not visible to the patient.
        </p>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={5}
          placeholder="Add your pre-consultation preparation notes here…"
          className="w-full rounded-lg border border-stone/20 bg-white px-3 py-2 font-body text-sm text-ink placeholder:text-stone/40 focus:border-forest focus:outline-none focus:ring-1 focus:ring-forest resize-y"
        />
        <div className="mt-2 flex items-center gap-3">
          <button
            onClick={() => saveNotesMutation.mutate(notes)}
            disabled={saveNotesMutation.isPending}
            className="rounded-lg bg-forest px-4 py-2 font-body text-sm text-white hover:bg-forest/90 disabled:opacity-50"
          >
            {saveNotesMutation.isPending ? 'Saving…' : 'Save Notes'}
          </button>
          {notesSaved && (
            <span className="flex items-center gap-1.5 font-body text-caption text-forest">
              <CheckCircle className="h-4 w-4" />
              Saved
            </span>
          )}
          {saveNotesMutation.isError && (
            <span className="font-body text-caption text-terracotta">Save failed — try again.</span>
          )}
        </div>
      </section>
    </div>
  );
}
