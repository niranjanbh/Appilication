import { useRouter } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { useThemePreference } from '../../lib/theme-context';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { captureConsentApi } from '../../lib/api/consent';
import { postHealthSync } from '../../lib/api/health-sync';
import { borderRadius, colors, fontFamily, fontSize, spacing , withAlpha } from '../../lib/design-tokens';
import { fetchHealthData } from '../../lib/native/health-data';
import { requestHealthPermissions } from '../../lib/native/health';
import { registerHealthSyncTask } from '../../lib/native/background-sync';

const HEALTH_SYNC_TEXT =
  'I consent to Kyros reading health data (steps, heart rate, sleep duration, weight, ' +
  'blood pressure, blood glucose) from Apple Health or Health Connect to support my care plan. ' +
  'I can revoke this permission at any time from Profile → My consents.';

const DATA_POINTS = [
  { icon: '👟', label: 'Steps and activity' },
  { icon: '❤️', label: 'Heart rate and HRV' },
  { icon: '😴', label: 'Sleep duration' },
  { icon: '⚖️', label: 'Weight and body composition' },
  { icon: '🩸', label: 'Blood pressure and glucose' },
];

const TOTAL_STEPS = 5;
const STEP = 4;

export default function HealthSyncScreen() {
  const router = useRouter();
  const isDark = useThemePreference().colorScheme === 'dark';
  const [loading, setLoading] = useState(false);

  const finish = async () => {
    router.push('/(onboarding)/abha-link');
  };

  // Preserve 100% of existing health sync logic
  const handleAllow = async () => {
    setLoading(true);
    try {
      const result = await requestHealthPermissions();
      if (result.granted) {
        await captureConsentApi({ consent_type: 'health_sync', version: '1.0', granted: true, consent_text: HEALTH_SYNC_TEXT });
        const source = Platform.OS === 'ios' ? 'apple_health' : 'google_health_connect';
        const until  = new Date();
        const since  = new Date(until.getTime() - 7 * 24 * 60 * 60 * 1000);
        const datapoints = await fetchHealthData(source, since, until);
        if (datapoints.length > 0) {
          await postHealthSync({ source, data_range_start: since.toISOString(), data_range_end: until.toISOString(), datapoints });
        }
        await registerHealthSyncTask();
      }
    } catch {
      // Best-effort — consent or sync failure doesn't block onboarding.
    } finally {
      setLoading(false);
      await finish();
    }
  };

  const handleSkip = async () => { await finish(); };

  const platformLabel = Platform.OS === 'ios' ? 'Apple Health' : 'Health Connect';
  const isWeb         = Platform.OS === 'web';

  const btnScale = useSharedValue(1);
  const btnAnim  = useAnimatedStyle(() => ({ transform: [{ scale: btnScale.value }] }));

  const bg      = isDark ? colors.forestInk     : colors.ivory;
  const textPri = isDark ? colors.ivoryText        : colors.ink;
  const textSub = isDark ? colors.stoneDim    : colors.stone;
  const cardBg  = isDark ? colors.forestSurface : colors.white;
  const cardBdr = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)';

  return (
    <View style={[styles.container, { backgroundColor: bg }]}>
      <View style={styles.content}>

        {/* Step progress */}
        <View style={styles.stepRow}>
          <View style={styles.progressTrack}>
            <View style={[styles.progressFill, { width: `${(STEP / TOTAL_STEPS) * 100}%` as never }]} />
          </View>
          <Text style={[styles.stepLabel, { color: textSub }]}>Step {STEP} of {TOTAL_STEPS}</Text>
        </View>

        {/* Header */}
        <View style={styles.header}>
          <Text style={[styles.title, { color: textPri }]}>
            {isWeb ? 'Health data sync' : `Connect ${platformLabel}`}
          </Text>
          <Text style={[styles.subtitle, { color: textSub }]}>
            {isWeb
              ? 'Health data sync is available on the mobile app.'
              : `Kyros can read health data from ${platformLabel} to give your doctor a richer picture between consultations.`}
          </Text>
        </View>

        {/* Data points card */}
        {!isWeb && (
          <View style={[styles.dataCard, { backgroundColor: cardBg, borderColor: cardBdr }]}>
            <Text style={[styles.dataCardTitle, { color: textPri }]}>What we read</Text>
            {DATA_POINTS.map(({ icon, label }) => (
              <View key={label} style={styles.dataRow}>
                <View style={[styles.dataIconWrap, { backgroundColor: isDark ? colors.forestSurfaceRaised : colors.ivory }]}>
                  <Text style={styles.dataIcon}>{icon}</Text>
                </View>
                <Text style={[styles.dataLabel, { color: textPri }]}>{label}</Text>
              </View>
            ))}
            <Text style={[styles.dataNote, { color: textSub }]}>
              We never write to {platformLabel}. Revoke access any time in Profile → My consents.
            </Text>
          </View>
        )}
      </View>

      {/* Footer */}
      <View style={styles.footer}>
        {!isWeb && (
          <Animated.View style={btnAnim}>
            <Pressable
              style={[styles.button, loading && styles.buttonMuted]}
              onPress={handleAllow}
              onPressIn={() => { btnScale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
              onPressOut={() => { btnScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
              disabled={loading}
              accessibilityLabel={`Allow ${platformLabel} access`}
            >
              {loading ? (
                <ActivityIndicator color={colors.white} size="small" />
              ) : (
                <Text style={styles.buttonText}>Allow access</Text>
              )}
            </Pressable>
          </Animated.View>
        )}

        <Pressable
          style={styles.skipBtn}
          onPress={handleSkip}
          disabled={loading}
          accessibilityLabel="Skip health sync"
        >
          <Text style={[styles.skipText, { color: textSub }]}>
            {isWeb ? 'Continue' : 'Skip for now'}
          </Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
    paddingBottom: spacing[8],
    justifyContent: 'space-between',
  },
  content: { gap: spacing[6] },

  stepRow: { gap: spacing[2] },
  progressTrack: { height: 4, backgroundColor: colors.borderLight, borderRadius: 2, overflow: 'hidden' },
  progressFill: { height: 4, backgroundColor: colors.jade, borderRadius: 2 },
  stepLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },

  header: { gap: spacing[2] },
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

  dataCard: {
    borderRadius: borderRadius.xxl,
    padding: spacing[5],
    gap: spacing[3],
    borderWidth: 1,
    boxShadow: '0 6px 14px rgba(0,0,0,0.07)',
  },
  dataCardTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    fontWeight: '700',
    marginBottom: spacing[1],
  },
  dataRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[3] },
  dataIconWrap: {
    width: 36,
    height: 36,
    borderRadius: borderRadius.lg,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  dataIcon:  { fontSize: 18 },
  dataLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '500',
  },
  dataNote: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    lineHeight: 18,
    marginTop: spacing[1],
  },

  footer: { gap: spacing[3] },
  button: {
    height: 56,
    backgroundColor: colors.forest,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: `0 8px 16px ${withAlpha(colors.forest, 0.25)}`,
  },
  buttonMuted: { opacity: 0.70 },
  buttonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.ivoryText,
    fontWeight: '600',
  },
  skipBtn: { height: 48, alignItems: 'center', justifyContent: 'center' },
  skipText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
  },
});
