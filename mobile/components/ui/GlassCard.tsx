import { BlurView } from 'expo-blur';
import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';
import { borderRadius, glass, shadow, spacing } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';
import { canLiveBlur } from '../../lib/platform/blur';

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

export function GlassCard({ children, strong = false, intensity, unpadded = false, style }: GlassCardProps) {
  const t = useTheme();
  const surface = strong || !canLiveBlur ? t.glass.surfaceStrong : t.glass.surface;

  const frame: StyleProp<ViewStyle> = [
    styles.frame,
    {
      borderColor: t.glass.border,
      backgroundColor: canLiveBlur ? undefined : surface,
      boxShadow: t.isDark ? shadow.darkMd : shadow.md,
    },
    style,
  ];

  if (!canLiveBlur) {
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
