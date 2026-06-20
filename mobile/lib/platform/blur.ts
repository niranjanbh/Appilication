import { Platform } from 'react-native';
import { glass } from '../design-tokens';

export const canLiveBlur = Platform.OS !== 'android';

export const blurIntensity = {
  card:   glass.blur.card,
  dock:   glass.blur.dock,
  shield: glass.blur.shield,
} as const;
