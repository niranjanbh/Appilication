/**
 * Lab report API functions.
 *
 * Upload flow:
 *   1. initiateUpload      → get presigned POST URL + fields
 *   2. uploadToS3          → PUT file bytes directly to S3 (no backend proxy)
 *   3. finalizeUpload      → HEAD-verify + dispatch OCR task
 *
 * Subsequent calls:
 *   listLabReports, getLabReport, correctLabReport, getDownloadUrl
 */

import { apiFetch } from './client';

// ── Types ─────────────────────────────────────────────────────────────────────

export type LabReportStatus =
  | 'upload_pending'
  | 'ocr_pending'
  | 'ocr_processing'
  | 'ocr_complete'
  | 'ocr_failed'
  | 'patient_review_needed';

export interface Biomarker {
  name: string;
  value: string;
  unit: string;
  ref_low: string | null;
  ref_high: string | null;
  flag: 'normal' | 'high' | 'low' | null;
  confidence: number;
  needs_patient_correction?: boolean;
}

export interface ParsedLabReport {
  lab_name: string | null;
  report_date: string | null;
  patient_info: { name_on_report: string | null; age: number | null; gender: string | null } | null;
  biomarkers: Biomarker[];
  overall_confidence: number;
}

export interface LabReport {
  id: string;
  patient_id: string;
  source: 'patient_upload' | 'kyros_order';
  lab_name: string | null;
  report_date: string | null;
  original_filename: string;
  content_type: string;
  file_size_bytes: number;
  status: LabReportStatus;
  ocr_confidence_avg: number | null;
  low_confidence_fields: string[] | null;
  patient_corrected: boolean;
  parsed_json: ParsedLabReport | null;
  created_at: string;
  updated_at: string;
}

export interface InitiateUploadResponse {
  lab_report_id: string;
  upload_url: string;
  fields: Record<string, string>;
  s3_key: string;
  content_type: string;
}

export interface FinalizeUploadResponse {
  lab_report_id: string;
  status: LabReportStatus;
  ocr_task_id: string | null;
}

export interface LabReportListResponse {
  items: LabReport[];
  total: number;
  page: number;
  page_size: number;
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function initiateUpload(params: {
  original_filename: string;
  content_type: string;
  file_size_bytes: number;
}): Promise<InitiateUploadResponse> {
  return apiFetch<InitiateUploadResponse>('/v1/clinic/patient/lab-reports/initiate-upload', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

/**
 * Upload the file directly to S3 using the presigned POST fields.
 * Returns true on success, throws on failure.
 */
export async function uploadToS3(params: {
  upload_url: string;
  fields: Record<string, string>;
  file_uri: string;
  content_type: string;
  filename: string;
}): Promise<void> {
  const formData = new FormData();
  // S3 presigned POST: all fields must come before the file
  Object.entries(params.fields).forEach(([key, value]) => {
    formData.append(key, value);
  });
  // React Native FormData accepts { uri, type, name } as a file blob
  formData.append('file', {
    uri: params.file_uri,
    type: params.content_type,
    name: params.filename,
  } as unknown as Blob);

  const resp = await fetch(params.upload_url, {
    method: 'POST',
    body: formData,
  });
  if (!resp.ok) {
    throw new Error(`S3 upload failed: ${resp.status}`);
  }
}

export async function finalizeUpload(labReportId: string): Promise<FinalizeUploadResponse> {
  return apiFetch<FinalizeUploadResponse>(
    `/v1/clinic/patient/lab-reports/${labReportId}/finalize`,
    { method: 'POST' },
  );
}

export async function listLabReports(page = 1, pageSize = 20): Promise<LabReportListResponse> {
  return apiFetch<LabReportListResponse>(
    `/v1/clinic/patient/lab-reports?page=${page}&page_size=${pageSize}`,
  );
}

export async function getLabReport(id: string): Promise<LabReport> {
  return apiFetch<LabReport>(`/v1/clinic/patient/lab-reports/${id}`);
}

export async function correctLabReport(
  id: string,
  parsed_json: ParsedLabReport,
): Promise<LabReport> {
  return apiFetch<LabReport>(`/v1/clinic/patient/lab-reports/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ parsed_json }),
  });
}

export async function getDownloadUrl(id: string): Promise<{ download_url: string }> {
  return apiFetch<{ download_url: string }>(`/v1/clinic/patient/lab-reports/${id}/download`);
}
