import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import { ActivityIndicator, StyleSheet, Switch, Text, View } from 'react-native';

import {
  getNotificationPreferencesApi,
  updateNotificationPreferencesApi,
} from '../lib/api/notifications';
import { colors, fontFamily, fontSize, spacing } from '../lib/design-tokens';
import type { NotificationPreferences } from '../types/notifications';

interface ChannelRowProps {
  label: string;
  description: string;
  value: boolean;
  onToggle: (v: boolean) => void;
  disabled?: boolean;
}

function ChannelRow({ label, description, value, onToggle, disabled }: ChannelRowProps) {
  return (
    <View style={styles.row}>
      <View style={styles.rowText}>
        <Text style={styles.rowLabel}>{label}</Text>
        <Text style={styles.rowDescription}>{description}</Text>
      </View>
      <Switch
        value={value}
        onValueChange={onToggle}
        disabled={disabled}
        trackColor={{ false: '#E5E0D8', true: colors.jade }}
        thumbColor={colors.white}
        accessibilityLabel={`${label} notifications ${value ? 'enabled' : 'disabled'}`}
      />
    </View>
  );
}

export default function NotificationPreferencesScreen() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery<NotificationPreferences>({
    queryKey: ['notification-preferences'],
    queryFn: getNotificationPreferencesApi,
  });

  const mutation = useMutation({
    mutationFn: updateNotificationPreferencesApi,
    onSuccess: (updated) => {
      queryClient.setQueryData(['notification-preferences'], updated);
    },
  });

  function toggle(channel: keyof NotificationPreferences) {
    if (!data) return;
    mutation.mutate({ [channel]: !data[channel] });
  }

  const isPending = mutation.isPending;

  return (
    <>
      <Stack.Screen options={{ title: 'Notification preferences' }} />
      <View style={styles.container}>
        {isLoading ? (
          <View style={styles.centered}>
            <ActivityIndicator size="large" color={colors.forest} />
          </View>
        ) : (
          <>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>Notification channels</Text>
              <Text style={styles.sectionSubtitle}>
                Choose how Kyros contacts you for appointment confirmations,
                reminders, and lab results.
              </Text>
            </View>

            <View style={styles.card}>
              <ChannelRow
                label="Push notifications"
                description="In-app alerts on your device"
                value={data?.push ?? true}
                onToggle={() => toggle('push')}
                disabled={isPending}
              />
              <View style={styles.divider} />
              <ChannelRow
                label="WhatsApp"
                description="Messages to your registered phone number"
                value={data?.whatsapp ?? true}
                onToggle={() => toggle('whatsapp')}
                disabled={isPending}
              />
              <View style={styles.divider} />
              <ChannelRow
                label="Email"
                description="Messages to your registered email address"
                value={data?.email ?? true}
                onToggle={() => toggle('email')}
                disabled={isPending}
              />
            </View>

            <Text style={styles.hint}>
              Disabling a channel stops future messages on that channel. You can
              re-enable at any time.
            </Text>
          </>
        )}
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.ivory,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  sectionHeader: {
    marginBottom: spacing.md,
  },
  sectionTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.h3,
    color: colors.forest,
    fontWeight: '600',
    marginBottom: spacing.xs,
  },
  sectionSubtitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    lineHeight: fontSize.body * 1.6,
  },
  card: {
    backgroundColor: colors.white,
    borderRadius: 12,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#E5E0D8',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  rowText: {
    flex: 1,
    marginRight: spacing.md,
  },
  rowLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.ink,
    fontWeight: '500',
    marginBottom: 2,
  },
  rowDescription: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
  },
  divider: {
    height: 1,
    backgroundColor: '#E5E0D8',
    marginLeft: spacing.lg,
  },
  hint: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    marginTop: spacing.md,
    lineHeight: fontSize.caption * 1.6,
  },
});
