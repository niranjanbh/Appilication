declare module 'react-native-gesture-handler/ReanimatedSwipeable' {
  import type React from 'react';
  import type { StyleProp, ViewStyle } from 'react-native';
  import type { SharedValue } from 'react-native-reanimated';

  export enum SwipeDirection {
    LEFT = 'left',
    RIGHT = 'right',
  }

  export interface SwipeableMethods {
    close: () => void;
    openLeft: () => void;
    openRight: () => void;
    reset: () => void;
  }

  export interface SwipeableProps {
    ref?: React.Ref<SwipeableMethods>;
    children?: React.ReactNode;
    friction?: number;
    leftThreshold?: number;
    rightThreshold?: number;
    overshootLeft?: boolean;
    overshootRight?: boolean;
    overshootFriction?: number;
    onSwipeableOpen?: (direction: SwipeDirection) => void;
    onSwipeableClose?: (direction: SwipeDirection) => void;
    onSwipeableWillOpen?: (direction: SwipeDirection) => void;
    onSwipeableWillClose?: (direction: SwipeDirection) => void;
    renderLeftActions?: (
      progress: SharedValue<number>,
      translation: SharedValue<number>,
      swipeableMethods: SwipeableMethods,
    ) => React.ReactNode;
    renderRightActions?: (
      progress: SharedValue<number>,
      translation: SharedValue<number>,
      swipeableMethods: SwipeableMethods,
    ) => React.ReactNode;
    containerStyle?: StyleProp<ViewStyle>;
    childrenContainerStyle?: StyleProp<ViewStyle>;
    enabled?: boolean;
  }

  const ReanimatedSwipeable: React.ForwardRefExoticComponent<
    SwipeableProps & React.RefAttributes<SwipeableMethods>
  >;
  export default ReanimatedSwipeable;
}
