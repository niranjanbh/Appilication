import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Canvas, Path, Skia } from '@shopify/react-native-skia';
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

function makeArcPath(cx: number, cy: number, r: number, startDeg: number, endDeg: number) {
  const path = Skia.Path.Make();
  path.addArc(
    { x: cx - r, y: cy - r, width: r * 2, height: r * 2 },
    startDeg,
    endDeg - startDeg,
  );
  return path;
}

export function ActivityRings({ rings, size = 140, strokeWidth = 12 }: ActivityRingsProps) {
  const t = useTheme();
  const cx = size / 2;
  const cy = size / 2;
  const gap = strokeWidth + 4;

  const ringColors = t.isDark ? RING_COLORS.dark : RING_COLORS.light;
  const trackColor = t.isDark ? RING_COLORS.track.dark : RING_COLORS.track.light;

  const accessLabel = rings.map(r => `${r.label}: ${r.percent}%`).join(', ');

  return (
    <View
      style={[styles.container, { width: size, height: size }]}
      accessibilityLabel={accessLabel}
    >
      <Canvas style={{ width: size, height: size }}>
        {rings.map((ring, i) => {
          const r = (size - strokeWidth) / 2 - i * gap;
          const sweepAngle = (ring.percent / 100) * 360;
          const trackPath = makeArcPath(cx, cy, r, -90, 270);
          const fillPath = makeArcPath(cx, cy, r, -90, -90 + Math.min(sweepAngle, 360));
          return (
            <React.Fragment key={i}>
              <Path
                path={trackPath}
                style="stroke"
                strokeWidth={strokeWidth}
                strokeCap="round"
                color={trackColor}
              />
              <Path
                path={fillPath}
                style="stroke"
                strokeWidth={strokeWidth}
                strokeCap="round"
                color={ringColors[i]}
              />
            </React.Fragment>
          );
        })}
      </Canvas>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: 'center', justifyContent: 'center' },
});
