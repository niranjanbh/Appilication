import { LinearGradient } from 'expo-linear-gradient';
import { useEffect, useState } from 'react';
import { StyleSheet, View, type DimensionValue } from 'react-native';
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';
import { borderRadius, spacing, withAlpha } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';
import { GlassCard } from './GlassCard';

interface SkeletonProps {
  width?: DimensionValue;
  height?: number;
  radius?: number | 'round';
}

/** Shimmering placeholder block, themed to the active palette. */
export function Skeleton({ width = '100%', height = 16, radius = borderRadius.md }: SkeletonProps) {
  const t = useTheme();
  const [trackW, setTrackW] = useState(0);
  const progress = useSharedValue(0);

  useEffect(() => {
    progress.value = withRepeat(
      withTiming(1, { duration: 1100, easing: Easing.linear }),
      -1,
    );
  }, [progress]);

  const sweep = useAnimatedStyle(() => ({
    transform: [{ translateX: -trackW + progress.value * trackW * 2 }],
  }));

  const highlight = withAlpha(t.surface, t.isDark ? 0.35 : 0.9);
  const edge      = withAlpha(t.surface, 0);

  return (
    <View
      accessibilityLabel="Loading"
      onLayout={e => setTrackW(e.nativeEvent.layout.width)}
      style={{
        width,
        height,
        borderRadius: radius === 'round' ? height / 2 : radius,
        backgroundColor: t.skeletonBase,
        overflow: 'hidden',
      }}
    >
      <Animated.View style={[StyleSheet.absoluteFill, sweep]}>
        <LinearGradient
          colors={[edge, highlight, edge]}
          start={{ x: 0, y: 0.5 }}
          end={{ x: 1, y: 0.5 }}
          style={styles.flex}
        />
      </Animated.View>
    </View>
  );
}

/**
 * Loading state for clinical list screens. Explicit and steady — lab values must
 * never appear to flicker in and out while reloading.
 */
export function SkeletonCards({ count = 3 }: { count?: number }) {
  return (
    <View style={styles.stack} accessibilityLabel="Loading">
      {Array.from({ length: count }, (_, i) => (
        <GlassCard key={i}>
          <View style={styles.row}>
            <Skeleton width={44} height={44} radius="round" />
            <View style={styles.lines}>
              <Skeleton width="70%" height={14} />
              <Skeleton width="45%" height={11} />
            </View>
          </View>
        </GlassCard>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  flex:  { flex: 1 },
  stack: { gap: spacing[3] },
  row:   { flexDirection: 'row', alignItems: 'center', gap: spacing[3] },
  lines: { flex: 1, gap: spacing[2] },
});
