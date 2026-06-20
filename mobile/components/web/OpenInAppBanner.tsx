/**
 * "Open in app" banner for mobile web users.
 *
 * Shown at the top of the screen when Platform.OS === 'web' AND width < 1024.
 * Forest tint background, dismissible, state persisted in sessionStorage
 * so it doesn't re-appear on navigation within the same session.
 *
 * Platform: web only — never rendered on native.
 */

import { Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { useState, useEffect } from 'react';
import { colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';
import { useBreakpoint } from '../../lib/hooks/useBreakpoint';

const DISMISSED_KEY = 'kyros_app_banner_dismissed';

export function OpenInAppBanner() {
  const { isMobileWeb } = useBreakpoint();
  const [dismissed, setDismissed] = useState(true); // start hidden, check on mount

  useEffect(() => {
    if (Platform.OS !== 'web') return;
    const val = (globalThis as Record<string, unknown>).sessionStorage
      ? (globalThis as { sessionStorage: Storage }).sessionStorage.getItem(DISMISSED_KEY)
      : null;
    setDismissed(val === '1');
  }, []);

  const dismiss = () => {
    if (Platform.OS === 'web') {
      (globalThis as { sessionStorage: Storage }).sessionStorage.setItem(DISMISSED_KEY, '1');
    }
    setDismissed(true);
  };

  if (!isMobileWeb || dismissed) return null;

  return (
    <View style={styles.banner}>
      <Text style={styles.text} numberOfLines={1}>
        Open Kyros in the app for the full experience
      </Text>
      <Pressable
        onPress={() => {
          // Attempt universal link / deep link — falls back to app store
          if (Platform.OS === 'web') {
            (globalThis as { location: { href: string } }).location.href = 'kyros://';
          }
        }}
        style={styles.openBtn}
        accessibilityLabel="Open in Kyros app"
      >
        <Text style={styles.openBtnText}>Open app</Text>
      </Pressable>
      <Pressable onPress={dismiss} style={styles.dismissBtn} accessibilityLabel="Dismiss banner">
        <Text style={styles.dismissText}>✕</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.forest + '14',
    paddingVertical: spacing[2],
    paddingHorizontal: spacing[3],
    gap: spacing[2],
  },
  text: {
    flex: 1,
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.forest,
  },
  openBtn: {
    backgroundColor: colors.forest,
    paddingVertical: spacing[1],
    paddingHorizontal: spacing[3],
    borderRadius: 4,
  },
  openBtnText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.ivoryText,
    fontWeight: '600',
  },
  dismissBtn: {
    padding: spacing[1],
  },
  dismissText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
  },
});
