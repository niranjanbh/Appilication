import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { getMeApi } from '../api/auth';
import { registerUnauthenticatedHandler } from '../api/client';
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

  const signIn = useCallback(async (tokens: AuthTokens) => {
    await saveTokens(tokens);
    const [user, onboardingComplete] = await Promise.all([
      getMeApi(),
      isOnboardingComplete(),
    ]);
    setState({ status: 'authenticated', user, onboardingComplete });
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
    <AuthContext.Provider value={{ state, signIn, signOut, markOnboardingComplete }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
