/**
 * Payments & refunds API client (patient-facing).
 */

import { apiFetch } from './client';

// ── Types ─────────────────────────────────────────────────────────────────────

export type RefundStatus = 'pending' | 'processed' | 'failed';

export interface Refund {
  id: string;
  payment_id: string;
  razorpay_refund_id: string | null;
  amount_paise: number;
  currency: string;
  status: RefundStatus;
  reason: string | null;
  created_at: string;
}

export interface RefundListResponse {
  items: Refund[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function listRefunds(page = 1, pageSize = 20): Promise<RefundListResponse> {
  return apiFetch<RefundListResponse>(
    `/v1/payments/refunds?page=${page}&page_size=${pageSize}`,
  );
}

export async function getRefund(id: string): Promise<Refund> {
  return apiFetch<Refund>(`/v1/payments/refunds/${id}`);
}
