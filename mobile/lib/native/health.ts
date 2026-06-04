/**
 * Health data sync helpers wrapping HealthKit (iOS) and Health Connect (Android).
 *
 * Real native calls require a custom dev client built with:
 *   @kingstinct/react-native-healthkit  (iOS)
 *   react-native-health-connect         (Android)
 *
 * Until the custom dev client is in place, requestHealthPermissions() resolves with
 * granted=false so the onboarding skip path is taken silently.
 */
import { Platform } from 'react-native';

export type HealthPermissionResult =
  | { granted: true }
  | { granted: false; reason: 'unavailable' | 'denied' | 'unsupported_platform' };

export async function requestHealthPermissions(): Promise<HealthPermissionResult> {
  if (Platform.OS === 'web') {
    return { granted: false, reason: 'unsupported_platform' };
  }

  if (Platform.OS === 'ios') {
    try {
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const HealthKit = require('@kingstinct/react-native-healthkit');
      await HealthKit.requestAuthorization(
        [], // write types
        [   // read types
          'HKQuantityTypeIdentifierStepCount',
          'HKQuantityTypeIdentifierHeartRate',
          'HKQuantityTypeIdentifierRestingHeartRate',
          'HKQuantityTypeIdentifierHeartRateVariabilitySDNN',
          'HKCategoryTypeIdentifierSleepAnalysis',
          'HKQuantityTypeIdentifierBodyMass',
          'HKCorrelationTypeIdentifierBloodPressure',
          'HKQuantityTypeIdentifierBloodGlucose',
          'HKWorkoutType',
        ],
      );
      return { granted: true };
    } catch {
      // Module not installed (standard Expo Go / missing prebuild)
      return { granted: false, reason: 'unavailable' };
    }
  }

  if (Platform.OS === 'android') {
    try {
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const { initialize, requestPermission } = require('react-native-health-connect');
      await initialize();
      const granted = await requestPermission([
        { accessType: 'read', recordType: 'Steps' },
        { accessType: 'read', recordType: 'HeartRate' },
        { accessType: 'read', recordType: 'RestingHeartRate' },
        { accessType: 'read', recordType: 'HeartRateVariabilityRmssd' },
        { accessType: 'read', recordType: 'SleepSession' },
        { accessType: 'read', recordType: 'Weight' },
        { accessType: 'read', recordType: 'BloodPressure' },
        { accessType: 'read', recordType: 'BloodGlucose' },
        { accessType: 'read', recordType: 'ExerciseSession' },
      ]);
      const allGranted = granted.every((p: { granted: boolean }) => p.granted);
      return allGranted ? { granted: true } : { granted: false, reason: 'denied' };
    } catch {
      return { granted: false, reason: 'unavailable' };
    }
  }

  return { granted: false, reason: 'unsupported_platform' };
}
