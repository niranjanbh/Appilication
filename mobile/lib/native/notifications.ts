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

function isAvailable(): boolean {
  if (Platform.OS === 'web') return false;
  try {
    require('expo-notifications');
    return true;
  } catch {
    return false;
  }
}

/**
 * Expo Go dropped remote (push) notification support in SDK 53 — calling
 * getExpoPushTokenAsync / addPushTokenListener there throws and logs a noisy
 * warning. Local notifications still work in Expo Go, so this only gates the
 * remote-push paths. A real build (standalone/bare/dev-client) returns false.
 */
function isExpoGo(): boolean {
  try {
    const Constants = require('expo-constants').default;
    return Constants?.executionEnvironment === 'storeClient';
  } catch {
    return false;
  }
}

function isRemotePushSupported(): boolean {
  // Check Expo Go first: it only requires expo-constants. Calling isAvailable()
  // first would require('expo-notifications'), which itself logs the Expo Go
  // "push removed in SDK 53" warning before we ever get to skip it.
  return !isExpoGo() && isAvailable();
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
