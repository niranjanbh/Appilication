/**
 * Manual vitals API client (patient-facing).
 */

import { apiFetch } from './client';

export type VitalType =
  | 'weight'
  | 'blood_pressure_systolic'
  | 'blood_pressure_diastolic'
  | 'blood_glucose';

export interface VitalReadItem {
  type: VitalType;
  value: { value: number; unit: string };
  measured_at: string;
}

export interface VitalsListResponse {
  items: VitalReadItem[];
}

export interface VitalsLogRequest {
  measured_at: string;
  weight_kg?: number | null;
  blood_pressure_systolic?: number | null;
  blood_pressure_diastolic?: number | null;
  blood_glucose_mg_dl?: number | null;
}

export function logVitalsApi(payload: VitalsLogRequest): Promise<{ logged_count: number }> {
  return apiFetch('/v1/wellness/vitals', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function listVitalsApi(): Promise<VitalsListResponse> {
  return apiFetch('/v1/wellness/vitals');
}
