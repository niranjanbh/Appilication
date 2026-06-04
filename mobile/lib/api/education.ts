import { apiFetch } from './client';

export interface EducationContent {
  id: string;
  title: string;
  slug: string;
  content_type: 'article' | 'video' | 'pdf';
  condition_categories: string[];
  content_url: string | null;
  body_md: string | null;
  ai_disclosure: boolean;
  reviewed_at: string | null;
}

export interface EducationAssignment {
  id: string;
  content_id: string;
  consultation_id: string | null;
  notes: string | null;
  read_at: string | null;
  created_at: string;
  content: EducationContent;
}

export interface PatientEducationResponse {
  assignments: EducationAssignment[];
  library: EducationContent[];
  library_total: number;
}

export interface ReadResponse {
  assignment_id: string;
  read_at: string;
}

export async function listPatientEducation(page = 1): Promise<PatientEducationResponse> {
  return apiFetch<PatientEducationResponse>(
    `/v1/clinic/patient/education?page=${page}&page_size=20`,
  );
}

export async function getEducationContent(contentId: string): Promise<EducationContent> {
  return apiFetch<EducationContent>(`/v1/clinic/patient/education/${contentId}`);
}

export async function markAssignmentRead(assignmentId: string): Promise<ReadResponse> {
  return apiFetch<ReadResponse>(`/v1/clinic/patient/education/${assignmentId}/read`, {
    method: 'POST',
  });
}
