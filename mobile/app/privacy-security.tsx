import { Ionicons } from '@expo/vector-icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { AmbientBackground } from '../components/ui/AmbientBackground';
import { GlassCard } from '../components/ui/GlassCard';
import { HapticPressable } from '../components/ui/HapticPressable';
import { listConsentsApi, withdrawConsentApi } from '../lib/api/consent';
import {
  borderRadius,
  colors,
  fontFamily,
  fontSize,
  spacing,
} from '../lib/design-tokens';
import { useTheme } from '../lib/theme';
import type { ConsentRecord, ConsentType } from '../types/auth';

const CONSENT_LABELS: Record<ConsentType, string> = {
  terms: 'Terms of Service',
  privacy: 'Privacy Policy',
  telemedicine: 'Telemedicine Consent',
  data_processing: 'Data Processing (DPDP)',
  health_sync: 'Health Data Sync',
  marketing: 'Marketing Communications',
  recording: 'Consultation Recording',
  research: 'Research Participation',
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'Asia/Kolkata',
  });
}

function ConsentCard({
  consent,
  onWithdraw,
  withdrawing,
}: {
  consent: ConsentRecord;
  onWithdraw?: (consent: ConsentRecord) => void;
  withdrawing?: boolean;
}) {
  const t = useTheme();
  const isActive = consent.granted && !consent.revoked_at;
  const statusColor = isActive ? colors.jade : colors.stone;
  const statusLabel = consent.revoked_at
    ? 'Revoked'
    : consent.granted
      ? 'Active'
      : 'Declined';

  return (
    <GlassCard>
      <View style={styles.consentRow}>
        <View style={styles.consentInfo}>
          <Text style={[styles.consentType, { color: t.text }]}>
            {CONSENT_LABELS[consent.consent_type] ?? consent.consent_type}
          </Text>
          <Text style={[styles.consentMeta, { color: t.textSub }]}>
            v{consent.version} · Granted {formatDate(consent.granted_at)}
          </Text>
          {consent.revoked_at && (
            <Text style={[styles.consentMeta, { color: t.textSub }]}>
              Revoked {formatDate(consent.revoked_at)}
            </Text>
          )}
        </View>
        <View style={[styles.statusPill, { backgroundColor: statusColor + '18' }]}>
          <Text style={[styles.statusText, { color: statusColor }]}>{statusLabel}</Text>
        </View>
      </View>
      {isActive && onWithdraw && (
        <Pressable
          onPress={() => onWithdraw(consent)}
          disabled={withdrawing}
          accessibilityLabel={`Withdraw ${CONSENT_LABELS[consent.consent_type] ?? consent.consent_type}`}
          style={[styles.withdrawBtn, withdrawing && styles.withdrawDisabled]}
        >
          <Text style={[styles.withdrawText, { color: colors.alert }]}>
            {withdrawing ? 'Withdrawing…' : 'Withdraw consent'}
          </Text>
        </Pressable>
      )}
    </GlassCard>
  );
}

export default function PrivacySecurityScreen() {
  const t = useTheme();
  const router = useRouter();

  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['consents'],
    queryFn: listConsentsApi,
    staleTime: 60_000,
  });

  const withdrawMutation = useMutation({
    mutationFn: (consent: ConsentRecord) => withdrawConsentApi(consent.consent_type),
    onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ['consents'] }); },
    onError: () => { Alert.alert('Error', 'Could not withdraw consent. Please try again.'); },
  });

  const handleWithdraw = (consent: ConsentRecord) => {
    Alert.alert(
      'Withdraw consent?',
      `You are withdrawing "${CONSENT_LABELS[consent.consent_type] ?? consent.consent_type}". `
        + 'Some features that rely on this consent may stop working.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Withdraw',
          style: 'destructive',
          onPress: () => withdrawMutation.mutate(consent),
        },
      ],
    );
  };

  const consents = data?.consents ?? [];
  const active = consents.filter(c => c.granted && !c.revoked_at);
  const inactive = consents.filter(c => !c.granted || c.revoked_at);
  const withdrawingType =
    withdrawMutation.isPending ? withdrawMutation.variables?.consent_type : undefined;

  return (
    <View style={[styles.flex, { backgroundColor: t.background }]}>
      <AmbientBackground />
      <ScrollView style={styles.flex} contentContainerStyle={styles.container}>
        <Text style={[styles.heading, { color: t.text }]}>Privacy & Security</Text>
        <Text style={[styles.subtitle, { color: t.textSub }]}>
          Manage your consents and data rights under the DPDP Act 2023.
        </Text>

        {isLoading ? (
          <ActivityIndicator size="large" color={t.primary} style={styles.loader} />
        ) : (
          <>
            {active.length > 0 && (
              <View style={styles.section}>
                <Text style={[styles.sectionLabel, { color: t.textSub }]}>Active consents</Text>
                {active.map(c => (
                  <ConsentCard
                    key={c.id}
                    consent={c}
                    onWithdraw={handleWithdraw}
                    withdrawing={withdrawingType === c.consent_type}
                  />
                ))}
              </View>
            )}

            {inactive.length > 0 && (
              <View style={styles.section}>
                <Text style={[styles.sectionLabel, { color: t.textSub }]}>Past consents</Text>
                {inactive.map(c => <ConsentCard key={c.id} consent={c} />)}
              </View>
            )}

            {consents.length === 0 && (
              <GlassCard>
                <Text style={[styles.emptyText, { color: t.textSub }]}>
                  No consent records found.
                </Text>
              </GlassCard>
            )}
          </>
        )}

        <View style={styles.section}>
          <Text style={[styles.sectionLabel, { color: t.textSub }]}>Your data rights</Text>
          <GlassCard>
            <HapticPressable
              haptic="selection"
              scaleTo={0.98}
              style={styles.rightRow}
              onPress={() => router.push('/download-data')}
              accessibilityLabel="Download my data"
            >
              <Ionicons name="download-outline" size={20} color={t.primary} />
              <Text style={[styles.rightLabel, { color: t.text }]}>Download my data</Text>
              <Ionicons name="chevron-forward" size={16} color={t.textSub} />
            </HapticPressable>
          </GlassCard>
          <GlassCard>
            <HapticPressable
              haptic="selection"
              scaleTo={0.98}
              style={styles.rightRow}
              onPress={() => router.push('/delete-account')}
              accessibilityLabel="Delete my account"
            >
              <Ionicons name="warning-outline" size={20} color={colors.alert} />
              <Text style={[styles.rightLabel, { color: colors.alert }]}>Delete my account</Text>
              <Ionicons name="chevron-forward" size={16} color={colors.alert} />
            </HapticPressable>
          </GlassCard>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
    paddingBottom: spacing[12],
    gap: spacing[4],
  },
  heading: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    fontWeight: '600',
  },
  subtitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    lineHeight: 22,
  },
  loader: { marginTop: spacing[10] },
  section: { gap: spacing[3], marginTop: spacing[4] },
  sectionLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
    paddingHorizontal: spacing[2],
  },
  consentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
  },
  consentInfo: { flex: 1, gap: 2 },
  consentType: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
  consentMeta: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
  },
  statusPill: {
    paddingHorizontal: spacing[2],
    paddingVertical: 3,
    borderRadius: borderRadius.full,
  },
  withdrawBtn: {
    marginTop: spacing[3],
    alignSelf: 'flex-start',
  },
  withdrawText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: '600',
  },
  withdrawDisabled: { opacity: 0.5 },
  statusText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
  },
  emptyText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    textAlign: 'center',
    paddingVertical: spacing[4],
  },
  rightRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    paddingVertical: spacing[2],
  },
  rightLabel: {
    flex: 1,
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '500',
  },
});
