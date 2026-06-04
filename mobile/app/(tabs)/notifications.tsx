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
  useColorScheme,
  View,
} from 'react-native';

import {
  listNotificationsApi,
  markAllNotificationsReadApi,
  markNotificationReadApi,
} from '../../lib/api/notifications';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';
import type { Notification } from '../../types/notifications';

const TEMPLATE_ICON: Record<string, string> = {
  appointment_confirmation:  '📅',
  appointment_reminder:      '⏰',
  lab_result_ready:          '🔬',
  pre_consult_report_ready:  '📋',
  medication_reminder:       '💊',
};

const SCREEN_ROUTE: Record<string, string> = {
  consultation:      '/(tabs)/consultations',
  report:            '/(tabs)/reports',
  pre_consult_report:'/(tabs)/consultations',
  reminders:         '/(tabs)/reminders',
};

// ── Notification row ──────────────────────────────────────────────────────────

interface NotificationRowProps {
  item: Notification;
  onPress: (item: Notification) => void;
  isDark: boolean;
}

function NotificationRow({ item, onPress, isDark }: NotificationRowProps) {
  const isUnread = item.read_at === null;
  const icon     = TEMPLATE_ICON[item.template_name] ?? '🔔';
  const sentDate = new Date(item.sent_at);
  const timeLabel = sentDate.toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  });

  const rowBg    = isUnread
    ? (isDark ? colors.navyMid + '40' : colors.iceBlue)
    : (isDark ? colors.nightSurface   : colors.white);
  const rowBdr   = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)';
  const titleClr = isDark ? colors.white     : colors.navyDeep;
  const bodyClr  = isDark ? colors.slateText : colors.coolGray;

  return (
    <Pressable
      style={[styles.row, { backgroundColor: rowBg, borderColor: rowBdr }]}
      onPress={() => onPress(item)}
      accessibilityLabel={`${item.title}. ${isUnread ? 'Unread.' : 'Read.'} ${item.body}`}
      accessibilityRole="button"
    >
      <View style={[styles.iconBubble, { backgroundColor: isDark ? colors.nightElev : colors.skyMist }]}>
        <Text style={styles.iconEmoji}>{icon}</Text>
        {isUnread && (
          <View style={[styles.unreadDot, { borderColor: rowBg }]} />
        )}
      </View>
      <View style={styles.rowContent}>
        <Text style={[styles.rowTitle, { color: titleClr, fontWeight: isUnread ? '700' : '500' }]} numberOfLines={1}>
          {item.title}
        </Text>
        <Text style={[styles.rowBody, { color: bodyClr }]} numberOfLines={2}>{item.body}</Text>
        <Text style={[styles.rowTime, { color: bodyClr }]}>{timeLabel}</Text>
      </View>
    </Pressable>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function NotificationsScreen() {
  const queryClient = useQueryClient();
  const router      = useRouter();
  const isDark      = useColorScheme() === 'dark';
  const [page, setPage] = useState(1);

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['notifications', page],
    queryFn: () => listNotificationsApi({ page, page_size: 30 }),
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => markNotificationReadApi(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['notifications'] }); },
  });

  const markAllMutation = useMutation({
    mutationFn: markAllNotificationsReadApi,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['notifications'] }); },
  });

  function handlePress(item: Notification) {
    if (item.read_at === null) markReadMutation.mutate(item.id);
    const screen = item.data?.screen;
    if (screen && SCREEN_ROUTE[screen]) {
      router.push(SCREEN_ROUTE[screen] as never);
    }
  }

  const unreadCount = data?.unread_count ?? 0;
  const bg = isDark ? colors.midnight : colors.skyMist;

  if (isLoading) {
    return (
      <View style={[styles.centered, { backgroundColor: bg }]}>
        <ActivityIndicator size="large" color={colors.electricBlue} />
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: bg }]}>

      {/* Unread toolbar */}
      {unreadCount > 0 && (
        <View style={[styles.toolbar, {
          backgroundColor: isDark ? colors.nightSurface : colors.white,
          borderBottomColor: isDark ? 'rgba(255,255,255,0.07)' : colors.borderLight,
        }]}>
          <View style={[styles.unreadBadge, { backgroundColor: isDark ? colors.nightElev : colors.iceBlue }]}>
            <Text style={[styles.unreadCount, { color: colors.electricBlue }]}>{unreadCount}</Text>
            <Text style={[styles.unreadLabel, { color: isDark ? colors.slateText : colors.coolGray }]}>unread</Text>
          </View>
          <Pressable
            onPress={() => markAllMutation.mutate()}
            disabled={markAllMutation.isPending}
            accessibilityLabel="Mark all notifications as read"
          >
            <Text style={[styles.markAll, { color: colors.electricBlue }]}>Mark all read</Text>
          </Pressable>
        </View>
      )}

      <FlatList
        data={data?.items ?? []}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <NotificationRow item={item} onPress={handlePress} isDark={isDark} />
        )}
        refreshControl={
          <RefreshControl
            refreshing={isFetching && !isLoading}
            onRefresh={refetch}
            tintColor={colors.electricBlue}
          />
        }
        contentContainerStyle={[
          styles.list,
          (data?.items ?? []).length === 0 && styles.emptyContainer,
        ]}
        ItemSeparatorComponent={() => <View style={{ height: spacing[2] }} />}
        ListEmptyComponent={
          <View style={styles.empty}>
            <View style={[styles.emptyIconWrap, { backgroundColor: isDark ? colors.nightSurface : colors.white }]}>
              <Text style={styles.emptyIcon}>🔔</Text>
            </View>
            <Text style={[styles.emptyTitle, { color: isDark ? colors.white : colors.navyDeep }]}>
              No notifications yet
            </Text>
            <Text style={[styles.emptyBody, { color: isDark ? colors.slateText : colors.coolGray }]}>
              Appointment confirmations, lab results, and reminders will appear here.
            </Text>
          </View>
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
  container: { flex: 1 },
  centered:  { flex: 1, alignItems: 'center', justifyContent: 'center' },

  toolbar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing[6],
    paddingVertical: spacing[3],
    borderBottomWidth: 1,
  },
  unreadBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[1],
    borderRadius: borderRadius.full,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1],
  },
  unreadCount: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '700',
  },
  unreadLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
  },
  markAll: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },

  list: { padding: spacing[4], gap: spacing[2] },

  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    padding: spacing[4],
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    gap: spacing[3],
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.04,
    shadowRadius: 6,
    elevation: 1,
  },
  iconBubble: {
    width: 44,
    height: 44,
    borderRadius: borderRadius.xl,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    position: 'relative',
  },
  iconEmoji:  { fontSize: 20 },
  unreadDot: {
    position: 'absolute',
    top: 0,
    right: 0,
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.electricBlue,
    borderWidth: 2,
  },
  rowContent: { flex: 1, gap: 2 },
  rowTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
  },
  rowBody: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    lineHeight: 20,
  },
  rowTime: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    marginTop: 2,
  },

  emptyContainer: { flexGrow: 1 },
  empty: { alignItems: 'center', paddingHorizontal: spacing[6], paddingTop: spacing[16], gap: spacing[4] },
  emptyIconWrap: {
    width: 72,
    height: 72,
    borderRadius: 36,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 3,
  },
  emptyIcon:  { fontSize: 32 },
  emptyTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.h3,
    fontWeight: '700',
    textAlign: 'center',
  },
  emptyBody: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    textAlign: 'center',
    lineHeight: 22,
  },
});
