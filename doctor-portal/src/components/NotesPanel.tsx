import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../lib/api';

interface NoteRead {
  id: string;
  note_type: string;
  version: number;
  created_at: string;
}

type NoteType = 'clinical' | 'coordinator_only' | 'patient_visible' | 'private';

const NOTE_TYPE_LABELS: Record<NoteType, string> = {
  clinical: 'Clinical',
  coordinator_only: 'Coordinator only',
  patient_visible: 'Visible to patient',
  private: 'Private',
};

function formatIST(iso: string) {
  return new Date(iso).toLocaleString('en-IN', {
    day: 'numeric', month: 'short',
    hour: '2-digit', minute: '2-digit', hour12: true,
    timeZone: 'Asia/Kolkata',
  });
}

const DRAFT_KEY = (consultationId: string) => `note_draft_${consultationId}`;

interface NotesPanelProps {
  consultationId: string;
}

export function NotesPanel({ consultationId }: NotesPanelProps) {
  const qc = useQueryClient();
  const [draft, setDraft] = useState(() => {
    return localStorage.getItem(DRAFT_KEY(consultationId)) ?? '';
  });
  const [noteType, setNoteType] = useState<NoteType>('clinical');
  const [lastSaved, setLastSaved] = useState<string | null>(null);
  const autoSaveRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const { data: notes = [] } = useQuery<NoteRead[]>({
    queryKey: ['consultation-notes', consultationId],
    queryFn: () => apiFetch<NoteRead[]>(`/v1/doctor/consultations/${consultationId}/notes`),
    refetchInterval: 30_000,
  });

  const save = useMutation({
    mutationFn: (content: string) =>
      apiFetch<NoteRead>(`/v1/doctor/consultations/${consultationId}/notes`, {
        method: 'POST',
        body: JSON.stringify({ note_type: noteType, content }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['consultation-notes', consultationId] });
      localStorage.removeItem(DRAFT_KEY(consultationId));
      setDraft('');
      setLastSaved(new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }));
    },
  });

  // Persist draft to localStorage on every keystroke.
  useEffect(() => {
    localStorage.setItem(DRAFT_KEY(consultationId), draft);
  }, [consultationId, draft]);

  // Auto-save every 5 minutes if draft is non-empty.
  useEffect(() => {
    autoSaveRef.current = setInterval(() => {
      if (draft.trim()) save.mutate(draft);
    }, 5 * 60 * 1000);
    return () => {
      if (autoSaveRef.current) clearInterval(autoSaveRef.current);
    };
  }, [draft, save]);

  const handleSave = () => {
    if (draft.trim()) save.mutate(draft);
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="bg-white rounded-card p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-body text-body font-semibold text-forest">New note</h3>
          <select
            value={noteType}
            onChange={e => setNoteType(e.target.value as NoteType)}
            className="font-body text-caption text-ink border border-stone/30 rounded px-2 py-1 bg-white"
          >
            {(Object.keys(NOTE_TYPE_LABELS) as NoteType[]).map(t => (
              <option key={t} value={t}>{NOTE_TYPE_LABELS[t]}</option>
            ))}
          </select>
        </div>

        <textarea
          value={draft}
          onChange={e => setDraft(e.target.value)}
          rows={5}
          placeholder="Write your clinical notes here…"
          className="w-full font-body text-body text-ink placeholder:text-stone/60 border border-stone/30 rounded-md p-3 resize-none focus:outline-none focus:ring-1 focus:ring-forest/50"
        />

        <div className="flex items-center justify-between mt-2">
          <span className="font-body text-caption text-stone">
            {save.isPending ? 'Saving…' : lastSaved ? `Saved at ${lastSaved}` : ''}
          </span>
          <button
            onClick={handleSave}
            disabled={!draft.trim() || save.isPending}
            className="bg-forest text-ivory font-body text-caption font-semibold px-4 py-1.5 rounded-md disabled:opacity-50 hover:bg-jade transition-colors"
          >
            Save note
          </button>
        </div>

        {save.isError && (
          <p className="font-body text-caption text-alert mt-1">Failed to save. Please try again.</p>
        )}
      </div>

      {notes.length > 0 && (
        <div className="bg-white rounded-card p-4">
          <h3 className="font-body text-body font-semibold text-forest mb-3">Saved notes</h3>
          <ul className="space-y-3">
            {notes.map(note => (
              <li key={note.id} className="border-b border-stone/10 pb-3 last:border-0 last:pb-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-body text-caption text-stone">{NOTE_TYPE_LABELS[note.note_type as NoteType] ?? note.note_type}</span>
                  <span className="font-body text-caption text-stone/60">· v{note.version} · {formatIST(note.created_at)}</span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
