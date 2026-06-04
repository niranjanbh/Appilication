import { Pressable, StyleSheet, Text, type PressableProps } from 'react-native';
import { colors, fontFamily, fontSize, fontWeight, borderRadius, spacing } from '../lib/design-tokens';

type ButtonVariant = 'forest' | 'saffron' | 'outline' | 'ghost';

interface ButtonProps extends PressableProps {
  variant?: ButtonVariant;
  label: string;
}

export function Button({ variant = 'forest', label, style, ...props }: ButtonProps) {
  return (
    <Pressable
      {...props}
      style={({ pressed }) => [
        styles.base,
        styles[variant],
        pressed && styles[`${variant}Pressed` as keyof typeof styles],
        style as object,
      ]}
    >
      <Text style={[styles.label, styles[`${variant}Label` as keyof typeof styles]]}>
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    paddingHorizontal: spacing[6],
    paddingVertical: spacing[3],
    borderRadius: borderRadius.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    fontWeight: fontWeight.medium,
  },
  // Forest
  forest: { backgroundColor: colors.forest },
  forestPressed: { backgroundColor: colors.jade },
  forestLabel: { color: colors.ivory },
  // Saffron
  saffron: { backgroundColor: colors.saffron },
  saffronPressed: { backgroundColor: colors.saffron },
  saffronLabel: { color: colors.forest },
  // Outline
  outline: { backgroundColor: 'transparent', borderWidth: 2, borderColor: colors.forest },
  outlinePressed: { backgroundColor: `${colors.forest}14` },
  outlineLabel: { color: colors.forest },
  // Ghost
  ghost: { backgroundColor: 'transparent' },
  ghostPressed: { backgroundColor: `${colors.forest}14` },
  ghostLabel: { color: colors.forest },
});
