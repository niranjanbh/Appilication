import { StyleSheet, TextInput, View, type TextInputProps, type StyleProp, type ViewStyle } from 'react-native';
import { borderRadius, fontFamily, fontSize, spacing } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';

interface NeumorphInputProps extends TextInputProps {
  containerStyle?: StyleProp<ViewStyle>;
}

export function NeumorphInput({ containerStyle, style, ...rest }: NeumorphInputProps) {
  const t = useTheme();

  const nm = t.neumorph;
  const insetShadow = `inset 2px 2px 5px ${nm.shadowInsetA}, inset -2px -2px 5px ${nm.shadowInsetB}`;

  return (
    <View
      style={[
        styles.wrapper,
        { backgroundColor: nm.surface, boxShadow: insetShadow },
        containerStyle,
      ]}
    >
      <TextInput
        style={[styles.input, { color: t.text }, style]}
        placeholderTextColor={t.textSub}
        {...rest}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    borderRadius: borderRadius.lg,
    overflow: 'hidden',
  },
  input: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    padding: spacing[4],
    lineHeight: 22,
  },
});
