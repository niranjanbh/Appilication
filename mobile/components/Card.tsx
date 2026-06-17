import { StyleSheet, View, type ViewProps } from 'react-native';
import { borderRadius, colors, spacing , withAlpha } from '../lib/design-tokens';
import { useThemePreference } from '../lib/theme-context';

type CardVariant = 'clay' | 'dark' | 'glass' | 'flat' | 'white' | 'ivory';

interface CardProps extends ViewProps {
  variant?: CardVariant;
}

export function Card({ variant = 'clay', style, children, ...props }: CardProps) {
  const isDark = useThemePreference().colorScheme === 'dark';

  const dynamicBg =
    variant === 'clay' || variant === 'white' || variant === 'flat'
      ? isDark ? colors.forestSurface       : colors.white
      : variant === 'ivory'
      ? isDark ? colors.forestSurfaceRaised : colors.ivory
      : undefined;

  const dynamicBorder = isDark ? 'rgba(79,163,131,0.12)' : 'rgba(0,31,63,0.06)';

  return (
    <View
      {...props}
      style={[
        styles.base,
        variant === 'clay'  && [styles.clay,  { backgroundColor: dynamicBg, borderColor: dynamicBorder }],
        variant === 'dark'  && styles.dark,
        variant === 'glass' && [styles.glass, { borderColor: dynamicBorder }],
        variant === 'flat'  && [styles.flat,  { backgroundColor: dynamicBg }],
        variant === 'white' && [styles.flat,  { backgroundColor: dynamicBg }],
        variant === 'ivory' && [styles.flat,  { backgroundColor: dynamicBg }],
        style,
      ]}
    >
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  base: {
    borderRadius: borderRadius.xxl,
    padding: spacing[6],
  },

  // Clay — soft background, large radius, layered shadow + inner border highlight
  clay: {
    borderWidth: 1,
    boxShadow: '0 8px 20px rgba(0,0,0,0.08)',
  },

  // Dark — forest hero card with jade border
  dark: {
    backgroundColor: colors.forest,
    borderWidth: 1,
    borderColor: 'rgba(79,163,131,0.20)',
    boxShadow: `0 14px 24px ${withAlpha(colors.forest, 0.40)}`,
  },

  // Glass — translucent surface
  glass: {
    backgroundColor: 'rgba(255,255,255,0.12)',
    borderWidth: 1,
    boxShadow: '0 4px 12px rgba(0,0,0,0.06)',
  },

  // Flat — minimal, just surface color
  flat: {
    boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
  },
});
