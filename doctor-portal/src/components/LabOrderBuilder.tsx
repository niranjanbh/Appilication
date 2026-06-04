import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { X } from 'lucide-react';
import { apiFetch } from '../lib/api';

interface LabOrderRead {
  id: string;
  status: string;
  tests: string[];
  lab_name: string | null;
  created_at: string;
}

interface LabOrderBuilderProps {
  consultationId: string;
}

export function LabOrderBuilder({ consultationId }: LabOrderBuilderProps) {
  const qc = useQueryClient();
  const [tests, setTests] = useState<string[]>([]);
  const [testInput, setTestInput] = useState('');
  const [labName, setLabName] = useState('');
  const [submitted, setSubmitted] = useState<LabOrderRead | null>(null);

  const create = useMutation({
    mutationFn: () =>
      apiFetch<LabOrderRead>(`/v1/doctor/consultations/${consultationId}/lab-order`, {
        method: 'POST',
        body: JSON.stringify({ tests, lab_name: labName || null }),
      }),
    onSuccess: data => {
      qc.invalidateQueries({ queryKey: ['consultation', consultationId] });
      setSubmitted(data);
      setTests([]);
      setLabName('');
    },
  });

  const addTest = () => {
    const t = testInput.trim();
    if (t && !tests.includes(t)) {
      setTests(prev => [...prev, t]);
    }
    setTestInput('');
  };

  const removeTest = (t: string) => setTests(prev => prev.filter(x => x !== t));

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') { e.preventDefault(); addTest(); }
  };

  if (submitted) {
    return (
      <div className="bg-sage/10 border border-sage/30 rounded-card p-4">
        <p className="font-body text-body font-semibold text-forest mb-1">Lab order placed</p>
        <p className="font-body text-caption text-stone">
          {submitted.tests.join(', ')}
          {submitted.lab_name ? ` · ${submitted.lab_name}` : ''}
        </p>
        <button
          onClick={() => setSubmitted(null)}
          className="mt-2 font-body text-caption text-forest hover:underline"
        >
          Place another order
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-card p-4">
      <h3 className="font-body text-body font-semibold text-forest mb-3">Order labs</h3>

      <div className="mb-3">
        <label className="font-body text-caption text-stone block mb-1">Tests</label>
        <div className="flex gap-2">
          <input
            value={testInput}
            onChange={e => setTestInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g. TSH, FT4, HbA1c"
            className="flex-1 font-body text-body text-ink border border-stone/30 rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-forest/50"
          />
          <button
            onClick={addTest}
            disabled={!testInput.trim()}
            className="font-body text-caption font-semibold text-forest border border-forest rounded px-3 py-1.5 disabled:opacity-40 hover:bg-forest/5 transition-colors"
          >
            Add
          </button>
        </div>

        {tests.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {tests.map(t => (
              <span
                key={t}
                className="inline-flex items-center gap-1 bg-sage/20 text-forest font-body text-caption px-2 py-0.5 rounded-full"
              >
                {t}
                <button onClick={() => removeTest(t)} className="hover:text-alert">
                  <X size={10} />
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="mb-4">
        <label className="font-body text-caption text-stone block mb-1">Lab name (optional)</label>
        <input
          value={labName}
          onChange={e => setLabName(e.target.value)}
          placeholder="e.g. Metropolis, Dr Lal"
          className="w-full font-body text-body text-ink border border-stone/30 rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-forest/50"
        />
      </div>

      <button
        onClick={() => create.mutate()}
        disabled={tests.length === 0 || create.isPending}
        className="w-full bg-forest text-ivory font-body text-body font-semibold py-2 rounded-md disabled:opacity-50 hover:bg-jade transition-colors"
      >
        {create.isPending ? 'Placing order…' : 'Place lab order'}
      </button>

      {create.isError && (
        <p className="font-body text-caption text-alert mt-2">Failed to place order. Please try again.</p>
      )}
    </div>
  );
}
