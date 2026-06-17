import { colors, glass } from './design-tokens';
import { useThemePreference } from './theme-context';

export const lightPalette = {
  background:   colors.skyMist,
  surface:      colors.white,
  surfaceMuted: colors.borderLight,
  primary:      colors.navyDeep,
  text:         colors.navyDeep,
  textSub:      colors.coolGray,
  border:       'rgba(0,31,63,0.07)',
  shadow:       colors.navyDeep,
  navBar:       colors.white,
  success:      colors.successGreen,
  warning:      colors.warningAmber,
  critical:     colors.criticalRed,
  glass:        glass.light,
  skeletonBase: colors.borderLight,
  isDark:       false as const,
} as const;

export const darkPalette = {
  background:   colors.forestInk,
  surface:      colors.forestSurface,
  surfaceMuted: colors.forestSurfaceRaised,
  primary:      colors.saffron,
  text:         colors.ivoryText,
  textSub:      colors.stoneDim,
  border:       'rgba(79,163,131,0.15)',
  shadow:       '#000000',
  navBar:       colors.forestSurface,
  success:      colors.jadeGlow,
  warning:      colors.warningAmber,
  critical:     colors.alertBright,
  glass:        glass.dark,
  skeletonBase: colors.forestSurfaceRaised,
  isDark:       true as const,
} as const;

export type AppPalette = typeof lightPalette | typeof darkPalette;

export function useTheme(): AppPalette {
  const { colorScheme } = useThemePreference();
  return colorScheme === 'dark' ? darkPalette : lightPalette;
}
