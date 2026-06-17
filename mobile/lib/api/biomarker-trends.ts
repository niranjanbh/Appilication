/**
 * Biomarker trend API client.
 *
 * GET /v1/clinic/patient/biomarker-trends/{biomarker}?range=7d|30d|90d|1y|all
 */

import { apiFetch } from './client';

// ── Types ─────────────────────────────────────────────────────────────────────

export type BiomarkerRange = '7d' | '30d' | '90d' | '1y' | 'all';

export type TrendDirection = 'better' | 'steady' | 'worse';

export interface BiomarkerDataPoint {
  report_id: string;
  report_date: string | null;
  value: number;
  unit: string;
  ref_low: number | null;
  ref_high: number | null;
  flag: 'normal' | 'high' | 'low' | null;
  lab_name: string | null;
  consultation_id: string | null;
}

export interface BiomarkerTrendResponse {
  biomarker_name: string;
  unit: string;
  data_points: BiomarkerDataPoint[];
  ref_low: number | null;
  ref_high: number | null;
  trend: TrendDirection;
}

// ── API call ──────────────────────────────────────────────────────────────────

export interface BiomarkerSummary {
  name: string;
  latest_value: number | null;
  unit: string;
  ref_low: number | null;
  ref_high: number | null;
  flag: 'normal' | 'high' | 'low' | null;
  report_date: string | null;
}

export interface BiomarkerListResponse {
  biomarkers: BiomarkerSummary[];
}

export async function listBiomarkers(): Promise<BiomarkerListResponse> {
  return apiFetch<BiomarkerListResponse>('/v1/clinic/patient/biomarkers');
}

export async function getBiomarkerTrend(
  biomarkerName: string,
  range: BiomarkerRange = 'all',
): Promise<BiomarkerTrendResponse> {
  const encoded = encodeURIComponent(biomarkerName);
  return apiFetch<BiomarkerTrendResponse>(
    `/v1/clinic/patient/biomarker-trends/${encoded}?range=${range}`,
  );
}
