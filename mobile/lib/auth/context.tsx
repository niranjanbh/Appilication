import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { getMeApi } from '../api/auth';
import { registerUnauthenticatedHandler } from '../api/client';
import {
  addPushTokenChangeListener,
  registerForPushNotifications,
} from '../native/notifications';
import {
  clearTokens,
  isOnboardingComplete,
  loadTokens,
  saveTokens,
  setOnboardingComplete,
} from './storage';
import type { AuthTokens, UserMe } from '../../types/auth';

type AuthState =
  | { status: 'loading' }
  | { status: 'unauthenticated' }
  | { status: 'authenticated'; user: UserMe; onboardingComplete: boolean };

interface AuthContextValue {
  state: AuthState;
  signIn: (tokens: AuthTokens) => Promise<void>;
  signOut: () => Promise<void>;
  markOnboardingComplete: () => Promise<void>;
  /** Re-fetch the current user (e.g. after capturing a phone number) so gates
   *  keyed on user fields re-evaluate. No-op unless authenticated. */
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: 'loading' });

  const signOut = useCallback(async () => {
    await clearTokens();
    setState({ status: 'unauthenticated' });
  }, []);

  useEffect(() => {
    registerUnauthenticatedHandler(signOut);
  }, [signOut]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const { accessToken } = await loadTokens();
      if (!accessToken) {
        if (!cancelled) setState({ status: 'unauthenticated' });
        return;
      }
      try {
        const [user, onboardingComplete] = await Promise.all([
          getMeApi(),
          isOnboardingComplete(),
        ]);
        if (!cancelled) setState({ status: 'authenticated', user, onboardingComplete });
      } catch {
        await clearTokens();
        if (!cancelled) setState({ status: 'unauthenticated' });
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // Once authenticated (after login/signup or on app start with a live session),
  // register this device's Expo push token with the backend and listen for token
  // rotation. Registration is idempotent and non-fatal — failures are swallowed
  // inside the native helper so they never block the authenticated experience.
  useEffect(() => {
    if (state.status !== 'authenticated') return;
    void registerForPushNotifications();
    const sub = addPushTokenChangeListener();
    return () => sub.remove();
  }, [state.status]);

  const signIn = useCallback(async (tokens: AuthTokens) => {
    await saveTokens(tokens);
    const [user, onboardingComplete] = await Promise.all([
      getMeApi(),
      isOnboardingComplete(),
    ]);
    setState({ status: 'authenticated', user, onboardingComplete });
  }, []);

  const refreshUser = useCallback(async () => {
    const user = await getMeApi();
    setState(prev =>
      prev.status === 'authenticated' ? { ...prev, user } : prev,
    );
  }, []);

  const markOnboardingComplete = useCallback(async () => {
    await setOnboardingComplete();
    setState(prev =>
      prev.status === 'authenticated'
        ? { ...prev, onboardingComplete: true }
        : prev,
    );
  }, []);

  return (
    <AuthContext.Provider value={{ state, signIn, signOut, markOnboardingComplete, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
