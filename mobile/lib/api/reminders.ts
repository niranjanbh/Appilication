import type {
  AdherenceLogRead,
  AdherenceLogRequest,
  DailySummary,
  Reminder,
  ReminderCreate,
  ReminderListResponse,
  ReminderUpdate,
  WeekSummaryResponse,
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

export function getDailySummaryApi(date?: string): Promise<DailySummary> {
  const params = date ? `?date=${date}` : '';
  return apiFetch(`/v1/wellness/reminders/daily-summary${params}`);
}

export function getWeekSummaryApi(weekStart: string): Promise<WeekSummaryResponse> {
  return apiFetch(`/v1/wellness/reminders/week-summary?start=${weekStart}`);
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
