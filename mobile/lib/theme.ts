import { useColorScheme } from 'react-native';
import { colors } from './design-tokens';

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
  isDark:       true as const,
} as const;

export type AppPalette = typeof lightPalette | typeof darkPalette;

export function useTheme(): AppPalette {
  const scheme = useColorScheme();
  return scheme === 'dark' ? darkPalette : lightPalette;
}
