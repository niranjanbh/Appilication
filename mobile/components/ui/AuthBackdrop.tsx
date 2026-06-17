import { LinearGradient } from 'expo-linear-gradient';
import { StyleSheet, View } from 'react-native';
import { colors, withAlpha } from '../../lib/design-tokens';

/**
 * Deep navy gradient with ambient glows for the auth screens. Replaces the flat
 * navy background so the glass form card has color depth to refract.
 */
export function AuthBackdrop() {
  return (
    <View style={[StyleSheet.absoluteFill, { pointerEvents: 'none' }]}>
      <LinearGradient
        colors={[colors.navyMid, colors.navyDeep, colors.midnight]}
        start={{ x: 0, y: 0 }}
        end={{ x: 0.4, y: 1 }}
        style={StyleSheet.absoluteFill}
      />
      <LinearGradient
        colors={[withAlpha(colors.electricBlue, 0.35), withAlpha(colors.electricBlue, 0)]}
        style={[styles.blob, styles.topRight]}
      />
      <LinearGradient
        colors={[withAlpha(colors.accentViolet, 0.28), withAlpha(colors.accentViolet, 0)]}
        style={[styles.blob, styles.bottomLeft]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  blob: {
    position: 'absolute',
    width: 380,
    height: 380,
    borderRadius: 190,
  },
  topRight:   { top: -120, right: -140 },
  bottomLeft: { bottom: -160, left: -120 },
});
