import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';
import { borderRadius, spacing } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';

interface NeumorphCardProps {
  children: React.ReactNode;
  unpadded?: boolean;
  inset?: boolean;
  style?: StyleProp<ViewStyle>;
}

export function NeumorphCard({ children, unpadded = false, inset = false, style }: NeumorphCardProps) {
  const t = useTheme();

  const nm = t.neumorph;
  const shadow = inset
    ? `inset 3px 3px 6px ${nm.shadowInsetA}, inset -3px -3px 6px ${nm.shadowInsetB}`
    : `6px 6px 14px ${nm.shadowRaise}, -6px -6px 14px ${nm.shadowLift}`;

  // Outer view carries the shadow (no overflow clip, or the neumorphic shadow is
  // cut off). Inner view clips content to the rounded corners.
  return (
    <View style={[styles.outer, { backgroundColor: nm.surface, boxShadow: shadow }, style]}>
      <View style={[styles.inner, !unpadded && styles.padded]}>
        {children}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  outer: {
    borderRadius: borderRadius.xxl,
  },
  inner: {
    borderRadius: borderRadius.xxl,
    overflow: 'hidden',
  },
  padded: { padding: spacing[5] },
});
