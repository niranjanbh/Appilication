import type {
  MarkAllReadResponse,
  Notification,
  NotificationListResponse,
  NotificationPreferences,
  NotificationPreferencesUpdate,
} from '../../types/notifications';
import { apiFetch } from './client';

export function listNotificationsApi(params?: {
  page?: number;
  page_size?: number;
  unread_only?: boolean;
}): Promise<NotificationListResponse> {
  const qs = new URLSearchParams();
  if (params?.page) qs.set('page', String(params.page));
  if (params?.page_size) qs.set('page_size', String(params.page_size));
  if (params?.unread_only) qs.set('unread_only', 'true');
  const query = qs.toString();
  return apiFetch(`/v1/users/notifications${query ? `?${query}` : ''}`);
}

export function markNotificationReadApi(id: string): Promise<Notification> {
  return apiFetch(`/v1/users/notifications/${id}/read`, { method: 'PATCH' });
}

export function markAllNotificationsReadApi(): Promise<MarkAllReadResponse> {
  return apiFetch('/v1/users/notifications/read-all', { method: 'POST' });
}

export function getNotificationPreferencesApi(): Promise<NotificationPreferences> {
  return apiFetch('/v1/users/notification-preferences');
}

export function updateNotificationPreferencesApi(
  payload: NotificationPreferencesUpdate,
): Promise<NotificationPreferences> {
  return apiFetch('/v1/users/notification-preferences', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}
