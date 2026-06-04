import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const body: unknown = await request.json();
    const resp = await fetch(`${BACKEND_URL}/v1/public/booking-inquiry`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data: unknown = await resp.json();
    return NextResponse.json(data, { status: resp.status });
  } catch {
    return NextResponse.json(
      { detail: 'Could not reach the server. Please try again.' },
      { status: 503 }
    );
  }
}
