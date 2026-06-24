import React from 'react';
import { StyleSheet, View } from 'react-native';
import { colors } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';

interface RingData {
  percent: number;
  label: string;
}

interface ActivityRingsProps {
  rings: [RingData, RingData, RingData];
  size?: number;
  strokeWidth?: number;
}

const RING_COLORS = {
  light: [colors.forest, colors.saffron, colors.jade],
  dark:  [colors.jadeGlow, colors.saffron, colors.jade],
  track: {
    light: 'rgba(60,52,30,0.06)',
    dark:   'rgba(79,163,131,0.10)',
  },
} as const;

/**
 * Web fallback for ActivityRings. The native implementation uses
 * @shopify/react-native-skia, whose CanvasKit WASM isn't loaded on web
 * (Skia is undefined → "Cannot read properties of undefined (reading 'Make')").
 * This renders the same concentric rings with CSS conic-gradient + a radial
 * mask to cut the donut hole, matching the native geometry.
 */
export function ActivityRings({ rings, size = 140, strokeWidth = 12 }: ActivityRingsProps) {
  const t = useTheme();
  const gap = strokeWidth + 4;

  const ringColors = t.isDark ? RING_COLORS.dark : RING_COLORS.light;
  const trackColor = t.isDark ? RING_COLORS.track.dark : RING_COLORS.track.light;

  const accessLabel = rings.map(r => `${r.label}: ${r.percent}%`).join(', ');

  return (
    <View
      style={[styles.container, { width: size, height: size }]}
      accessibilityLabel={accessLabel}
    >
      {rings.map((ring, i) => {
        const outerDiameter = size - i * 2 * gap;
        const holeRadius = outerDiameter / 2 - strokeWidth;
        const sweepDeg = (Math.min(ring.percent, 100) / 100) * 360;

        // Web-only CSS (conic-gradient / mask) not present in RN style types.
        const webStyle = {
          position: 'absolute',
          width: outerDiameter,
          height: outerDiameter,
          borderRadius: outerDiameter / 2,
          backgroundImage: `conic-gradient(from 0deg, ${ringColors[i]} 0deg ${sweepDeg}deg, ${trackColor} ${sweepDeg}deg 360deg)`,
          WebkitMaskImage: `radial-gradient(circle, transparent ${holeRadius}px, #000 ${holeRadius}px)`,
          maskImage: `radial-gradient(circle, transparent ${holeRadius}px, #000 ${holeRadius}px)`,
        } as unknown as React.ComponentProps<typeof View>['style'];

        return <View key={i} style={webStyle} />;
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: 'center', justifyContent: 'center' },
});
