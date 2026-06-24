/**
 * OnboardingIntakeProvider — holds the patient's condition + intake answers for
 * the duration of the onboarding wizard.
 *
 * Previously these answers were threaded through router params and silently
 * dropped at the consent screen, so nothing the patient picked was ever stored
 * or turned into a consultation request. This context spans the conditions,
 * intake-form, and abha-link screens (the consent + health-sync screens pass
 * through), which is why it lives in shared state rather than params.
 */

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { EMPTY_INTAKE, type OnboardingIntake } from './intake';

interface IntakeContextValue {
  intake: OnboardingIntake;
  update: (patch: Partial<OnboardingIntake>) => void;
}

const IntakeContext = createContext<IntakeContextValue | null>(null);

export function OnboardingIntakeProvider({ children }: { children: ReactNode }) {
  const [intake, setIntake] = useState<OnboardingIntake>(EMPTY_INTAKE);

  const update = useCallback((patch: Partial<OnboardingIntake>) => {
    setIntake(prev => ({ ...prev, ...patch }));
  }, []);

  const value = useMemo(() => ({ intake, update }), [intake, update]);

  return <IntakeContext.Provider value={value}>{children}</IntakeContext.Provider>;
}

export function useOnboardingIntake(): IntakeContextValue {
  const ctx = useContext(IntakeContext);
  if (!ctx) {
    throw new Error('useOnboardingIntake must be used within OnboardingIntakeProvider');
  }
  return ctx;
}
