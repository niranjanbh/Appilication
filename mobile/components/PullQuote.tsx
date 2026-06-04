import { StyleSheet, Text, View, type ViewProps } from 'react-native';
import { colors, fontFamily, fontSize, spacing } from '../lib/design-tokens';

type PullQuoteAccent = 'terracotta' | 'saffron';

interface PullQuoteProps extends ViewProps {
  accent?: PullQuoteAccent;
  children: string;
}

export function PullQuote({ accent = 'terracotta', children, style, ...props }: PullQuoteProps) {
  const borderColor = accent === 'terracotta' ? colors.terracotta : colors.saffron;
  return (
    <View {...props} style={[styles.container, { borderLeftColor: borderColor }, style]}>
      <Text style={styles.text}>{children}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderLeftWidth: 4,
    paddingLeft: spacing[6],
    paddingVertical: spacing[1],
  },
  text: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h3,
    color: colors.forest,
    fontStyle: 'italic',
    lineHeight: fontSize.h3 * 1.3,
  },
});
