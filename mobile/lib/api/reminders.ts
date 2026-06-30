import type {
  AdherenceLogRead,
  AdherenceLogRequest,
  AdherenceSummary,
  DailySummary,
  Reminder,
  ReminderCreate,
  ReminderListResponse,
  ReminderUpdate,
  WeekSummaryResponse,
} from '../../types/wellness';
import { apiFetch } from './client';
import { uploadToS3 } from './lab-reports';

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

export function getAdherenceSummaryApi(): Promise<AdherenceSummary> {
  return apiFetch('/v1/wellness/reminders/adherence-summary');
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

// ── Reminder image (patient custom photo) ───────────────────────────────────────

interface ReminderImageInitiateResponse {
  reminder_id: string;
  upload_url: string;
  fields: Record<string, string>;
  s3_key: string;
  content_type: string;
}

function initiateReminderImageApi(
  id: string,
  params: { filename: string; content_type: string; file_size_bytes: number },
): Promise<ReminderImageInitiateResponse> {
  return apiFetch(`/v1/wellness/reminders/${id}/image-initiate`, {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

function finalizeReminderImageApi(id: string): Promise<{ reminder_id: string; image_uploaded: boolean }> {
  return apiFetch(`/v1/wellness/reminders/${id}/image-finalize`, { method: 'POST' });
}

export function getReminderImageUrlApi(id: string): Promise<{ url: string }> {
  return apiFetch(`/v1/wellness/reminders/${id}/image-url`);
}

export function deleteReminderImageApi(id: string): Promise<void> {
  return apiFetch(`/v1/wellness/reminders/${id}/image`, { method: 'DELETE' });
}

/**
 * Full custom-image upload for a reminder: initiate → direct S3 POST → finalize.
 * The backend stores the S3 key on the reminder's metadata at initiate.
 */
export async function uploadReminderImageApi(
  id: string,
  image: { uri: string; mimeType: string; fileName: string; fileSize: number | null },
): Promise<void> {
  const init = await initiateReminderImageApi(id, {
    filename: image.fileName,
    content_type: image.mimeType,
    file_size_bytes: image.fileSize ?? 1,
  });
  await uploadToS3({
    upload_url: init.upload_url,
    fields: init.fields,
    file_uri: image.uri,
    content_type: image.mimeType,
    filename: image.fileName,
  });
  await finalizeReminderImageApi(id);
}
