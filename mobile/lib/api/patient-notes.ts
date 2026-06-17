import type {
  PatientNote,
  PatientNoteCreate,
  PatientNoteListResponse,
  PatientNoteUpdate,
} from '../../types/clinic';
import { apiFetch } from './client';

export function listPatientNotesApi(page = 1, pageSize = 20): Promise<PatientNoteListResponse> {
  return apiFetch(`/v1/clinic/patient/notes?page=${page}&page_size=${pageSize}`);
}

export function createPatientNoteApi(payload: PatientNoteCreate): Promise<PatientNote> {
  return apiFetch('/v1/clinic/patient/notes', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updatePatientNoteApi(id: string, payload: PatientNoteUpdate): Promise<PatientNote> {
  return apiFetch(`/v1/clinic/patient/notes/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function deletePatientNoteApi(id: string): Promise<void> {
  return apiFetch(`/v1/clinic/patient/notes/${id}`, { method: 'DELETE' });
}
