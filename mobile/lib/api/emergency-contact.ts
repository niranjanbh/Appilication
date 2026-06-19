/**
 * Emergency contact API client (patient-facing).
 */

import { apiFetch } from './client';

export interface EmergencyContactRead {
  name: string | null;
  relationship: string | null;
  phone: string | null;
  email: string | null;
}

export interface EmergencyContactWrite {
  name: string;
  relationship: string;
  phone: string;
  email?: string | null;
}

export function getEmergencyContactApi(): Promise<EmergencyContactRead> {
  return apiFetch('/v1/users/me/emergency-contact');
}

export function setEmergencyContactApi(
  payload: EmergencyContactWrite,
): Promise<EmergencyContactRead> {
  return apiFetch('/v1/users/me/emergency-contact', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}
