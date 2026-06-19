/**
 * Care Plans API client (patient-facing).
 */

import { apiFetch } from './client';

// ── Types ─────────────────────────────────────────────────────────────────────

export type CarePlanStatus = 'active' | 'completed';

export interface CarePlanItem {
  id: string;
  category: string;
  title: string;
  description: string | null;
  frequency: string | null;
  duration: string | null;
  priority: string;
  order_index: number;
}

export interface CarePlan {
  id: string;
  consultation_id: string;
  title: string;
  status: CarePlanStatus;
  condition_category: string | null;
  goals: string | null;
  notes: string | null;
  valid_from: string | null;
  valid_until: string | null;
  activated_at: string | null;
  completed_at: string | null;
  version: number;
  items: CarePlanItem[];
}

export interface CarePlanListResponse {
  items: CarePlan[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function listCarePlans(
  page = 1,
  pageSize = 20,
): Promise<CarePlanListResponse> {
  return apiFetch<CarePlanListResponse>(
    `/v1/clinic/patient/care-plans?page=${page}&page_size=${pageSize}`,
  );
}

export async function getCarePlan(id: string): Promise<CarePlan> {
  return apiFetch<CarePlan>(`/v1/clinic/patient/care-plans/${id}`);
}
