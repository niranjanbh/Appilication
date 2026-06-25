/**
 * Local notification helpers wrapping expo-notifications.
 *
 * expo-notifications requires a native dev client (not supported in Expo Go web).
 * On web or when the module is unavailable, all functions are no-ops so the
 * rest of the app can call them without platform guards.
 */

import { Platform } from 'react-native';
import type { AdherenceAction } from '../../types/wellness';
import { registerPushTokenApi } from '../api/notifications';

export type { AdherenceAction };

declare const process: { env: Record<string, string | undefined> };

export interface ReminderNotificationData {
  reminderId: string;
  scheduledAt: string; // ISO string
  label: string;
}

/**
 * Expo Go dropped expo-notifications support in SDK 53 — and importantly,
 * merely importing the module on Android Expo Go logs a noisy ERROR about
 * removed push functionality (the require succeeds, it does not throw). So we
 * must detect Expo Go *before* touching expo-notifications. expo-constants is
 * still present in Expo Go and importing it is silent. A real build
 * (standalone/bare/dev-client) returns false here.
 */
function isExpoGo(): boolean {
  try {
    const Constants = require('expo-constants').default;
    return Constants?.executionEnvironment === 'storeClient';
  } catch {
    return false;
  }
}

function isAvailable(): boolean {
  if (Platform.OS === 'web') return false;
  // Treat Expo Go like web — notifications are unavailable there since SDK 53.
  // Short-circuiting before require('expo-notifications') avoids the module's
  // own import-time ERROR log. Use a development build for notifications.
  if (isExpoGo()) return false;
  try {
    require('expo-notifications');
    return true;
  } catch {
    return false;
  }
}

function isRemotePushSupported(): boolean {
  // isAvailable() already excludes Expo Go and web.
  return isAvailable();
}

export async function requestNotificationPermissions(): Promise<boolean> {
  if (!isAvailable()) return false;
  try {
    const Notifications = require('expo-notifications');
    const { status } = await Notifications.requestPermissionsAsync();
    return status === 'granted';
  } catch {
    return false;
  }
}

export async function scheduleReminderNotification(
  reminderId: string,
  label: string,
  scheduledAt: Date,
): Promise<string | null> {
  if (!isAvailable()) return null;
  try {
    const Notifications = require('expo-notifications');
    const id = await Notifications.scheduleNotificationAsync({
      content: {
        title: 'Reminder',
        body: label,
        data: {
          reminderId,
          scheduledAt: scheduledAt.toISOString(),
          label,
        } satisfies ReminderNotificationData,
        categoryIdentifier: 'REMINDER_ADHERENCE',
      },
      trigger: {
        type: Notifications.SchedulableTriggerInputTypes.DATE,
        date: scheduledAt,
      },
    });
    return id as string;
  } catch {
    return null;
  }
}

export async function cancelReminderNotification(notificationId: string): Promise<void> {
  if (!isAvailable()) return;
  try {
    const Notifications = require('expo-notifications');
    await Notifications.cancelScheduledNotificationAsync(notificationId);
  } catch {
    // ignore
  }
}

/**
 * Cancel every scheduled notification belonging to a reminder.
 *
 * Notification IDs are not persisted, so we discover them by scanning the OS
 * scheduled queue and matching on our own `data.reminderId`. Used before
 * (re)scheduling on edit/toggle and on delete, to keep scheduling idempotent
 * and avoid duplicate daily notifications stacking up.
 */
export async function cancelReminderNotifications(reminderId: string): Promise<void> {
  if (!isAvailable()) return;
  try {
    const Notifications = require('expo-notifications');
    const scheduled: Array<{
      identifier: string;
      content?: { data?: Partial<ReminderNotificationData> };
    }> = await Notifications.getAllScheduledNotificationsAsync();
    await Promise.all(
      scheduled
        .filter(n => n.content?.data?.reminderId === reminderId)
        .map(n => Notifications.cancelScheduledNotificationAsync(n.identifier)),
    );
  } catch {
    // ignore
  }
}

export interface ReminderSchedule {
  id: string;
  label: string;
  schedule_cron: string | null;
  schedule_interval_minutes: number | null;
}

function parseCronHourMinute(cron: string): { hour: number; minute: number } | null {
  const parts = cron.split(' ');
  const minute = parseInt(parts[0] ?? '', 10);
  const hour = parseInt(parts[1] ?? '', 10);
  if (isNaN(hour) || isNaN(minute)) return null;
  if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return null;
  return { hour, minute };
}

/**
 * Schedule (or reschedule) a reminder as a *repeating* local notification.
 *
 * - Interval reminders → repeating TIME_INTERVAL trigger.
 * - Daily (cron) reminders → repeating DAILY trigger at hour:minute. A DAILY
 *   trigger fires at the next occurrence of that time — *today* if it is still
 *   ahead, otherwise tomorrow — then every day after. This is what fixes a
 *   reminder set for 8:00 AM not firing today.
 *
 * Existing notifications for the reminder are cancelled first so repeated calls
 * (e.g. on edit) don't stack duplicates. No-op on web / Expo Go.
 */
export async function scheduleRepeatingReminder(
  reminder: ReminderSchedule,
): Promise<string | null> {
  if (!isAvailable()) return null;
  await cancelReminderNotifications(reminder.id);
  try {
    const Notifications = require('expo-notifications');
    const types = Notifications.SchedulableTriggerInputTypes;

    let trigger: Record<string, unknown> | null = null;
    if (reminder.schedule_interval_minutes && reminder.schedule_interval_minutes > 0) {
      trigger = {
        type: types.TIME_INTERVAL,
        seconds: Math.max(60, reminder.schedule_interval_minutes * 60),
        repeats: true,
      };
    } else if (reminder.schedule_cron) {
      const hm = parseCronHourMinute(reminder.schedule_cron);
      if (hm) trigger = { type: types.DAILY, hour: hm.hour, minute: hm.minute };
    }
    if (!trigger) return null;

    const id = await Notifications.scheduleNotificationAsync({
      content: {
        title: 'Reminder',
        body: reminder.label,
        data: {
          reminderId: reminder.id,
          scheduledAt: new Date().toISOString(),
          label: reminder.label,
        } satisfies ReminderNotificationData,
        categoryIdentifier: 'REMINDER_ADHERENCE',
      },
      trigger,
    });
    return id as string;
  } catch {
    return null;
  }
}

export function registerNotificationCategories(): void {
  if (!isAvailable()) return;
  try {
    const Notifications = require('expo-notifications');
    Notifications.setNotificationCategoryAsync('REMINDER_ADHERENCE', [
      { identifier: 'taken', buttonTitle: 'Taken', options: { opensAppToForeground: true } },
      { identifier: 'skipped', buttonTitle: 'Skip', options: { opensAppToForeground: false } },
      { identifier: 'snoozed', buttonTitle: 'Snooze 15 min', options: { opensAppToForeground: false } },
    ]);
  } catch {
    // ignore
  }
}

export type NotificationResponseListener = { remove: () => void };

/**
 * Resolve the EAS projectId required by getExpoPushTokenAsync. Primary source is
 * app.json -> expo.extra.eas.projectId (read via expo-constants when available);
 * an EXPO_PUBLIC_EAS_PROJECT_ID env var overrides it for local/dev builds.
 */
function getProjectId(): string | undefined {
  const envId = process.env['EXPO_PUBLIC_EAS_PROJECT_ID'];
  if (envId) return envId;
  try {
    // expo-constants is bundled with the Expo runtime on native; guard the
    // require so web / test bundles that lack it don't crash.
    const Constants = require('expo-constants').default;
    return (
      Constants?.expoConfig?.extra?.eas?.projectId ??
      Constants?.easConfig?.projectId ??
      undefined
    );
  } catch {
    return undefined;
  }
}

async function getExpoPushToken(): Promise<string | null> {
  if (!isRemotePushSupported()) return null;
  try {
    const Notifications = require('expo-notifications');
    const projectId = getProjectId();
    const { data } = await Notifications.getExpoPushTokenAsync(
      projectId ? { projectId } : undefined,
    );
    return (data as string) ?? null;
  } catch {
    return null;
  }
}

/**
 * Obtain this device's Expo push token and register it with the backend.
 *
 * Idempotent and non-fatal: on web, when the native module is unavailable, when
 * permission is denied, or when the token can't be fetched/registered, it
 * resolves to false without throwing so callers can fire-and-forget. The backend
 * PUT overwrites the stored token, so repeated calls with the same token are
 * harmless. No PHI is involved — only the opaque Expo push token.
 */
export async function registerForPushNotifications(): Promise<boolean> {
  if (!isRemotePushSupported()) return false;
  try {
    const granted = await requestNotificationPermissions();
    if (!granted) return false;

    const token = await getExpoPushToken();
    if (!token) return false;

    await registerPushTokenApi(token);
    return true;
  } catch {
    // Permission denial, missing projectId, network/API errors are all
    // non-fatal — push is a best-effort enhancement, not a blocking flow.
    return false;
  }
}

/**
 * Listen for device push token rotation and re-register with the backend.
 *
 * Note: addPushTokenListener emits the *device* token (FCM/APNs), but the
 * backend stores the *Expo* push token. So on rotation we re-fetch a fresh Expo
 * token and register that, rather than forwarding the raw device token.
 * Returns a subscription with remove(); no-op on web/unavailable.
 */
export function addPushTokenChangeListener(): NotificationResponseListener {
  if (!isRemotePushSupported()) return { remove: () => {} };
  try {
    const Notifications = require('expo-notifications');
    const sub = Notifications.addPushTokenListener(() => {
      // Fire-and-forget; failures are non-fatal.
      void (async () => {
        const expoToken = await getExpoPushToken();
        if (expoToken) await registerPushTokenApi(expoToken).catch(() => {});
      })();
    });
    return { remove: () => sub.remove() };
  } catch {
    return { remove: () => {} };
  }
}

export function addNotificationResponseListener(
  handler: (reminderId: string, scheduledAt: string, action: AdherenceAction) => void,
): NotificationResponseListener {
  if (!isAvailable()) return { remove: () => {} };
  try {
    const Notifications = require('expo-notifications');
    const sub = Notifications.addNotificationResponseReceivedListener(
      (response: {
        actionIdentifier: string;
        notification: { request: { content: { data: ReminderNotificationData } } };
      }) => {
        const { reminderId, scheduledAt } = response.notification.request.content.data;
        const actionId = response.actionIdentifier;
        let action: AdherenceAction = 'taken';
        if (actionId === 'skipped') action = 'skipped';
        else if (actionId === 'snoozed') action = 'snoozed';
        handler(reminderId, scheduledAt, action);
      },
    );
    return { remove: () => sub.remove() };
  } catch {
    return { remove: () => {} };
  }
}

// ── Remote push deep-linking ────────────────────────────────────────────────

/** Data payload attached to remote (server-sent) push notifications. */
export interface PushNotificationData {
  template_name?: string;
  resource_id?: string;
  // Legacy keys also sent by the backend; resource_id is preferred.
  id?: string;
  screen?: string;
}

/**
 * Map a remote push payload to an in-app route. Local medication-reminder
 * notifications (which carry `reminderId` and adherence action buttons) are
 * intentionally ignored here — they are handled by addNotificationResponseListener.
 * Returns null when the response is a local reminder or has no usable payload.
 */
export function routeForPushData(data: PushNotificationData | undefined): string | null {
  if (!data) return null;
  const template = data.template_name;
  const resourceId = data.resource_id ?? data.id;

  switch (template) {
    case 'appointment_confirmation':
    case 'appointment_reminder':
    case 'doctor_assigned':
      return resourceId ? `/consultations/${resourceId}` : '/consultations';
    case 'lab_result_ready':
    case 'pre_consult_report_ready':
      return '/(tabs)/reports';
    case 'medication_reminder':
      return '/(tabs)/reminders';
    default:
      return '/(tabs)/notifications';
  }
}

/**
 * Listen for taps on remote push notifications and navigate via the supplied
 * router. Local medication-reminder taps (identified by a `reminderId` in the
 * payload) are skipped so they don't double-handle with the adherence listener.
 * No-op on web / Expo Go. Returns a subscription with remove().
 */
export function addPushDeepLinkListener(
  navigate: (route: string) => void,
): NotificationResponseListener {
  if (!isAvailable()) return { remove: () => {} };
  try {
    const Notifications = require('expo-notifications');
    const sub = Notifications.addNotificationResponseReceivedListener(
      (response: {
        notification: { request: { content: { data: Record<string, unknown> } } };
      }) => {
        const data = response.notification.request.content.data;
        // Skip local reminder notifications — handled elsewhere.
        if (data && typeof data.reminderId === 'string') return;
        const route = routeForPushData(data as PushNotificationData);
        if (route) navigate(route);
      },
    );
    return { remove: () => sub.remove() };
  } catch {
    return { remove: () => {} };
  }
}

/**
 * Handle a notification tap that cold-started the app (app was killed, opened
 * via a push). Reads the last notification response on mount and navigates.
 * Local reminder taps are skipped. No-op on web / Expo Go.
 */
export async function handleInitialPushNotification(
  navigate: (route: string) => void,
): Promise<void> {
  if (!isAvailable()) return;
  try {
    const Notifications = require('expo-notifications');
    const response = await Notifications.getLastNotificationResponseAsync();
    if (!response) return;
    const data = response.notification?.request?.content?.data as
      | Record<string, unknown>
      | undefined;
    if (data && typeof data.reminderId === 'string') return;
    const route = routeForPushData(data as PushNotificationData);
    if (route) navigate(route);
  } catch {
    // ignore — best-effort deep link on cold start.
  }
}
