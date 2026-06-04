import { getToken, logout } from './auth';

const API_BASE = (import.meta.env['VITE_API_BASE_URL'] ?? 'http://localhost:8000').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(detail);
  }
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string> | undefined),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const resp = await fetch(`${API_BASE}${path}`, { ...init, headers });

  if (resp.status === 401) {
    logout();
    window.location.href = '/login';
    throw new ApiError(401, 'Session expired');
  }

  if (!resp.ok) {
    const body = await resp.json().catch(() => ({})) as Record<string, unknown>;
    throw new ApiError(resp.status, (body['detail'] as string | undefined) ?? 'Request failed');
  }

  if (resp.status === 204) return undefined as unknown as T;
  return resp.json() as Promise<T>;
}
