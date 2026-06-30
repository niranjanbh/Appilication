import { useEffect, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { CheckCircle, Clock, Maximize2, Minimize2, ShieldCheck, Video, VideoOff } from 'lucide-react';
import { ControlBar, LiveKitRoom, VideoTrack, useTracks } from '@livekit/components-react';
import { Track } from 'livekit-client';
import '@livekit/components-styles';
import { apiFetch } from '../lib/api';
import { PatientContextPanel } from './PatientContextPanel';
import { NotesPanel } from './NotesPanel';
import { LabOrderBuilder } from './LabOrderBuilder';
import { PreConsultReport } from './PreConsultReport';
import { PrescriptionPanel } from './PrescriptionPanel';
import { CarePlanPanel } from './CarePlanPanel';
import { DiagnosisPanel } from './DiagnosisPanel';
import { EducationAssignPanel } from './EducationAssignPanel';

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

interface JoinResponse {
  room_id: string;
  token: string;
  endpoint?: string;
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

/** Custom call layout: patient fills the main area, doctor self-view is a PIP.
 *  Clicking the PIP swaps them — doctor becomes main, patient goes to PIP. */
function CustomVideoLayout() {
  const [swapped, setSwapped] = useState(false);

  const tracks = useTracks(
    [{ source: Track.Source.Camera, withPlaceholder: true }],
    { onlySubscribed: false },
  );

  const localTrack = tracks.find(t => t.participant.isLocal);
  const remoteTrack = tracks.find(t => !t.participant.isLocal);

  const mainTrack = swapped ? localTrack : remoteTrack;
  const pipTrack = swapped ? remoteTrack : localTrack;

  return (
    <div className="relative w-full h-full bg-ink rounded-card overflow-hidden">
      {/* Main video */}
      <div className="absolute inset-0">
        {mainTrack?.publication?.track ? (
          <VideoTrack
            trackRef={mainTrack}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <VideoOff size={32} className="text-stone" />
          </div>
        )}
      </div>

      {/* PIP — click to swap */}
      {pipTrack && (
        <button
          onClick={() => setSwapped(s => !s)}
          title={swapped ? 'Show patient as main' : 'Show your video as main'}
          className="absolute bottom-16 right-3 w-36 h-24 rounded-lg overflow-hidden border-2 border-ivory/30 hover:border-ivory/70 transition-colors shadow-xl cursor-pointer group"
        >
          {pipTrack.publication?.track ? (
            <VideoTrack trackRef={pipTrack} className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full bg-ink/80 flex items-center justify-center">
              <VideoOff size={18} className="text-stone" />
            </div>
          )}
          <span className="absolute inset-0 flex items-center justify-center bg-ink/0 group-hover:bg-ink/30 transition-colors">
            {swapped ? (
              <Minimize2 size={18} className="text-ivory opacity-0 group-hover:opacity-100 transition-opacity" />
            ) : (
              <Maximize2 size={18} className="text-ivory opacity-0 group-hover:opacity-100 transition-opacity" />
            )}
          </span>
        </button>
      )}

      {/* LiveKit controls bar */}
      <div className="absolute bottom-0 inset-x-0">
        <ControlBar
          controls={{ screenShare: false, chat: false, leave: false }}
          className="!bg-ink/70 !border-t-0 !rounded-none"
        />
      </div>
    </div>
  );
}

interface VideoAreaProps {
  consultation: ConsultationDetail;
}

function VideoArea({ consultation }: VideoAreaProps) {
  const qc = useQueryClient();
  const [session, setSession] = useState<{ token: string; endpoint: string } | null>(null);
  const isActive = ACTIVE_STATUSES.has(consultation.status);

  // Fetch a doctor-scoped LiveKit token + server URL from the backend. The token
  // is requested only after the doctor acknowledges recording consent.
  const join = useMutation({
    mutationFn: () =>
      apiFetch<JoinResponse>(`/v1/doctor/consultations/${consultation.id}/join`),
    onSuccess: data => {
      if (data.endpoint) {
        setSession({ token: data.token, endpoint: data.endpoint });
      }
      // Joining opens the consult (CONFIRMED -> IN_PROGRESS) server-side. Refresh
      // the detail query so the cached status reflects that — otherwise the
      // "Complete consultation" button (gated on in_progress) never appears.
      qc.invalidateQueries({ queryKey: ['consultation', consultation.id] });
    },
  });

  if (!isActive) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-ink/90 rounded-card gap-3">
        <VideoOff size={40} className="text-stone" />
        <p className="font-body text-body text-stone">
          {consultation.status === 'completed' ? 'Consultation ended' : 'Video not yet available'}
        </p>
      </div>
    );
  }

  // Consent gate: the doctor must acknowledge recording before a token is issued.
  if (!session) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-ink/90 rounded-card gap-4 px-8 text-center">
        <ShieldCheck size={40} className="text-sage" />
        <div>
          <p className="font-body text-body text-ivory font-medium mb-1">
            Ready to join the consultation
          </p>
          <p className="font-body text-caption text-stone max-w-sm">
            This consultation may be recorded. By joining, you consent to recording for clinical
            and compliance purposes.
          </p>
        </div>
        <button
          onClick={() => join.mutate()}
          disabled={join.isPending}
          className="inline-flex items-center gap-2 bg-forest text-ivory font-body text-body font-semibold px-5 py-2.5 rounded-md hover:bg-jade transition-colors disabled:opacity-50"
        >
          <Video size={16} />
          {join.isPending ? 'Connecting…' : 'I consent — Join consultation'}
        </button>
        {join.isError && (
          <p className="font-body text-caption text-alert">
            Could not join: {join.error instanceof Error ? join.error.message : 'please try again'}.
          </p>
        )}
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

      {/* LiveKit room with custom PIP layout. Patient is main by default;
          clicking the doctor self-view PIP swaps them. */}
      <div className="flex-1 w-full min-h-0">
        <LiveKitRoom
          serverUrl={session.endpoint}
          token={session.token}
          connect={true}
          video={true}
          audio={true}
          options={{
            adaptiveStream: true,
            dynacast: true,
            publishDefaults: {
              simulcast: true,
              videoEncoding: { maxBitrate: 3_000_000, maxFramerate: 30 },
            },
          }}
          onDisconnected={() => setSession(null)}
          data-lk-theme="default"
          style={{ height: '100%' }}
        >
          <CustomVideoLayout />
        </LiveKitRoom>
      </div>
    </div>
  );
}

type SideTab = 'notes' | 'context' | 'labs' | 'prep' | 'rx' | 'careplan' | 'dx' | 'edu';

const SIDE_TABS: { id: SideTab; label: string }[] = [
  { id: 'prep', label: 'Pre-consult' },
  { id: 'notes', label: 'Notes' },
  { id: 'context', label: 'Patient context' },
  { id: 'dx', label: 'Diagnoses' },
  { id: 'rx', label: 'Prescription' },
  { id: 'careplan', label: 'Care plan' },
  { id: 'labs', label: 'Order labs' },
  { id: 'edu', label: 'Education' },
];

// The backend only permits IN_PROGRESS -> COMPLETED (consultation_service
// _ALLOWED_TRANSITIONS). Showing the button on scheduled/confirmed produced a
// silent 409; gate it to in_progress so it only appears once the doctor has
// opened (joined) the call.
const COMPLETABLE_STATUSES = new Set(['in_progress']);

// Map the backend's 409 detail codes to doctor-facing guidance.
function completeErrorMessage(err: unknown): string {
  const msg = err instanceof Error ? err.message : '';
  if (msg.includes('doctor_notes_required')) {
    return 'Add at least one consultation note before completing.';
  }
  if (msg.includes('consultation_not_in_progress')) {
    return 'This consultation is not in progress — join the call before completing.';
  }
  if (msg.includes('consultation_not_started')) {
    return 'The consultation has not started yet.';
  }
  return 'Could not complete the consultation. Please try again.';
}

function CompleteConsultationButton({ consultation }: { consultation: ConsultationDetail }) {
  const qc = useQueryClient();
  const [confirming, setConfirming] = useState(false);

  const complete = useMutation({
    mutationFn: () =>
      apiFetch<{ id: string; status: string }>(
        `/v1/doctor/consultations/${consultation.id}/complete`,
        { method: 'POST' },
      ),
    onSuccess: () => {
      setConfirming(false);
      qc.invalidateQueries({ queryKey: ['consultation', consultation.id] });
    },
    // Keep the confirm UI open on failure so the error message stays visible
    // and the doctor can fix the cause (e.g. add a note) and retry.
  });

  if (!COMPLETABLE_STATUSES.has(consultation.status)) return null;

  if (confirming) {
    return (
      <div className="flex items-center gap-2">
        <span className="font-body text-caption text-stone">End this consultation?</span>
        <button
          onClick={() => complete.mutate()}
          disabled={complete.isPending}
          className="font-body text-caption font-semibold bg-forest text-ivory px-3 py-1.5 rounded-md hover:bg-jade transition-colors disabled:opacity-50"
        >
          {complete.isPending ? 'Ending…' : 'Yes, complete'}
        </button>
        <button
          onClick={() => setConfirming(false)}
          disabled={complete.isPending}
          className="font-body text-caption font-semibold text-stone hover:text-ink px-2 py-1.5 disabled:opacity-50"
        >
          Cancel
        </button>
        {complete.isError && (
          <span className="font-body text-caption text-alert">
            {completeErrorMessage(complete.error)}
          </span>
        )}
      </div>
    );
  }

  return (
    <button
      onClick={() => setConfirming(true)}
      className="inline-flex items-center gap-1.5 font-body text-caption font-semibold text-forest border border-forest rounded-md px-3 py-1.5 hover:bg-forest/5 transition-colors"
    >
      <CheckCircle size={14} />
      Complete consultation
    </button>
  );
}

interface ConsultationVideoLayoutProps {
  consultation: ConsultationDetail;
}

export function ConsultationVideoLayout({ consultation }: ConsultationVideoLayoutProps) {
  const [sideTab, setSideTab] = useState<SideTab>('notes');
  const isCompleted = consultation.status === 'completed';

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] overflow-hidden">
      {/* Action bar */}
      <div className="flex items-center justify-end px-4 py-2 border-b border-stone/15 bg-white shrink-0">
        <CompleteConsultationButton consultation={consultation} />
      </div>

      <div className="flex flex-1 gap-0 overflow-hidden">
        {/* Left: Video */}
        <div className="flex-[3] min-w-0 p-4">
          <VideoArea consultation={consultation} />
        </div>

        {/* Right: Side panel */}
        <div className="flex-[2] min-w-0 border-l border-stone/15 flex flex-col bg-ivory">
          {/* Tab bar */}
          <div className="flex flex-wrap border-b border-stone/15 px-2 pt-2 shrink-0">
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

            {sideTab === 'dx' && <DiagnosisPanel consultationId={consultation.id} />}

            {sideTab === 'rx' && <PrescriptionPanel consultationId={consultation.id} />}

            {sideTab === 'careplan' && <CarePlanPanel consultationId={consultation.id} />}

            {sideTab === 'labs' && <LabOrderBuilder consultationId={consultation.id} />}

            {sideTab === 'edu' && <EducationAssignPanel consultationId={consultation.id} />}
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
    </div>
  );
}
