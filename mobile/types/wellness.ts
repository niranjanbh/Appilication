// ── Health sync ────────────────────────────────────────────────────────────────

export type HealthSyncSource = 'apple_health' | 'google_health_connect';

export type HealthDatapointType =
  | 'steps'
  | 'heart_rate'
  | 'resting_heart_rate'
  | 'hrv'
  | 'sleep_duration'
  | 'sleep_quality'
  | 'weight'
  | 'blood_pressure_systolic'
  | 'blood_pressure_diastolic'
  | 'blood_glucose'
  | 'workout'
  | 'active_calories';

export type HealthSyncStatus = 'success' | 'partial' | 'failed';

export interface HealthDatapointItem {
  type: HealthDatapointType;
  source_record_id: string;
  measured_at: string; // ISO 8601
  value: Record<string, unknown>;
}

export interface HealthSyncRequest {
  source: HealthSyncSource;
  data_range_start: string; // ISO 8601
  data_range_end: string; // ISO 8601
  datapoints: HealthDatapointItem[];
}

export interface HealthSyncResponse {
  session_id: string;
  inserted_count: number;
  skipped_count: number;
  status: HealthSyncStatus;
}

// ── Reminders ─────────────────────────────────────────────────────────────────

export type ReminderType = 'water' | 'supplement' | 'medication' | 'gym' | 'custom';
export type ReminderAction = 'taken' | 'skipped' | 'snoozed' | 'missed';
export type AdherenceAction = 'taken' | 'skipped' | 'snoozed';

export interface Reminder {
  id: string;
  type: ReminderType;
  label: string;
  schedule_cron: string | null;
  schedule_interval_minutes: number | null;
  active: boolean;
  notification_channels: string[];
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  adherence_rate: number;
}

export interface ReminderListResponse {
  reminders: Reminder[];
  total: number;
}

export interface ReminderCreate {
  type: ReminderType;
  label: string;
  schedule_cron?: string | null;
  schedule_interval_minutes?: number | null;
  notification_channels?: string[];
  metadata?: Record<string, unknown> | null;
}

export interface ReminderUpdate {
  label?: string;
  schedule_cron?: string | null;
  schedule_interval_minutes?: number | null;
  active?: boolean;
  notification_channels?: string[];
  metadata?: Record<string, unknown> | null;
}

export interface DailySummary {
  date: string;
  total: number;
  completed: number;
  streak: number;
}

export interface WeekDaySummary {
  date: string;
  total: number;
  completed: number;
}

export interface WeekSummaryResponse {
  days: WeekDaySummary[];
}

export interface AdherenceLogRequest {
  scheduled_at: string; // ISO 8601
  action: ReminderAction;
  notes?: string | null;
}

export interface AdherenceLogRead {
  id: string;
  reminder_id: string;
  scheduled_at: string;
  action: ReminderAction;
  action_at: string;
  notes: string | null;
  created_at: string;
}
