import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View, type PressableProps } from 'react-native';
import { borderRadius, colors, fontFamily, fontSize, fontWeight, shadow, spacing, withAlpha } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';

type CompletionTier = 'critical' | 'care' | 'enrichment';

interface CompletionCardProps extends Omit<PressableProps, 'children'> {
  tier: CompletionTier;
  title: string;
  description: string;
  icon?: React.ComponentProps<typeof Ionicons>['name'];
  locked?: boolean;
  completed?: boolean;
  accessibilityLabel?: string;
}

const TIER_CONFIG = {
  critical: {
    lightBg: colors.peachMist,
    darkBg:  'rgba(252,228,204,0.10)',
    accent:  colors.saffron,
    iconFallback: 'alert-circle-outline' as const,
  },
  care: {
    lightBg: colors.white,
    darkBg:  'rgba(255,255,255,0.05)',
    accent:  colors.forest,
    iconFallback: 'heart-outline' as const,
  },
  enrichment: {
    lightBg: withAlpha(colors.sage, 0.12),
    darkBg:  'rgba(143,168,142,0.08)',
    accent:  colors.sage,
    iconFallback: 'sparkles-outline' as const,
  },
};

export function CompletionCard({
  tier,
  title,
  description,
  icon,
  locked = false,
  completed = false,
  accessibilityLabel,
  ...props
}: CompletionCardProps) {
  const t = useTheme();
  const config = TIER_CONFIG[tier];
  const bg = t.isDark ? config.darkBg : config.lightBg;
  const iconName = icon ?? config.iconFallback;

  return (
    <Pressable
      {...props}
      disabled={locked}
      accessibilityLabel={accessibilityLabel ?? title}
      accessibilityState={{ disabled: locked }}
      style={({ pressed }) => [
        styles.card,
        {
          backgroundColor: bg,
          borderColor: t.isDark ? 'rgba(79,163,131,0.10)' : withAlpha(colors.forest, 0.06),
          boxShadow: t.isDark ? shadow.darkXs : shadow.sm,
          opacity: (locked || pressed) ? 0.7 : 1,
        },
      ]}
    >
      <View style={styles.row}>
        <View style={[styles.iconWrap, { backgroundColor: withAlpha(config.accent, 0.12) }]}>
          {locked ? (
            <Ionicons name="lock-closed" size={20} color={t.textSub} />
          ) : completed ? (
            <Ionicons name="checkmark-circle" size={20} color={t.success} />
          ) : (
            <Ionicons name={iconName} size={20} color={config.accent} />
          )}
        </View>
        <View style={styles.content}>
          <Text style={[styles.title, { color: locked ? t.textSub : t.text }]} numberOfLines={1}>
            {title}
          </Text>
          <Text style={[styles.desc, { color: t.textSub }]} numberOfLines={2}>
            {description}
          </Text>
        </View>
        {!locked && !completed && (
          <Ionicons name="chevron-forward" size={18} color={t.textSub} />
        )}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    padding: spacing[4],
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
  },
  iconWrap: {
    width: 40,
    height: 40,
    borderRadius: borderRadius.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  content: { flex: 1, gap: 2 },
  title: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: fontWeight.medium,
  },
  desc: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
  },
});
