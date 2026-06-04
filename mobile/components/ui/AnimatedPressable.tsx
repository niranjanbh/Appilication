import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from 'react-native-reanimated';
import { Pressable, type PressableProps, type StyleProp, type ViewStyle } from 'react-native';

interface Props extends Omit<PressableProps, 'style'> {
  children: React.ReactNode;
  scaleTo?: number;
  containerStyle?: StyleProp<ViewStyle>;
  style?: StyleProp<ViewStyle>;
}

const SPRING = { mass: 0.3, stiffness: 500, damping: 20 };

export function AnimatedPressable({
  children,
  scaleTo = 0.96,
  containerStyle,
  style,
  onPressIn,
  onPressOut,
  ...rest
}: Props) {
  const scale = useSharedValue(1);

  const animStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  return (
    <Animated.View style={[animStyle, containerStyle]}>
      <Pressable
        {...rest}
        style={style}
        onPressIn={(e) => {
          scale.value = withSpring(scaleTo, SPRING);
          onPressIn?.(e);
        }}
        onPressOut={(e) => {
          scale.value = withSpring(1, SPRING);
          onPressOut?.(e);
        }}
      >
        {children}
      </Pressable>
    </Animated.View>
  );
}
