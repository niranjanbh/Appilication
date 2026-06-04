import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import {
  listNotificationsApi,
  markAllNotificationsReadApi,
  markNotificationReadApi,
} from '../../lib/api/notifications';
import {
  borderRadius,
  colors,
  fontFamily,
  fontSize,
  spacing,
} from '../../lib/design-tokens';
import type { Notification } from '../../types/notifications';

const TEMPLATE_ICON: Record<string, string> = {
  appointment_confirmation: '📅',
  appointment_reminder: '⏰',
  lab_result_ready: '🔬',
  pre_consult_report_ready: '📋',
  medication_reminder: '💊',
};

const SCREEN_ROUTE: Record<string, string> = {
  consultation: '/(tabs)/consultations',
  report: '/(tabs)/reports',
  pre_consult_report: '/(tabs)/consultations',
  reminders: '/(tabs)/reminders',
};

// ── Single notification row ───────────────────────────────────────────────────

interface NotificationRowProps {
  item: Notification;
  onPress: (item: Notification) => void;
}

function NotificationRow({ item, onPress }: NotificationRowProps) {
  const isUnread = item.read_at === null;
  const icon = TEMPLATE_ICON[item.template_name] ?? '🔔';
  const sentDate = new Date(item.sent_at);
  const timeLabel = sentDate.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <Pressable
      style={[styles.row, isUnread && styles.rowUnread]}
      onPress={() => onPress(item)}
      accessibilityLabel={`${item.title}. ${isUnread ? 'Unread.' : 'Read.'} ${item.body}`}
      accessibilityRole="button"
    >
      <View style={styles.iconContainer}>
        <Text style={styles.icon}>{icon}</Text>
        {isUnread && <View style={styles.unreadDot} />}
      </View>
      <View style={styles.rowContent}>
        <Text
          style={[styles.rowTitle, isUnread && styles.rowTitleUnread]}
          numberOfLines={1}
        >
          {item.title}
        </Text>
        <Text style={styles.rowBody} numberOfLines={2}>
          {item.body}
        </Text>
        <Text style={styles.rowTime}>{timeLabel}</Text>
      </View>
    </Pressable>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function NotificationsScreen() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const [page, setPage] = useState(1);

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['notifications', page],
    queryFn: () => listNotificationsApi({ page, page_size: 30 }),
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => markNotificationReadApi(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  const markAllMutation = useMutation({
    mutationFn: markAllNotificationsReadApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  function handlePress(item: Notification) {
    if (item.read_at === null) {
      markReadMutation.mutate(item.id);
    }
    const screen = item.data?.screen;
    if (screen && SCREEN_ROUTE[screen]) {
      router.push(SCREEN_ROUTE[screen] as never);
    }
  }

  const unreadCount = data?.unread_count ?? 0;

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.forest} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {unreadCount > 0 && (
        <View style={styles.toolbar}>
          <Text style={styles.unreadLabel}>
            {unreadCount} unread
          </Text>
          <Pressable
            onPress={() => markAllMutation.mutate()}
            disabled={markAllMutation.isPending}
            accessibilityLabel="Mark all notifications as read"
            accessibilityRole="button"
          >
            <Text style={styles.markAllText}>Mark all read</Text>
          </Pressable>
        </View>
      )}

      <FlatList
        data={data?.items ?? []}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <NotificationRow item={item} onPress={handlePress} />
        )}
        refreshControl={
          <RefreshControl
            refreshing={isFetching && !isLoading}
            onRefresh={refetch}
            tintColor={colors.forest}
          />
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyIcon}>🔔</Text>
            <Text style={styles.emptyTitle}>No notifications yet</Text>
            <Text style={styles.emptyBody}>
              You&#39;ll see appointment confirmations, lab results, and
              reminders here.
            </Text>
          </View>
        }
        contentContainerStyle={
          (data?.items ?? []).length === 0 ? styles.emptyContainer : undefined
        }
        onEndReached={() => {
          if (data && page < data.pages) setPage((p) => p + 1);
        }}
        onEndReachedThreshold={0.4}
      />
    </View>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.ivory,
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.ivory,
  },
  toolbar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    backgroundColor: colors.white,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E0D8',
  },
  unreadLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
  },
  markAllText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.jade,
    fontWeight: '600',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    backgroundColor: colors.white,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E0D8',
  },
  rowUnread: {
    backgroundColor: '#F0F7F4',
  },
  iconContainer: {
    width: 40,
    height: 40,
    borderRadius: borderRadius.full,
    backgroundColor: colors.ivory,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: spacing.md,
    position: 'relative',
    flexShrink: 0,
  },
  icon: {
    fontSize: 20,
  },
  unreadDot: {
    position: 'absolute',
    top: 0,
    right: 0,
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.saffron,
    borderWidth: 1.5,
    borderColor: colors.white,
  },
  rowContent: {
    flex: 1,
  },
  rowTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.stone,
    marginBottom: 2,
  },
  rowTitleUnread: {
    color: colors.ink,
    fontWeight: '600',
  },
  rowBody: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    lineHeight: fontSize.body * 1.5,
    marginBottom: 4,
  },
  rowTime: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
  },
  empty: {
    alignItems: 'center',
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.xl * 2,
  },
  emptyContainer: {
    flexGrow: 1,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: spacing.md,
  },
  emptyTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.h3,
    color: colors.ink,
    fontWeight: '600',
    marginBottom: spacing.sm,
    textAlign: 'center',
  },
  emptyBody: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    textAlign: 'center',
    lineHeight: fontSize.body * 1.6,
  },
});
