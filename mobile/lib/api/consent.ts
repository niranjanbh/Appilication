import type { ConsentRecord, ConsentType } from '../../types/auth';
import { apiFetch } from './client';

export interface CaptureConsentPayload {
  consent_type: ConsentType;
  version: string;
  granted: boolean;
  consent_text: string;
}

export function captureConsentApi(payload: CaptureConsentPayload): Promise<ConsentRecord> {
  return apiFetch('/v1/users/me/consent', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function listConsentsApi(): Promise<{ consents: ConsentRecord[] }> {
  return apiFetch('/v1/users/me/consents');
}
