import { apiFetch } from './client';

export interface PatientNote {
  id: string;
  body: string;
  created_at: string;
  updated_at: string;
}

export interface PatientNotesListResponse {
  items: PatientNote[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export function listPatientNotesApi(page = 1, pageSize = 20): Promise<PatientNotesListResponse> {
  return apiFetch(`/v1/clinic/patient/notes?page=${page}&page_size=${pageSize}`);
}

export function createPatientNoteApi(body: string): Promise<PatientNote> {
  return apiFetch('/v1/clinic/patient/notes', { method: 'POST', body: JSON.stringify({ body }) });
}

export function updatePatientNoteApi(id: string, body: string): Promise<PatientNote> {
  return apiFetch(`/v1/clinic/patient/notes/${id}`, { method: 'PATCH', body: JSON.stringify({ body }) });
}

export function deletePatientNoteApi(id: string): Promise<void> {
  return apiFetch(`/v1/clinic/patient/notes/${id}`, { method: 'DELETE' });
}
