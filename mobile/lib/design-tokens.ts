/**
 * Typed design-token exports for React Native.
 * All values derive from @kyros/design-tokens/tokens.json — no hex literals here.
 * React Native StyleSheet expects numeric pixels; px() strips the "px" suffix.
 */
import tokens from '@kyros/design-tokens';

function px(value: string): number {
  return parseInt(value, 10);
}

export const colors = {
  // Original palette
  forest:       tokens.colors.forest,
  jade:         tokens.colors.jade,
  sage:         tokens.colors.sage,
  saffron:      tokens.colors.saffron,
  terracotta:   tokens.colors.terracotta,
  ivory:        tokens.colors.ivory,
  peachMist:    tokens.colors.peachMist,
  white:        tokens.colors.white,
  ink:          tokens.colors.ink,
  stone:        tokens.colors.stone,
  alert:        tokens.colors.alert,
  // Premium navy/dark palette
  navyDeep:     tokens.colors.navyDeep,
  navyMid:      tokens.colors.navyMid,
  skyMist:      tokens.colors.skyMist,
  iceBlue:      tokens.colors.iceBlue,
  coolGray:     tokens.colors.coolGray,
  borderLight:  tokens.colors.borderLight,
  successGreen: tokens.colors.successGreen,
  successLight: tokens.colors.successLight,
  warningAmber: tokens.colors.warningAmber,
  criticalRed:  tokens.colors.criticalRed,
  midnight:     tokens.colors.midnight,
  nightSurface: tokens.colors.nightSurface,
  nightElev:    tokens.colors.nightElev,
  electricBlue: tokens.colors.electricBlue,
  slateText:    tokens.colors.slateText,
} as const;

export const fontFamily = {
  display: tokens.typography.fontFamily.display[0],
  body:    tokens.typography.fontFamily.body[0],
  hindi:   tokens.typography.fontFamily.hindi[0],
} as const;

export const fontSize = {
  xs:      px(tokens.typography.fontSize.xs),
  sm:      px(tokens.typography.fontSize.sm),
  caption: px(tokens.typography.fontSize.caption),
  body:    px(tokens.typography.fontSize.body),
  bodyLg:  px(tokens.typography.fontSize.bodyLg),
  h3:      px(tokens.typography.fontSize.h3),
  h2:      px(tokens.typography.fontSize.h2),
  h1:      px(tokens.typography.fontSize.h1),
  display: px(tokens.typography.fontSize.display),
} as const;

export const lineHeight = {
  caption: parseFloat(tokens.typography.lineHeight.caption),
  body:    parseFloat(tokens.typography.lineHeight.body),
} as const;

export const fontWeight = {
  normal:   tokens.typography.fontWeight.normal   as '400',
  medium:   tokens.typography.fontWeight.medium   as '500',
  semibold: tokens.typography.fontWeight.semibold as '600',
} as const;

export const spacing = {
  1:  px(tokens.spacing['1']),
  2:  px(tokens.spacing['2']),
  3:  px(tokens.spacing['3']),
  4:  px(tokens.spacing['4']),
  5:  px(tokens.spacing['5']),
  6:  px(tokens.spacing['6']),
  8:  px(tokens.spacing['8']),
  10: px(tokens.spacing['10']),
  12: px(tokens.spacing['12']),
  16: px(tokens.spacing['16']),
  24: px(tokens.spacing['24']),
} as const;

export const borderRadius = {
  sm:   px(tokens.borderRadius.sm),
  md:   px(tokens.borderRadius.md),
  lg:   px(tokens.borderRadius.lg),
  xl:   px(tokens.borderRadius.xl),
  xxl:  px(tokens.borderRadius.xxl),
  full: px(tokens.borderRadius.full),
} as const;

export const motionDuration = {
  micro:      parseInt(tokens.motion.duration.micro, 10),
  entrance:   parseInt(tokens.motion.duration.entrance, 10),
  transition: parseInt(tokens.motion.duration.transition, 10),
  lineDraw:   parseInt(tokens.motion.duration.lineDraw, 10),
  pullQuote:  parseInt(tokens.motion.duration.pullQuote, 10),
  statCount:  parseInt(tokens.motion.duration.statCount, 10),
  photoFade:  parseInt(tokens.motion.duration.photoFade, 10),
} as const;
