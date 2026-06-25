import { Ionicons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback } from 'react';
import { listNotificationsApi } from '../../lib/api/notifications';
import { colors, fontSize, fontWeight } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';

export function HeaderBell() {
  const t = useTheme();
  const router = useRouter();

  // Fetch the unread count from the list endpoint (page_size=1 keeps the payload
  // tiny — we only need `unread_count`). Polls in the background and refetches on
  // screen focus so the badge stays current.
  const { data, refetch } = useQuery({
    queryKey: ['notifications', 'unread-count'],
    queryFn: () => listNotificationsApi({ page_size: 1, unread_only: true }),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });

  useFocusEffect(
    useCallback(() => {
      void refetch();
    }, [refetch]),
  );

  const unreadCount = data?.unread_count ?? 0;

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
