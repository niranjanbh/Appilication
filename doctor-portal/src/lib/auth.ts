const API_BASE = (import.meta.env['VITE_API_BASE_URL'] ?? 'http://localhost:8000').replace(/\/$/, '');

const TOKEN_KEY = 'kyros_dr_access';
const REFRESH_KEY = 'kyros_dr_refresh';

export interface LoginResult {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export async function login(emailOrPhone: string, password: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email_or_phone: emailOrPhone, password }),
  });

  if (!resp.ok) {
    const body = await resp.json().catch(() => ({})) as Record<string, unknown>;
    throw new Error((body['detail'] as string | undefined) ?? 'Login failed');
  }

  const data = await resp.json() as LoginResult;

  // Decode role from JWT payload (base64 middle segment)
  const payload = JSON.parse(atob(data.access_token.split('.')[1]!)) as Record<string, unknown>;
  if (payload['role'] !== 'doctor') {
    throw new Error('doctor_role_required');
  }

  localStorage.setItem(TOKEN_KEY, data.access_token);
  localStorage.setItem(REFRESH_KEY, data.refresh_token);
}

export async function requestPasswordReset(identifier: string): Promise<void> {
  // Response is deliberately generic (no account enumeration); we ignore the body.
  await fetch(`${API_BASE}/v1/auth/password-reset/request`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ identifier }),
  });
}

export async function confirmPasswordReset(
  identifier: string,
  otp: string,
  newPassword: string,
): Promise<void> {
  const resp = await fetch(`${API_BASE}/v1/auth/password-reset/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ identifier, otp, new_password: newPassword }),
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({})) as Record<string, unknown>;
    throw new Error((body['detail'] as string | undefined) ?? 'reset_failed');
  }
}

export function logout(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  const token = getToken();
  if (!token) return false;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]!)) as Record<string, unknown>;
    const exp = payload['exp'] as number | undefined;
    if (exp && Date.now() / 1000 > exp) {
      logout();
      return false;
    }
    return payload['role'] === 'doctor';
  } catch {
    return false;
  }
}
