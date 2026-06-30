import { Ionicons } from '@expo/vector-icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Stack, useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import {
  ActivityIndicator,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Alert } from '../../lib/ui/alert';

import { AmbientBackground } from '../../components/ui/AmbientBackground';
import { IconChip } from '../../components/ui/IconChip';
import { ReminderFormModal } from '../../components/reminders/ReminderFormModal';
import {
  deleteReminderApi,
  deleteReminderImageApi,
  getReminderImageUrlApi,
  listRemindersApi,
  logAdherenceApi,
  updateReminderApi,
  uploadReminderImageApi,
} from '../../lib/api/reminders';
import {
  cancelReminderNotifications,
  scheduleReminderNotification,
  scheduleRepeatingReminder,
} from '../../lib/native/notifications';
import { pickReminderImageFromLibrary } from '../../lib/native/image-picker';
import { resolveReminderImage } from '../../lib/reminder-image';
import { borderRadius, colors, fontFamily, fontSize, spacing, withAlpha } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';
import { useThemePreference } from '../../lib/theme-context';
import type { DailySummary, Reminder, ReminderAction, ReminderCreate, ReminderType, WeekSummaryResponse } from '../../types/wellness';

function isoOf(dt: Date): string {
  return `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`;
}

const TYPE_LABEL: Record<ReminderType, string> = {
  water: 'Hydration',
  supplement: 'Supplement',
  medication: 'Medication',
  gym: 'Exercise',
  custom: 'Custom',
};

function formatScheduleTime(cron: string | null): string {
  if (!cron) return '';
  const parts = cron.split(' ');
  const h24 = parseInt(parts[1] ?? '0', 10);
  const min = (parts[0] ?? '0').padStart(2, '0');
  const ampm = h24 >= 12 ? 'PM' : 'AM';
  const h12 = h24 % 12 === 0 ? 12 : h24 % 12;
  return `${h12}:${min} ${ampm}`;
}

function formatFrequency(intervalMinutes: number | null, cron: string | null): string {
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

function metaStr(meta: Record<string, unknown> | null, key: string): string {
  const v = meta?.[key];
  return v === null || v === undefined ? '' : String(v);
}

function detailRows(r: Reminder): { label: string; value: string }[] {
  const meta = r.metadata ?? {};
  const rows: { label: string; value: string }[] = [];
  switch (r.type) {
    case 'water':
      if (meta.amount) rows.push({ label: 'Amount', value: `${meta.amount} ${meta.unit === 'ml' ? 'ml' : 'glasses'}` });
      break;
    case 'supplement':
    case 'medication':
      if (meta.dosage) rows.push({ label: 'Dosage', value: metaStr(meta, 'dosage') });
      rows.push({ label: 'With food', value: meta.with_food === true ? 'Yes' : 'No' });
      if (meta.instructions) rows.push({ label: 'Instructions', value: metaStr(meta, 'instructions') });
      break;
    case 'gym':
      if (meta.duration_minutes) rows.push({ label: 'Duration', value: `${meta.duration_minutes} min` });
      if (meta.activity) rows.push({ label: 'Activity', value: metaStr(meta, 'activity') });
      break;
    case 'custom':
      if (meta.notes) rows.push({ label: 'Note', value: metaStr(meta, 'notes') });
      break;
  }
  return rows;
}

function adherenceColor(rate: number): string {
  if (rate >= 0.9) return colors.jade;
  if (rate >= 0.7) return colors.saffron;
  return colors.terracotta;
}

export default function ReminderDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const t = useTheme();
  const isDark = useThemePreference().colorScheme === 'dark';
  const [editVisible, setEditVisible] = useState(false);

  const remindersQuery = useQuery({ queryKey: ['reminders'], queryFn: listRemindersApi, staleTime: 60_000 });
  const reminder = remindersQuery.data?.reminders.find(r => r.id === id) ?? null;

  function invalidateAll() {
    qc.invalidateQueries({ queryKey: ['reminders'] });
    qc.invalidateQueries({ queryKey: ['daily-summary'] });
    qc.invalidateQueries({ queryKey: ['week-summary'] });
  }

  const updateMutation = useMutation({
    mutationFn: ({ rid, payload }: { rid: string; payload: ReminderCreate }) => updateReminderApi(rid, payload),
    onSuccess: async (updated) => {
      invalidateAll();
      if (updated.active && updated.notification_channels.includes('push')) {
        await scheduleRepeatingReminder(updated);
      } else {
        await cancelReminderNotifications(updated.id);
      }
      setEditVisible(false);
    },
    onError: () => Alert.alert('Error', 'Could not update reminder.'),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ rid, active }: { rid: string; active: boolean }) => updateReminderApi(rid, { active }),
    onMutate: async ({ rid, active }) => {
      await qc.cancelQueries({ queryKey: ['reminders'] });
      const prev = qc.getQueryData<{ reminders: Reminder[]; total: number }>(['reminders']);
      if (prev) {
        qc.setQueryData<{ reminders: Reminder[]; total: number }>(['reminders'], {
          ...prev,
          reminders: prev.reminders.map(r => r.id === rid ? { ...r, active } : r),
        });
      }
      return { prev };
    },
    onError: (_err, _vars, context) => {
      if (context?.prev) qc.setQueryData(['reminders'], context.prev);
      Alert.alert('Error', 'Could not update reminder.');
    },
    onSuccess: async (updated) => {
      invalidateAll();
      if (updated.active && updated.notification_channels.includes('push')) {
        await scheduleRepeatingReminder(updated);
      } else {
        await cancelReminderNotifications(updated.id);
      }
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (rid: string) => deleteReminderApi(rid),
    onSuccess: (_data, rid) => {
      invalidateAll();
      void cancelReminderNotifications(rid);
      router.back();
    },
    onError: () => Alert.alert('Error', 'Could not delete reminder.'),
  });

  const logMutation = useMutation({
    mutationFn: ({ rid, scheduledAt, action }: { rid: string; scheduledAt: string; action: ReminderAction }) =>
      logAdherenceApi(rid, { scheduled_at: scheduledAt, action }),
    // Optimistically sync today's progress ring and week dots (the detail screen
    // always logs against today) so the tab is already up to date on back-nav.
    // adherence_rate is a 30-day server figure, so it's left to onSettled.
    onMutate: async ({ rid, action }) => {
      const now = new Date();
      const todayIso = isoOf(now);
      const sunday = new Date(now);
      sunday.setDate(sunday.getDate() - sunday.getDay());
      const dailyKey = ['daily-summary', todayIso];
      const weekKey = ['week-summary', isoOf(sunday)];
      await qc.cancelQueries({ queryKey: ['daily-summary'] });
      await qc.cancelQueries({ queryKey: ['week-summary'] });
      const prevDaily = qc.getQueryData<DailySummary>(dailyKey);
      const prevWeek = qc.getQueryData<WeekSummaryResponse>(weekKey);

      const resolves = action === 'taken' || action === 'skipped';
      const newlyTaken =
        action === 'taken' && !(prevDaily?.completed_reminder_ids.includes(rid) ?? false);

      if (prevDaily) {
        let nextDaily = prevDaily;
        if (resolves && !prevDaily.resolved_reminder_ids.includes(rid)) {
          nextDaily = { ...nextDaily, resolved_reminder_ids: [...nextDaily.resolved_reminder_ids, rid] };
        }
        if (newlyTaken) {
          nextDaily = {
            ...nextDaily,
            completed: Math.min(nextDaily.completed + 1, nextDaily.total),
            completed_reminder_ids: [...nextDaily.completed_reminder_ids, rid],
          };
        }
        if (nextDaily !== prevDaily) qc.setQueryData<DailySummary>(dailyKey, nextDaily);
      }
      if (prevWeek && newlyTaken) {
        qc.setQueryData<WeekSummaryResponse>(weekKey, {
          days: prevWeek.days.map(d =>
            d.date === todayIso ? { ...d, completed: Math.min(d.completed + 1, d.total) } : d,
          ),
        });
      }
      return { prevDaily, prevWeek, dailyKey, weekKey };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prevDaily) qc.setQueryData(ctx.dailyKey, ctx.prevDaily);
      if (ctx?.prevWeek) qc.setQueryData(ctx.weekKey, ctx.prevWeek);
      Alert.alert('Error', 'Could not log adherence.');
    },
    onSettled: () => invalidateAll(),
  });

  // ── Image (custom photo or doctor catalog image) ──────────────────────────────
  const meta = reminder?.metadata ?? {};
  const hasPhoto = !!(meta.image_key || meta.catalog_id);

  const imageUrlQuery = useQuery({
    queryKey: ['reminder-image', id],
    queryFn: () => getReminderImageUrlApi(id),
    enabled: !!id && hasPhoto,
    staleTime: 5 * 60_000,
  });

  function invalidateImage() {
    qc.invalidateQueries({ queryKey: ['reminders'] });
    // The image query is disabled once the photo is removed, so invalidate would
    // skip it and leave the stale signed URL cached. Remove it outright instead.
    qc.removeQueries({ queryKey: ['reminder-image', id] });
  }

  const uploadImageMutation = useMutation({
    mutationFn: (img: { uri: string; mimeType: string; fileName: string; fileSize: number | null }) =>
      uploadReminderImageApi(id, img),
    onSuccess: invalidateImage,
    onError: () => Alert.alert('Upload failed', 'Could not upload the photo. Please try again.'),
  });

  const removeImageMutation = useMutation({
    mutationFn: () => deleteReminderImageApi(id),
    onSuccess: invalidateImage,
    onError: () => Alert.alert('Error', 'Could not remove the photo.'),
  });

  async function handlePickImage() {
    const picked = await pickReminderImageFromLibrary();
    if (picked) uploadImageMutation.mutate(picked);
  }

  function handleSave(payload: ReminderCreate, editing: Reminder | null) {
    if (editing) updateMutation.mutate({ rid: editing.id, payload });
  }

  function handleTaken() {
    if (!reminder) return;
    const scheduledAt = todayScheduledAt(reminder.schedule_cron);
    logMutation.mutate({ rid: reminder.id, scheduledAt, action: 'taken' });
  }

  async function handleSnooze() {
    if (!reminder) return;
    const scheduledAt = todayScheduledAt(reminder.schedule_cron);
    logMutation.mutate({ rid: reminder.id, scheduledAt, action: 'snoozed' });
    const snoozeAt = new Date(Date.now() + 15 * 60_000);
    await scheduleReminderNotification(reminder.id, reminder.label, snoozeAt);
  }

  function confirmDelete() {
    if (!reminder) return;
    Alert.alert('Delete reminder?', reminder.label, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: () => deleteMutation.mutate(reminder.id) },
    ]);
  }

  const bg = isDark ? colors.forestInk : colors.ivory;

  if (remindersQuery.isLoading) {
    return (
      <View style={[s.center, { backgroundColor: bg }]}>
        <Stack.Screen options={{ title: 'Reminder' }} />
        <ActivityIndicator color={t.primary} />
      </View>
    );
  }

  if (!reminder) {
    return (
      <View style={[s.center, { backgroundColor: bg }]}>
        <Stack.Screen options={{ title: 'Reminder' }} />
        <Ionicons name="alarm-outline" size={36} color={t.textSub} />
        <Text style={[s.missing, { color: t.textSub }]}>This reminder no longer exists.</Text>
        <Pressable onPress={() => router.back()} accessibilityLabel="Go back">
          <Text style={[s.missingLink, { color: t.primary }]}>Go back</Text>
        </Pressable>
      </View>
    );
  }

  const image = resolveReminderImage(reminder);
  const photoUri = imageUrlQuery.data?.url;
  const hasCustomPhoto = !!reminder.metadata?.image_key;
  const uploadingPhoto = uploadImageMutation.isPending;
  const time = formatScheduleTime(reminder.schedule_cron);
  const freq = formatFrequency(reminder.schedule_interval_minutes ?? null, reminder.schedule_cron);
  const rows = detailRows(reminder);
  const adherencePct = Math.round(reminder.adherence_rate * 100);
  const prescribed = reminder.source_type === 'prescription';

  return (
    <View style={[s.container, { backgroundColor: bg }]}>
      <AmbientBackground />
      <Stack.Screen
        options={{
          title: '',
          // Doctor-prescribed reminders are read-only to the patient — no Edit affordance.
          headerRight: prescribed
            ? undefined
            : () => (
                <Pressable onPress={() => setEditVisible(true)} hitSlop={8} accessibilityLabel="Edit reminder">
                  <Text style={[s.editBtn, { color: t.primary }]}>Edit</Text>
                </Pressable>
              ),
        }}
      />

      <ScrollView contentContainerStyle={s.scroll} showsVerticalScrollIndicator={false}>
        {/* Image / illustration */}
        <View style={[s.imageWrap, { backgroundColor: t.surface }]}>
          {photoUri ? (
            <Image source={{ uri: photoUri }} style={s.image} resizeMode="cover" accessibilityLabel={`${reminder.label} image`} />
          ) : (
            <IconChip icon={image.icon} tint={image.tint} size={96} />
          )}
          {uploadingPhoto && (
            <View style={s.imageOverlay}>
              <ActivityIndicator color={colors.white} />
            </View>
          )}
        </View>

        {/* Photo controls (patient custom photo) */}
        <View style={s.photoControls}>
          <Pressable
            style={s.photoBtn}
            onPress={handlePickImage}
            disabled={uploadingPhoto}
            accessibilityLabel={photoUri ? 'Change photo' : 'Add photo'}
          >
            <Ionicons name="camera-outline" size={16} color={t.primary} />
            <Text style={[s.photoBtnText, { color: t.primary }]}>
              {hasCustomPhoto ? 'Change photo' : photoUri ? 'Use my photo' : 'Add photo'}
            </Text>
          </Pressable>
          {hasCustomPhoto && (
            <Pressable
              style={s.photoBtn}
              onPress={() => removeImageMutation.mutate()}
              disabled={removeImageMutation.isPending}
              accessibilityLabel="Remove photo"
            >
              <Ionicons name="trash-outline" size={16} color={colors.terracotta} />
              <Text style={[s.photoBtnText, { color: colors.terracotta }]}>Remove</Text>
            </Pressable>
          )}
        </View>

        {/* Title */}
        <Text style={[s.title, { color: t.text }]}>{reminder.label}</Text>
        <View style={s.subRow}>
          <Text style={[s.subtitle, { color: t.textSub }]}>{TYPE_LABEL[reminder.type]}</Text>
          {prescribed ? (
            <View style={[s.rxBadge, { backgroundColor: withAlpha(colors.jade, isDark ? 0.2 : 0.1) }]}>
              <Text style={[s.rxText, { color: isDark ? colors.jadeGlow : colors.jade }]}>Doctor prescribed</Text>
            </View>
          ) : (
            <View style={[s.rxBadge, { backgroundColor: withAlpha(colors.stone, 0.15) }]}>
              <Text style={[s.rxText, { color: t.textSub }]}>Personal</Text>
            </View>
          )}
          {!reminder.active && (
            <View style={[s.rxBadge, { backgroundColor: withAlpha(colors.stone, 0.15) }]}>
              <Text style={[s.rxText, { color: t.textSub }]}>Paused</Text>
            </View>
          )}
        </View>

        {/* Schedule */}
        <View style={[s.card, { backgroundColor: t.surface }]}>
          <View style={s.cardRow}>
            <Ionicons name="time-outline" size={18} color={t.textSub} />
            <Text style={[s.cardRowText, { color: t.text }]}>
              {time ? `${time} · ${freq}` : freq}
            </Text>
          </View>
        </View>

        {/* Per-type details */}
        {rows.length > 0 && (
          <View style={[s.card, { backgroundColor: t.surface }]}>
            {rows.map((r, i) => (
              <View key={r.label} style={[s.detailRow, i > 0 && s.detailRowBorder, { borderTopColor: t.border }]}>
                <Text style={[s.detailLabel, { color: t.textSub }]}>{r.label}</Text>
                <Text style={[s.detailValue, { color: t.text }]}>{r.value}</Text>
              </View>
            ))}
          </View>
        )}

        {/* Adherence */}
        <View style={[s.card, { backgroundColor: t.surface }]}>
          <View style={s.cardRow}>
            <Ionicons name="stats-chart-outline" size={18} color={t.textSub} />
            <Text style={[s.cardRowText, { color: t.text }]}>Adherence</Text>
            <Text style={[s.adherencePct, { color: adherenceColor(reminder.adherence_rate) }]}>
              {adherencePct}%
            </Text>
          </View>
        </View>

        {/* Actions */}
        <View style={s.actions}>
          <Pressable
            style={[s.primaryBtn, { backgroundColor: colors.jade }]}
            onPress={handleTaken}
            disabled={logMutation.isPending}
            accessibilityLabel="Mark taken"
          >
            <Ionicons name="checkmark" size={18} color={colors.white} />
            <Text style={[s.primaryBtnText, { color: colors.white }]}>Mark taken</Text>
          </Pressable>
          <Pressable
            style={[s.secondaryBtn, { borderColor: colors.saffron }]}
            onPress={handleSnooze}
            disabled={logMutation.isPending}
            accessibilityLabel="Snooze 15 minutes"
          >
            <Text style={[s.secondaryBtnText, { color: colors.saffron }]}>Snooze 15m</Text>
          </Pressable>
        </View>

        {/* Secondary controls — hidden for doctor-prescribed reminders, which the
            patient cannot pause, edit, or delete (the backend rejects those edits). */}
        {prescribed ? (
          <View style={[s.rxNote, { backgroundColor: t.surface }]}>
            <Ionicons name="lock-closed-outline" size={16} color={t.textSub} />
            <Text style={[s.rxNoteText, { color: t.textSub }]}>
              This reminder was set by your doctor and cannot be modified.
            </Text>
          </View>
        ) : (
          <View style={s.controls}>
            <Pressable
              style={s.controlBtn}
              onPress={() => toggleMutation.mutate({ rid: reminder.id, active: !reminder.active })}
              accessibilityLabel={reminder.active ? 'Pause reminder' : 'Resume reminder'}
            >
              <Ionicons name={reminder.active ? 'pause-outline' : 'play-outline'} size={18} color={t.textSub} />
              <Text style={[s.controlText, { color: t.textSub }]}>{reminder.active ? 'Pause' : 'Resume'}</Text>
            </Pressable>
            <Pressable style={s.controlBtn} onPress={confirmDelete} accessibilityLabel="Delete reminder">
              <Ionicons name="trash-outline" size={18} color={colors.terracotta} />
              <Text style={[s.controlText, { color: colors.terracotta }]}>Delete</Text>
            </Pressable>
          </View>
        )}
      </ScrollView>

      <ReminderFormModal
        visible={editVisible}
        editing={reminder}
        onClose={() => setEditVisible(false)}
        onSave={handleSave}
        isSaving={updateMutation.isPending}
        isDark={isDark}
      />
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex: 1 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing[3], padding: spacing[6] },
  missing: { fontFamily: fontFamily.body, fontSize: fontSize.body },
  missingLink: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '700' },
  editBtn: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '700' },
  scroll: { padding: spacing[5], paddingBottom: spacing[16], gap: spacing[4] },
  imageWrap: {
    borderRadius: borderRadius.xxl,
    height: 200,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  image: { width: '100%', height: '100%' },
  imageOverlay: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(0,0,0,0.35)',
  },
  photoControls: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: spacing[5],
    marginTop: -spacing[2],
  },
  photoBtn: { flexDirection: 'row', alignItems: 'center', gap: spacing[1], padding: spacing[1] },
  photoBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontWeight: '600' },
  title: { fontFamily: fontFamily.display, fontSize: fontSize.h2, fontWeight: '700' },
  subRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[2], marginTop: -spacing[2] },
  subtitle: { fontFamily: fontFamily.body, fontSize: fontSize.body },
  rxBadge: { paddingHorizontal: spacing[2], paddingVertical: 1, borderRadius: borderRadius.full },
  rxText: { fontFamily: fontFamily.body, fontSize: fontSize.xs, fontWeight: '700', letterSpacing: 0.5 },
  card: {
    borderRadius: borderRadius.xl,
    padding: spacing[4],
  },
  cardRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  cardRowText: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '500', flex: 1 },
  adherencePct: { fontFamily: fontFamily.data, fontSize: fontSize.body, fontWeight: '700' },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: spacing[4],
    paddingVertical: spacing[2],
  },
  detailRowBorder: { borderTopWidth: 1 },
  detailLabel: { fontFamily: fontFamily.body, fontSize: fontSize.caption },
  detailValue: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '500', flexShrink: 1, textAlign: 'right' },
  actions: { flexDirection: 'row', gap: spacing[3], marginTop: spacing[2] },
  primaryBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing[2],
    height: 52,
    borderRadius: borderRadius.xxl,
  },
  primaryBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '700' },
  secondaryBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing[5],
    height: 52,
    borderRadius: borderRadius.xxl,
    borderWidth: 1.5,
  },
  secondaryBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '700' },
  controls: { flexDirection: 'row', justifyContent: 'center', gap: spacing[6], paddingTop: spacing[2] },
  controlBtn: { flexDirection: 'row', alignItems: 'center', gap: spacing[1], padding: spacing[2] },
  controlText: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '500' },
  rxNote: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
    borderRadius: borderRadius.xl,
    padding: spacing[4],
    marginTop: spacing[2],
  },
  rxNoteText: { flex: 1, fontFamily: fontFamily.body, fontSize: fontSize.caption, lineHeight: 18 },
});
