import { useEffect, useRef, useState } from 'react';
import { Clock, Video, VideoOff } from 'lucide-react';
import { PatientContextPanel } from './PatientContextPanel';
import { NotesPanel } from './NotesPanel';
import { LabOrderBuilder } from './LabOrderBuilder';
import { PreConsultReport } from './PreConsultReport';
import { PrescriptionPanel } from './PrescriptionPanel';

interface ConsultationDetail {
  id: string;
  patient_id: string;
  patient_user_id: string;
  patient_name: string;
  kyros_patient_id: string;
  condition_category: string;
  status: string;
  video_room_id: string | null;
  scheduled_start_at: string;
}

const ACTIVE_STATUSES = new Set(['scheduled', 'confirmed', 'in_progress']);

function ElapsedTimer({ startISO }: { startISO: string }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const start = new Date(startISO).getTime();
    const tick = () => setElapsed(Math.floor((Date.now() - start) / 1000));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [startISO]);

  const mm = String(Math.floor(elapsed / 60)).padStart(2, '0');
  const ss = String(elapsed % 60).padStart(2, '0');

  return (
    <span className="inline-flex items-center gap-1.5 font-body text-caption text-stone">
      <Clock size={12} />
      {mm}:{ss}
    </span>
  );
}

interface VideoAreaProps {
  consultation: ConsultationDetail;
}

function VideoArea({ consultation }: VideoAreaProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const isActive = ACTIVE_STATUSES.has(consultation.status);

  if (!isActive || !consultation.video_room_id) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-ink/90 rounded-card gap-3">
        <VideoOff size={40} className="text-stone" />
        <p className="font-body text-body text-stone">
          {consultation.status === 'completed' ? 'Consultation ended' : 'Video not yet available'}
        </p>
      </div>
    );
  }

  return (
    <div className="relative h-full bg-ink rounded-card overflow-hidden flex flex-col">
      <div className="flex items-center justify-between px-4 py-2 bg-ink/80">
        <div className="inline-flex items-center gap-2">
          <Video size={14} className="text-ivory" />
          <span className="font-body text-caption text-ivory font-medium">
            {consultation.patient_name}
          </span>
        </div>
        <ElapsedTimer startISO={consultation.scheduled_start_at} />
      </div>

      <iframe
        ref={iframeRef}
        src={`https://app.100ms.live/meeting/${consultation.video_room_id}`}
        allow="camera; microphone; display-capture; fullscreen"
        className="flex-1 w-full border-0"
        title="Video consultation"
      />
    </div>
  );
}

type SideTab = 'notes' | 'context' | 'labs' | 'prep' | 'rx';

const SIDE_TABS: { id: SideTab; label: string }[] = [
  { id: 'prep', label: 'Pre-consult' },
  { id: 'notes', label: 'Notes' },
  { id: 'context', label: 'Patient context' },
  { id: 'rx', label: 'Prescription' },
  { id: 'labs', label: 'Order labs' },
];

interface ConsultationVideoLayoutProps {
  consultation: ConsultationDetail;
}

export function ConsultationVideoLayout({ consultation }: ConsultationVideoLayoutProps) {
  const [sideTab, setSideTab] = useState<SideTab>('notes');
  const isCompleted = consultation.status === 'completed';

  return (
    <div className="flex h-[calc(100vh-4rem)] gap-0 overflow-hidden">
      {/* Left: Video */}
      <div className="flex-[3] min-w-0 p-4">
        <VideoArea consultation={consultation} />
      </div>

      {/* Right: Side panel */}
      <div className="flex-[2] min-w-0 border-l border-stone/15 flex flex-col bg-ivory">
        {/* Tab bar */}
        <div className="flex border-b border-stone/15 px-2 pt-2 shrink-0">
          {SIDE_TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setSideTab(tab.id)}
              className={`font-body text-caption px-3 py-2 border-b-2 transition-colors whitespace-nowrap ${
                sideTab === tab.id
                  ? 'border-forest text-forest font-semibold'
                  : 'border-transparent text-stone hover:text-ink'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto p-4">
          {sideTab === 'prep' && <PreConsultReport consultationId={consultation.id} />}

          {sideTab === 'notes' && <NotesPanel consultationId={consultation.id} />}

          {sideTab === 'context' && (
            <PatientContextPanel
              consultationId={consultation.id}
              patientId={consultation.patient_id}
              patientUserId={consultation.patient_user_id}
              patientName={consultation.patient_name}
            />
          )}

          {sideTab === 'rx' && <PrescriptionPanel consultationId={consultation.id} />}

          {sideTab === 'labs' && <LabOrderBuilder consultationId={consultation.id} />}
        </div>

        {/* Post-call summary banner (completed only) */}
        {isCompleted && (
          <div className="shrink-0 border-t border-stone/15 bg-sage/10 px-4 py-3">
            <p className="font-body text-caption font-semibold text-forest mb-0.5">Post-call</p>
            <p className="font-body text-caption text-stone">
              Add a prescription or lab order from the tabs above, then review the patient profile.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
