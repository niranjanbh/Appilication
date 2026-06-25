import { Ionicons } from '@expo/vector-icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import {
  Modal,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Alert } from '../../lib/ui/alert';
import { useThemePreference } from '../../lib/theme-context';
import { useTheme } from '../../lib/theme';

import { AmbientBackground } from '../../components/ui/AmbientBackground';
import { EmptyState } from '../../components/ui/EmptyState';
import { TAB_DOCK_CLEARANCE } from '../../components/ui/GlassTabBar';
import { HapticPressable } from '../../components/ui/HapticPressable';
import { SkeletonCards } from '../../components/ui/Skeleton';
import {
  createReminderApi,
  deleteReminderApi,
  getDailySummaryApi,
  getWeekSummaryApi,
  listRemindersApi,
  logAdherenceApi,
  updateReminderApi,
} from '../../lib/api/reminders';
import {
  addNotificationResponseListener,
  cancelReminderNotifications,
  registerNotificationCategories,
  requestNotificationPermissions,
  scheduleReminderNotification,
  scheduleRepeatingReminder,
} from '../../lib/native/notifications';
import { borderRadius, colors, fontFamily, fontSize, spacing, withAlpha } from '../../lib/design-tokens';
import { ReminderList } from '../../components/reminders/ReminderList';
import { ReminderFormModal } from '../../components/reminders/ReminderFormModal';
import type { AdherenceAction, Reminder, ReminderAction, ReminderCreate } from '../../types/wellness';


function formatCronTime(cron: string): string {
  const parts = cron.split(' ');
  const h24 = parseInt(parts[1] ?? '8', 10);
  const min = (parts[0] ?? '0').padStart(2, '0');
  const ampm = h24 >= 12 ? 'PM' : 'AM';
  const h12 = h24 % 12 === 0 ? 12 : h24 % 12;
  return `${h12}:${min} ${ampm}`;
}

function formatCronFreq(intervalMinutes: number | null, cron: string | null): string {
  if (intervalMinutes) return `Every ${intervalMinutes} min`;
  if (cron) return 'Every day';
  return 'As needed';
}

function todayScheduledAt(cron: string | null): string {
  if (!cron) return new Date().toISOString();
  const parts = cron.split(' ');
  const hour = parseInt(parts[1] ?? '0', 10);
  const minute = parseInt(parts[0] ?? '0', 10);
  if (isNaN(hour) || isNaN(minute)) return new Date().toISOString();
  const d = new Date();
  d.setHours(hour, minute, 0, 0);
  return d.toISOString();
}


// ── Adherence dialog ──────────────────────────────────────────────────────────

interface AdherenceDialogProps {
  visible: boolean;
  reminderId: string;
  scheduledAt: string;
  label: string;
  onLog: (reminderId: string, scheduledAt: string, action: AdherenceAction) => void;
  onClose: () => void;
  isDark: boolean;
}

function AdherenceDialog({ visible, reminderId, scheduledAt, label, onLog, onClose, isDark }: AdherenceDialogProps) {
  const sheetBg = isDark ? colors.forestSurface : colors.white;
  const textPri = isDark ? colors.ivoryText     : colors.ink;
  const textSub = isDark ? colors.stoneDim      : colors.stone;

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={ad.overlay}>
        <View style={[ad.sheet, { backgroundColor: sheetBg }]}>
          <View style={ad.handle} />
          <Text style={[ad.title, { color: textPri }]}>{label}</Text>
          <Text style={[ad.sub, { color: textSub }]}>Did you take this?</Text>
          {(
            [
              { action: 'taken'   as AdherenceAction, label: '✓  Taken',      bg: colors.jade,                                    border: undefined },
              { action: 'skipped' as AdherenceAction, label: 'Skip',           bg: isDark ? colors.forestSurfaceRaised : colors.borderLight, border: undefined },
              { action: 'snoozed' as AdherenceAction, label: 'Snooze 15 min', bg: colors.saffron + '25',                           border: colors.saffron },
            ]
          ).map(({ action, label: btnLabel, bg, border }) => (
            <Pressable
              key={action}
              style={[ad.btn, { backgroundColor: bg, borderColor: border, borderWidth: border ? 1 : 0 }]}
              onPress={() => onLog(reminderId, scheduledAt, action)}
              accessibilityLabel={btnLabel}
            >
              <Text style={[ad.btnText, { color: action === 'taken' ? colors.white : textPri }]}>{btnLabel}</Text>
            </Pressable>
          ))}
          <Pressable onPress={onClose} accessibilityLabel="Dismiss">
            <Text style={[ad.dismiss, { color: textSub }]}>Dismiss</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const ad = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.45)', justifyContent: 'flex-end' },
  sheet: {
    borderTopLeftRadius: borderRadius.xxl,
    borderTopRightRadius: borderRadius.xxl,
    padding: spacing[6],
    gap: spacing[3],
    paddingBottom: spacing[10],
  },
  handle: { width: 36, height: 4, backgroundColor: colors.borderLight, borderRadius: 2, alignSelf: 'center', marginBottom: spacing[2] },
  title:   { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700', textAlign: 'center' },
  sub:     { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center' },
  btn:     { height: 52, borderRadius: borderRadius.xxl, alignItems: 'center', justifyContent: 'center' },
  btnText: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600' },
  dismiss: { fontFamily: fontFamily.body, fontSize: fontSize.caption, textAlign: 'center', paddingTop: spacing[2] },
});

// ── Main screen ───────────────────────────────────────────────────────────────

export default function RemindersScreen() {
  const qc     = useQueryClient();
  const router = useRouter();
  const t      = useTheme();
  const isDark = useThemePreference().colorScheme === 'dark';
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedDate, setSelectedDate] = useState(() => new Date());
  const [adherenceState, setAdherenceState] = useState<{
    visible: boolean; reminderId: string; scheduledAt: string; label: string;
  }>({ visible: false, reminderId: '', scheduledAt: '', label: '' });

  const notifListenerRef = useRef<{ remove: () => void } | null>(null);
  const remindersRef = useRef<Reminder[]>([]);

  useEffect(() => {
    registerNotificationCategories();
    requestNotificationPermissions();
    notifListenerRef.current = addNotificationResponseListener(
      (reminderId, scheduledAt, action) => {
        if (action === 'taken' || action === 'skipped') {
          logMutation.mutate({ reminderId, scheduledAt, action });
        } else if (action === 'snoozed') {
          logMutation.mutate({ reminderId, scheduledAt, action });
          const reminder = remindersRef.current.find(r => r.id === reminderId);
          if (reminder) {
            const snoozeAt = new Date(Date.now() + 15 * 60_000);
            void scheduleReminderNotification(reminderId, reminder.label, snoozeAt);
          }
        } else {
          const reminder = remindersRef.current.find(r => r.id === reminderId);
          setAdherenceState({ visible: true, reminderId, scheduledAt, label: reminder?.label ?? 'Reminder' });
        }
      },
    );
    return () => { notifListenerRef.current?.remove(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const remindersQuery = useQuery({ queryKey: ['reminders'], queryFn: listRemindersApi, staleTime: 60_000 });
  useEffect(() => {
    remindersRef.current = remindersQuery.data?.reminders ?? [];
  }, [remindersQuery.data]);
  const selectedIso = `${selectedDate.getFullYear()}-${String(selectedDate.getMonth() + 1).padStart(2, '0')}-${String(selectedDate.getDate()).padStart(2, '0')}`;
  const summaryQuery = useQuery({ queryKey: ['daily-summary', selectedIso], queryFn: () => getDailySummaryApi(selectedIso), staleTime: 60_000 });
  const weekSunday = new Date(selectedDate);
  weekSunday.setDate(weekSunday.getDate() - weekSunday.getDay());
  const weekStartIso = `${weekSunday.getFullYear()}-${String(weekSunday.getMonth() + 1).padStart(2, '0')}-${String(weekSunday.getDate()).padStart(2, '0')}`;
  const weekQuery = useQuery({ queryKey: ['week-summary', weekStartIso], queryFn: () => getWeekSummaryApi(weekStartIso), staleTime: 60_000 });

  function invalidateAll() {
    qc.invalidateQueries({ queryKey: ['reminders'] });
    qc.invalidateQueries({ queryKey: ['daily-summary'] });
    qc.invalidateQueries({ queryKey: ['week-summary'] });
  }

  function onRefresh() {
    remindersQuery.refetch();
    summaryQuery.refetch();
    weekQuery.refetch();
  }

  const refreshing = remindersQuery.isFetching && !remindersQuery.isLoading;

  const createMutation = useMutation({
    mutationFn: createReminderApi,
    onSuccess: async (reminder) => {
      invalidateAll();
      // Repeating trigger: fires today if the time is still ahead, else the
      // next occurrence, then daily/interval thereafter.
      if (reminder.active) await scheduleRepeatingReminder(reminder);
      setModalVisible(false);
    },
    onError: () => Alert.alert('Error', 'Could not create reminder. Please try again.'),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      updateReminderApi(id, { active }),
    onSuccess: async (reminder) => {
      invalidateAll();
      if (reminder.active) await scheduleRepeatingReminder(reminder);
      else await cancelReminderNotifications(reminder.id);
    },
    onError: () => Alert.alert('Error', 'Could not update reminder.'),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteReminderApi,
    onSuccess: (_data, id) => { invalidateAll(); void cancelReminderNotifications(id); },
    onError: () => Alert.alert('Error', 'Could not delete reminder.'),
  });

  const logMutation = useMutation({
    mutationFn: ({ reminderId, scheduledAt, action }: { reminderId: string; scheduledAt: string; action: ReminderAction }) =>
      logAdherenceApi(reminderId, { scheduled_at: scheduledAt, action }),
    onSuccess: () => { invalidateAll(); setAdherenceState(s => ({ ...s, visible: false })); },
    onError: () => Alert.alert('Error', 'Could not log adherence.'),
  });

  function handleSave(payload: ReminderCreate) {
    createMutation.mutate(payload);
  }

  function openDetail(r: Reminder) { router.push(`/reminders/${r.id}`); }
  function openCreate()             { setModalVisible(true); }
  function handleToggle(r: Reminder) {
    toggleMutation.mutate({ id: r.id, active: !r.active });
  }
  function confirmDelete(r: Reminder) {
    const time = r.schedule_cron ? formatCronTime(r.schedule_cron) : null;
    const subtitle = [
      r.label,
      [formatCronFreq(r.schedule_interval_minutes ?? null, r.schedule_cron), time].filter(Boolean).join(' at '),
    ].filter(Boolean).join('\n');
    Alert.alert('Delete Reminder?', subtitle, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: () => deleteMutation.mutate(r.id) },
    ]);
  }
  function handleTakeNow(r: Reminder) {
    const scheduledAt = todayScheduledAt(r.schedule_cron);
    logMutation.mutate({ reminderId: r.id, scheduledAt, action: 'taken' as ReminderAction });
  }
  async function handleAdherenceLog(reminderId: string, scheduledAt: string, action: AdherenceAction) {
    logMutation.mutate({ reminderId, scheduledAt, action: action as ReminderAction });
    if (action === 'snoozed') {
      const reminder = remindersRef.current.find(r => r.id === reminderId);
      if (reminder) {
        const snoozeAt = new Date(Date.now() + 15 * 60_000);
        await scheduleReminderNotification(reminderId, reminder.label, snoozeAt);
      }
    }
  }

  const bg = isDark ? colors.forestInk : colors.ivory;

  if (remindersQuery.isLoading) {
    return (
      <View style={[styles.container, { backgroundColor: bg }]}>
        <AmbientBackground />
        <View style={styles.list}>
          <SkeletonCards count={3} />
        </View>
      </View>
    );
  }

  const reminders = remindersQuery.data?.reminders ?? [];

  return (
    <View style={[styles.container, { backgroundColor: bg }]}>
      <AmbientBackground />
      {reminders.length === 0 ? (
        <View style={styles.emptyState}>
          <EmptyState
            icon="alarm-outline"
            tint="amber"
            title="No reminders yet"
            body="Set up water intake, medication, or supplement reminders and track your adherence."
            ctaLabel="Create reminder"
            onCtaPress={openCreate}
          />
        </View>
      ) : (
        <>
          <ReminderList
            reminders={reminders}
            selectedDate={selectedDate}
            onDateChange={setSelectedDate}
            onEdit={openDetail}
            onDelete={confirmDelete}
            onToggle={handleToggle}
            onTakeNow={handleTakeNow}
            dailySummary={summaryQuery.data ?? null}
            weekSummary={weekQuery.data?.days ?? null}
            refreshControl={
              <RefreshControl
                refreshing={refreshing}
                onRefresh={onRefresh}
                tintColor={t.primary}
              />
            }
          />
          <HapticPressable
            haptic="medium"
            containerStyle={styles.fab}
            style={styles.fabBtn}
            onPress={openCreate}
            accessibilityLabel="Add reminder"
          >
            <Ionicons name="add" size={28} color={colors.white} />
          </HapticPressable>
        </>
      )}

      <ReminderFormModal
        visible={modalVisible}
        editing={null}
        onClose={() => setModalVisible(false)}
        onSave={handleSave}
        isSaving={createMutation.isPending}
        isDark={isDark}
      />

      <AdherenceDialog
        visible={adherenceState.visible}
        reminderId={adherenceState.reminderId}
        scheduledAt={adherenceState.scheduledAt}
        label={adherenceState.label}
        onLog={handleAdherenceLog}
        onClose={() => setAdherenceState(s => ({ ...s, visible: false }))}
        isDark={isDark}
      />
    </View>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1 },

  list: {
    paddingHorizontal: spacing[4],
    paddingTop: spacing[4],
    paddingBottom: TAB_DOCK_CLEARANCE + 72,
  },

  card: {
    padding: spacing[4],
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
  },
  reminderContent: { flex: 1 },
  reminderLabel: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600' },
  reminderSub:   { fontFamily: fontFamily.body, fontSize: fontSize.caption, marginTop: 2 },
  adherenceBadge: {
    borderRadius: borderRadius.sm,
    paddingHorizontal: spacing[2],
    paddingVertical: 3,
    minWidth: 44,
    alignItems: 'center',
  },
  adherencePct: { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontWeight: '700' },
  actions:    { flexDirection: 'row', gap: spacing[1] },
  actionBtn:  { padding: spacing[1] },
  actionBtnText: { fontSize: 16 },

  fab: {
    position: 'absolute',
    bottom: TAB_DOCK_CLEARANCE - spacing[6],
    right: spacing[6],
  },
  fabBtn: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.saffron,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: `0 8px 16px ${withAlpha(colors.saffron, 0.35)}`,
  },

  emptyState: { flex: 1, justifyContent: 'center', paddingHorizontal: spacing[6] },
});
