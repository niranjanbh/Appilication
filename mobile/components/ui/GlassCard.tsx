import { BlurView } from 'expo-blur';
import { Platform, StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';
import { borderRadius, glass, spacing, withAlpha } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';

interface GlassCardProps {
  children: React.ReactNode;
  /** More opaque surface — use for forms and clinical values that need contrast. */
  strong?: boolean;
  /** Override the default blur intensity. */
  intensity?: number;
  /** Remove the default inner padding. */
  unpadded?: boolean;
  style?: StyleProp<ViewStyle>;
}

// Live blur is expensive on low-end Android; those devices get a translucent solid
// surface instead. iOS and web (CSS backdrop-filter) render true glass.
const CAN_BLUR = Platform.OS !== 'android';

export function GlassCard({ children, strong = false, intensity, unpadded = false, style }: GlassCardProps) {
  const t = useTheme();
  const surface = strong || !CAN_BLUR ? t.glass.surfaceStrong : t.glass.surface;

  const frame: StyleProp<ViewStyle> = [
    styles.frame,
    {
      borderColor: t.glass.border,
      backgroundColor: CAN_BLUR ? undefined : surface,
      boxShadow: `0 8px 20px ${withAlpha(t.shadow, 0.10)}`,
    },
    style,
  ];

  if (!CAN_BLUR) {
    return (
      <View style={frame}>
        <View style={[styles.content, !unpadded && styles.padded]}>{children}</View>
      </View>
    );
  }

  return (
    <View style={frame}>
      <BlurView
        tint={t.isDark ? 'dark' : 'light'}
        intensity={intensity ?? glass.blur.card}
        style={StyleSheet.absoluteFill}
      />
      {/* Tinted wash over the blur so content keeps contrast on busy backgrounds */}
      <View style={[StyleSheet.absoluteFill, { backgroundColor: surface }]} />
      <View style={[styles.content, !unpadded && styles.padded]}>{children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  frame: {
    borderRadius: borderRadius.xxl,
    borderWidth: 1,
    overflow: 'hidden',
  },
  content: { position: 'relative' },
  padded: { padding: spacing[5] },
});
