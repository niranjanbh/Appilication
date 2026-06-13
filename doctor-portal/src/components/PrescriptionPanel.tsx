import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FileText, Plus, Trash2 } from 'lucide-react';
import { apiFetch } from '../lib/api';

interface PrescriptionItem {
  drug_generic_name: string;
  drug_form: string;
  dosage: string;
  frequency: string;
  duration_days: number | null;
  instructions: string | null;
  refill_allowed: boolean;
}

interface PrescriptionRead {
  id: string;
  consultation_id: string;
  status: 'draft' | 'signed' | 'dispensed' | 'cancelled';
  signed_at: string | null;
  pdf_url: string | null;
  version: number;
  diagnosis_note: string | null;
  general_instructions: string | null;
  items: (PrescriptionItem & { id: string; order_index: number })[];
}

const DRUG_FORMS = ['tablet', 'capsule', 'syrup', 'injection', 'topical', 'other'] as const;

const EMPTY_ITEM: PrescriptionItem = {
  drug_generic_name: '',
  drug_form: 'tablet',
  dosage: '',
  frequency: '',
  duration_days: null,
  instructions: null,
  refill_allowed: false,
};

function formatIST(iso: string) {
  return new Date(iso).toLocaleString('en-IN', {
    day: 'numeric', month: 'long', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: true,
    timeZone: 'Asia/Kolkata',
  });
}

function isItemComplete(item: PrescriptionItem): boolean {
  return !!(item.drug_generic_name.trim() && item.dosage.trim() && item.frequency.trim());
}

function SignedSummary({ rx }: { rx: PrescriptionRead }) {
  return (
    <div className="bg-sage/10 border border-sage/30 rounded-card p-4 mb-3">
      <div className="flex items-center justify-between mb-2">
        <p className="font-body text-body font-semibold text-forest">
          Signed prescription · v{rx.version}
        </p>
        {rx.signed_at && (
          <span className="font-body text-caption text-stone">{formatIST(rx.signed_at)}</span>
        )}
      </div>
      <ul className="mb-2">
        {rx.items.map(item => (
          <li key={item.id} className="font-body text-caption text-ink py-0.5">
            <span className="font-semibold">{item.drug_generic_name}</span>
            {' · '}{item.drug_form} · {item.dosage} · {item.frequency}
            {item.duration_days ? ` · ${item.duration_days} days` : ''}
          </li>
        ))}
      </ul>
      {rx.pdf_url ? (
        <a
          href={rx.pdf_url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 font-body text-caption font-semibold text-forest hover:underline"
        >
          <FileText size={12} /> View PDF
        </a>
      ) : (
        <p className="font-body text-caption text-stone">PDF is being generated…</p>
      )}
    </div>
  );
}

interface PrescriptionPanelProps {
  consultationId: string;
}

export function PrescriptionPanel({ consultationId }: PrescriptionPanelProps) {
  const qc = useQueryClient();

  const { data: prescriptions, isLoading } = useQuery({
    queryKey: ['prescriptions', consultationId],
    queryFn: () => apiFetch<PrescriptionRead[]>(`/v1/doctor/consultations/${consultationId}/prescriptions`),
  });

  const draft = prescriptions?.find(rx => rx.status === 'draft') ?? null;
  const signed = prescriptions?.filter(rx => rx.status === 'signed' || rx.status === 'dispensed') ?? [];

  const [diagnosisNote, setDiagnosisNote] = useState('');
  const [generalInstructions, setGeneralInstructions] = useState('');
  const [items, setItems] = useState<PrescriptionItem[]>([{ ...EMPTY_ITEM }]);
  const [reviewing, setReviewing] = useState(false);
  const [hydratedDraftId, setHydratedDraftId] = useState<string | null>(null);

  // Load the server draft into the form once per draft id (not on every refetch,
  // which would clobber in-progress edits).
  useEffect(() => {
    if (draft && draft.id !== hydratedDraftId) {
      setDiagnosisNote(draft.diagnosis_note ?? '');
      setGeneralInstructions(draft.general_instructions ?? '');
      setItems(
        draft.items.length > 0
          ? draft.items.map(({ id: _id, order_index: _oi, ...item }) => ({ ...item }))
          : [{ ...EMPTY_ITEM }],
      );
      setHydratedDraftId(draft.id);
    }
  }, [draft, hydratedDraftId]);

  const completeItems = items.filter(isItemComplete);
  const canSave = completeItems.length > 0;

  const payload = () => ({
    diagnosis_note: diagnosisNote.trim() || null,
    general_instructions: generalInstructions.trim() || null,
    items: completeItems.map(item => ({
      ...item,
      drug_generic_name: item.drug_generic_name.trim(),
      dosage: item.dosage.trim(),
      frequency: item.frequency.trim(),
      instructions: item.instructions?.trim() || null,
    })),
  });

  const saveDraft = useMutation({
    mutationFn: (): Promise<PrescriptionRead> =>
      draft
        ? apiFetch<PrescriptionRead>(`/v1/doctor/prescriptions/${draft.id}`, {
            method: 'PATCH',
            body: JSON.stringify(payload()),
          })
        : apiFetch<PrescriptionRead>(`/v1/doctor/consultations/${consultationId}/prescription`, {
            method: 'POST',
            body: JSON.stringify(payload()),
          }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['prescriptions', consultationId] }),
  });

  const sign = useMutation({
    mutationFn: async () => {
      // Persist any in-form edits, then sign the resulting draft.
      const saved = await saveDraft.mutateAsync();
      return apiFetch<PrescriptionRead>(`/v1/doctor/prescriptions/${saved.id}/sign`, {
        method: 'POST',
      });
    },
    onSuccess: () => {
      setReviewing(false);
      setHydratedDraftId(null);
      setDiagnosisNote('');
      setGeneralInstructions('');
      setItems([{ ...EMPTY_ITEM }]);
      qc.invalidateQueries({ queryKey: ['prescriptions', consultationId] });
    },
  });

  const updateItem = (index: number, patch: Partial<PrescriptionItem>) =>
    setItems(prev => prev.map((item, i) => (i === index ? { ...item, ...patch } : item)));

  if (isLoading) {
    return <p className="font-body text-caption text-stone">Loading prescription…</p>;
  }

  // Review step: read-only summary, deliberate confirm (signing is irreversible).
  if (reviewing) {
    return (
      <div className="bg-white rounded-card p-4">
        <h3 className="font-body text-body font-semibold text-forest mb-1">Review before signing</h3>
        <p className="font-body text-caption text-stone mb-3">
          Signing locks this prescription and makes it visible to the patient. It cannot be edited afterwards.
        </p>

        {diagnosisNote.trim() && (
          <div className="mb-2">
            <p className="font-body text-caption font-semibold text-stone">Diagnosis</p>
            <p className="font-body text-body text-ink">{diagnosisNote}</p>
          </div>
        )}

        <div className="mb-2">
          <p className="font-body text-caption font-semibold text-stone mb-1">Medications</p>
          {completeItems.map((item, i) => (
            <div key={i} className="border border-stone/20 rounded px-3 py-2 mb-1.5">
              <p className="font-body text-body font-semibold text-ink">{item.drug_generic_name}</p>
              <p className="font-body text-caption text-stone">
                {item.drug_form} · {item.dosage} · {item.frequency}
                {item.duration_days ? ` · ${item.duration_days} days` : ' · ongoing'}
              </p>
              {item.instructions && (
                <p className="font-body text-caption text-stone italic">{item.instructions}</p>
              )}
            </div>
          ))}
        </div>

        {generalInstructions.trim() && (
          <div className="mb-3">
            <p className="font-body text-caption font-semibold text-stone">General instructions</p>
            <p className="font-body text-body text-ink">{generalInstructions}</p>
          </div>
        )}

        <div className="flex gap-2">
          <button
            onClick={() => setReviewing(false)}
            disabled={sign.isPending}
            className="flex-1 font-body text-body font-semibold text-forest border border-forest rounded-md py-2 hover:bg-forest/5 transition-colors disabled:opacity-50"
          >
            Back to edit
          </button>
          <button
            onClick={() => sign.mutate()}
            disabled={sign.isPending}
            className="flex-1 bg-forest text-ivory font-body text-body font-semibold py-2 rounded-md disabled:opacity-50 hover:bg-jade transition-colors"
          >
            {sign.isPending ? 'Signing…' : 'Confirm & sign'}
          </button>
        </div>
        {sign.isError && (
          <p className="font-body text-caption text-alert mt-2">Failed to sign. Please try again.</p>
        )}
      </div>
    );
  }

  return (
    <div>
      {signed.map(rx => (
        <SignedSummary key={rx.id} rx={rx} />
      ))}

      <div className="bg-white rounded-card p-4">
        <h3 className="font-body text-body font-semibold text-forest mb-3">
          {draft ? `Draft prescription · v${draft.version}` : 'New prescription'}
        </h3>

        <div className="mb-3">
          <label className="font-body text-caption text-stone block mb-1">Diagnosis / chief complaint</label>
          <input
            value={diagnosisNote}
            onChange={e => setDiagnosisNote(e.target.value)}
            maxLength={500}
            placeholder="e.g. Primary hypothyroidism"
            className="w-full font-body text-body text-ink border border-stone/30 rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-forest/50"
          />
        </div>

        <label className="font-body text-caption text-stone block mb-1">Medications</label>
        {items.map((item, i) => (
          <div key={i} className="border border-stone/20 rounded p-3 mb-2">
            <div className="flex gap-2 mb-2">
              <input
                value={item.drug_generic_name}
                onChange={e => updateItem(i, { drug_generic_name: e.target.value })}
                placeholder="Generic drug name"
                className="flex-1 font-body text-body text-ink border border-stone/30 rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-forest/50"
              />
              <select
                value={item.drug_form}
                onChange={e => updateItem(i, { drug_form: e.target.value })}
                className="font-body text-caption text-ink border border-stone/30 rounded px-2 py-1.5 focus:outline-none"
              >
                {DRUG_FORMS.map(form => (
                  <option key={form} value={form}>{form}</option>
                ))}
              </select>
              {items.length > 1 && (
                <button
                  onClick={() => setItems(prev => prev.filter((_, j) => j !== i))}
                  className="text-stone hover:text-alert"
                  aria-label="Remove medication"
                >
                  <Trash2 size={14} />
                </button>
              )}
            </div>
            <div className="flex gap-2">
              <input
                value={item.dosage}
                onChange={e => updateItem(i, { dosage: e.target.value })}
                placeholder="Dose (e.g. 50mcg)"
                className="flex-1 font-body text-caption text-ink border border-stone/30 rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-forest/50"
              />
              <input
                value={item.frequency}
                onChange={e => updateItem(i, { frequency: e.target.value })}
                placeholder="Frequency (e.g. once daily)"
                className="flex-1 font-body text-caption text-ink border border-stone/30 rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-forest/50"
              />
              <input
                type="number"
                min={1}
                value={item.duration_days ?? ''}
                onChange={e => updateItem(i, { duration_days: e.target.value ? Number(e.target.value) : null })}
                placeholder="Days"
                className="w-20 font-body text-caption text-ink border border-stone/30 rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-forest/50"
              />
            </div>
            <input
              value={item.instructions ?? ''}
              onChange={e => updateItem(i, { instructions: e.target.value || null })}
              placeholder="Instructions (e.g. empty stomach)"
              className="w-full mt-2 font-body text-caption text-ink border border-stone/30 rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-forest/50"
            />
          </div>
        ))}

        <button
          onClick={() => setItems(prev => [...prev, { ...EMPTY_ITEM }])}
          className="inline-flex items-center gap-1.5 font-body text-caption font-semibold text-forest hover:underline mb-3"
        >
          <Plus size={12} /> Add medication
        </button>

        <div className="mb-4">
          <label className="font-body text-caption text-stone block mb-1">General instructions</label>
          <textarea
            value={generalInstructions}
            onChange={e => setGeneralInstructions(e.target.value)}
            rows={2}
            placeholder="Diet, lifestyle, repeat testing…"
            className="w-full font-body text-caption text-ink border border-stone/30 rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-forest/50"
          />
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => saveDraft.mutate()}
            disabled={!canSave || saveDraft.isPending}
            className="flex-1 font-body text-body font-semibold text-forest border border-forest rounded-md py-2 hover:bg-forest/5 transition-colors disabled:opacity-40"
          >
            {saveDraft.isPending ? 'Saving…' : 'Save draft'}
          </button>
          <button
            onClick={() => setReviewing(true)}
            disabled={!canSave}
            className="flex-1 bg-forest text-ivory font-body text-body font-semibold py-2 rounded-md disabled:opacity-40 hover:bg-jade transition-colors"
          >
            Review & sign
          </button>
        </div>

        {saveDraft.isSuccess && !saveDraft.isPending && (
          <p className="font-body text-caption text-forest mt-2">Draft saved.</p>
        )}
        {saveDraft.isError && (
          <p className="font-body text-caption text-alert mt-2">Failed to save draft. Please try again.</p>
        )}
        {!canSave && (
          <p className="font-body text-caption text-stone mt-2">
            At least one medication with name, dose, and frequency is required.
          </p>
        )}
      </div>
    </div>
  );
}
