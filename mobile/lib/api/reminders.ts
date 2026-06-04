import type {
  AdherenceLogRead,
  AdherenceLogRequest,
  Reminder,
  ReminderCreate,
  ReminderListResponse,
  ReminderUpdate,
} from '../../types/wellness';
import { apiFetch } from './client';

export function listRemindersApi(): Promise<ReminderListResponse> {
  return apiFetch('/v1/wellness/reminders');
}

export function createReminderApi(payload: ReminderCreate): Promise<Reminder> {
  return apiFetch('/v1/wellness/reminders', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateReminderApi(id: string, payload: ReminderUpdate): Promise<Reminder> {
  return apiFetch(`/v1/wellness/reminders/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function deleteReminderApi(id: string): Promise<void> {
  return apiFetch(`/v1/wellness/reminders/${id}`, { method: 'DELETE' });
}

export function logAdherenceApi(
  id: string,
  payload: AdherenceLogRequest,
): Promise<AdherenceLogRead> {
  return apiFetch(`/v1/wellness/reminders/${id}/log`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
