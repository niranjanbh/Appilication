export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

export interface UserMe {
  id: string;
  name: string;
  email: string | null;
  phone: string | null;
  phone_verified: boolean;
  email_verified: boolean;
  role: 'patient' | 'doctor' | 'coordinator' | 'super_admin';
  date_of_birth: string | null;
  gender: string | null;
  city: string | null;
  state: string | null;
  language_preference: string | null;
  timezone: string;
  last_login_at: string | null;
  created_at: string;
}

export type ConsentType = 'terms' | 'privacy' | 'telemedicine' | 'data_processing' | 'health_sync' | 'marketing' | 'recording' | 'research';

export interface ConsentRecord {
  id: string;
  consent_type: ConsentType;
  version: string;
  granted: boolean;
  granted_at: string;
  revoked_at: string | null;
  ip_address: string | null;
}
