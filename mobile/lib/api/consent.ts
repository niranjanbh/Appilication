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

export function withdrawConsentApi(consentType: ConsentType): Promise<ConsentRecord> {
  return apiFetch('/v1/users/me/consent/withdraw', {
    method: 'POST',
    body: JSON.stringify({ consent_type: consentType }),
  });
}

export interface DataSubjectResponse {
  message: string;
  request_id: string;
}

export function requestDataExportApi(): Promise<DataSubjectResponse> {
  return apiFetch('/v1/users/me/data-export', { method: 'POST' });
}

export function requestErasureApi(): Promise<DataSubjectResponse> {
  return apiFetch('/v1/users/me/delete', { method: 'POST' });
}
