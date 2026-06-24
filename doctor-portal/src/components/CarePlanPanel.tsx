import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, ChevronDown, Plus, Trash2 } from 'lucide-react';
import { apiFetch } from '../lib/api';
import { MedicationCatalogPicker } from './MedicationCatalogPicker';

interface CarePlanItemInput {
  category: string;
  title: string;
  description: string | null;
  frequency: string | null;
  duration: string | null;
  priority: string;
}

interface CarePlanItemRead extends CarePlanItemInput {
  id: string;
  order_index: number;
}

interface CarePlanRead {
  id: string;
  consultation_id: string;
  doctor_id: string;
  title: string;
  status: 'draft' | 'active' | 'completed' | 'cancelled';
  condition_category: string | null;
  goals: string | null;
  notes: string | null;
  valid_from: string | null;
  valid_until: string | null;
  activated_at: string | null;
  completed_at: string | null;
  version: number;
  items: CarePlanItemRead[];
}

const CATEGORIES: { value: string; label: string }[] = [
  { value: 'medication', label: 'Medication' },
  { value: 'exercise', label: 'Exercise' },
  { value: 'diet', label: 'Diet' },
  { value: 'lifestyle', label: 'Lifestyle' },
  { value: 'follow_up', label: 'Follow-up' },
  { value: 'lab_test', label: 'Lab test' },
];

const PRIORITIES: { value: string; label: string }[] = [
  { value: 'high', label: 'High' },
  { value: 'normal', label: 'Normal' },
  { value: 'low', label: 'Low' },
];

const CONDITION_CATEGORIES = [
  '', 'thyroid', 'pcos', 'weight', 'skin', 'hair', 'mens_health', 'trt', 'longevity',
] as const;

function emptyItem(): CarePlanItemInput {
  return {
    category: 'medication',
    title: '',
    description: null,
    frequency: null,
    duration: null,
    priority: 'normal',
  };
}

function isItemComplete(item: CarePlanItemInput): boolean {
  return !!item.title.trim();
}

function formatIST(iso: string) {
  return new Date(iso).toLocaleString('en-IN', {
    day: 'numeric', month: 'long', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: true,
    timeZone: 'Asia/Kolkata',
  });
}

function priorityColor(p: string): string {
  if (p === 'high') return 'text-alert';
  if (p === 'low') return 'text-stone';
  return 'text-ink';
}

function statusBadge(status: string) {
  const cls =
    status === 'active'
      ? 'bg-forest/10 text-forest'
      : status === 'completed'
        ? 'bg-stone/10 text-stone'
        : 'bg-sage/10 text-ink';
  return (
    <span className={`font-body text-caption font-semibold rounded-full px-2 py-0.5 ${cls}`}>
      {status}
    </span>
  );
}

function ActiveSummary({ plan }: { plan: CarePlanRead }) {
  return (
    <div className="bg-sage/10 border border-sage/30 rounded-card p-4 mb-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <p className="font-body text-body font-semibold text-forest">{plan.title}</p>
          {statusBadge(plan.status)}
        </div>
        {plan.activated_at && (
          <span className="font-body text-caption text-stone">{formatIST(plan.activated_at)}</span>
        )}
      </div>
      {plan.goals && (
        <p className="font-body text-caption text-ink mb-1">{plan.goals}</p>
      )}
      <ul className="mb-0">
        {plan.items.map(item => (
          <li key={item.id} className="font-body text-caption text-ink py-0.5 flex items-center gap-1.5">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-forest shrink-0" />
            <span className="font-semibold">{CATEGORIES.find(c => c.value === item.category)?.label ?? item.category}</span>
            {' — '}{item.title}
            {item.frequency ? ` · ${item.frequency}` : ''}
            {item.duration ? ` · ${item.duration}` : ''}
          </li>
        ))}
      </ul>
    </div>
  );
}

interface CarePlanPanelProps {
  consultationId: string;
}

export function CarePlanPanel({ consultationId }: CarePlanPanelProps) {
  const qc = useQueryClient();

  const { data: carePlans, isLoading } = useQuery({
    queryKey: ['care-plans', consultationId],
    queryFn: () => apiFetch<CarePlanRead[]>(`/v1/doctor/consultations/${consultationId}/care-plans`),
  });

  const draft = carePlans?.find(cp => cp.status === 'draft') ?? null;
  const nonDraft = carePlans?.filter(cp => cp.status !== 'draft') ?? [];

  const [title, setTitle] = useState('');
  const [conditionCategory, setConditionCategory] = useState('');
  const [goals, setGoals] = useState('');
  const [notes, setNotes] = useState('');
  const [items, setItems] = useState<CarePlanItemInput[]>([emptyItem()]);
  const [reviewing, setReviewing] = useState(false);
  const [hydratedDraftId, setHydratedDraftId] = useState<string | null>(null);

  useEffect(() => {
    if (draft && draft.id !== hydratedDraftId) {
      setTitle(draft.title ?? '');
      setConditionCategory(draft.condition_category ?? '');
      setGoals(draft.goals ?? '');
      setNotes(draft.notes ?? '');
      setItems(
        draft.items.length > 0
          ? draft.items.map(({ id: _id, order_index: _oi, ...item }) => ({ ...item }))
          : [emptyItem()],
      );
      setHydratedDraftId(draft.id);
    }
  }, [draft, hydratedDraftId]);

  const completeItems = items.filter(isItemComplete);
  const canSave = !!title.trim() && completeItems.length > 0;

  const payload = () => ({
    title: title.trim(),
    condition_category: conditionCategory || null,
    goals: goals.trim() || null,
    notes: notes.trim() || null,
    items: completeItems.map(item => ({
      category: item.category,
      title: item.title.trim(),
      description: item.description?.trim() || null,
      frequency: item.frequency?.trim() || null,
      duration: item.duration?.trim() || null,
      priority: item.priority,
    })),
  });

  const saveDraft = useMutation({
    mutationFn: (): Promise<CarePlanRead> =>
      draft
        ? apiFetch<CarePlanRead>(`/v1/doctor/care-plans/${draft.id}`, {
            method: 'PATCH',
            body: JSON.stringify(payload()),
          })
        : apiFetch<CarePlanRead>(`/v1/doctor/consultations/${consultationId}/care-plan`, {
            method: 'POST',
            body: JSON.stringify(payload()),
          }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['care-plans', consultationId] }),
  });

  const activate = useMutation({
    mutationFn: async () => {
      const saved = await saveDraft.mutateAsync();
      return apiFetch<CarePlanRead>(`/v1/doctor/care-plans/${saved.id}/activate`, {
        method: 'POST',
      });
    },
    onSuccess: () => {
      setReviewing(false);
      setHydratedDraftId(null);
      setTitle('');
      setConditionCategory('');
      setGoals('');
      setNotes('');
      setItems([emptyItem()]);
      qc.invalidateQueries({ queryKey: ['care-plans', consultationId] });
    },
  });

  const complete = useMutation({
    mutationFn: (planId: string) =>
      apiFetch<CarePlanRead>(`/v1/doctor/care-plans/${planId}/complete`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['care-plans', consultationId] }),
  });

  const updateItem = (index: number, patch: Partial<CarePlanItemInput>) =>
    setItems(prev => prev.map((item, i) => (i === index ? { ...item, ...patch } : item)));

  if (isLoading) {
    return <p className="font-body text-caption text-stone">Loading care plans...</p>;
  }

  if (reviewing) {
    return (
      <div className="bg-white rounded-card p-4">
        <h3 className="font-body text-body font-semibold text-forest mb-1">Review before activating</h3>
        <p className="font-body text-caption text-stone mb-3">
          Activating makes this care plan visible to the patient. It cannot be edited afterwards.
        </p>

        <p className="font-body text-body font-semibold text-ink mb-1">{title}</p>
        {conditionCategory && (
          <p className="font-body text-caption text-stone mb-1">Condition: {conditionCategory}</p>
        )}
        {goals.trim() && (
          <div className="mb-2">
            <p className="font-body text-caption font-semibold text-stone">Goals</p>
            <p className="font-body text-body text-ink">{goals}</p>
          </div>
        )}

        <div className="mb-2">
          <p className="font-body text-caption font-semibold text-stone mb-1">Plan items</p>
          {completeItems.map((item, i) => (
            <div key={i} className="border border-stone/20 rounded px-3 py-2 mb-1.5">
              <div className="flex items-center gap-2">
                <span className="font-body text-caption font-semibold text-forest">
                  {CATEGORIES.find(c => c.value === item.category)?.label}
                </span>
                <span className={`font-body text-caption ${priorityColor(item.priority)}`}>
                  {item.priority !== 'normal' && `[${item.priority}]`}
                </span>
              </div>
              <p className="font-body text-body text-ink">{item.title}</p>
              {item.description && (
                <p className="font-body text-caption text-stone">{item.description}</p>
              )}
              <p className="font-body text-caption text-stone">
                {item.frequency ?? ''}
                {item.frequency && item.duration ? ' · ' : ''}
                {item.duration ?? ''}
              </p>
            </div>
          ))}
        </div>

        {notes.trim() && (
          <div className="mb-3">
            <p className="font-body text-caption font-semibold text-stone">Notes</p>
            <p className="font-body text-body text-ink">{notes}</p>
          </div>
        )}

        <div className="flex gap-2">
          <button
            onClick={() => setReviewing(false)}
            disabled={activate.isPending}
            className="flex-1 font-body text-body font-semibold text-forest border border-forest rounded-md py-2 hover:bg-forest/5 transition-colors disabled:opacity-50"
          >
            Back to edit
          </button>
          <button
            onClick={() => activate.mutate()}
            disabled={activate.isPending}
            className="flex-1 bg-forest text-ivory font-body text-body font-semibold py-2 rounded-md disabled:opacity-50 hover:bg-jade transition-colors"
          >
            {activate.isPending ? 'Activating...' : 'Confirm & activate'}
          </button>
        </div>
        {activate.isError && (
          <p className="font-body text-caption text-alert mt-2">Failed to activate. Please try again.</p>
        )}
      </div>
    );
  }

  return (
    <div>
      {nonDraft.map(plan => (
        <div key={plan.id}>
          <ActiveSummary plan={plan} />
          {plan.status === 'active' && (
            <button
              onClick={() => complete.mutate(plan.id)}
              disabled={complete.isPending}
              className="inline-flex items-center gap-1.5 font-body text-caption font-semibold text-stone hover:text-forest mb-3"
            >
              <Check size={12} /> Mark completed
            </button>
          )}
        </div>
      ))}

      <div className="bg-white rounded-card p-4">
        <h3 className="font-body text-body font-semibold text-forest mb-3">
          {draft ? `Draft care plan · v${draft.version}` : 'New care plan'}
        </h3>

        <div className="mb-3">
          <label className="font-body text-caption text-stone block mb-1">Plan title</label>
          <input
            value={title}
            onChange={e => setTitle(e.target.value)}
            maxLength={255}
            placeholder="e.g. Thyroid Management Plan"
            className="w-full font-body text-body text-ink border border-stone/30 rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-forest/50"
          />
        </div>

        <div className="flex gap-3 mb-3">
          <div className="flex-1">
            <label className="font-body text-caption text-stone block mb-1">Condition</label>
            <div className="relative">
              <select
                value={conditionCategory}
                onChange={e => setConditionCategory(e.target.value)}
                className="w-full appearance-none font-body text-caption text-ink border border-stone/30 rounded px-3 py-1.5 pr-8 focus:outline-none focus:ring-1 focus:ring-forest/50 bg-white"
              >
                <option value="">Select condition...</option>
                {CONDITION_CATEGORIES.filter(Boolean).map(c => (
                  <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>
                ))}
              </select>
              <ChevronDown size={14} className="absolute right-2 top-1/2 -translate-y-1/2 text-stone pointer-events-none" />
            </div>
          </div>
        </div>

        <div className="mb-3">
          <label className="font-body text-caption text-stone block mb-1">Goals</label>
          <textarea
            value={goals}
            onChange={e => setGoals(e.target.value)}
            rows={2}
            placeholder="e.g. Normalize TSH within 3 months"
            className="w-full font-body text-caption text-ink border border-stone/30 rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-forest/50"
          />
        </div>

        <label className="font-body text-caption text-stone block mb-1">Plan items</label>
        {items.map((item, i) => (
          <div key={i} className="border border-stone/20 rounded p-3 mb-2">
            <div className="flex gap-2 mb-2">
              <select
                value={item.category}
                onChange={e => updateItem(i, { category: e.target.value })}
                aria-label="Category"
                className="font-body text-caption text-ink border border-stone/30 rounded px-2 py-1.5 focus:outline-none bg-white"
              >
                {CATEGORIES.map(c => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
              {item.category === 'medication' ? (
                <MedicationCatalogPicker
                  value={item.title}
                  onChange={name => updateItem(i, { title: name })}
                  placeholder="Search medication…"
                />
              ) : (
                <input
                  value={item.title}
                  onChange={e => updateItem(i, { title: e.target.value })}
                  placeholder="Item title"
                  className="flex-1 font-body text-body text-ink border border-stone/30 rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-forest/50"
                />
              )}
              <select
                value={item.priority}
                onChange={e => updateItem(i, { priority: e.target.value })}
                aria-label="Priority"
                className="font-body text-caption text-ink border border-stone/30 rounded px-2 py-1.5 focus:outline-none bg-white"
              >
                {PRIORITIES.map(p => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
              {items.length > 1 && (
                <button
                  onClick={() => setItems(prev => prev.filter((_, j) => j !== i))}
                  className="text-stone hover:text-alert"
                  aria-label="Remove item"
                >
                  <Trash2 size={14} />
                </button>
              )}
            </div>

            <input
              value={item.description ?? ''}
              onChange={e => updateItem(i, { description: e.target.value || null })}
              placeholder="Description (optional)"
              className="w-full mb-2 font-body text-caption text-ink border border-stone/30 rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-forest/50"
            />

            <div className="flex gap-2">
              <input
                value={item.frequency ?? ''}
                onChange={e => updateItem(i, { frequency: e.target.value || null })}
                placeholder="Frequency (e.g. Once daily)"
                className="flex-1 font-body text-caption text-ink border border-stone/30 rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-forest/50"
              />
              <input
                value={item.duration ?? ''}
                onChange={e => updateItem(i, { duration: e.target.value || null })}
                placeholder="Duration (e.g. 12 weeks)"
                className="flex-1 font-body text-caption text-ink border border-stone/30 rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-forest/50"
              />
            </div>
          </div>
        ))}

        <button
          onClick={() => setItems(prev => [...prev, emptyItem()])}
          className="inline-flex items-center gap-1.5 font-body text-caption font-semibold text-forest hover:underline mb-3"
        >
          <Plus size={12} /> Add item
        </button>

        <div className="mb-4">
          <label className="font-body text-caption text-stone block mb-1">Notes</label>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            rows={2}
            placeholder="Additional notes for the patient..."
            className="w-full font-body text-caption text-ink border border-stone/30 rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-forest/50"
          />
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => saveDraft.mutate()}
            disabled={!canSave || saveDraft.isPending}
            className="flex-1 font-body text-body font-semibold text-forest border border-forest rounded-md py-2 hover:bg-forest/5 transition-colors disabled:opacity-40"
          >
            {saveDraft.isPending ? 'Saving...' : 'Save draft'}
          </button>
          <button
            onClick={() => setReviewing(true)}
            disabled={!canSave}
            className="flex-1 bg-forest text-ivory font-body text-body font-semibold py-2 rounded-md disabled:opacity-40 hover:bg-jade transition-colors"
          >
            Review & activate
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
            A title and at least one item with a name are required.
          </p>
        )}
      </div>
    </div>
  );
}
