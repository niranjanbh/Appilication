import { useEffect } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Canvas, Path, Skia } from '@shopify/react-native-skia';
import { useSharedValue, withTiming, Easing } from 'react-native-reanimated';
import { colors, fontFamily, fontSize, fontWeight, motionDuration } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';
import { useReducedMotion } from '../../lib/hooks/useReducedMotion';

interface AdherenceRingProps {
  percent: number;
  size?: number;
  label?: string;
  strokeWidth?: number;
}

function makeArcPath(cx: number, cy: number, r: number, startAngle: number, endAngle: number): ReturnType<typeof Skia.Path.Make> {
  const path = Skia.Path.Make();
  path.addArc(
    { x: cx - r, y: cy - r, width: r * 2, height: r * 2 },
    startAngle,
    endAngle - startAngle,
  );
  return path;
}

export function AdherenceRing({ percent, size = 120, label, strokeWidth = 10 }: AdherenceRingProps) {
  const t = useTheme();
  const reduced = useReducedMotion();
  const progress = useSharedValue(reduced ? percent / 100 : 0);
  const cx = size / 2;
  const cy = size / 2;
  const r = (size - strokeWidth) / 2;

  useEffect(() => {
    if (reduced) {
      progress.value = percent / 100;
    } else {
      progress.value = withTiming(percent / 100, {
        duration: motionDuration.statCount,
        easing: Easing.out(Easing.cubic),
      });
    }
  }, [percent, reduced, progress]);

  const trackPath = makeArcPath(cx, cy, r, -90, 270);
  const sweepAngle = (percent / 100) * 360;
  const fillPath = makeArcPath(cx, cy, r, -90, -90 + sweepAngle);

  const trackColor = t.isDark ? 'rgba(79,163,131,0.15)' : 'rgba(60,52,30,0.08)';
  const fillColor = t.isDark ? colors.jadeGlow : colors.forest;

  return (
    <View style={styles.container} accessibilityLabel={label ?? `${percent}% adherence`}>
      <Canvas style={{ width: size, height: size }}>
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
          color={fillColor}
        />
      </Canvas>
      <View style={[styles.labelWrap, { width: size, height: size }]}>
        <Text style={[styles.percent, { color: t.text }]}>{percent}%</Text>
        {label && <Text style={[styles.label, { color: t.textSub }]}>{label}</Text>}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: 'center', justifyContent: 'center' },
  labelWrap: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
  percent: {
    fontFamily: fontFamily.data,
    fontSize: fontSize.h3,
    fontWeight: fontWeight.medium,
  },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    marginTop: 2,
  },
});
