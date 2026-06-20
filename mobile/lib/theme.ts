import { colors, glass, neumorph, skeu, slider, withAlpha } from './design-tokens';
import { useThemePreference } from './theme-context';

export const lightPalette = {
  background:   colors.ivory,
  surface:      colors.white,
  surfaceMuted: colors.peachMist,
  primary:      colors.forest,
  text:         colors.ink,
  textSub:      colors.stone,
  border:       withAlpha(colors.forest, 0.08),
  shadow:       colors.forest,
  navBar:       colors.white,
  success:      colors.jade,
  warning:      colors.saffron,
  critical:     colors.alert,
  glass:        glass.light,
  neumorph:     neumorph.light,
  skeu:         skeu.light,
  slider:       slider.light,
  skeletonBase: withAlpha(colors.stone, 0.12),
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
  warning:      colors.saffron,
  critical:     colors.alertBright,
  glass:        glass.dark,
  neumorph:     neumorph.dark,
  skeu:         skeu.dark,
  slider:       slider.dark,
  skeletonBase: colors.forestSurfaceRaised,
  isDark:       true as const,
} as const;

export type AppPalette = typeof lightPalette | typeof darkPalette;

export function useTheme(): AppPalette {
  const { colorScheme } = useThemePreference();
  return colorScheme === 'dark' ? darkPalette : lightPalette;
}
