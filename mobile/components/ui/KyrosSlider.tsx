import { useRef } from 'react';
import {
  PanResponder,
  StyleSheet,
  Text,
  View,
  type LayoutChangeEvent,
} from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from 'react-native-reanimated';
import { fontFamily, fontSize, spacing } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';
import { triggerHaptic } from './HapticPressable';

interface SnapPoint {
  value: number;
  label: string;
}

interface KyrosSliderProps {
  min: number;
  max: number;
  value: number;
  onValueChange: (value: number) => void;
  step?: number;
  snapPoints?: SnapPoint[];
  label?: string;
  formatValue?: (value: number) => string;
  accessibilityLabel?: string;
}

const TRACK_H = 6;
const THUMB_SIZE = 28;
const SPRING = { mass: 0.3, stiffness: 500, damping: 24 };

export function KyrosSlider({
  min,
  max,
  value,
  onValueChange,
  step = 1,
  snapPoints,
  label,
  formatValue,
  accessibilityLabel,
}: KyrosSliderProps) {
  const t = useTheme();
  const sl = t.slider;
  const sk = t.skeu;

  const trackWidth = useRef(0);
  const thumbScale = useSharedValue(1);
  const lastSnap = useRef(-1);

  const fraction = max > min ? (value - min) / (max - min) : 0;

  // Refs keep the PanResponder (created once) reading the latest props instead of
  // closing over stale values from the first render.
  const configRef = useRef({ min, max, step, snapPoints, onValueChange });
  configRef.current = { min, max, step, snapPoints, onValueChange };
  const valueRef = useRef(value);
  valueRef.current = value;
  // The fraction captured at the moment the drag begins — the drag is relative to it.
  const startFraction = useRef(0);

  const onLayout = (e: LayoutChangeEvent) => {
    trackWidth.current = e.nativeEvent.layout.width;
  };

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: () => {
        const { min: lo, max: hi } = configRef.current;
        startFraction.current = hi > lo ? (valueRef.current - lo) / (hi - lo) : 0;
        thumbScale.value = withSpring(1.2, SPRING);
        triggerHaptic('light');
      },
      onPanResponderMove: (_e, gesture) => {
        if (trackWidth.current === 0) return;
        const { min: lo, max: hi, step: st, snapPoints: snaps, onValueChange: emit } = configRef.current;
        const thumbOffset = (startFraction.current * trackWidth.current) + gesture.dx;
        const newFraction = Math.max(0, Math.min(1, thumbOffset / trackWidth.current));
        const raw = lo + newFraction * (hi - lo);
        const stepped = Math.round(raw / st) * st;
        const snapped = Math.max(lo, Math.min(hi, stepped));

        if (snaps) {
          const snapIdx = snaps.findIndex(sp => sp.value === snapped);
          if (snapIdx !== -1 && snapIdx !== lastSnap.current) {
            lastSnap.current = snapIdx;
            triggerHaptic('selection');
          }
        }

        emit(snapped);
      },
      onPanResponderRelease: () => {
        thumbScale.value = withSpring(1, SPRING);
        lastSnap.current = -1;
      },
    }),
  ).current;

  const thumbAnimStyle = useAnimatedStyle(() => ({
    transform: [{ scale: thumbScale.value }],
  }));

  const grooveShadow = t.isDark
    ? `inset 1px 1px 3px ${sl.groove}`
    : `inset 1px 1px 3px ${sl.groove}, inset -1px -1px 2px rgba(255,255,255,0.40)`;
  const thumbShadow = `0 2px 6px ${sl.thumbShadow}, 0 -1px 0 ${sk.highlight}`;
  const displayVal = formatValue ? formatValue(value) : String(value);

  return (
    <View
      style={styles.container}
      accessibilityRole="adjustable"
      accessibilityLabel={accessibilityLabel ?? label}
      accessibilityValue={{ min, max, now: value, text: displayVal }}
    >
      {(label || formatValue) && (
        <View style={styles.header}>
          {label && <Text style={[styles.label, { color: t.text }]}>{label}</Text>}
          <Text style={[styles.valueLabel, { color: t.primary }]}>{displayVal}</Text>
        </View>
      )}

      <View style={styles.trackContainer} onLayout={onLayout}>
        {/* Groove track */}
        <View
          style={[
            styles.track,
            { backgroundColor: sl.track, boxShadow: grooveShadow },
          ]}
        />
        {/* Active fill */}
        <View
          style={[
            styles.trackFill,
            {
              backgroundColor: sl.trackActive,
              width: `${fraction * 100}%` as unknown as number,
            },
          ]}
        />
        {/* Thumb */}
        <Animated.View
          {...panResponder.panHandlers}
          style={[
            styles.thumb,
            {
              backgroundColor: sl.thumb,
              borderColor: sl.thumbBorder,
              boxShadow: thumbShadow,
              left: `${fraction * 100}%` as unknown as number,
            },
            thumbAnimStyle,
          ]}
        />
      </View>

      {/* Snap point labels */}
      {snapPoints && snapPoints.length > 0 && (
        <View style={styles.snapRow}>
          {snapPoints.map((sp) => {
            const active = value === sp.value;
            return (
              <Text
                key={sp.value}
                style={[
                  styles.snapLabel,
                  { color: active ? t.primary : t.textSub, fontWeight: active ? '700' : '400' },
                ]}
              >
                {sp.label}
              </Text>
            );
          })}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: spacing[2] },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '500',
  },
  valueLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    fontWeight: '700',
  },
  trackContainer: {
    height: THUMB_SIZE + 8,
    justifyContent: 'center',
    position: 'relative',
  },
  track: {
    height: TRACK_H,
    borderRadius: TRACK_H / 2,
    position: 'absolute',
    left: 0,
    right: 0,
  },
  trackFill: {
    height: TRACK_H,
    borderRadius: TRACK_H / 2,
    position: 'absolute',
    left: 0,
  },
  thumb: {
    width: THUMB_SIZE,
    height: THUMB_SIZE,
    borderRadius: THUMB_SIZE / 2,
    borderWidth: 1.5,
    position: 'absolute',
    marginLeft: -(THUMB_SIZE / 2),
  },
  snapRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 2,
  },
  snapLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
  },
});
