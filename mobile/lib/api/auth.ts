import type { AuthTokens, UserMe } from '../../types/auth';
import { apiFetch, publicFetch } from './client';

export interface SignupPayload {
  name: string;
  phone: string;
  email: string;
  password: string;
}

export interface SignupResult {
  message: string;
  phone: string;
  otp_hint?: string | null;
  otp_required: boolean;
  access_token?: string | null;
  token_type?: string;
  refresh_token?: string | null;
  expires_in?: number | null;
}

export interface VerifyOtpPayload {
  phone: string;
  otp: string;
}

export interface LoginPayload {
  email_or_phone: string;
  password: string;
}

export function signupApi(payload: SignupPayload): Promise<SignupResult> {
  return publicFetch('/v1/auth/signup', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function sendOtpApi(phone: string): Promise<{ message: string }> {
  return publicFetch('/v1/auth/send-otp', {
    method: 'POST',
    body: JSON.stringify({ phone }),
  });
}

export function verifyOtpApi(payload: VerifyOtpPayload): Promise<AuthTokens> {
  return publicFetch('/v1/auth/verify-otp', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function loginApi(payload: LoginPayload): Promise<AuthTokens> {
  return publicFetch('/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export interface PasswordResetRequestResult {
  message: string;
  otp_hint?: string | null;
}

export interface PasswordResetConfirmPayload {
  identifier: string;
  otp: string;
  new_password: string;
}

export interface AuthConfig {
  google_oauth_enabled: boolean;
  signup_otp_enabled: boolean;
}

export function requestPasswordResetApi(
  identifier: string,
): Promise<PasswordResetRequestResult> {
  return publicFetch('/v1/auth/password-reset/request', {
    method: 'POST',
    body: JSON.stringify({ identifier }),
  });
}

export function confirmPasswordResetApi(
  payload: PasswordResetConfirmPayload,
): Promise<{ message: string }> {
  return publicFetch('/v1/auth/password-reset/confirm', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function googleLoginApi(idToken: string): Promise<AuthTokens> {
  return publicFetch('/v1/auth/google', {
    method: 'POST',
    body: JSON.stringify({ id_token: idToken }),
  });
}

export function getAuthConfigApi(): Promise<AuthConfig> {
  return publicFetch('/v1/auth/config', { method: 'GET' });
}

export function getMeApi(): Promise<UserMe> {
  return apiFetch('/v1/users/me');
}

export interface PhoneCaptureResult {
  message: string;
  phone: string;
  // When signup OTP is admin-enabled the number must be confirmed via
  // confirmPhoneCaptureApi; when disabled it is stored verified immediately.
  otp_required: boolean;
  otp_hint?: string | null;
}

/** Attach a mobile number to the signed-in account (e.g. after Google sign-in). */
export function requestPhoneCaptureApi(phone: string): Promise<PhoneCaptureResult> {
  return apiFetch('/v1/auth/me/phone/request', {
    method: 'POST',
    body: JSON.stringify({ phone }),
  });
}

export function confirmPhoneCaptureApi(
  payload: VerifyOtpPayload,
): Promise<{ message: string; phone: string }> {
  return apiFetch('/v1/auth/me/phone/confirm', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
