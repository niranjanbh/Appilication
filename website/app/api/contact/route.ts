import { NextRequest, NextResponse } from 'next/server';
import { verifyTurnstileToken } from '../../../lib/turnstileVerify';

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const { turnstileToken, ...body } = (await request.json()) as Record<string, unknown>;

    const verified = await verifyTurnstileToken(turnstileToken, request.headers.get('cf-connecting-ip'));
    if (!verified) {
      return NextResponse.json({ detail: 'We could not verify your request. Please try again.' }, { status: 403 });
    }

    const resp = await fetch(`${BACKEND_URL}/v1/public/lead`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data: unknown = await resp.json().catch(() => ({ ok: true }));
    return NextResponse.json(data, { status: resp.ok ? 200 : resp.status });
  } catch {
    return NextResponse.json(
      { detail: 'Could not reach the server. Please email us directly at hello@kyrosclinic.com' },
      { status: 503 }
    );
  }
}
