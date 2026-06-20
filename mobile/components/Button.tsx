import { ActivityIndicator, Pressable, StyleSheet, Text, type PressableProps } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { borderRadius, colors, fontFamily, fontSize, fontWeight, spacing, withAlpha } from '../lib/design-tokens';

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
    boxShadow: `0 4px 12px ${withAlpha(colors.forest, 0.25)}`,
  },
  forestPressed: { backgroundColor: colors.jade },
  forestLabel:   { color: colors.ivory },

  // Navy (alias → forest for warm theme back-compat)
  navy: {
    backgroundColor: colors.forest,
    boxShadow: `0 4px 12px ${withAlpha(colors.forest, 0.25)}`,
  },
  navyPressed: { backgroundColor: colors.jade },
  navyLabel:   { color: colors.ivory },

  // Saffron
  saffron: {
    backgroundColor: colors.saffron,
    boxShadow: `0 4px 12px ${withAlpha(colors.saffron, 0.20)}`,
  },
  saffronPressed: { backgroundColor: colors.saffron },
  saffronLabel:   { color: colors.forest },

  // Outline
  outline: {
    backgroundColor: 'transparent',
    borderWidth: 1.5,
    borderColor: colors.forest,
  },
  outlinePressed: { backgroundColor: withAlpha(colors.forest, 0.06) },
  outlineLabel:   { color: colors.forest },

  // Ghost
  ghost: {
    backgroundColor: 'transparent',
  },
  ghostPressed: { backgroundColor: withAlpha(colors.forest, 0.06) },
  ghostLabel:   { color: colors.forest },
});
