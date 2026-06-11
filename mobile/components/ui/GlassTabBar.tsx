import { BlurView } from 'expo-blur';
import { Platform, Pressable, StyleSheet, type PressableProps } from 'react-native';
import { glass } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';
import { triggerHaptic } from './HapticPressable';

/** Bottom padding scroll content needs so the floating dock never hides the last row. */
export const TAB_DOCK_CLEARANCE = 128;

/**
 * Frosted backdrop for the floating tab dock. Android skips live blur (cost on
 * low-end devices) — the dock's own translucent background carries the look there.
 */
export function GlassTabBackground() {
  const t = useTheme();
  if (Platform.OS === 'android') return null;
  return (
    <BlurView
      tint={t.isDark ? 'dark' : 'light'}
      intensity={glass.blur.dock}
      style={StyleSheet.absoluteFill}
    />
  );
}

// Typed locally: @react-navigation/bottom-tabs is not a direct dependency under
// pnpm strict resolution, and its button props are structurally a Pressable.
type TabButtonProps = Omit<PressableProps, 'children'> & { children: React.ReactNode };

/** Tab button with selection haptics — drop-in for the default tabBarButton. */
export function HapticTabButton({ onPress, ...rest }: TabButtonProps) {
  return (
    <Pressable
      {...rest}
      onPress={(e) => {
        triggerHaptic('selection');
        onPress?.(e);
      }}
    />
  );
}
