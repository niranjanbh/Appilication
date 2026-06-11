import { usePreventScreenCapture } from 'expo-screen-capture';
import { Platform } from 'react-native';

function NativeGuard() {
  // Android: sets FLAG_SECURE (blocks screenshots + hides content in recents).
  // iOS: blanks the screen during capture/recording where supported.
  usePreventScreenCapture();
  return null;
}

/**
 * Render inside screens that display PHI documents (prescriptions, lab reports)
 * to block screen capture while the screen is focused. No-op on web.
 */
export function CaptureGuard() {
  if (Platform.OS === 'web') return null;
  return <NativeGuard />;
}
