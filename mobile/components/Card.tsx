import { StyleSheet, View, type ViewProps } from 'react-native';
import { colors, borderRadius, spacing } from '../lib/design-tokens';

type CardVariant = 'white' | 'ivory';

interface CardProps extends ViewProps {
  variant?: CardVariant;
}

export function Card({ variant = 'white', style, children, ...props }: CardProps) {
  return (
    <View
      {...props}
      style={[styles.base, styles[variant], style]}
    >
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  base: {
    borderRadius: borderRadius.md,
    padding: spacing[6],
    shadowColor: colors.ink,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
  },
  white: { backgroundColor: colors.white },
  ivory: { backgroundColor: colors.ivory },
});
