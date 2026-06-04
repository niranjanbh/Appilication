import { apiFetch } from './client';

export interface AbhaStatus {
  linked: boolean;
  abha_number_masked: string | null;
}

export interface AbhaCreateInitResponse {
  txn_id: string;
  message: string;
}

export function getAbhaStatus(): Promise<AbhaStatus> {
  return apiFetch('/v1/clinic/patient/abha');
}

export function linkAbhaNumber(abha_number: string): Promise<AbhaStatus> {
  return apiFetch('/v1/clinic/patient/abha/link', {
    method: 'POST',
    body: JSON.stringify({ abha_number }),
  });
}

export function initAbhaCreation(aadhaar_number: string): Promise<AbhaCreateInitResponse> {
  return apiFetch('/v1/clinic/patient/abha/create/init', {
    method: 'POST',
    body: JSON.stringify({ aadhaar_number }),
  });
}

export function confirmAbhaCreation(txn_id: string, otp: string): Promise<AbhaStatus> {
  return apiFetch('/v1/clinic/patient/abha/create/confirm', {
    method: 'POST',
    body: JSON.stringify({ txn_id, otp }),
  });
}
