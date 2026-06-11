import { BlurView } from 'expo-blur';
import { useEffect, useState } from 'react';
import { AppState, Platform, StyleSheet, Text, View } from 'react-native';
import { fontFamily, glass } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';

/**
 * Covers app content the moment the app leaves the foreground so PHI is not
 * readable in the OS app switcher. iOS snapshots the screen on 'inactive', which
 * fires before the snapshot is taken; Android recents is additionally covered by
 * FLAG_SECURE on PHI screens (see CaptureGuard).
 *
 * Mount once, as the last child of the root layout. Web has no app switcher.
 */
export function PrivacyShield() {
  const t = useTheme();
  const [shielded, setShielded] = useState(false);

  useEffect(() => {
    if (Platform.OS === 'web') return;
    const sub = AppState.addEventListener('change', (state) => {
      setShielded(state !== 'active');
    });
    return () => sub.remove();
  }, []);

  if (!shielded) return null;

  return (
    <View style={[StyleSheet.absoluteFill, styles.shield]} pointerEvents="none">
      <BlurView
        tint={t.isDark ? 'dark' : 'light'}
        intensity={glass.blur.shield}
        style={StyleSheet.absoluteFill}
      />
      {/* Opaque-ish wash in case blur is unavailable on this device */}
      <View style={[StyleSheet.absoluteFill, { backgroundColor: t.glass.overlay }]} />
      <View style={styles.center}>
        <Text style={[styles.wordmark, { color: t.text }]}>Kyros</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  shield: { zIndex: 9999, elevation: 9999 },
  center: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
  wordmark: {
    fontFamily: fontFamily.display,
    fontSize: 40,
    fontWeight: '500',
    letterSpacing: -0.5,
  },
});
