import { useRouter } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { captureConsentApi } from '../../lib/api/consent';
import { postHealthSync } from '../../lib/api/health-sync';
import { useAuth } from '../../lib/auth/context';
import { colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';
import { fetchHealthData } from '../../lib/native/health-data';
import { requestHealthPermissions } from '../../lib/native/health';
import { registerHealthSyncTask } from '../../lib/native/background-sync';

const HEALTH_SYNC_TEXT =
  'I consent to Kyros reading health data (steps, heart rate, sleep duration, weight, ' +
  'blood pressure, blood glucose) from Apple Health or Health Connect to support my care plan. ' +
  'I can revoke this permission at any time from Profile → My consents.';

const DATA_POINTS = [
  'Steps and activity',
  'Heart rate and HRV',
  'Sleep duration',
  'Weight and body composition',
  'Blood pressure and glucose',
];

export default function HealthSyncScreen() {
  const router = useRouter();
  const { markOnboardingComplete } = useAuth();
  const [loading, setLoading] = useState(false);

  const finish = async () => {
    // ABHA linking is next (optional) — it owns the markOnboardingComplete call.
    router.push('/(onboarding)/abha-link');
  };

  const handleAllow = async () => {
    setLoading(true);
    try {
      const result = await requestHealthPermissions();
      if (result.granted) {
        await captureConsentApi({
          consent_type: 'health_sync',
          version: '1.0',
          granted: true,
          consent_text: HEALTH_SYNC_TEXT,
        });

        // Seed the first sync immediately so the doctor has data on day one.
        const source = Platform.OS === 'ios' ? 'apple_health' : 'google_health_connect';
        const until = new Date();
        const since = new Date(until.getTime() - 7 * 24 * 60 * 60 * 1000);
        const datapoints = await fetchHealthData(source, since, until);
        if (datapoints.length > 0) {
          await postHealthSync({
            source,
            data_range_start: since.toISOString(),
            data_range_end: until.toISOString(),
            datapoints,
          });
        }

        // Arm the recurring 4-hour background sync.
        await registerHealthSyncTask();
      }
    } catch {
      // Best-effort — consent or sync failure doesn't block onboarding.
    } finally {
      setLoading(false);
      await finish();
    }
  };

  const handleSkip = async () => {
    await finish();
  };

  const platformLabel = Platform.OS === 'ios' ? 'Apple Health' : 'Health Connect';
  const isWeb = Platform.OS === 'web';

  return (
    <View style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.step}>Step 4 of 5</Text>
        <Text style={styles.title}>
          {isWeb ? 'Health data sync' : `Connect ${platformLabel}`}
        </Text>
        <Text style={styles.subtitle}>
          {isWeb
            ? 'Health data sync is available on the mobile app.'
            : `Kyros can read health data from ${platformLabel} to give your doctor a richer picture between consultations.`}
        </Text>

        {!isWeb && (
          <View style={styles.dataPoints}>
            <Text style={styles.dataPointsLabel}>What we read:</Text>
            {DATA_POINTS.map(point => (
              <View key={point} style={styles.dataPoint}>
                <Text style={styles.dataPointBullet}>·</Text>
                <Text style={styles.dataPointText}>{point}</Text>
              </View>
            ))}
            <Text style={styles.dataNote}>
              We never write to {platformLabel}. Revoke access any time in Profile → My consents.
            </Text>
          </View>
        )}
      </View>

      <View style={styles.footer}>
        {!isWeb && (
          <Pressable
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleAllow}
            disabled={loading}
            accessibilityLabel={`Allow ${platformLabel} access`}
          >
            {loading ? (
              <ActivityIndicator color={colors.ivory} />
            ) : (
              <Text style={styles.buttonText}>Allow access</Text>
            )}
          </Pressable>
        )}

        <Pressable
          style={styles.skipButton}
          onPress={handleSkip}
          disabled={loading}
          accessibilityLabel="Skip health sync"
        >
          <Text style={styles.skipText}>
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
    backgroundColor: colors.ivory,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[12],
    paddingBottom: spacing[8],
    justifyContent: 'space-between',
  },
  content: { gap: spacing[6] },
  step: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    fontWeight: '500',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  title: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    color: colors.forest,
    fontWeight: '500',
  },
  subtitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    lineHeight: 22,
  },
  dataPoints: {
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: spacing[4],
    gap: spacing[2],
  },
  dataPointsLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    fontWeight: '600',
    marginBottom: spacing[2],
  },
  dataPoint: { flexDirection: 'row', gap: spacing[2] },
  dataPointBullet: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.forest,
    fontWeight: '700',
  },
  dataPointText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
  },
  dataNote: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    marginTop: spacing[2],
    lineHeight: 18,
  },
  footer: { gap: spacing[3] },
  button: {
    backgroundColor: colors.forest,
    borderRadius: 8,
    paddingVertical: spacing[4],
    alignItems: 'center',
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.ivory,
    fontWeight: '600',
  },
  skipButton: {
    paddingVertical: spacing[3],
    alignItems: 'center',
  },
  skipText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
  },
});
