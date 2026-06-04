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

export function getMeApi(): Promise<UserMe> {
  return apiFetch('/v1/users/me');
}
