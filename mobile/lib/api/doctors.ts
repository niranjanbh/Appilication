import { apiFetch } from './client';

export interface AvailableDoctor {
  id: string;
  name: string;
  specialty: string[];
  conditions_treated: string[];
  consultation_languages: string[];
  bio_short: string | null;
  photo_url: string | null;
  consultation_duration_minutes_default: number;
  verified_at: string | null;
}

export interface AvailableDoctorListResponse {
  items: AvailableDoctor[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export function listAvailableDoctorsApi(
  conditionCategory?: string,
  page = 1,
  pageSize = 20,
): Promise<AvailableDoctorListResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (conditionCategory) params.set('condition_category', conditionCategory);
  return apiFetch(`/v1/clinic/patient/doctors/available?${params}`);
}
