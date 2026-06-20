import { useRouter } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useThemePreference } from '../../lib/theme-context';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { captureConsentApi } from '../../lib/api/consent';
import { borderRadius, colors, fontFamily, fontSize, spacing , withAlpha } from '../../lib/design-tokens';
import type { ConsentType } from '../../types/auth';

const DPDP_TEXT =
  'Kyros Clinic collects and processes your personal health data under the Digital Personal ' +
  'Data Protection Act 2023 (DPDP). Your data is stored in India, is never sold, and is ' +
  'used only to provide and improve your care. You may withdraw consent, download your data, ' +
  'or request deletion at any time from Profile → My consents.';

const TELEMEDICINE_TEXT =
  'I consent to receive telemedicine consultations via the Kyros platform, delivered by ' +
  'registered medical practitioners in accordance with NMC Telemedicine Practice Guidelines ' +
  '2020 and the Indian Medical Council Act 1956. I understand that telemedicine does not ' +
  'replace in-person care for emergencies.';

const TOTAL_STEPS = 4;
const STEP = 3;

// ─── Consent card ─────────────────────────────────────────────────────────────

interface ConsentCardProps {
  icon: string;
  title: string;
  summary: string;
  fullText: string;
  agreed: boolean;
  onAgree: () => void;
  isDark: boolean;
}

function ConsentCard({ icon, title, summary, fullText, agreed, onAgree, isDark }: ConsentCardProps) {
  const [expanded, setExpanded] = useState(false);

  const cardBg  = isDark ? colors.forestSurface : colors.white;
  const cardBdr = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)';
  const textPri = isDark ? colors.ivoryText     : colors.ink;
  const textSub = isDark ? colors.stoneDim : colors.stone;

  return (
    <View style={[c.card, { backgroundColor: cardBg, borderColor: cardBdr }]}>
      <View style={c.cardHeader}>
        <View style={[c.iconWrap, { backgroundColor: isDark ? colors.forestSurfaceRaised : colors.ivory }]}>
          <Text style={c.icon}>{icon}</Text>
        </View>
        <View style={c.cardHeaderText}>
          <Text style={[c.title, { color: textPri }]}>{title}</Text>
          {agreed && (
            <View style={[c.agreedBadge, { backgroundColor: colors.jade + '20' }]}>
              <Text style={[c.agreedBadgeText, { color: colors.jade }]}>✓ Agreed</Text>
            </View>
          )}
        </View>
      </View>

      <Text style={[c.summary, { color: textSub }]}>{summary}</Text>

      <Pressable onPress={() => setExpanded(e => !e)} accessibilityLabel="Read full consent text">
        <Text style={[c.toggle, { color: colors.jade }]}>
          {expanded ? 'Hide full text ↑' : 'Read full text ↓'}
        </Text>
      </Pressable>

      {expanded && (
        <Text style={[c.fullText, { color: textSub }]}>{fullText}</Text>
      )}

      {!agreed && (
        <Pressable
          style={[c.agreeBtn, { borderColor: colors.forest, backgroundColor: isDark ? colors.jade : colors.ivory }]}
          onPress={onAgree}
          accessibilityLabel={`I agree to ${title}`}
        >
          <Text style={[c.agreeBtnText, { color: isDark ? colors.ivoryText : colors.ink }]}>
            I agree
          </Text>
        </Pressable>
      )}
    </View>
  );
}

const c = StyleSheet.create({
  card: {
    borderRadius: borderRadius.xxl,
    padding: spacing[5],
    marginBottom: spacing[4],
    gap: spacing[3],
    borderWidth: 1,
    boxShadow: '0 6px 14px rgba(0,0,0,0.07)',
  },
  cardHeader: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing[3] },
  iconWrap: {
    width: 44,
    height: 44,
    borderRadius: borderRadius.xl,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  icon: { fontSize: 22 },
  cardHeaderText: { flex: 1, gap: spacing[1] },
  title: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    fontWeight: '700',
  },
  agreedBadge: {
    alignSelf: 'flex-start',
    borderRadius: borderRadius.full,
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
  },
  agreedBadgeText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
  },
  summary: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    lineHeight: 22,
  },
  toggle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: '600',
  },
  fullText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    lineHeight: 20,
  },
  agreeBtn: {
    height: 48,
    borderWidth: 1.5,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
  },
  agreeBtnText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
});

// ─── Main screen ──────────────────────────────────────────────────────────────

export default function ConsentScreen() {
  const router  = useRouter();
  const isDark  = useThemePreference().colorScheme === 'dark';
  const [dpdpAgreed, setDpdpAgreed] = useState(false);
  const [teleAgreed, setTeleAgreed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError]           = useState<string | null>(null);

  const bothAgreed = dpdpAgreed && teleAgreed;

  // Preserve all existing consent capture logic
  const handleAgree = async (type: ConsentType, text: string, setAgreed: (v: boolean) => void) => {
    setError(null);
    try {
      await captureConsentApi({ consent_type: type, version: '1.0', granted: true, consent_text: text });
      setAgreed(true);
    } catch {
      setError('Could not record your consent. Please check your connection and try again.');
    }
  };

  const handleContinue = async () => {
    setSubmitting(true);
    router.push('/(onboarding)/health-sync');
    setSubmitting(false);
  };

  const btnScale = useSharedValue(1);
  const btnAnim  = useAnimatedStyle(() => ({ transform: [{ scale: btnScale.value }] }));

  const bg      = isDark ? colors.forestInk  : colors.ivory;
  const textSub = isDark ? colors.stoneDim : colors.stone;
  const textPri = isDark ? colors.ivoryText     : colors.ink;

  return (
    <ScrollView style={[styles.flex, { backgroundColor: bg }]} contentContainerStyle={styles.container}>

      {/* Step progress */}
      <View style={styles.stepRow}>
        <View style={styles.progressTrack}>
          <View style={[styles.progressFill, { width: `${(STEP / TOTAL_STEPS) * 100}%` as never }]} />
        </View>
        <Text style={[styles.stepLabel, { color: textSub }]}>Step {STEP} of {TOTAL_STEPS}</Text>
      </View>

      <View style={styles.header}>
        <Text style={[styles.title, { color: textPri }]}>Your rights and permissions</Text>
        <Text style={[styles.subtitle, { color: textSub }]}>Two quick consents — read, agree, then continue.</Text>
      </View>

      <ConsentCard
        icon="🔒"
        title="Data protection (DPDP)"
        summary="We store your health data securely in India under the DPDP Act 2023. You can withdraw, download, or delete your data at any time."
        fullText={DPDP_TEXT}
        agreed={dpdpAgreed}
        onAgree={() => handleAgree('data_processing', DPDP_TEXT, setDpdpAgreed)}
        isDark={isDark}
      />

      <ConsentCard
        icon="🩺"
        title="Telemedicine consent"
        summary="You consent to receive medical consultations via video call from registered Kyros doctors, per NMC Telemedicine Guidelines 2020."
        fullText={TELEMEDICINE_TEXT}
        agreed={teleAgreed}
        onAgree={() => handleAgree('telemedicine', TELEMEDICINE_TEXT, setTeleAgreed)}
        isDark={isDark}
      />

      {error && <Text style={styles.error}>{error}</Text>}

      <Animated.View style={btnAnim}>
        <Pressable
          style={[styles.button, (!bothAgreed || submitting) && styles.buttonMuted]}
          onPress={handleContinue}
          onPressIn={() => { btnScale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
          onPressOut={() => { btnScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
          disabled={!bothAgreed || submitting}
          accessibilityLabel="Continue"
        >
          {submitting ? (
            <ActivityIndicator color={colors.white} size="small" />
          ) : (
            <Text style={styles.buttonText}>Continue</Text>
          )}
        </Pressable>
      </Animated.View>

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
    paddingBottom: spacing[8],
  },

  stepRow: { gap: spacing[2], marginBottom: spacing[6] },
  progressTrack: {
    height: 4,
    backgroundColor: colors.borderLight,
    borderRadius: 2,
    overflow: 'hidden',
  },
  progressFill: {
    height: 4,
    backgroundColor: colors.jade,
    borderRadius: 2,
  },
  stepLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },

  header: { gap: spacing[2], marginBottom: spacing[6] },
  title: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    fontWeight: '600',
  },
  subtitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    lineHeight: 22,
  },

  error: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: colors.alert,
    textAlign: 'center',
    marginBottom: spacing[3],
  },

  button: {
    height: 56,
    backgroundColor: colors.forest,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: spacing[2],
    boxShadow: `0 8px 16px ${withAlpha(colors.forest, 0.25)}`,
  },
  buttonMuted: { opacity: 0.40 },
  buttonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.ivoryText,
    fontWeight: '600',
  },
});
