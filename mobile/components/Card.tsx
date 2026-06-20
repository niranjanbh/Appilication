import { StyleSheet, View, type ViewProps } from 'react-native';
import { borderRadius, colors, shadow, spacing, withAlpha } from '../lib/design-tokens';
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

  const dynamicBorder = isDark ? 'rgba(79,163,131,0.12)' : withAlpha(colors.forest, 0.06);

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

  clay: {
    borderWidth: 1,
    boxShadow: shadow.md,
  },

  dark: {
    backgroundColor: colors.forest,
    borderWidth: 1,
    borderColor: 'rgba(79,163,131,0.20)',
    boxShadow: shadow.hero,
  },

  glass: {
    backgroundColor: 'rgba(255,255,255,0.12)',
    borderWidth: 1,
    boxShadow: shadow.sm,
  },

  flat: {
    boxShadow: shadow.xs,
  },
});
