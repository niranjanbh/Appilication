import type { HealthSyncRequest, HealthSyncResponse } from '../../types/wellness';
import { apiFetch } from './client';

export function postHealthSync(payload: HealthSyncRequest): Promise<HealthSyncResponse> {
  return apiFetch<HealthSyncResponse>('/v1/wellness/health-sync', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Latest synced activity metrics for the lifestyle dashboard. Every field is
 * nullable — a metric is absent until a wearable that provides it has synced.
 */
export interface HealthSummary {
  steps_today: number | null;
  resting_heart_rate_bpm: number | null;
  hrv_ms: number | null;
  updated_at: string | null;
}

export function getHealthSummaryApi(): Promise<HealthSummary> {
  return apiFetch<HealthSummary>('/v1/wellness/health-summary');
}
