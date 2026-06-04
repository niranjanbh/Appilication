import { ActivityIndicator, Pressable, StyleSheet, Text, type PressableProps } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { borderRadius, colors, fontFamily, fontSize, fontWeight, spacing } from '../lib/design-tokens';

type ButtonVariant = 'forest' | 'saffron' | 'outline' | 'ghost' | 'navy';

interface ButtonProps extends PressableProps {
  variant?: ButtonVariant;
  label: string;
  isLoading?: boolean;
}

const SPRING = { mass: 0.3, stiffness: 500, damping: 20 };

export function Button({ variant = 'forest', label, style, isLoading, disabled, ...props }: ButtonProps) {
  const scale = useSharedValue(1);
  const anim  = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));

  return (
    <Animated.View style={anim}>
      <Pressable
        {...props}
        disabled={disabled ?? isLoading}
        onPressIn={(e) => {
          scale.value = withSpring(0.97, SPRING);
          props.onPressIn?.(e);
        }}
        onPressOut={(e) => {
          scale.value = withSpring(1, SPRING);
          props.onPressOut?.(e);
        }}
        style={({ pressed }) => [
          styles.base,
          styles[variant],
          pressed && styles[`${variant}Pressed` as keyof typeof styles],
          (disabled ?? isLoading) && styles.muted,
          style as object,
        ]}
      >
        {isLoading ? (
          <ActivityIndicator
            size="small"
            color={variant === 'outline' || variant === 'ghost' ? colors.forest : colors.ivory}
          />
        ) : (
          <Text style={[styles.label, styles[`${variant}Label` as keyof typeof styles]]}>
            {label}
          </Text>
        )}
      </Pressable>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  base: {
    height: 56,
    paddingHorizontal: spacing[6],
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 12,
  },
  muted: { opacity: 0.55 },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    fontWeight: fontWeight.medium,
  },

  // Forest
  forest: {
    backgroundColor: colors.forest,
    shadowColor: colors.forest,
    shadowOpacity: 0.25,
    elevation: 4,
  },
  forestPressed: { backgroundColor: colors.jade },
  forestLabel:   { color: colors.ivory },

  // Navy (premium primary)
  navy: {
    backgroundColor: colors.navyDeep,
    shadowColor: colors.navyDeep,
    shadowOpacity: 0.30,
    elevation: 6,
  },
  navyPressed: { backgroundColor: colors.navyMid },
  navyLabel:   { color: colors.white },

  // Saffron
  saffron: {
    backgroundColor: colors.saffron,
    shadowColor: colors.saffron,
    shadowOpacity: 0.20,
    elevation: 3,
  },
  saffronPressed: { backgroundColor: colors.saffron },
  saffronLabel:   { color: colors.forest },

  // Outline
  outline: {
    backgroundColor: 'transparent',
    borderWidth: 1.5,
    borderColor: colors.navyDeep,
    shadowOpacity: 0,
    elevation: 0,
  },
  outlinePressed: { backgroundColor: `${colors.navyDeep}0E` },
  outlineLabel:   { color: colors.navyDeep },

  // Ghost
  ghost: {
    backgroundColor: 'transparent',
    shadowOpacity: 0,
    elevation: 0,
  },
  ghostPressed: { backgroundColor: `${colors.navyDeep}0E` },
  ghostLabel:   { color: colors.navyDeep },
});
