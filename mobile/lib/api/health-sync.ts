import type { HealthSyncRequest, HealthSyncResponse } from '../../types/wellness';
import { apiFetch } from './client';

export function postHealthSync(payload: HealthSyncRequest): Promise<HealthSyncResponse> {
  return apiFetch<HealthSyncResponse>('/v1/wellness/health-sync', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
