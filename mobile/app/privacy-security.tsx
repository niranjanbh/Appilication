import { Ionicons } from '@expo/vector-icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from 'react-native';
import { Alert } from '../lib/ui/alert';

import { AmbientBackground } from '../components/ui/AmbientBackground';
import { GlassCard } from '../components/ui/GlassCard';
import { HapticPressable } from '../components/ui/HapticPressable';
import { captureConsentApi, listConsentsApi, withdrawConsentApi } from '../lib/api/consent';
import {
  borderRadius,
  colors,
  fontFamily,
  fontSize,
  spacing,
  tintSoft,
  withAlpha,
  type TintName,
} from '../lib/design-tokens';
import { useTheme } from '../lib/theme';
import type { ConsentRecord, ConsentType } from '../types/auth';

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

// ── Consent definitions ──────────────────────────────────────────────────────

interface ConsentDef {
  type: ConsentType;
  label: string;
  icon: IoniconName;
  tint: TintName;
  required: boolean;
  description: string;
  benefit: string;
}

const CONSENT_DEFS: ConsentDef[] = [
  {
    type: 'terms',
    label: 'Terms of Service',
    icon: 'document-text-outline',
    tint: 'forest',
    required: true,
    description: 'Agreement to use the Kyros platform.',
    benefit: 'Required to use the app.',
  },
  {
    type: 'privacy',
    label: 'Privacy Policy',
    icon: 'shield-checkmark-outline',
    tint: 'forest',
    required: true,
    description: 'How we collect, store, and protect your data.',
    benefit: 'Required to use the app.',
  },
  {
    type: 'telemedicine',
    label: 'Telemedicine Consent',
    icon: 'videocam-outline',
    tint: 'blue',
    required: true,
    description: 'Consent for remote medical consultations.',
    benefit: 'Required to book and join video consultations.',
  },
  {
    type: 'data_processing',
    label: 'Data Processing (DPDP)',
    icon: 'server-outline',
    tint: 'sage',
    required: true,
    description: 'Processing of your health data under the DPDP Act 2023.',
    benefit: 'Required for care plans, prescriptions, and lab report analysis.',
  },
  {
    type: 'health_sync',
    label: 'Health Data Sync',
    icon: 'fitness-outline',
    tint: 'green',
    required: false,
    description: 'Sync steps, heart rate, and sleep from Apple Health or Google Health Connect.',
    benefit: 'Gives your doctor a fuller picture of your daily activity and recovery.',
  },
  {
    type: 'recording',
    label: 'Consultation Recording',
    icon: 'mic-outline',
    tint: 'saffron',
    required: false,
    description: 'Record video consultations for your personal reference.',
    benefit: 'Review what your doctor said anytime — no need to take notes during the call.',
  },
  {
    type: 'marketing',
    label: 'Marketing Communications',
    icon: 'mail-outline',
    tint: 'peach',
    required: false,
    description: 'Receive health tips, offers, and product updates.',
    benefit: 'Stay informed about new features, seasonal health tips, and exclusive offers.',
  },
  {
    type: 'research',
    label: 'Research Participation',
    icon: 'flask-outline',
    tint: 'violet',
    required: false,
    description: 'Contribute anonymized data to hormonal health research.',
    benefit: 'Help advance hormonal health science — your data is always anonymized.',
  },
];

const CONSENT_VERSIONS: Record<ConsentType, string> = {
  terms: '1.0',
  privacy: '1.0',
  telemedicine: '1.0',
  data_processing: '1.0',
  health_sync: '1.0',
  marketing: '1.0',
  recording: '1.0',
  research: '1.0',
};

const CONSENT_TEXTS: Record<ConsentType, string> = {
  terms: 'I agree to the Kyros Terms of Service.',
  privacy: 'I agree to the Kyros Privacy Policy.',
  telemedicine: 'I consent to receiving medical consultations via telemedicine.',
  data_processing: 'I consent to the processing of my health data under DPDP Act 2023.',
  health_sync: 'I consent to syncing health data from my device.',
  marketing: 'I consent to receiving marketing communications from Kyros.',
  recording: 'I consent to the recording of my consultations.',
  research: 'I consent to contributing anonymized data to research.',
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'Asia/Kolkata',
  });
}

// ── Consent toggle card ──────────────────────────────────────────────────────

function ConsentToggleCard({
  def,
  record,
  onGrant,
  onWithdraw,
  busy,
}: {
  def: ConsentDef;
  record: ConsentRecord | null;
  onGrant: (type: ConsentType) => void;
  onWithdraw: (consent: ConsentRecord) => void;
  busy: boolean;
}) {
  const t = useTheme();
  const isActive = record != null && record.granted && !record.revoked_at;
  const pair = tintSoft[def.tint];
  const chipBg = t.isDark ? pair.bgDark : pair.bgLight;
  const tint = t.isDark ? pair.tintDark : pair.tintLight;

  const handleToggle = () => {
    if (busy) return;
    if (isActive && record) {
      onWithdraw(record);
    } else {
      onGrant(def.type);
    }
  };

  return (
    <GlassCard>
      <View style={card.row}>
        <View style={[card.iconWrap, { backgroundColor: chipBg }]}>
          <Ionicons name={def.icon} size={20} color={tint} />
        </View>
        <View style={card.body}>
          <View style={card.titleRow}>
            <Text style={[card.label, { color: t.text }]}>{def.label}</Text>
            {def.required && (
              <View style={[card.reqPill, { backgroundColor: withAlpha(tint, 0.12) }]}>
                <Text style={[card.reqText, { color: tint }]}>Required</Text>
              </View>
            )}
          </View>
          <Text style={[card.desc, { color: t.textSub }]}>{def.description}</Text>
        </View>
        <Switch
          value={isActive}
          onValueChange={handleToggle}
          disabled={busy}
          trackColor={{
            false: t.isDark ? withAlpha(colors.stoneDim, 0.30) : colors.borderLight,
            true: withAlpha(colors.jade, 0.50),
          }}
          thumbColor={isActive ? colors.jade : (t.isDark ? colors.stoneDim : colors.white)}
          ios_backgroundColor={t.isDark ? withAlpha(colors.stoneDim, 0.30) : colors.borderLight}
          accessibilityLabel={`${def.label}: ${isActive ? 'granted' : 'not granted'}`}
        />
      </View>

      {/* Active: show granted date */}
      {isActive && record && (
        <Text style={[card.meta, { color: t.textSub }]}>
          Granted {formatDate(record.granted_at)} · v{record.version}
        </Text>
      )}

      {/* Not active: show benefit nudge */}
      {!isActive && (
        <View style={[card.benefitRow, { backgroundColor: withAlpha(tint, t.isDark ? 0.08 : 0.05) }]}>
          <Ionicons name="sparkles-outline" size={14} color={tint} />
          <Text style={[card.benefitText, { color: tint }]}>{def.benefit}</Text>
        </View>
      )}
    </GlassCard>
  );
}

const card = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
  },
  iconWrap: {
    width: 40,
    height: 40,
    borderRadius: borderRadius.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  body: { flex: 1, gap: 2 },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
  },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
    flexShrink: 1,
  },
  reqPill: {
    paddingHorizontal: spacing[2],
    paddingVertical: 1,
    borderRadius: borderRadius.full,
  },
  reqText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
  },
  desc: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    lineHeight: 18,
  },
  meta: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    marginTop: spacing[2],
    paddingLeft: 52,
  },
  benefitRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
    marginTop: spacing[3],
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
    borderRadius: borderRadius.lg,
  },
  benefitText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    fontWeight: '500',
    flex: 1,
    lineHeight: 18,
  },
});

// ── Screen ───────────────────────────────────────────────────────────────────

export default function PrivacySecurityScreen() {
  const t = useTheme();
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['consents'],
    queryFn: listConsentsApi,
    staleTime: 60_000,
  });

  const consents = data?.consents ?? [];
  const consentMap = new Map<ConsentType, ConsentRecord>();
  for (const c of consents) {
    const existing = consentMap.get(c.consent_type);
    if (!existing || new Date(c.granted_at) > new Date(existing.granted_at)) {
      consentMap.set(c.consent_type, c);
    }
  }

  const grantMutation = useMutation({
    mutationFn: (type: ConsentType) =>
      captureConsentApi({
        consent_type: type,
        version: CONSENT_VERSIONS[type],
        granted: true,
        consent_text: CONSENT_TEXTS[type],
      }),
    onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ['consents'] }); },
    onError: () => { Alert.alert('Error', 'Could not grant consent. Please try again.'); },
  });

  const withdrawMutation = useMutation({
    mutationFn: (consent: ConsentRecord) => withdrawConsentApi(consent.consent_type),
    onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ['consents'] }); },
    onError: () => { Alert.alert('Error', 'Could not withdraw consent. Please try again.'); },
  });

  const handleGrant = (type: ConsentType) => {
    grantMutation.mutate(type);
  };

  const handleWithdraw = (consent: ConsentRecord) => {
    const def = CONSENT_DEFS.find(d => d.type === consent.consent_type);
    const label = def?.label ?? consent.consent_type;

    if (def?.required) {
      Alert.alert(
        'Cannot withdraw',
        `"${label}" is required to use Kyros. Withdrawing it will limit your access to the app.`,
        [
          { text: 'Keep it', style: 'cancel' },
          {
            text: 'Withdraw anyway',
            style: 'destructive',
            onPress: () => withdrawMutation.mutate(consent),
          },
        ],
      );
    } else {
      Alert.alert(
        'Withdraw consent?',
        `You are withdrawing "${label}". Some features that rely on this consent may stop working.`,
        [
          { text: 'Cancel', style: 'cancel' },
          {
            text: 'Withdraw',
            style: 'destructive',
            onPress: () => withdrawMutation.mutate(consent),
          },
        ],
      );
    }
  };

  const busyType = grantMutation.isPending
    ? (grantMutation.variables as ConsentType)
    : withdrawMutation.isPending
      ? withdrawMutation.variables?.consent_type
      : undefined;

  const requiredDefs = CONSENT_DEFS.filter(d => d.required);
  const optionalDefs = CONSENT_DEFS.filter(d => !d.required);

  const grantedCount = CONSENT_DEFS.filter(d => {
    const r = consentMap.get(d.type);
    return r && r.granted && !r.revoked_at;
  }).length;

  return (
    <View style={[styles.flex, { backgroundColor: t.background }]}>
      <AmbientBackground />
      <ScrollView
        style={styles.flex}
        contentContainerStyle={styles.container}
        showsVerticalScrollIndicator={false}
      >
        <Text style={[styles.heading, { color: t.text }]}>Privacy & Consent</Text>
        <Text style={[styles.subtitle, { color: t.textSub }]}>
          Manage your consents and data rights under the DPDP Act 2023.
          You can change these anytime.
        </Text>

        {/* Summary bar */}
        <View style={[styles.summaryBar, { backgroundColor: t.surface }]}>
          <View style={styles.summaryLeft}>
            <Ionicons name="shield-checkmark" size={20} color={colors.jade} />
            <Text style={[styles.summaryText, { color: t.text }]}>
              {grantedCount} of {CONSENT_DEFS.length} consents active
            </Text>
          </View>
          {grantedCount < CONSENT_DEFS.length && (
            <View style={[styles.summaryPill, { backgroundColor: withAlpha(colors.saffron, 0.12) }]}>
              <Text style={[styles.summaryPillText, { color: colors.saffron }]}>
                {CONSENT_DEFS.length - grantedCount} pending
              </Text>
            </View>
          )}
        </View>

        {isLoading ? (
          <ActivityIndicator size="large" color={t.primary} style={styles.loader} />
        ) : (
          <>
            {/* Required consents */}
            <View style={styles.section}>
              <Text style={[styles.sectionLabel, { color: t.textSub }]}>Required</Text>
              <Text style={[styles.sectionHint, { color: t.textSub }]}>
                These are needed for the app to function.
              </Text>
              {requiredDefs.map(def => (
                <ConsentToggleCard
                  key={def.type}
                  def={def}
                  record={consentMap.get(def.type) ?? null}
                  onGrant={handleGrant}
                  onWithdraw={handleWithdraw}
                  busy={busyType === def.type}
                />
              ))}
            </View>

            {/* Optional consents */}
            <View style={styles.section}>
              <Text style={[styles.sectionLabel, { color: t.textSub }]}>Optional</Text>
              <Text style={[styles.sectionHint, { color: t.textSub }]}>
                Enable these for a better experience.
              </Text>
              {optionalDefs.map(def => (
                <ConsentToggleCard
                  key={def.type}
                  def={def}
                  record={consentMap.get(def.type) ?? null}
                  onGrant={handleGrant}
                  onWithdraw={handleWithdraw}
                  busy={busyType === def.type}
                />
              ))}
            </View>
          </>
        )}

        {/* Data rights */}
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
              <View style={styles.rightBody}>
                <Text style={[styles.rightLabel, { color: t.text }]}>Download my data</Text>
                <Text style={[styles.rightSub, { color: t.textSub }]}>
                  Get a copy of all your health records and account data.
                </Text>
              </View>
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
              <View style={styles.rightBody}>
                <Text style={[styles.rightLabel, { color: colors.alert }]}>Delete my account</Text>
                <Text style={[styles.rightSub, { color: t.textSub }]}>
                  Permanently erase your account and all associated data.
                </Text>
              </View>
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

  summaryBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    borderRadius: borderRadius.xl,
  },
  summaryLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
  },
  summaryText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
  summaryPill: {
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
    borderRadius: borderRadius.full,
  },
  summaryPillText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
  },

  section: { gap: spacing[3], marginTop: spacing[2] },
  sectionLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
    paddingHorizontal: spacing[2],
  },
  sectionHint: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    paddingHorizontal: spacing[2],
    marginTop: -spacing[2],
  },

  rightRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    paddingVertical: spacing[1],
  },
  rightBody: { flex: 1, gap: 2 },
  rightLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '500',
  },
  rightSub: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    lineHeight: 18,
  },
});
