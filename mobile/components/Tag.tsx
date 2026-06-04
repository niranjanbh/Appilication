import { StyleSheet, Text, View, type ViewProps } from 'react-native';
import { colors, fontFamily, fontSize, fontWeight, borderRadius, spacing } from '../lib/design-tokens';

type TagVariant = 'sage' | 'saffron' | 'terracotta' | 'forest';

interface TagProps extends ViewProps {
  variant?: TagVariant;
  label: string;
}

const tagStyles: Record<TagVariant, { bg: string; text: string }> = {
  sage:       { bg: `${colors.sage}33`,       text: colors.forest },
  saffron:    { bg: `${colors.saffron}33`,    text: colors.forest },
  terracotta: { bg: `${colors.terracotta}33`, text: colors.terracotta },
  forest:     { bg: colors.forest,            text: colors.ivory },
};

export function Tag({ variant = 'forest', label, style, ...props }: TagProps) {
  const { bg, text } = tagStyles[variant];
  return (
    <View {...props} style={[styles.container, { backgroundColor: bg }, style]}>
      <Text style={[styles.label, { color: text }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1],
    borderRadius: borderRadius.sm,
    alignSelf: 'flex-start',
  },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    fontWeight: fontWeight.medium,
  },
});
