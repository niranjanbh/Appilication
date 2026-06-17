// ── Patient health notes ────────────────────────────────────────────────────

export interface PatientNote {
  id: string;
  body: string;
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}

export interface PatientNoteCreate {
  body: string;
}

export interface PatientNoteUpdate {
  body: string;
}

export interface PatientNoteListResponse {
  items: PatientNote[];
  total: number;
  page: number;
  page_size: number;
}
