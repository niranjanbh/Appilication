/**
 * Payments & refunds API client (patient-facing).
 */

import { apiFetch } from './client';

// ── Types ─────────────────────────────────────────────────────────────────────

export type PaymentStatus =
  | 'created' | 'authorized' | 'captured' | 'failed' | 'refunded';

/** Mirrors backend PaymentRead (app/api/v1/payments/schemas.py). */
export interface Payment {
  id: string;
  user_id: string;
  consultation_id: string | null;
  razorpay_order_id: string;
  razorpay_payment_id: string | null;
  amount_paise: number;
  currency: string;
  status: PaymentStatus;
  gst_invoice_number: string | null;
  gst_invoice_url: string | null;
}

/** The Razorpay handshake fields returned by checkout on a successful payment. */
export interface RazorpayCheckoutResult {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

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

/**
 * Create a standalone Razorpay order for a consultation.
 *
 * Note: the consultation booking flow already returns an embedded order
 * (`consultation.payment`), so this is only needed when paying for a
 * consultation that does not yet have an order attached. The backend
 * `CreateOrderRequest` requires the amount in paise.
 */
export async function createPaymentOrder(
  consultationId: string,
  amountPaise: number,
  currency = 'INR',
): Promise<Payment> {
  return apiFetch<Payment>('/v1/payments/order', {
    method: 'POST',
    body: JSON.stringify({
      consultation_id: consultationId,
      amount_paise: amountPaise,
      currency,
    }),
  });
}

/**
 * Verify a Razorpay payment after checkout. The backend recomputes the
 * HMAC signature server-side; a tampered signature is rejected.
 */
export async function verifyPayment(data: {
  payment_id: string;
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}): Promise<Payment> {
  return apiFetch<Payment>('/v1/payments/verify', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/** Fetch a single payment's details (cross-user access returns 404). */
export async function getPayment(paymentId: string): Promise<Payment> {
  return apiFetch<Payment>(`/v1/payments/${paymentId}`);
}

/**
 * Confirm a consultation after a successful Razorpay payment. The backend
 * verifies the signature and transitions the consultation to `confirmed`.
 */
export async function confirmConsultationPayment(
  consultationId: string,
  result: RazorpayCheckoutResult,
): Promise<unknown> {
  return apiFetch(
    `/v1/clinic/patient/consultations/${consultationId}/confirm-payment`,
    {
      method: 'POST',
      body: JSON.stringify({
        razorpay_order_id: result.razorpay_order_id,
        razorpay_payment_id: result.razorpay_payment_id,
        razorpay_signature: result.razorpay_signature,
      }),
    },
  );
}

export async function listRefunds(page = 1, pageSize = 20): Promise<RefundListResponse> {
  return apiFetch<RefundListResponse>(
    `/v1/payments/refunds?page=${page}&page_size=${pageSize}`,
  );
}

export async function getRefund(id: string): Promise<Refund> {
  return apiFetch<Refund>(`/v1/payments/refunds/${id}`);
}
