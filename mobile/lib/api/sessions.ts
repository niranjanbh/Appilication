/**
 * Device session management API client (patient-facing).
 */

import { apiFetch } from './client';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Session {
  session_id: string;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
  last_used_at: string;
  expires_at: string;
  is_current: boolean;
}

export interface SessionListResponse {
  items: Session[];
}

export interface SessionRevokeResponse {
  revoked: number;
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function listSessions(): Promise<SessionListResponse> {
  return apiFetch<SessionListResponse>('/v1/users/me/sessions');
}

export async function revokeSession(sessionId: string): Promise<SessionRevokeResponse> {
  return apiFetch<SessionRevokeResponse>(`/v1/users/me/sessions/${sessionId}`, {
    method: 'DELETE',
  });
}
