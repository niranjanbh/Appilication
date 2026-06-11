import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import { ActivityIndicator, StyleSheet, Switch, Text, View } from 'react-native';
import { useThemePreference } from '../lib/theme-context';

import {
  getNotificationPreferencesApi,
  updateNotificationPreferencesApi,
} from '../lib/api/notifications';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../lib/design-tokens';
import type { NotificationPreferences } from '../types/notifications';

// ── Channel toggle row ─────────────────────────────────────────────────────────

interface ChannelRowProps {
  icon: string;
  iconBg: string;
  label: string;
  description: string;
  value: boolean;
  onToggle: (v: boolean) => void;
  disabled?: boolean;
  isDark: boolean;
  textPri: string;
  textSub: string;
}

function ChannelRow({ icon, iconBg, label, description, value, onToggle, disabled, textPri, textSub }: ChannelRowProps) {
  return (
    <View style={r.row}>
      <View style={[r.iconWrap, { backgroundColor: iconBg }]}>
        <Text style={r.icon}>{icon}</Text>
      </View>
      <View style={r.text}>
        <Text style={[r.label, { color: textPri }]}>{label}</Text>
        <Text style={[r.desc,  { color: textSub }]}>{description}</Text>
      </View>
      <Switch
        value={value}
        onValueChange={onToggle}
        disabled={disabled}
        trackColor={{
          false: colors.borderLight,
          true:  colors.electricBlue + '80',
        }}
        thumbColor={value ? colors.electricBlue : colors.white}
        ios_backgroundColor={colors.borderLight}
        accessibilityLabel={`${label} notifications ${value ? 'enabled' : 'disabled'}`}
      />
    </View>
  );
}

const r = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing[3],
    gap: spacing[3],
  },
  iconWrap: {
    width: 40,
    height: 40,
    borderRadius: borderRadius.lg,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  icon: { fontSize: 20 },
  text: { flex: 1 },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    fontWeight: '600',
  },
  desc: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    marginTop: 2,
  },
});

// ── Main screen ───────────────────────────────────────────────────────────────

export default function NotificationPreferencesScreen() {
  const queryClient = useQueryClient();
  const isDark      = useThemePreference().colorScheme === 'dark';

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

  const bg      = isDark ? colors.midnight     : colors.skyMist;
  const textPri = isDark ? colors.white        : colors.navyDeep;
  const textSub = isDark ? colors.slateText    : colors.coolGray;
  const cardBg  = isDark ? colors.nightSurface : colors.white;
  const cardBdr = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)';
  const iconBlue = isDark ? '#0F1E38' : '#EBF3FF';
  const iconAmb  = isDark ? '#2A1A05' : '#FFF4E5';
  const iconGreen = isDark ? '#061E12' : '#EDFAF3';

  return (
    <>
      <Stack.Screen options={{ title: 'Notification preferences' }} />
      <View style={[styles.container, { backgroundColor: bg }]}>
        {isLoading ? (
          <View style={styles.centered}>
            <ActivityIndicator size="large" color={colors.electricBlue} />
          </View>
        ) : (
          <>
            <View style={styles.header}>
              <Text style={[styles.title, { color: textPri }]}>Notification channels</Text>
              <Text style={[styles.subtitle, { color: textSub }]}>
                Choose how Kyros contacts you for appointment confirmations, reminders, and lab results.
              </Text>
            </View>

            <View style={[styles.card, { backgroundColor: cardBg, borderColor: cardBdr }]}>
              <ChannelRow
                icon="🔔"
                iconBg={iconBlue}
                label="Push notifications"
                description="In-app alerts on your device"
                value={data?.push ?? true}
                onToggle={() => toggle('push')}
                disabled={isPending}
                isDark={isDark}
                textPri={textPri}
                textSub={textSub}
              />
              <View style={[styles.divider, { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : colors.borderLight }]} />
              <ChannelRow
                icon="💬"
                iconBg={iconGreen}
                label="WhatsApp"
                description="Messages to your registered phone"
                value={data?.whatsapp ?? true}
                onToggle={() => toggle('whatsapp')}
                disabled={isPending}
                isDark={isDark}
                textPri={textPri}
                textSub={textSub}
              />
              <View style={[styles.divider, { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : colors.borderLight }]} />
              <ChannelRow
                icon="✉️"
                iconBg={iconAmb}
                label="Email"
                description="Messages to your registered email"
                value={data?.email ?? true}
                onToggle={() => toggle('email')}
                disabled={isPending}
                isDark={isDark}
                textPri={textPri}
                textSub={textSub}
              />
            </View>

            <Text style={[styles.hint, { color: textSub }]}>
              Disabling a channel stops future messages on that channel. You can re-enable at any time.
            </Text>
          </>
        )}
      </View>
    </>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
  },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },

  header: { gap: spacing[2], marginBottom: spacing[6] },
  title: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.h3,
    fontWeight: '700',
  },
  subtitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    lineHeight: 22,
  },

  card: {
    borderRadius: borderRadius.xxl,
    paddingHorizontal: spacing[5],
    paddingVertical: spacing[2],
    borderWidth: 1,
    boxShadow: '0 6px 14px rgba(0,0,0,0.07)',
  },
  divider: { height: 1, marginLeft: 40 + spacing[3] },

  hint: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    lineHeight: 18,
    marginTop: spacing[4],
  },
});
