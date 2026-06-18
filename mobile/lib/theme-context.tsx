import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { Platform, useColorScheme } from 'react-native';

export type ThemePreference = 'light' | 'dark' | 'system';
export type ColorScheme = 'light' | 'dark';

const STORAGE_KEY = 'kyros_theme_preference';

// expo-secure-store is unavailable on web; fall back to localStorage.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let SecureStore: any = null;
if (Platform.OS !== 'web') {
  // Dynamic require so the web bundle never references the native module.
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  SecureStore = require('expo-secure-store');
}

function isThemePreference(value: string | null): value is ThemePreference {
  return value === 'light' || value === 'dark' || value === 'system';
}

async function loadPreference(): Promise<ThemePreference | null> {
  const value = SecureStore
    ? await SecureStore.getItemAsync(STORAGE_KEY)
    : localStorage.getItem(STORAGE_KEY);
  return isThemePreference(value) ? value : null;
}

async function savePreference(preference: ThemePreference): Promise<void> {
  if (SecureStore) {
    await SecureStore.setItemAsync(STORAGE_KEY, preference);
  } else {
    localStorage.setItem(STORAGE_KEY, preference);
  }
}

interface ThemeContextValue {
  preference: ThemePreference;
  colorScheme: ColorScheme;
  setPreference: (preference: ThemePreference) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const systemScheme = useColorScheme();
  const [preference, setPreferenceState] = useState<ThemePreference>('light');

  useEffect(() => {
    let cancelled = false;
    void loadPreference().then(stored => {
      if (!cancelled && stored) {
        setPreferenceState(stored);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  function setPreference(next: ThemePreference) {
    setPreferenceState(next);
    void savePreference(next);
  }

  const colorScheme: ColorScheme =
    preference === 'system' ? (systemScheme === 'dark' ? 'dark' : 'light') : preference;

  return (
    <ThemeContext.Provider value={{ preference, colorScheme, setPreference }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useThemePreference(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  const systemScheme = useColorScheme();

  if (ctx) {
    return ctx;
  }

  // Fallback for usage outside <ThemeProvider> (e.g. unit tests / Storybook):
  // mirrors the system scheme and the toggle is a no-op.
  return {
    preference: 'system',
    colorScheme: systemScheme === 'dark' ? 'dark' : 'light',
    setPreference: () => {},
  };
}
