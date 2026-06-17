import { useEffect, useRef } from 'react';
import { Animated, Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useQueryClient } from '@tanstack/react-query';
import { useNetworkStatus } from '../../lib/hooks/useNetworkStatus';
import { colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

export function OfflineBanner() {
  const { isConnected, isInternetReachable } = useNetworkStatus();
  const queryClient = useQueryClient();
  const slideAnim = useRef(new Animated.Value(-60)).current;

  const isOffline = !isConnected || isInternetReachable === false;

  useEffect(() => {
    Animated.timing(slideAnim, {
      toValue: isOffline ? 0 : -60,
      duration: 300,
      useNativeDriver: true,
    }).start();
  }, [isOffline, slideAnim]);

  function handleRetry() {
    queryClient.invalidateQueries();
  }

  return (
    <Animated.View
      style={[styles.banner, { transform: [{ translateY: slideAnim }] }]}
      pointerEvents={isOffline ? 'auto' : 'none'}
      accessibilityLiveRegion="polite"
    >
      <View style={styles.content}>
        <Ionicons name="cloud-offline-outline" size={18} color={colors.white} />
        <Text style={styles.text}>No internet connection</Text>
        <Pressable onPress={handleRetry} style={styles.retryBtn} accessibilityLabel="Retry connection">
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
    zIndex: 9999,
    backgroundColor: colors.criticalRed,
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
    color: colors.white,
    flex: 1,
  },
  retryBtn: {
    backgroundColor: 'rgba(255,255,255,0.25)',
    borderRadius: 12,
    paddingVertical: spacing[1],
    paddingHorizontal: spacing[3],
  },
  retryText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    color: colors.white,
  },
});
