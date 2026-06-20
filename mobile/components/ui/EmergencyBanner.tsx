import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, type PressableProps } from 'react-native';
import { borderRadius, colors, fontFamily, fontSize, fontWeight, spacing, withAlpha } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';

interface EmergencyBannerProps extends Omit<PressableProps, 'children'> {
  message: string;
  actionLabel?: string;
}

export function EmergencyBanner({ message, actionLabel, ...props }: EmergencyBannerProps) {
  const t = useTheme();

  return (
    <Pressable
      {...props}
      accessibilityRole="alert"
      accessibilityLabel={message}
      style={({ pressed }) => [
        styles.banner,
        {
          backgroundColor: t.isDark ? withAlpha(colors.alert, 0.15) : withAlpha(colors.alert, 0.08),
          borderColor: t.isDark ? withAlpha(colors.alertBright, 0.30) : withAlpha(colors.alert, 0.20),
          opacity: pressed ? 0.85 : 1,
        },
      ]}
    >
      <Ionicons name="warning" size={20} color={t.isDark ? colors.alertBright : colors.alert} />
      <Text style={[styles.message, { color: t.isDark ? colors.alertBright : colors.alert }]} numberOfLines={2}>
        {message}
      </Text>
      {actionLabel && (
        <Text style={[styles.action, { color: t.isDark ? colors.alertBright : colors.alert }]}>
          {actionLabel}
        </Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
    padding: spacing[3],
    borderRadius: borderRadius.lg,
    borderWidth: 1,
    marginHorizontal: spacing[4],
  },
  message: {
    flex: 1,
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: fontWeight.medium,
  },
  action: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: fontWeight.semibold,
  },
});
