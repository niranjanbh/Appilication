const SITEVERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify';

/**
 * Verifies a Cloudflare Turnstile token server-side. Returns true when no
 * secret is configured (local dev without Turnstile set up) so the proxy
 * keeps working; production deploys must set TURNSTILE_SECRET_KEY.
 */
export async function verifyTurnstileToken(token: unknown, remoteIp?: string | null): Promise<boolean> {
  const secret = process.env.TURNSTILE_SECRET_KEY;
  if (!secret) return true;
  if (typeof token !== 'string' || token.length === 0) return false;

  const body = new URLSearchParams({ secret, response: token });
  if (remoteIp) body.append('remoteip', remoteIp);

  try {
    const resp = await fetch(SITEVERIFY_URL, { method: 'POST', body });
    const outcome: unknown = await resp.json();
    return (outcome as { success?: boolean }).success === true;
  } catch {
    return false;
  }
}
