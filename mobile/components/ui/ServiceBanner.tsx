import { useEffect, useRef, useSyncExternalStore } from 'react';
import { Animated, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useQueryClient } from '@tanstack/react-query';
import { getServiceHealth, subscribeServiceHealth } from '../../lib/api/service-health';
import { useNetworkStatus } from '../../lib/hooks/useNetworkStatus';
import { useAuth } from '../../lib/auth/context';
import { colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

/**
 * "Kyros is unavailable" indicator. Distinct from OfflineBanner: that one means
 * the device has no connectivity (red); this one means the device is online but
 * the backend isn't answering — network failures or 5xx from API calls (amber).
 *
 * Suppressed while the device is actually offline so the two banners never stack
 * (OfflineBanner owns that case).
 */
export function ServiceBanner() {
  const health = useSyncExternalStore(subscribeServiceHealth, getServiceHealth, getServiceHealth);
  const { isConnected, isInternetReachable } = useNetworkStatus();
  const { state } = useAuth();
  const queryClient = useQueryClient();
  // Hidden offset must exceed the banner's full height (paddingTop spacing[10]
  // + content + paddingBottom) or a saffron sliver peeks below the top edge on
  // every screen. -120 clears it with margin.
  const slideAnim = useRef(new Animated.Value(-120)).current;

  const deviceOffline = !isConnected || isInternetReachable === false;
  // Only surface backend trouble inside the authenticated app — never on the
  // login / onboarding flow, where it's noise.
  const show = health === 'unavailable' && !deviceOffline && state.status === 'authenticated';

  useEffect(() => {
    Animated.timing(slideAnim, {
      toValue: show ? 0 : -120,
      duration: 300,
      useNativeDriver: Platform.OS !== 'web',
    }).start();
  }, [show, slideAnim]);

  function handleRetry() {
    queryClient.invalidateQueries();
  }

  return (
    <Animated.View
      style={[
        styles.banner,
        { transform: [{ translateY: slideAnim }], pointerEvents: show ? 'auto' : 'none' },
      ]}
      accessibilityLiveRegion="polite"
    >
      <View style={styles.content}>
        <Ionicons name="warning-outline" size={18} color={colors.ink} />
        <Text style={styles.text}>We're having trouble reaching Baseline</Text>
        <Pressable onPress={handleRetry} style={styles.retryBtn} accessibilityLabel="Retry">
          <Text style={styles.retryText}>Retry</Text>
        </Pressable>
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  banner: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 9998,
    backgroundColor: colors.saffron,
    paddingTop: spacing[10],
    paddingBottom: spacing[3],
    paddingHorizontal: spacing[4],
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing[2],
  },
  text: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: '600',
    color: colors.ink,
    flex: 1,
  },
  retryBtn: {
    backgroundColor: 'rgba(26,26,26,0.12)',
    borderRadius: 12,
    paddingVertical: spacing[1],
    paddingHorizontal: spacing[3],
  },
  retryText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    color: colors.ink,
  },
});
