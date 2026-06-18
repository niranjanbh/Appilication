import { useEffect } from 'react';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from 'react-native-reanimated';
import { Pressable, StyleSheet, View } from 'react-native';
import { useTheme } from '../../lib/theme';
import { triggerHaptic } from './HapticPressable';

interface SkeuToggleProps {
  value: boolean;
  onValueChange: (val: boolean) => void;
  disabled?: boolean;
  accessibilityLabel?: string;
}

const TRACK_W = 52;
const TRACK_H = 30;
const THUMB_SIZE = 24;
const THUMB_MARGIN = 3;
const TRAVEL = TRACK_W - THUMB_SIZE - THUMB_MARGIN * 2;

const SPRING = { mass: 0.4, stiffness: 400, damping: 22 };

export function SkeuToggle({ value, onValueChange, disabled = false, accessibilityLabel }: SkeuToggleProps) {
  const t = useTheme();
  const sk = t.skeu;
  const sl = t.slider;

  const offset = useSharedValue(value ? TRAVEL : 0);

  // Animate to the new position whenever `value` changes — including external
  // changes (not just taps). Never mutate a shared value during render.
  useEffect(() => {
    offset.value = withSpring(value ? TRAVEL : 0, SPRING);
  }, [value, offset]);

  const thumbStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: offset.value }],
  }));

  const toggle = () => {
    if (disabled) return;
    triggerHaptic('selection');
    // Animation is driven by the useEffect reacting to the new `value`.
    onValueChange(!value);
  };

  const trackBg = value ? sl.trackActive : sl.track;
  const grooveShadow = t.isDark
    ? `inset 2px 2px 4px rgba(0,0,0,0.40), inset -1px -1px 3px rgba(79,163,131,0.08)`
    : `inset 2px 2px 4px rgba(0,31,63,0.12), inset -1px -1px 3px rgba(255,255,255,0.60)`;
  const thumbShadow = `0 2px 5px ${sl.thumbShadow}, 0 -1px 0 ${sk.highlight}`;

  return (
    <Pressable
      onPress={toggle}
      disabled={disabled}
      accessibilityLabel={accessibilityLabel}
      accessibilityRole="switch"
      accessibilityState={{ checked: value, disabled }}
    >
      <View
        style={[
          styles.track,
          {
            backgroundColor: trackBg,
            boxShadow: grooveShadow,
            opacity: disabled ? 0.5 : 1,
          },
        ]}
      >
        <Animated.View
          style={[
            styles.thumb,
            {
              backgroundColor: sl.thumb,
              borderColor: sl.thumbBorder,
              boxShadow: thumbShadow,
            },
            thumbStyle,
          ]}
        />
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  track: {
    width: TRACK_W,
    height: TRACK_H,
    borderRadius: TRACK_H / 2,
    justifyContent: 'center',
    paddingHorizontal: THUMB_MARGIN,
  },
  thumb: {
    width: THUMB_SIZE,
    height: THUMB_SIZE,
    borderRadius: THUMB_SIZE / 2,
    borderWidth: 1,
  },
});
