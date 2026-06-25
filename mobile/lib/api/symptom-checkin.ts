import { apiFetch } from './client';

export type MoodLevel = 1 | 2 | 3 | 4 | 5;

export interface SymptomCheckIn {
  id: string;
  mood: MoodLevel;
  energy: MoodLevel;
  note: string | null;
  checked_in_at: string;
}

export interface SymptomCheckInCreate {
  mood: MoodLevel;
  energy: MoodLevel;
  note?: string | null;
}

export interface TodayCheckInResponse {
  checked_in: boolean;
  entry: SymptomCheckIn | null;
}

export function getTodayCheckIn(): Promise<TodayCheckInResponse> {
  return apiFetch('/v1/wellness/symptom-checkin/today');
}

export function submitCheckIn(payload: SymptomCheckInCreate): Promise<SymptomCheckIn> {
  return apiFetch('/v1/wellness/symptom-checkin', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
