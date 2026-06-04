import { useState, type FormEvent } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ChevronLeft, Flag } from 'lucide-react';
import { apiFetch } from '../../lib/api';

interface LabReport {
  id: string;
  patient_id: string;
  lab_name: string | null;
  report_date: string | null;
  status: string;
  original_filename: string;
  parsed_json: Record<string, unknown> | null;
  ocr_confidence_avg: number | null;
  doctor_reviewed_by_id: string | null;
  doctor_commentary: Record<string, string> | null;
  patient_attention_flags: string[] | null;
}

type Biomarker = { name: string; value: unknown; unit?: unknown; reference_range?: unknown };

function parseBiomarkers(parsed: Record<string, unknown> | null): Biomarker[] {
  if (!parsed) return [];
  const items = parsed['biomarkers'] ?? parsed['tests'] ?? parsed['results'];
  if (Array.isArray(items)) {
    return items.map((item: unknown) => {
      if (typeof item === 'object' && item !== null) {
        const o = item as Record<string, unknown>;
        return {
          name: String(o['name'] ?? o['test_name'] ?? o['parameter'] ?? ''),
          value: o['value'] ?? o['result'] ?? null,
          unit: o['unit'] ?? null,
          reference_range: o['reference_range'] ?? o['normal_range'] ?? null,
        };
      }
      return { name: String(item), value: null };
    });
  }
  // flat key-value object
  return Object.entries(parsed).map(([name, value]) => ({ name, value }));
}

export function LabReportAnnotate() {
  const { id: patientId, reportId } = useParams<{ id: string; reportId: string }>();
  const queryClient = useQueryClient();

  const { data: report, isLoading } = useQuery({
    queryKey: ['lab-report', patientId, reportId],
    queryFn: () =>
      apiFetch<LabReport>(`/v1/doctor/patients/${patientId}/lab-reports/${reportId}`),
    enabled: !!patientId && !!reportId,
  });

  const [commentary, setCommentary] = useState<Record<string, string>>({});
  const [flagged, setFlagged] = useState<Set<string>>(new Set());
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initialise from existing annotations when data loads
  const [initialised, setInitialised] = useState(false);
  if (report && !initialised) {
    setCommentary(report.doctor_commentary ?? {});
    setFlagged(new Set(report.patient_attention_flags ?? []));
    setInitialised(true);
  }

  const annotate = useMutation({
    mutationFn: (body: { commentary: Record<string, string>; patient_attention_flags: string[] }) =>
      apiFetch(`/v1/doctor/lab-reports/${reportId}/annotate`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lab-report', patientId, reportId] });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
    onError: (e: Error) => setError(e.message),
  });

  function toggleFlag(name: string) {
    setFlagged(prev => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  function handleSave(e: FormEvent) {
    e.preventDefault();
    setError(null);
    annotate.mutate({
      commentary: Object.fromEntries(
        Object.entries(commentary).filter(([, v]) => v.trim().length > 0)
      ),
      patient_attention_flags: [...flagged],
    });
  }

  if (isLoading || !report) {
    return (
      <div className="px-8 py-8">
        <p className="font-body text-body text-stone">Loading report…</p>
      </div>
    );
  }

  const biomarkers = parseBiomarkers(report.parsed_json);

  return (
    <div className="px-8 py-8 max-w-3xl">
      <Link
        to={`/patients/${patientId}`}
        className="inline-flex items-center gap-1 font-body text-caption text-stone hover:text-forest mb-4"
      >
        <ChevronLeft size={14} />
        Back to patient
      </Link>

      <h1 className="font-display text-h2 text-forest font-medium mb-1">
        Lab Report Review
      </h1>
      {report.lab_name && (
        <p className="font-body text-body text-stone mb-1">{report.lab_name}</p>
      )}
      {report.report_date && (
        <p className="font-body text-caption text-stone mb-4">
          Report date: {new Date(report.report_date).toLocaleDateString('en-IN')}
        </p>
      )}
      {report.ocr_confidence_avg !== null && report.ocr_confidence_avg < 0.85 && (
        <div className="bg-saffron/15 border border-saffron/30 text-ink font-body text-caption rounded-md px-4 py-3 mb-4">
          OCR confidence is low ({Math.round((report.ocr_confidence_avg ?? 0) * 100)}%). Review biomarker values before annotating.
        </div>
      )}

      {error && (
        <div className="bg-alert/10 border border-alert/30 text-alert font-body text-caption rounded-md px-4 py-3 mb-4">
          {error}
        </div>
      )}
      {saved && (
        <div className="bg-sage/20 border border-sage/40 text-forest font-body text-caption rounded-md px-4 py-3 mb-4">
          Annotations saved. Patient will see them on next view.
        </div>
      )}

      {biomarkers.length === 0 ? (
        <div className="bg-white rounded-card p-5 mb-6">
          <p className="font-body text-body text-stone">
            No parsed biomarkers found. The report may still be processing, or the OCR did not extract structured data.
          </p>
        </div>
      ) : (
        <form onSubmit={handleSave}>
          <div className="bg-white rounded-card p-5 mb-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-display text-h3 text-forest font-medium">Biomarkers</h2>
              <span className="font-body text-caption text-stone">
                <Flag size={12} className="inline mr-1" />
                Flag biomarkers for patient attention
              </span>
            </div>

            <div className="space-y-5">
              {biomarkers.map(bm => (
                <div key={bm.name} className="border-b border-stone/10 pb-5 last:border-0 last:pb-0">
                  <div className="flex items-start justify-between gap-4 mb-2">
                    <div>
                      <p className="font-body text-body text-ink font-medium">{bm.name}</p>
                      <p className="font-body text-caption text-stone">
                        {bm.value != null ? String(bm.value) : '—'}
                        {bm.unit ? ` ${String(bm.unit)}` : ''}
                        {bm.reference_range ? (
                          <span className="ml-2 text-stone/60">
                            (ref: {String(bm.reference_range)})
                          </span>
                        ) : null}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => toggleFlag(bm.name)}
                      className={`flex items-center gap-1 shrink-0 font-body text-caption px-3 py-1.5 rounded-full border transition-colors ${
                        flagged.has(bm.name)
                          ? 'bg-saffron/20 border-saffron/40 text-ink'
                          : 'bg-transparent border-stone/30 text-stone hover:border-saffron/40'
                      }`}
                    >
                      <Flag size={12} />
                      {flagged.has(bm.name) ? 'Flagged' : 'Flag'}
                    </button>
                  </div>
                  <textarea
                    rows={2}
                    value={commentary[bm.name] ?? ''}
                    onChange={e =>
                      setCommentary(prev => ({ ...prev, [bm.name]: e.target.value }))
                    }
                    placeholder="Add commentary for this biomarker (optional)…"
                    className="w-full border border-stone/30 rounded-md px-3 py-2 font-body text-caption text-ink focus:outline-none focus:border-forest resize-none"
                  />
                </div>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={annotate.isPending}
            className="bg-forest text-ivory font-body text-body font-semibold px-6 py-2.5 rounded-md hover:bg-jade transition-colors disabled:opacity-50"
          >
            {annotate.isPending ? 'Saving…' : 'Save annotations'}
          </button>
        </form>
      )}
    </div>
  );
}
