import { LinearGradient } from 'expo-linear-gradient';
import { StyleSheet, View } from 'react-native';
import { colors, withAlpha } from '../../lib/design-tokens';
import { useAuth } from '../../lib/auth/context';

/**
 * Ambient gradient backdrop for the auth + welcome screens, giving the glass
 * form card color depth to refract.
 *
 * Pre-login (login / signup / password reset / OTP) it's a warm ivory wash to
 * match the light-mode auth flow. Once authenticated (the onboarding/welcome
 * screen, which is built for white-on-forest), it's the deep forest gradient.
 */
export function AuthBackdrop() {
  const { state } = useAuth();
  const dark = state.status === 'authenticated';

  const base: readonly [string, string, string] = dark
    ? [colors.forestSurface, colors.forestInk, colors.forestInk]
    : [colors.peachMist, colors.ivory, colors.ivory];

  const jadeTint = dark ? colors.jadeGlow : colors.jade;
  const topGlow    = dark ? withAlpha(jadeTint, 0.30)   : withAlpha(jadeTint, 0.12);
  const bottomGlow = dark ? withAlpha(colors.saffron, 0.22) : withAlpha(colors.saffron, 0.14);

  return (
    <View style={[StyleSheet.absoluteFill, { pointerEvents: 'none', overflow: 'hidden' }]}>
      <LinearGradient
        colors={base}
        start={{ x: 0, y: 0 }}
        end={{ x: 0.4, y: 1 }}
        style={StyleSheet.absoluteFill}
      />
      <LinearGradient
        colors={[topGlow, withAlpha(jadeTint, 0)]}
        style={[styles.blob, styles.topRight]}
      />
      <LinearGradient
        colors={[bottomGlow, withAlpha(colors.saffron, 0)]}
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
