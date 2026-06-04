import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { apiFetch } from '../lib/api';

interface Prescription {
  id: string;
  status: string;
  created_at: string;
}

interface LabReport {
  id: string;
  lab_name: string | null;
  report_date: string | null;
  status: string;
  created_at: string;
}

type Tab = 'notes' | 'prescriptions' | 'labs' | 'wearables';

const TABS: { id: Tab; label: string }[] = [
  { id: 'notes', label: 'Notes' },
  { id: 'prescriptions', label: 'Prescriptions' },
  { id: 'labs', label: 'Labs' },
  { id: 'wearables', label: 'Wearables' },
];

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
    timeZone: 'Asia/Kolkata',
  });
}

interface NoteRead {
  id: string;
  note_type: string;
  version: number;
  created_at: string;
}

const NOTE_TYPE_LABELS: Record<string, string> = {
  clinical: 'Clinical',
  coordinator_only: 'Coordinator only',
  patient_visible: 'Visible to patient',
  private: 'Private',
};

function NotesTab({ consultationId }: { consultationId: string }) {
  const { data: notes = [], isLoading } = useQuery<NoteRead[]>({
    queryKey: ['consultation-notes', consultationId],
    queryFn: () => apiFetch<NoteRead[]>(`/v1/doctor/consultations/${consultationId}/notes`),
  });

  if (isLoading) return <p className="font-body text-caption text-stone">Loading…</p>;
  if (notes.length === 0) return <p className="font-body text-caption text-stone">No notes yet.</p>;

  return (
    <ul className="space-y-2">
      {notes.map(note => (
        <li key={note.id} className="border border-stone/15 rounded p-2.5">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="font-body text-caption font-medium text-forest">
              {NOTE_TYPE_LABELS[note.note_type] ?? note.note_type}
            </span>
            <span className="font-body text-caption text-stone/60">v{note.version}</span>
          </div>
          <p className="font-body text-caption text-stone">{formatDate(note.created_at)}</p>
        </li>
      ))}
    </ul>
  );
}

function PrescriptionsTab({ patientId }: { patientId: string }) {
  const { data, isLoading } = useQuery<{ items: Prescription[] }>({
    queryKey: ['doctor-patient-prescriptions', patientId],
    queryFn: () => apiFetch<{ items: Prescription[] }>(`/v1/doctor/patients/${patientId}/prescriptions`),
  });

  if (isLoading) return <p className="font-body text-caption text-stone">Loading…</p>;
  const prescriptions = data?.items ?? [];
  if (prescriptions.length === 0) return <p className="font-body text-caption text-stone">No prescriptions.</p>;

  return (
    <ul className="space-y-2">
      {prescriptions.map(p => (
        <li key={p.id} className="border border-stone/15 rounded p-2.5">
          <div className="flex items-center justify-between">
            <span className={`font-body text-caption font-medium ${p.status === 'signed' ? 'text-forest' : 'text-stone'}`}>
              {p.status === 'signed' ? 'Signed' : p.status === 'draft' ? 'Draft' : p.status}
            </span>
            <span className="font-body text-caption text-stone">{formatDate(p.created_at)}</span>
          </div>
        </li>
      ))}
    </ul>
  );
}

function LabsTab({ patientId }: { patientId: string }) {
  const { data, isLoading } = useQuery<{ items: LabReport[] }>({
    queryKey: ['doctor-patient-labs', patientId],
    queryFn: () => apiFetch<{ items: LabReport[] }>(`/v1/doctor/patients/${patientId}/labs`),
  });

  if (isLoading) return <p className="font-body text-caption text-stone">Loading…</p>;
  const reports = data?.items ?? [];
  if (reports.length === 0) return <p className="font-body text-caption text-stone">No lab reports.</p>;

  return (
    <ul className="space-y-2">
      {reports.map(r => (
        <li key={r.id} className="border border-stone/15 rounded p-2.5">
          <p className="font-body text-caption font-medium text-ink">{r.lab_name ?? 'Lab report'}</p>
          <p className="font-body text-caption text-stone">
            {r.report_date ? formatDate(r.report_date) : formatDate(r.created_at)} · {r.status}
          </p>
        </li>
      ))}
    </ul>
  );
}

function WearablesTab({ patientId }: { patientId: string }) {
  return (
    <div className="bg-sage/10 rounded p-3">
      <p className="font-body text-caption text-stone">
        Wearable trend data will appear here.{' '}
        <Link to={`/patients/${patientId}`} className="text-forest hover:underline">
          View full patient profile →
        </Link>
      </p>
    </div>
  );
}

interface PatientContextPanelProps {
  consultationId: string;
  patientId: string;
  patientName: string;
}

export function PatientContextPanel({ consultationId, patientId, patientName }: PatientContextPanelProps) {
  const [activeTab, setActiveTab] = useState<Tab>('notes');

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 pt-4 pb-0 border-b border-stone/15">
        <p className="font-body text-caption text-stone mb-2">
          Patient:{' '}
          <Link to={`/patients/${patientId}`} className="text-forest hover:underline font-medium">
            {patientName}
          </Link>
        </p>
        <div className="flex gap-1">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`font-body text-caption px-3 py-1.5 rounded-t border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-forest text-forest font-semibold'
                  : 'border-transparent text-stone hover:text-ink'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'notes' && <NotesTab consultationId={consultationId} />}
        {activeTab === 'prescriptions' && <PrescriptionsTab patientId={patientId} />}
        {activeTab === 'labs' && <LabsTab patientId={patientId} />}
        {activeTab === 'wearables' && <WearablesTab patientId={patientId} />}
      </div>
    </div>
  );
}
