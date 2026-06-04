/**
 * Fetch the last N days of health data from HealthKit (iOS) or Health Connect (Android).
 *
 * Requires a custom dev client built with:
 *   @kingstinct/react-native-healthkit  (iOS)
 *   react-native-health-connect         (Android)
 *
 * Returns an empty array on web or when the native module is unavailable (Expo Go).
 */
import { Platform } from 'react-native';

import type { HealthDatapointItem, HealthSyncSource } from '../../types/wellness';

// ── iOS HealthKit ──────────────────────────────────────────────────────────────

async function fetchFromHealthKit(since: Date, until: Date): Promise<HealthDatapointItem[]> {
  const datapoints: HealthDatapointItem[] = [];
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const HK = require('@kingstinct/react-native-healthkit');

    const options = { from: since, to: until, limit: 1000, ascending: false };

    // Steps (daily aggregated samples from HealthKit)
    const steps = await HK.queryQuantitySamples('HKQuantityTypeIdentifierStepCount', options);
    for (const s of steps) {
      datapoints.push({
        type: 'steps',
        source_record_id: `hk-${s.uuid}`,
        measured_at: new Date(s.startDate).toISOString(),
        value: { count: Math.round(s.quantity) },
      });
    }

    // Heart rate
    const hr = await HK.queryQuantitySamples('HKQuantityTypeIdentifierHeartRate', options);
    for (const s of hr) {
      datapoints.push({
        type: 'heart_rate',
        source_record_id: `hk-${s.uuid}`,
        measured_at: new Date(s.startDate).toISOString(),
        value: { bpm: Math.round(s.quantity) },
      });
    }

    // Resting heart rate
    const rhr = await HK.queryQuantitySamples('HKQuantityTypeIdentifierRestingHeartRate', options);
    for (const s of rhr) {
      datapoints.push({
        type: 'resting_heart_rate',
        source_record_id: `hk-${s.uuid}`,
        measured_at: new Date(s.startDate).toISOString(),
        value: { bpm: Math.round(s.quantity) },
      });
    }

    // HRV (SDNN in ms)
    const hrv = await HK.queryQuantitySamples(
      'HKQuantityTypeIdentifierHeartRateVariabilitySDNN',
      options,
    );
    for (const s of hrv) {
      datapoints.push({
        type: 'hrv',
        source_record_id: `hk-${s.uuid}`,
        measured_at: new Date(s.startDate).toISOString(),
        value: { ms: parseFloat(s.quantity.toFixed(2)) },
      });
    }

    // Weight (kg)
    const weight = await HK.queryQuantitySamples('HKQuantityTypeIdentifierBodyMass', options);
    for (const s of weight) {
      datapoints.push({
        type: 'weight',
        source_record_id: `hk-${s.uuid}`,
        measured_at: new Date(s.startDate).toISOString(),
        value: { kg: parseFloat(s.quantity.toFixed(2)) },
      });
    }

    // Blood glucose (mmol/L)
    const glucose = await HK.queryQuantitySamples(
      'HKQuantityTypeIdentifierBloodGlucose',
      options,
    );
    for (const s of glucose) {
      datapoints.push({
        type: 'blood_glucose',
        source_record_id: `hk-${s.uuid}`,
        measured_at: new Date(s.startDate).toISOString(),
        value: { mmol_l: parseFloat(s.quantity.toFixed(2)) },
      });
    }
  } catch {
    // Native module unavailable (Expo Go or missing prebuild)
  }
  return datapoints;
}

// ── Android Health Connect ─────────────────────────────────────────────────────

async function fetchFromHealthConnect(since: Date, until: Date): Promise<HealthDatapointItem[]> {
  const datapoints: HealthDatapointItem[] = [];
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const HC = require('react-native-health-connect');
    const timeRange = {
      operator: 'between' as const,
      startTime: since.toISOString(),
      endTime: until.toISOString(),
    };

    const steps = await HC.readRecords('Steps', { timeRangeFilter: timeRange });
    for (const r of steps.records ?? []) {
      datapoints.push({
        type: 'steps',
        source_record_id: `hc-${r.metadata?.id ?? r.startTime}`,
        measured_at: r.startTime,
        value: { count: r.count },
      });
    }

    const hr = await HC.readRecords('HeartRate', { timeRangeFilter: timeRange });
    for (const r of hr.records ?? []) {
      for (const sample of r.samples ?? []) {
        datapoints.push({
          type: 'heart_rate',
          source_record_id: `hc-${r.metadata?.id ?? r.startTime}-${sample.time}`,
          measured_at: sample.time,
          value: { bpm: sample.beatsPerMinute },
        });
      }
    }

    const rhr = await HC.readRecords('RestingHeartRate', { timeRangeFilter: timeRange });
    for (const r of rhr.records ?? []) {
      datapoints.push({
        type: 'resting_heart_rate',
        source_record_id: `hc-${r.metadata?.id ?? r.time}`,
        measured_at: r.time,
        value: { bpm: r.beatsPerMinute },
      });
    }

    const hrv = await HC.readRecords('HeartRateVariabilityRmssd', { timeRangeFilter: timeRange });
    for (const r of hrv.records ?? []) {
      datapoints.push({
        type: 'hrv',
        source_record_id: `hc-${r.metadata?.id ?? r.time}`,
        measured_at: r.time,
        value: { ms: parseFloat(r.heartRateVariabilityMillis.toFixed(2)) },
      });
    }

    const weight = await HC.readRecords('Weight', { timeRangeFilter: timeRange });
    for (const r of weight.records ?? []) {
      datapoints.push({
        type: 'weight',
        source_record_id: `hc-${r.metadata?.id ?? r.time}`,
        measured_at: r.time,
        value: { kg: parseFloat(r.weight.inKilograms.toFixed(2)) },
      });
    }

    const glucose = await HC.readRecords('BloodGlucose', { timeRangeFilter: timeRange });
    for (const r of glucose.records ?? []) {
      datapoints.push({
        type: 'blood_glucose',
        source_record_id: `hc-${r.metadata?.id ?? r.time}`,
        measured_at: r.time,
        value: { mmol_l: parseFloat(r.level.inMillimolesPerLiter.toFixed(2)) },
      });
    }
  } catch {
    // Native module unavailable
  }
  return datapoints;
}

// ── Public API ─────────────────────────────────────────────────────────────────

export async function fetchHealthData(
  source: HealthSyncSource,
  since: Date,
  until: Date,
): Promise<HealthDatapointItem[]> {
  if (Platform.OS === 'web') return [];

  if (source === 'apple_health' && Platform.OS === 'ios') {
    return fetchFromHealthKit(since, until);
  }
  if (source === 'google_health_connect' && Platform.OS === 'android') {
    return fetchFromHealthConnect(since, until);
  }
  return [];
}
