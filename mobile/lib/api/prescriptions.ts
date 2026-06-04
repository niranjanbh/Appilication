/**
 * Prescription API client (patient-facing).
 */

import { apiFetch } from './client';

// ── Types ─────────────────────────────────────────────────────────────────────

export type PrescriptionStatus = 'signed' | 'dispensed';

export interface PrescriptionItem {
  id: string;
  drug_generic_name: string;
  drug_form: string;
  dosage: string;
  frequency: string;
  duration_days: number | null;
  instructions: string | null;
  refill_allowed: boolean;
  order_index: number;
}

export interface Prescription {
  id: string;
  consultation_id: string;
  status: PrescriptionStatus;
  signed_at: string | null;
  version: number;
  diagnosis_note: string | null;
  general_instructions: string | null;
  items: PrescriptionItem[];
}

export interface PrescriptionListResponse {
  items: Prescription[];
  total: number;
  page: number;
  page_size: number;
}

export interface PrescriptionPdfResponse {
  download_url: string;
  expires_in_seconds: number;
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function listPrescriptions(
  page = 1,
  pageSize = 20,
): Promise<PrescriptionListResponse> {
  return apiFetch<PrescriptionListResponse>(
    `/v1/clinic/patient/prescriptions?page=${page}&page_size=${pageSize}`,
  );
}

export async function getPrescription(id: string): Promise<Prescription> {
  return apiFetch<Prescription>(`/v1/clinic/patient/prescriptions/${id}`);
}

export async function getPrescriptionPdfUrl(id: string): Promise<PrescriptionPdfResponse> {
  return apiFetch<PrescriptionPdfResponse>(`/v1/clinic/patient/prescriptions/${id}/pdf`);
}
