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

export type ReminderSourceType = 'manual' | 'prescription';

export interface Reminder {
  id: string;
  type: ReminderType;
  label: string;
  schedule_cron: string | null;
  schedule_interval_minutes: number | null;
  active: boolean;
  notification_channels: string[];
  // Provenance: 'prescription' reminders are doctor-prescribed and immutable to
  // the patient; 'manual' reminders are patient-created and fully editable.
  source_type: ReminderSourceType;
  generated_by: string;
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
  // Reminder ids already resolved (taken or skipped) today. Used to suppress
  // overdue reminders the user has already handled from the "Next Up" card.
  resolved_reminder_ids: string[];
  // Subset of resolved that were taken (not just skipped) — used to mark a
  // reminder row as done vs merely dismissed.
  completed_reminder_ids: string[];
}

export interface WeekDaySummary {
  date: string;
  total: number;
  completed: number;
}

export interface WeekSummaryResponse {
  days: WeekDaySummary[];
}

export interface AdherenceSummary {
  adherence_rate_30d: number;
  current_streak: number;
  longest_streak: number;
  last_missed_at: string | null;
  active_prescription_reminders: number;
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
