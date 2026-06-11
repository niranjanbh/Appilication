import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';
import { borderRadius, fontFamily, fontSize, spacing, type TintName } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';
import { GlassCard } from './GlassCard';
import { HapticPressable } from './HapticPressable';
import { IconChip } from './IconChip';

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

interface EmptyStateProps {
  icon: IoniconName;
  title: string;
  /** Reassuring next-step copy — never leave a worried patient with a blank screen. */
  body: string;
  tint?: TintName;
  ctaLabel?: string;
  onCtaPress?: () => void;
}

export function EmptyState({ icon, title, body, tint = 'blue', ctaLabel, onCtaPress }: EmptyStateProps) {
  const t = useTheme();
  return (
    <GlassCard style={styles.card}>
      <View style={styles.inner}>
        <IconChip icon={icon} tint={tint} size={56} />
        <Text style={[styles.title, { color: t.text }]}>{title}</Text>
        <Text style={[styles.body, { color: t.textSub }]}>{body}</Text>
        {ctaLabel && onCtaPress ? (
          <HapticPressable
            onPress={onCtaPress}
            accessibilityLabel={ctaLabel}
            style={[styles.cta, { backgroundColor: t.primary }]}
          >
            <Text style={[styles.ctaText, { color: t.isDark ? t.background : t.surface }]}>{ctaLabel}</Text>
          </HapticPressable>
        ) : null}
      </View>
    </GlassCard>
  );
}

const styles = StyleSheet.create({
  card:  { marginTop: spacing[4] },
  inner: { alignItems: 'center', gap: spacing[3], paddingVertical: spacing[4] },
  title: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    fontWeight: '600',
    textAlign: 'center',
  },
  body: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    lineHeight: 21,
    textAlign: 'center',
    maxWidth: 280,
  },
  cta: {
    marginTop: spacing[2],
    paddingHorizontal: spacing[6],
    paddingVertical: spacing[3],
    borderRadius: borderRadius.full,
  },
  ctaText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
});
