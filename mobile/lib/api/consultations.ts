/**
 * Patient consultations API client.
 *
 * GET /v1/clinic/patient/consultations?upcoming=&status=&page=&page_size=
 *
 * A `requested` consultation has no doctor/slot yet — the coordinator assigns
 * those before the patient pays. See the coordinator-assigned-consults flow.
 */

import { apiFetch } from './client';

// ── Types ─────────────────────────────────────────────────────────────────────

export type ConsultationStatus =
  | 'requested'
  | 'scheduled'
  | 'confirmed'
  | 'in_progress'
  | 'completed'
  | 'cancelled'
  | 'no_show';

export interface Consultation {
  id: string;
  doctor_id: string | null;
  /** Assigned doctor's name/specialty — null while status is `requested`. */
  doctor_name: string | null;
  doctor_specialty: string[] | null;
  condition_category: string;
  consultation_type: string;
  scheduled_start_at: string | null;
  scheduled_end_at: string | null;
  status: ConsultationStatus;
  consultation_fee_paise: number | null;
  payment_id: string | null;
  cancellation_reason: string | null;
}

export interface ConsultationListResponse {
  items: Consultation[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// ── Status presentation ─────────────────────────────────────────────────────

const UPCOMING_STATUSES: ConsultationStatus[] = [
  'requested',
  'scheduled',
  'confirmed',
  'in_progress',
];

export function isUpcoming(c: Consultation): boolean {
  return UPCOMING_STATUSES.includes(c.status);
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function listConsultations(
  opts: { upcoming?: boolean; status?: ConsultationStatus; page?: number; pageSize?: number } = {},
): Promise<ConsultationListResponse> {
  const params = new URLSearchParams();
  if (opts.upcoming != null) params.set('upcoming', String(opts.upcoming));
  if (opts.status) params.set('status', opts.status);
  params.set('page', String(opts.page ?? 1));
  params.set('page_size', String(opts.pageSize ?? 50));
  return apiFetch<ConsultationListResponse>(`/v1/clinic/patient/consultations?${params.toString()}`);
}

// ── Create a request ──────────────────────────────────────────────────────────

export interface ConsultationRequestPayload {
  condition_category: string;
  consultation_type?: 'initial' | 'follow_up';
  requirement_notes?: string | null;
  preferred_time_window?: string | null;
}

export interface ConsultationRequestResult {
  consultation_id: string;
  status: ConsultationStatus;
  condition_category: string;
  consultation_type: string;
  requirement_notes: string | null;
  preferred_time_window: string | null;
  created_at: string;
}

/**
 * Submit a consultation request. The patient does not pick a doctor or slot —
 * a coordinator assigns those, and the request lands in `requested` status.
 */
export async function requestConsultation(
  payload: ConsultationRequestPayload,
): Promise<ConsultationRequestResult> {
  return apiFetch<ConsultationRequestResult>('/v1/clinic/patient/consultations', {
    method: 'POST',
    body: JSON.stringify({ consultation_type: 'initial', ...payload }),
  });
}
