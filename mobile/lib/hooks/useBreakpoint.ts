import { Platform, useWindowDimensions } from 'react-native';

const DESKTOP_MIN_WIDTH = 1024;

export interface Breakpoint {
  /** true on web AND width >= 1024 */
  isDesktop: boolean;
  /** true on web AND width < 1024 */
  isMobileWeb: boolean;
  /** true when running as a native app (iOS / Android) */
  isNative: boolean;
  width: number;
}

export function useBreakpoint(): Breakpoint {
  const { width } = useWindowDimensions();
  const isWeb = Platform.OS === 'web';
  return {
    isDesktop: isWeb && width >= DESKTOP_MIN_WIDTH,
    isMobileWeb: isWeb && width < DESKTOP_MIN_WIDTH,
    isNative: !isWeb,
    width,
  };
}
