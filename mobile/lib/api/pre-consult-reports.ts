import { apiFetch } from './client';

export interface BiomarkerSummary {
  name: string;
  value: string | null;
  unit: string | null;
  flag: 'high' | 'low' | null;
  ref_low: string | null;
  ref_high: string | null;
  trend: 'up' | 'down' | 'stable';
}

export interface LabSummary {
  biomarkers: BiomarkerSummary[];
  window_days: number;
}

export interface AdherenceSummary {
  compliance_pct: number | null;
  taken: number;
  skipped: number;
  snoozed: number;
  total: number;
  window_days: number;
}

export interface WearableSummary {
  avg_steps: number | null;
  avg_resting_hr: number | null;
  avg_sleep_hours: number | null;
  window_days: number;
}

export interface PatientFlags {
  flags: string[];
}

export interface PreConsultReport {
  id: string;
  consultation_id: string | null;
  generated_at: string;
  lab_summary: LabSummary | null;
  adherence_summary: AdherenceSummary | null;
  wearable_summary: WearableSummary | null;
  patient_flags: PatientFlags | null;
  intake_responses: Record<string, unknown> | null;
  pdf_url: string | null;
}

export async function getPreConsultReport(consultationId: string): Promise<PreConsultReport> {
  return apiFetch<PreConsultReport>(
    `/v1/clinic/patient/consultations/${consultationId}/pre-consult-report`,
  );
}
