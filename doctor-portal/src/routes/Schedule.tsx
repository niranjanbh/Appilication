import { useState, type FormEvent } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../lib/api';

interface Slot {
  id: string;
  slot_start: string;
  slot_end: string;
  status: string;
}

interface Preferences {
  consultation_duration_minutes_default: number;
  buffer_time_minutes: number;
}

const STATUS_COLOUR: Record<string, string> = {
  available: 'bg-sage/20 text-forest',
  booked:    'bg-saffron/20 text-ink',
  blocked:   'bg-stone/20 text-stone',
};

function formatSlotTime(iso: string) {
  return new Date(iso).toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata',
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });
}

export function Schedule() {
  const queryClient = useQueryClient();

  const { data: slots, isLoading: slotsLoading } = useQuery({
    queryKey: ['schedule'],
    queryFn: () => apiFetch<Slot[]>('/v1/doctor/schedule'),
  });

  const { data: prefs, isLoading: prefsLoading } = useQuery({
    queryKey: ['doctor-me'],
    queryFn: () => apiFetch<Preferences>('/v1/doctor/me'),
  });

  // — Slot creation state —
  const [date, setDate] = useState('');
  const [startTime, setStartTime] = useState('');
  const [count, setCount] = useState(1);
  const [intervalMin, setIntervalMin] = useState(30);
  const [addError, setAddError] = useState<string | null>(null);

  // — Preferences state —
  const [duration, setDuration] = useState<number | ''>('');
  const [buffer, setBuffer] = useState<number | ''>('');
  const [prefSaved, setPrefSaved] = useState(false);
  const [prefError, setPrefError] = useState<string | null>(null);

  const deleteSlot = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/v1/doctor/schedule/${id}`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['schedule'] }),
  });

  const addSlots = useMutation({
    mutationFn: (slots: { slot_start: string; slot_end: string }[]) =>
      apiFetch('/v1/doctor/schedule/bulk', {
        method: 'POST',
        body: JSON.stringify({ slots }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedule'] });
      setAddError(null);
    },
    onError: (e: Error) => setAddError(e.message),
  });

  function handleAddSlots(e: FormEvent) {
    e.preventDefault();
    if (!date || !startTime) {
      setAddError('Date and start time are required');
      return;
    }
    const slotsToCreate: { slot_start: string; slot_end: string }[] = [];
    let baseMs = new Date(`${date}T${startTime}:00`).getTime();
    const durationMs = (prefs?.consultation_duration_minutes_default ?? 30) * 60_000;
    const bufferMs = (prefs?.buffer_time_minutes ?? 5) * 60_000;
    const gapMs = intervalMin * 60_000;

    for (let i = 0; i < count; i++) {
      const start = new Date(baseMs);
      const end = new Date(baseMs + durationMs);
      slotsToCreate.push({
        slot_start: start.toISOString(),
        slot_end: end.toISOString(),
      });
      baseMs += gapMs + bufferMs;
    }
    addSlots.mutate(slotsToCreate);
  }

  async function handleSavePrefs(e: FormEvent) {
    e.preventDefault();
    setPrefError(null);
    setPrefSaved(false);
    try {
      await apiFetch('/v1/doctor/schedule/preferences', {
        method: 'PATCH',
        body: JSON.stringify({
          consultation_duration_minutes_default: duration !== '' ? Number(duration) : undefined,
          buffer_time_minutes: buffer !== '' ? Number(buffer) : undefined,
        }),
      });
      await queryClient.invalidateQueries({ queryKey: ['doctor-me'] });
      setPrefSaved(true);
      setTimeout(() => setPrefSaved(false), 3000);
    } catch (err) {
      setPrefError(err instanceof Error ? err.message : 'Save failed');
    }
  }

  if (slotsLoading || prefsLoading) {
    return (
      <div className="px-8 py-8">
        <p className="font-body text-body text-stone">Loading…</p>
      </div>
    );
  }

  return (
    <div className="px-8 py-8 max-w-3xl">
      <h1 className="font-display text-h2 text-forest font-medium mb-6">Schedule</h1>

      {/* Preferences */}
      <div className="bg-white rounded-card p-5 mb-6">
        <h2 className="font-display text-h3 text-forest font-medium mb-4">Preferences</h2>
        {prefError && (
          <div className="bg-alert/10 border border-alert/30 text-alert font-body text-caption rounded-md px-4 py-3 mb-3">
            {prefError}
          </div>
        )}
        {prefSaved && (
          <div className="bg-sage/20 border border-sage/40 text-forest font-body text-caption rounded-md px-4 py-3 mb-3">
            Preferences saved.
          </div>
        )}
        <form onSubmit={(e) => { void handleSavePrefs(e); }} className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block font-body text-caption text-stone mb-1.5">
              Consultation duration (min)
            </label>
            <input
              type="number"
              min={10}
              max={120}
              value={duration !== '' ? duration : (prefs?.consultation_duration_minutes_default ?? 30)}
              onChange={e => setDuration(e.target.value === '' ? '' : Number(e.target.value))}
              className="w-32 border border-stone/30 rounded-md px-3 py-2.5 font-body text-body text-ink focus:outline-none focus:border-forest"
            />
          </div>
          <div>
            <label className="block font-body text-caption text-stone mb-1.5">
              Buffer time (min)
            </label>
            <input
              type="number"
              min={0}
              max={60}
              value={buffer !== '' ? buffer : (prefs?.buffer_time_minutes ?? 5)}
              onChange={e => setBuffer(e.target.value === '' ? '' : Number(e.target.value))}
              className="w-28 border border-stone/30 rounded-md px-3 py-2.5 font-body text-body text-ink focus:outline-none focus:border-forest"
            />
          </div>
          <button
            type="submit"
            className="bg-forest text-ivory font-body text-body font-semibold px-5 py-2.5 rounded-md hover:bg-jade transition-colors"
          >
            Save preferences
          </button>
        </form>
      </div>

      {/* Add slots */}
      <div className="bg-white rounded-card p-5 mb-6">
        <h2 className="font-display text-h3 text-forest font-medium mb-4">Add availability slots</h2>
        {addError && (
          <div className="bg-alert/10 border border-alert/30 text-alert font-body text-caption rounded-md px-4 py-3 mb-3">
            {addError}
          </div>
        )}
        <form onSubmit={handleAddSlots} className="space-y-4">
          <div className="flex flex-wrap gap-4">
            <div>
              <label className="block font-body text-caption text-stone mb-1.5">Date</label>
              <input
                type="date"
                value={date}
                onChange={e => setDate(e.target.value)}
                required
                className="border border-stone/30 rounded-md px-3 py-2.5 font-body text-body text-ink focus:outline-none focus:border-forest"
              />
            </div>
            <div>
              <label className="block font-body text-caption text-stone mb-1.5">Start time</label>
              <input
                type="time"
                value={startTime}
                onChange={e => setStartTime(e.target.value)}
                required
                className="border border-stone/30 rounded-md px-3 py-2.5 font-body text-body text-ink focus:outline-none focus:border-forest"
              />
            </div>
            <div>
              <label className="block font-body text-caption text-stone mb-1.5">
                Number of slots <span className="text-stone/60">(max 20)</span>
              </label>
              <input
                type="number"
                min={1}
                max={20}
                value={count}
                onChange={e => setCount(Number(e.target.value))}
                className="w-24 border border-stone/30 rounded-md px-3 py-2.5 font-body text-body text-ink focus:outline-none focus:border-forest"
              />
            </div>
            <div>
              <label className="block font-body text-caption text-stone mb-1.5">
                Interval between slots (min)
              </label>
              <input
                type="number"
                min={15}
                max={240}
                value={intervalMin}
                onChange={e => setIntervalMin(Number(e.target.value))}
                className="w-32 border border-stone/30 rounded-md px-3 py-2.5 font-body text-body text-ink focus:outline-none focus:border-forest"
              />
            </div>
          </div>
          <p className="font-body text-caption text-stone">
            Duration from preferences ({prefs?.consultation_duration_minutes_default ?? 30} min).
            Slots will be created starting at the chosen time, spaced by interval + buffer.
          </p>
          <button
            type="submit"
            disabled={addSlots.isPending}
            className="bg-forest text-ivory font-body text-body font-semibold px-6 py-2.5 rounded-md hover:bg-jade transition-colors disabled:opacity-50"
          >
            {addSlots.isPending ? 'Adding…' : `Add ${count} slot${count !== 1 ? 's' : ''}`}
          </button>
        </form>
      </div>

      {/* Slot list */}
      <div className="bg-white rounded-card p-5">
        <h2 className="font-display text-h3 text-forest font-medium mb-4">
          Availability slots
          {slots && slots.length > 0 && (
            <span className="ml-2 font-body text-caption text-stone font-normal">
              ({slots.length})
            </span>
          )}
        </h2>
        {!slots || slots.length === 0 ? (
          <p className="font-body text-body text-stone">No slots yet. Add some above.</p>
        ) : (
          <div className="divide-y divide-stone/10">
            {slots.map(slot => (
              <div key={slot.id} className="flex items-center justify-between py-3">
                <div>
                  <p className="font-body text-body text-ink">
                    {formatSlotTime(slot.slot_start)}
                    <span className="text-stone mx-1">→</span>
                    {formatSlotTime(slot.slot_end)}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`font-body text-caption px-2 py-0.5 rounded-full ${STATUS_COLOUR[slot.status] ?? 'bg-stone/10 text-stone'}`}>
                    {slot.status}
                  </span>
                  {slot.status === 'available' && (
                    <button
                      onClick={() => deleteSlot.mutate(slot.id)}
                      disabled={deleteSlot.isPending}
                      className="font-body text-caption text-alert hover:underline disabled:opacity-50"
                    >
                      Remove
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
