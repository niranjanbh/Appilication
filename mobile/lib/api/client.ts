import { clearTokens, loadTokens, saveTokens } from '../auth/storage';

// Override by setting EXPO_PUBLIC_API_BASE_URL in your .env file.
// Expo substitutes EXPO_PUBLIC_* vars at bundle time.
declare const process: { env: Record<string, string | undefined> };
const API_BASE_URL = (process.env['EXPO_PUBLIC_API_BASE_URL'] ?? 'https://api.kyrosclinic.com').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: unknown,
  ) {
    super(`API error ${status}`);
  }
}

let _onUnauthenticated: (() => void) | null = null;

/** Register a callback that fires when a token refresh fails (log the user out). */
export function registerUnauthenticatedHandler(cb: () => void): void {
  _onUnauthenticated = cb;
}

async function refreshAccessToken(): Promise<string | null> {
  const { refreshToken } = await loadTokens();
  if (!refreshToken) return null;

  const resp = await fetch(`${API_BASE_URL}/v1/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!resp.ok) return null;

  const tokens = await resp.json();
  await saveTokens(tokens);
  return tokens.access_token as string;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  _retry = true,
): Promise<T> {
  const { accessToken } = await loadTokens();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  };
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }

  const resp = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  if (resp.status === 401 && _retry) {
    const newToken = await refreshAccessToken();
    if (!newToken) {
      await clearTokens();
      _onUnauthenticated?.();
      throw new ApiError(401, null);
    }
    return apiFetch<T>(path, options, false);
  }

  if (!resp.ok) {
    const body = await resp.json().catch(() => null);
    throw new ApiError(resp.status, body);
  }

  // 204 No Content
  if (resp.status === 204) return undefined as T;

  return resp.json() as Promise<T>;
}

/** Unauthenticated fetch for auth endpoints. */
export async function publicFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  };
  const resp = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (!resp.ok) {
    const body = await resp.json().catch(() => null);
    throw new ApiError(resp.status, body);
  }
  return resp.json() as Promise<T>;
}
