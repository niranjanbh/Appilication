import { StyleSheet, Text, View, type ViewProps } from 'react-native';
import { colors, fontFamily, fontSize, fontWeight, spacing } from '../lib/design-tokens';

type StatColor = 'forest' | 'saffron';

interface StatProps extends ViewProps {
  numeral: string;
  caption: string;
  color?: StatColor;
}

export function Stat({ numeral, caption, color = 'forest', style, ...props }: StatProps) {
  const numeralColor = color === 'forest' ? colors.forest : colors.saffron;
  return (
    <View {...props} style={[styles.container, style]}>
      <Text style={[styles.numeral, { color: numeralColor }]}>{numeral}</Text>
      <Text style={styles.caption}>{caption}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing[1],
  },
  numeral: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h1,
    fontWeight: fontWeight.medium,
    lineHeight: fontSize.h1,
  },
  caption: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    lineHeight: fontSize.caption * 1.5,
  },
});
