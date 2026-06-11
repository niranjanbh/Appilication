import * as Haptics from 'expo-haptics';
import { Platform, type GestureResponderEvent } from 'react-native';
import { AnimatedPressable } from './AnimatedPressable';

type HapticStrength = 'light' | 'medium' | 'selection';

interface Props extends React.ComponentProps<typeof AnimatedPressable> {
  /** Haptic feedback fired on press-in. Defaults to a light impact. */
  haptic?: HapticStrength;
}

export function triggerHaptic(strength: HapticStrength = 'light'): void {
  if (Platform.OS === 'web') return;
  const fire =
    strength === 'selection'
      ? Haptics.selectionAsync()
      : Haptics.impactAsync(
          strength === 'medium' ? Haptics.ImpactFeedbackStyle.Medium : Haptics.ImpactFeedbackStyle.Light,
        );
  // Haptics are decorative; never let an unsupported device surface an error.
  void fire.catch(() => undefined);
}

/** AnimatedPressable (spring scale) + tactile haptic feedback on press-in. */
export function HapticPressable({ haptic = 'light', onPressIn, ...rest }: Props) {
  return (
    <AnimatedPressable
      {...rest}
      onPressIn={(e: GestureResponderEvent) => {
        triggerHaptic(haptic);
        onPressIn?.(e);
      }}
    />
  );
}
