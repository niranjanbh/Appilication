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
  background:   colors.midnight,
  surface:      colors.nightSurface,
  surfaceMuted: colors.nightElev,
  primary:      colors.electricBlue,
  text:         colors.white,
  textSub:      colors.slateText,
  border:       'rgba(255,255,255,0.08)',
  shadow:       '#000000',
  navBar:       colors.nightSurface,
  success:      colors.successLight,
  warning:      colors.warningAmber,
  critical:     colors.criticalRed,
  glass:        glass.dark,
  skeletonBase: colors.nightElev,
  isDark:       true as const,
} as const;

export type AppPalette = typeof lightPalette | typeof darkPalette;

export function useTheme(): AppPalette {
  const { colorScheme } = useThemePreference();
  return colorScheme === 'dark' ? darkPalette : lightPalette;
}
