import { Ionicons } from '@expo/vector-icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import {
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useThemePreference } from '../../lib/theme-context';

import {
  listNotificationsApi,
  markAllNotificationsReadApi,
  markNotificationReadApi,
} from '../../lib/api/notifications';
import { AmbientBackground } from '../../components/ui/AmbientBackground';
import { EmptyState } from '../../components/ui/EmptyState';
import { GlassCard } from '../../components/ui/GlassCard';
import { TAB_DOCK_CLEARANCE } from '../../components/ui/GlassTabBar';
import { HapticPressable } from '../../components/ui/HapticPressable';
import { SkeletonCards } from '../../components/ui/Skeleton';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';
import type { Notification } from '../../types/notifications';

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

const TEMPLATE_ICON: Record<string, IoniconName> = {
  appointment_confirmation:  'calendar-outline',
  appointment_reminder:      'alarm-outline',
  lab_result_ready:          'flask-outline',
  pre_consult_report_ready:  'clipboard-outline',
  medication_reminder:       'medical-outline',
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
  const icon     = TEMPLATE_ICON[item.template_name] ?? 'notifications-outline';
  const sentDate = new Date(item.sent_at);
  const timeLabel = sentDate.toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  });

  const unreadWash = isDark ? colors.navyMid + '40' : colors.iceBlue;
  const titleClr   = isDark ? colors.white     : colors.navyDeep;
  const bodyClr    = isDark ? colors.slateText : colors.coolGray;
  const iconClr    = isUnread ? colors.electricBlue : bodyClr;

  return (
    <HapticPressable
      haptic="selection"
      scaleTo={0.98}
      onPress={() => onPress(item)}
      accessibilityLabel={`${item.title}. ${isUnread ? 'Unread.' : 'Read.'} ${item.body}`}
      accessibilityRole="button"
    >
      <GlassCard unpadded strong={isUnread}>
        <View style={[styles.row, isUnread && { backgroundColor: unreadWash }]}>
          <View style={[styles.iconBubble, { backgroundColor: isDark ? colors.nightElev : colors.skyMist }]}>
            <Ionicons name={icon} size={20} color={iconClr} />
            {isUnread && (
              <View style={styles.unreadDot} />
            )}
          </View>
          <View style={styles.rowContent}>
            <Text style={[styles.rowTitle, { color: titleClr, fontWeight: isUnread ? '700' : '500' }]} numberOfLines={1}>
              {item.title}
            </Text>
            <Text style={[styles.rowBody, { color: bodyClr }]} numberOfLines={2}>{item.body}</Text>
            <Text style={[styles.rowTime, { color: bodyClr }]}>{timeLabel}</Text>
          </View>
        </View>
      </GlassCard>
    </HapticPressable>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function NotificationsScreen() {
  const queryClient = useQueryClient();
  const router      = useRouter();
  const isDark      = useThemePreference().colorScheme === 'dark';
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
      <View style={[styles.container, { backgroundColor: bg }]}>
        <AmbientBackground />
        <View style={styles.list}>
          <SkeletonCards count={4} />
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: bg }]}>
      <AmbientBackground />

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
          <EmptyState
            icon="notifications-outline"
            tint="blue"
            title="No notifications yet"
            body="Appointment confirmations, lab results, and reminders will appear here."
          />
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

  list: {
    padding: spacing[4],
    paddingBottom: TAB_DOCK_CLEARANCE,
    gap: spacing[2],
  },

  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    padding: spacing[4],
    gap: spacing[3],
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
  unreadDot: {
    position: 'absolute',
    top: 0,
    right: 0,
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.electricBlue,
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

  emptyContainer: { flexGrow: 1, justifyContent: 'center' },
});
