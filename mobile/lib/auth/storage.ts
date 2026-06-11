import { Platform } from 'react-native';
import type { AuthTokens } from '../../types/auth';

const KEY_ACCESS = 'kyros_access_token';
const KEY_REFRESH = 'kyros_refresh_token';
const KEY_ONBOARDING = 'kyros_onboarding_complete';

// expo-secure-store is unavailable on web; fall back to localStorage.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let SecureStore: any = null;
if (Platform.OS !== 'web') {
  // Dynamic require so the web bundle never references the native module.
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  SecureStore = require('expo-secure-store');
}

async function setItem(key: string, value: string): Promise<void> {
  if (SecureStore) {
    // WHEN_UNLOCKED_THIS_DEVICE_ONLY: tokens are unreadable while the device is
    // locked and are excluded from device backups / transfers to a new device.
    await SecureStore.setItemAsync(key, value, {
      keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
    });
  } else {
    localStorage.setItem(key, value);
  }
}

async function getItem(key: string): Promise<string | null> {
  if (SecureStore) {
    return SecureStore.getItemAsync(key);
  }
  return localStorage.getItem(key);
}

async function removeItem(key: string): Promise<void> {
  if (SecureStore) {
    await SecureStore.deleteItemAsync(key);
  } else {
    localStorage.removeItem(key);
  }
}

export async function saveTokens(tokens: AuthTokens): Promise<void> {
  await setItem(KEY_ACCESS, tokens.access_token);
  await setItem(KEY_REFRESH, tokens.refresh_token);
}

export async function loadTokens(): Promise<{ accessToken: string | null; refreshToken: string | null }> {
  const [accessToken, refreshToken] = await Promise.all([
    getItem(KEY_ACCESS),
    getItem(KEY_REFRESH),
  ]);
  return { accessToken, refreshToken };
}

export async function clearTokens(): Promise<void> {
  await Promise.all([removeItem(KEY_ACCESS), removeItem(KEY_REFRESH)]);
}

export async function setOnboardingComplete(): Promise<void> {
  await setItem(KEY_ONBOARDING, '1');
}

export async function isOnboardingComplete(): Promise<boolean> {
  const val = await getItem(KEY_ONBOARDING);
  return val === '1';
}
