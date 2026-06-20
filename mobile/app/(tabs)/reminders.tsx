import { Ionicons } from '@expo/vector-icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useThemePreference } from '../../lib/theme-context';

import { AmbientBackground } from '../../components/ui/AmbientBackground';
import { EmptyState } from '../../components/ui/EmptyState';
import { TAB_DOCK_CLEARANCE } from '../../components/ui/GlassTabBar';
import { HapticPressable } from '../../components/ui/HapticPressable';
import { SkeletonCards } from '../../components/ui/Skeleton';
import {
  createReminderApi,
  deleteReminderApi,
  listRemindersApi,
  logAdherenceApi,
  updateReminderApi,
} from '../../lib/api/reminders';
import {
  addNotificationResponseListener,
  registerNotificationCategories,
  requestNotificationPermissions,
  scheduleReminderNotification,
} from '../../lib/native/notifications';
import { KyrosSlider } from '../../components/ui/KyrosSlider';
import { borderRadius, colors, fontFamily, fontSize, spacing, type TintName , withAlpha } from '../../lib/design-tokens';
import { ReminderList } from '../../components/reminders/ReminderList';
import type { AdherenceAction, Reminder, ReminderAction, ReminderCreate, ReminderType } from '../../types/wellness';

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

const TYPE_ICON: Record<ReminderType, { icon: IoniconName; tint: TintName }> = {
  water:      { icon: 'water-outline',         tint: 'sage' },
  supplement: { icon: 'leaf-outline',          tint: 'forest' },
  medication: { icon: 'medical-outline',       tint: 'peach' },
  gym:        { icon: 'barbell-outline',       tint: 'saffron' },
  custom:     { icon: 'notifications-outline', tint: 'sage' },
};

const REMINDER_TYPES: { value: ReminderType; label: string }[] = [
  { value: 'water',      label: 'Water' },
  { value: 'supplement', label: 'Supplement' },
  { value: 'medication', label: 'Medication' },
  { value: 'gym',        label: 'Gym' },
  { value: 'custom',     label: 'Custom' },
];

// ── Reminder form modal ───────────────────────────────────────────────────────

interface ReminderFormState {
  type: ReminderType;
  label: string;
  scheduleHour: string;
  scheduleMinute: string;
  intervalMinutes: string;
}

const DEFAULT_FORM: ReminderFormState = {
  type: 'water', label: '', scheduleHour: '08', scheduleMinute: '00', intervalMinutes: '',
};

interface ReminderFormModalProps {
  visible: boolean;
  editing: Reminder | null;
  onClose: () => void;
  onSave: (payload: ReminderCreate, editing: Reminder | null) => void;
  isSaving: boolean;
  isDark: boolean;
}

function ReminderFormModal({ visible, editing, onClose, onSave, isSaving, isDark }: ReminderFormModalProps) {
  const [form, setForm] = useState<ReminderFormState>(DEFAULT_FORM);

  useEffect(() => {
    if (editing) {
      const cron = editing.schedule_cron ?? '';
      const cronParts = cron.split(' ');
      setForm({
        type: editing.type, label: editing.label,
        scheduleHour: cronParts[1] ?? '08', scheduleMinute: cronParts[0] ?? '00',
        intervalMinutes: editing.schedule_interval_minutes ? String(editing.schedule_interval_minutes) : '',
      });
    } else {
      setForm(DEFAULT_FORM);
    }
  }, [editing, visible]);

  function handleSave() {
    if (!form.label.trim()) {
      Alert.alert('Label required', 'Please enter a name for this reminder.');
      return;
    }
    const hour    = parseInt(form.scheduleHour, 10);
    const minute  = parseInt(form.scheduleMinute, 10);
    const validH  = !isNaN(hour)   && hour   >= 0 && hour   <= 23;
    const validM  = !isNaN(minute) && minute >= 0 && minute <= 59;
    const payload: ReminderCreate = {
      type: form.type,
      label: form.label.trim(),
      schedule_cron: validH && validM ? `${minute} ${hour} * * *` : null,
      schedule_interval_minutes: form.intervalMinutes ? parseInt(form.intervalMinutes, 10) || null : null,
      notification_channels: ['push'],
    };
    onSave(payload, editing);
  }

  const modalBg  = isDark ? colors.forestSurface       : colors.white;
  const sheetBg  = isDark ? colors.forestInk           : colors.ivory;
  const textPri  = isDark ? colors.ivoryText           : colors.ink;
  const textSub  = isDark ? colors.stoneDim            : colors.stone;
  const inputBg  = isDark ? colors.forestSurfaceRaised : colors.white;
  const inputBdr = isDark ? 'rgba(79,163,131,0.20)'   : colors.borderLight;

  return (
    <Modal visible={visible} animationType="slide" presentationStyle="pageSheet" onRequestClose={onClose}>
      <View style={[m.container, { backgroundColor: sheetBg }]}>
        {/* Header */}
        <View style={[m.header, { backgroundColor: modalBg, borderBottomColor: isDark ? 'rgba(255,255,255,0.07)' : colors.borderLight }]}>
          <Pressable onPress={onClose} accessibilityLabel="Cancel">
            <Text style={[m.cancel, { color: textSub }]}>Cancel</Text>
          </Pressable>
          <Text style={[m.title, { color: textPri }]}>{editing ? 'Edit reminder' : 'New reminder'}</Text>
          <Pressable onPress={handleSave} disabled={isSaving} accessibilityLabel="Save reminder">
            {isSaving ? <ActivityIndicator color={colors.jadeGlow} size="small" /> : <Text style={m.save}>Save</Text>}
          </Pressable>
        </View>

        <ScrollView contentContainerStyle={m.body}>
          {/* Type chips */}
          <Text style={[m.fieldLabel, { color: textSub }]}>Type</Text>
          <View style={m.typeRow}>
            {REMINDER_TYPES.map(t => {
              const active = form.type === t.value;
              return (
                <Pressable
                  key={t.value}
                  style={[m.typeChip, { backgroundColor: active ? colors.forest : (isDark ? colors.forestSurfaceRaised : colors.white), borderColor: active ? colors.forest : inputBdr }]}
                  onPress={() => setForm(f => ({ ...f, type: t.value }))}
                  accessibilityLabel={`Reminder type ${t.label}`}
                >
                  <Ionicons
                    name={TYPE_ICON[t.value].icon}
                    size={14}
                    color={active ? colors.white : textPri}
                  />
                  <Text style={[m.typeChipText, { color: active ? colors.white : textPri }]}>{t.label}</Text>
                </Pressable>
              );
            })}
          </View>

          {/* Label */}
          <Text style={[m.fieldLabel, { color: textSub }]}>Name</Text>
          <View style={[m.inputWrap, { backgroundColor: inputBg, borderColor: inputBdr }]}>
            <TextInput
              style={[m.input, { color: textPri }]}
              value={form.label}
              onChangeText={v => setForm(f => ({ ...f, label: v }))}
              placeholder="e.g. Vitamin D, 8 glasses water"
              placeholderTextColor={textSub}
              maxLength={255}
              accessibilityLabel="Reminder name"
            />
          </View>

          {/* Schedule time — skeuomorphic sliders */}
          <KyrosSlider
            label="Hour"
            min={0}
            max={23}
            step={1}
            value={parseInt(form.scheduleHour, 10) || 0}
            onValueChange={v => setForm(f => ({ ...f, scheduleHour: String(v).padStart(2, '0') }))}
            formatValue={v => `${String(v).padStart(2, '0')}:${form.scheduleMinute}`}
            accessibilityLabel="Schedule hour"
          />
          <KyrosSlider
            label="Minute"
            min={0}
            max={59}
            step={5}
            value={parseInt(form.scheduleMinute, 10) || 0}
            onValueChange={v => setForm(f => ({ ...f, scheduleMinute: String(v).padStart(2, '0') }))}
            formatValue={v => `${form.scheduleHour}:${String(v).padStart(2, '0')}`}
            accessibilityLabel="Schedule minute"
          />

          {/* Interval (water only) */}
          {form.type === 'water' && (
            <>
              <Text style={[m.fieldLabel, { color: textSub }]}>Or repeat every (minutes)</Text>
              <View style={[m.inputWrap, { backgroundColor: inputBg, borderColor: inputBdr }]}>
                <TextInput
                  style={[m.input, { color: textPri }]}
                  value={form.intervalMinutes}
                  onChangeText={v => setForm(f => ({ ...f, intervalMinutes: v }))}
                  keyboardType="number-pad"
                  placeholder="e.g. 90"
                  placeholderTextColor={textSub}
                  accessibilityLabel="Interval in minutes"
                />
              </View>
            </>
          )}
        </ScrollView>
      </View>
    </Modal>
  );
}

const m = StyleSheet.create({
  container: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing[5],
    paddingVertical: spacing[4],
    borderBottomWidth: 1,
  },
  title:  { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700' },
  cancel: { fontFamily: fontFamily.body, fontSize: fontSize.body },
  save:   { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.jadeGlow, fontWeight: '700' },
  body:   { padding: spacing[5], gap: spacing[4] },
  fieldLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: -spacing[2],
  },
  inputWrap: {
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
  },
  input: { fontFamily: fontFamily.body, fontSize: fontSize.body, padding: 0 },
  typeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  typeChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[1],
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
    borderRadius: borderRadius.full,
    borderWidth: 1,
  },
  typeChipText: { fontFamily: fontFamily.body, fontSize: fontSize.sm, fontWeight: '500' },
  timeRow:   { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  timeInput: { flex: 1 },
  timeCenter: { textAlign: 'center' },
  timeSep: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '600' },
});

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
  const isDark = useThemePreference().colorScheme === 'dark';
  const [modalVisible, setModalVisible] = useState(false);
  const [editingReminder, setEditingReminder] = useState<Reminder | null>(null);
  const [selectedDate, setSelectedDate] = useState(() => new Date());
  const [adherenceState, setAdherenceState] = useState<{
    visible: boolean; reminderId: string; scheduledAt: string; label: string;
  }>({ visible: false, reminderId: '', scheduledAt: '', label: '' });

  const notifListenerRef = useRef<{ remove: () => void } | null>(null);

  // Preserve 100% of existing notification and adherence logic
  useEffect(() => {
    registerNotificationCategories();
    requestNotificationPermissions();
    notifListenerRef.current = addNotificationResponseListener(
      (reminderId, scheduledAt, action) => {
        if (action === 'taken' || action === 'skipped') {
          logMutation.mutate({ reminderId, scheduledAt, action });
        } else {
          const reminder = remindersQuery.data?.reminders.find(r => r.id === reminderId);
          setAdherenceState({ visible: true, reminderId, scheduledAt, label: reminder?.label ?? 'Reminder' });
        }
      },
    );
    return () => { notifListenerRef.current?.remove(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const remindersQuery = useQuery({ queryKey: ['reminders'], queryFn: listRemindersApi, staleTime: 60_000 });

  const createMutation = useMutation({
    mutationFn: createReminderApi,
    onSuccess: async (reminder) => {
      await qc.invalidateQueries({ queryKey: ['reminders'] });
      const cron = reminder.schedule_cron;
      if (cron) {
        const parts = cron.split(' ');
        const hour = parseInt(parts[1] ?? '8', 10);
        const minute = parseInt(parts[0] ?? '0', 10);
        const next = new Date();
        next.setHours(hour, minute, 0, 0);
        if (next <= new Date()) next.setDate(next.getDate() + 1);
        await scheduleReminderNotification(reminder.id, reminder.label, next);
      }
      setModalVisible(false);
    },
    onError: () => Alert.alert('Error', 'Could not create reminder. Please try again.'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ReminderCreate }) => updateReminderApi(id, payload),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['reminders'] }); setModalVisible(false); setEditingReminder(null); },
    onError: () => Alert.alert('Error', 'Could not update reminder.'),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteReminderApi,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reminders'] }),
    onError: () => Alert.alert('Error', 'Could not delete reminder.'),
  });

  const logMutation = useMutation({
    mutationFn: ({ reminderId, scheduledAt, action }: { reminderId: string; scheduledAt: string; action: ReminderAction }) =>
      logAdherenceApi(reminderId, { scheduled_at: scheduledAt, action }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['reminders'] }); setAdherenceState(s => ({ ...s, visible: false })); },
    onError: () => Alert.alert('Error', 'Could not log adherence.'),
  });

  function handleSave(payload: ReminderCreate, editing: Reminder | null) {
    if (editing) updateMutation.mutate({ id: editing.id, payload });
    else createMutation.mutate(payload);
  }

  function openEdit(r: Reminder)   { setEditingReminder(r); setModalVisible(true); }
  function openCreate()             { setEditingReminder(null); setModalVisible(true); }
  function handleAdherenceLog(reminderId: string, scheduledAt: string, action: AdherenceAction) {
    logMutation.mutate({ reminderId, scheduledAt, action: action as ReminderAction });
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
            onEdit={openEdit}
            onDelete={r => deleteMutation.mutate(r.id)}
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
        editing={editingReminder}
        onClose={() => { setModalVisible(false); setEditingReminder(null); }}
        onSave={handleSave}
        isSaving={createMutation.isPending || updateMutation.isPending}
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
