import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { colors, fontSize, fontWeight } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';

interface HeaderBellProps {
  unreadCount?: number;
}

export function HeaderBell({ unreadCount = 0 }: HeaderBellProps) {
  const t = useTheme();
  const router = useRouter();

  return (
    <Pressable
      onPress={() => router.push('/(tabs)/notifications' as Parameters<typeof router.push>[0])}
      accessibilityLabel={unreadCount > 0 ? `${unreadCount} unread notifications` : 'Notifications'}
      style={styles.button}
    >
      <Ionicons
        name={unreadCount > 0 ? 'notifications' : 'notifications-outline'}
        size={22}
        color={t.text}
      />
      {unreadCount > 0 && (
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{unreadCount > 9 ? '9+' : unreadCount}</Text>
        </View>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    width: 36,
    height: 36,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badge: {
    position: 'absolute',
    top: 2,
    right: 2,
    minWidth: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: colors.saffron,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 4,
  },
  badgeText: {
    fontSize: fontSize.xs - 2,
    fontWeight: fontWeight.semibold,
    color: colors.ivoryText,
  },
});
