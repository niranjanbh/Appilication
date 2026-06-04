/**
 * Local notification helpers wrapping expo-notifications.
 *
 * expo-notifications requires a native dev client (not supported in Expo Go web).
 * On web or when the module is unavailable, all functions are no-ops so the
 * rest of the app can call them without platform guards.
 */

import { Platform } from 'react-native';
import type { AdherenceAction } from '../../types/wellness';

export type { AdherenceAction };

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
