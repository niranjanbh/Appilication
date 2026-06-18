import { useState } from 'react';
import { StyleSheet, Text, type StyleProp, type ViewStyle } from 'react-native';
import { borderRadius, fontFamily, fontSize, spacing } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';
import { HapticPressable } from './HapticPressable';

type HapticStrength = 'light' | 'medium' | 'selection';

interface SkeuButtonProps {
  label: string;
  onPress: () => void;
  color?: string;
  textColor?: string;
  haptic?: HapticStrength;
  disabled?: boolean;
  icon?: React.ReactNode;
  size?: 'sm' | 'md' | 'lg';
  style?: StyleProp<ViewStyle>;
  accessibilityLabel?: string;
}

export function SkeuButton({
  label,
  onPress,
  color,
  textColor,
  haptic = 'medium',
  disabled = false,
  icon,
  size = 'md',
  style,
  accessibilityLabel,
}: SkeuButtonProps) {
  const t = useTheme();
  const sk = t.skeu;
  const [pressed, setPressed] = useState(false);

  const bg = color ?? t.primary;
  const fg = textColor ?? '#FFFFFF';
  const height = size === 'sm' ? 36 : size === 'lg' ? 56 : 46;
  const textSize = size === 'sm' ? fontSize.sm : size === 'lg' ? fontSize.bodyLg : fontSize.body;

  const raisedShadow = `0 -1px 0 ${sk.highlight}, 0 2px 4px ${sk.shadow}, 0 4px 10px ${sk.shadow}`;
  const pressedShadow = `0 1px 0 ${sk.highlight}, inset 0 1px 3px ${sk.shadow}`;

  return (
    <HapticPressable
      haptic={haptic}
      scaleTo={0.97}
      onPress={onPress}
      onPressIn={() => setPressed(true)}
      onPressOut={() => setPressed(false)}
      disabled={disabled}
      accessibilityLabel={accessibilityLabel ?? label}
      style={[
        styles.btn,
        {
          height,
          backgroundColor: bg,
          borderColor: sk.edgeBorder,
          boxShadow: pressed ? pressedShadow : raisedShadow,
          opacity: disabled ? 0.5 : 1,
          transform: [{ translateY: pressed ? 1 : 0 }],
        },
        style,
      ]}
    >
      {icon}
      <Text style={[styles.label, { color: fg, fontSize: textSize }]}>{label}</Text>
    </HapticPressable>
  );
}

const styles = StyleSheet.create({
  btn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing[2],
    paddingHorizontal: spacing[5],
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    borderBottomWidth: 2,
  },
  label: {
    fontFamily: fontFamily.body,
    fontWeight: '700',
  },
});
