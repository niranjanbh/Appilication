import { LinearGradient } from 'expo-linear-gradient';
import { StyleSheet, View } from 'react-native';
import { colors, withAlpha } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';

/**
 * Soft ambient color glows rendered behind screen content. Gives glass surfaces
 * something to refract — without it, blur over a flat background reads as solid.
 * Render as the first child of a screen; content scrolls above it.
 */
export function AmbientBackground() {
  const t = useTheme();
  const glowA = t.isDark ? withAlpha(colors.electricBlue, 0.16) : withAlpha(colors.electricBlue, 0.10);
  const glowB = t.isDark ? withAlpha(colors.accentViolet, 0.13) : withAlpha(colors.accentViolet, 0.08);
  const glowC = t.isDark ? withAlpha(colors.successLight, 0.08) : withAlpha(colors.successLight, 0.10);
  const fade  = withAlpha(t.background, 0);

  return (
    <View style={[StyleSheet.absoluteFill, { pointerEvents: 'none' }]}>
      <LinearGradient colors={[glowA, fade]} style={[styles.blob, styles.topLeft]} />
      <LinearGradient colors={[glowB, fade]} style={[styles.blob, styles.right]} />
      <LinearGradient colors={[glowC, fade]} style={[styles.blob, styles.bottom]} />
    </View>
  );
}

const styles = StyleSheet.create({
  blob: {
    position: 'absolute',
    width: 420,
    height: 420,
    borderRadius: 210,
  },
  topLeft: { top: -160, left: -140 },
  right:   { top: 180, right: -220 },
  bottom:  { bottom: -180, left: -60 },
});
