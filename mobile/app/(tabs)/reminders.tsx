import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  useColorScheme,
  View,
} from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';

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
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';
import type { AdherenceAction, Reminder, ReminderAction, ReminderCreate, ReminderType } from '../../types/wellness';

const REMINDER_TYPES: { value: ReminderType; label: string; icon: string }[] = [
  { value: 'water',      label: 'Water',      icon: '💧' },
  { value: 'supplement', label: 'Supplement', icon: '🌿' },
  { value: 'medication', label: 'Medication', icon: '💊' },
  { value: 'gym',        label: 'Gym',        icon: '🏋️' },
  { value: 'custom',     label: 'Custom',     icon: '🔔' },
];

const TYPE_EMOJI: Record<ReminderType, string> = {
  water: '💧', supplement: '🌿', medication: '💊', gym: '🏋️', custom: '🔔',
};

const TYPE_COLOR: Record<ReminderType, string> = {
  water:      '#EBF3FF',
  supplement: '#EDFAF3',
  medication: '#F3EFFF',
  gym:        '#FFF4E5',
  custom:     colors.nightElev,
};

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

  const modalBg  = isDark ? colors.nightSurface : colors.white;
  const sheetBg  = isDark ? colors.midnight     : colors.skyMist;
  const textPri  = isDark ? colors.white     : colors.navyDeep;
  const textSub  = isDark ? colors.slateText : colors.coolGray;
  const inputBg  = isDark ? colors.nightElev : colors.white;
  const inputBdr = isDark ? 'rgba(255,255,255,0.10)' : colors.borderLight;

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
            {isSaving ? <ActivityIndicator color={colors.electricBlue} size="small" /> : <Text style={m.save}>Save</Text>}
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
                  style={[m.typeChip, { backgroundColor: active ? colors.navyDeep : (isDark ? colors.nightElev : colors.white), borderColor: active ? colors.navyDeep : inputBdr }]}
                  onPress={() => setForm(f => ({ ...f, type: t.value }))}
                  accessibilityLabel={`Reminder type ${t.label}`}
                >
                  <Text style={m.typeChipIcon}>{t.icon}</Text>
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

          {/* Schedule time */}
          <Text style={[m.fieldLabel, { color: textSub }]}>Daily time (HH : MM)</Text>
          <View style={m.timeRow}>
            <View style={[m.inputWrap, m.timeInput, { backgroundColor: inputBg, borderColor: inputBdr }]}>
              <TextInput
                style={[m.input, m.timeCenter, { color: textPri }]}
                value={form.scheduleHour}
                onChangeText={v => setForm(f => ({ ...f, scheduleHour: v }))}
                keyboardType="number-pad"
                maxLength={2}
                placeholder="08"
                placeholderTextColor={textSub}
                accessibilityLabel="Hour"
              />
            </View>
            <Text style={[m.timeSep, { color: textSub }]}>:</Text>
            <View style={[m.inputWrap, m.timeInput, { backgroundColor: inputBg, borderColor: inputBdr }]}>
              <TextInput
                style={[m.input, m.timeCenter, { color: textPri }]}
                value={form.scheduleMinute}
                onChangeText={v => setForm(f => ({ ...f, scheduleMinute: v }))}
                keyboardType="number-pad"
                maxLength={2}
                placeholder="00"
                placeholderTextColor={textSub}
                accessibilityLabel="Minute"
              />
            </View>
          </View>

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
  save:   { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.electricBlue, fontWeight: '700' },
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
  typeChipIcon: { fontSize: 14 },
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
  const sheetBg = isDark ? colors.nightSurface : colors.white;
  const textPri = isDark ? colors.white     : colors.navyDeep;
  const textSub = isDark ? colors.slateText : colors.coolGray;

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={ad.overlay}>
        <View style={[ad.sheet, { backgroundColor: sheetBg }]}>
          <View style={ad.handle} />
          <Text style={[ad.title, { color: textPri }]}>{label}</Text>
          <Text style={[ad.sub, { color: textSub }]}>Did you take this?</Text>
          {(
            [
              { action: 'taken'   as AdherenceAction, label: '✓  Taken',      bg: colors.successGreen,                          border: undefined },
              { action: 'skipped' as AdherenceAction, label: 'Skip',           bg: isDark ? colors.nightElev : colors.borderLight, border: undefined },
              { action: 'snoozed' as AdherenceAction, label: 'Snooze 15 min', bg: colors.warningAmber + '25',                    border: colors.warningAmber },
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

// ── Reminder card ─────────────────────────────────────────────────────────────

interface ReminderCardProps {
  reminder: Reminder;
  isDark: boolean;
  onEdit: (r: Reminder) => void;
  onDelete: (r: Reminder) => void;
}

function ReminderCard({ reminder, isDark, onEdit, onDelete }: ReminderCardProps) {
  const scale  = useSharedValue(1);
  const anim   = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));
  const pct    = Math.round(reminder.adherence_rate * 100);
  const pctColor = pct >= 80 ? colors.successGreen : pct >= 50 ? colors.warningAmber : colors.criticalRed;

  const cardBg  = isDark ? colors.nightSurface : colors.white;
  const cardBdr = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)';
  const textPri = isDark ? colors.white     : colors.navyDeep;
  const textSub = isDark ? colors.slateText : colors.coolGray;
  const iconBg  = isDark ? colors.nightElev : (TYPE_COLOR[reminder.type] ?? colors.iceBlue);

  function confirmDelete() {
    Alert.alert('Delete reminder', `Remove "${reminder.label}"?`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: () => onDelete(reminder) },
    ]);
  }

  return (
    <Animated.View style={anim}>
      <Pressable
        style={[styles.card, { backgroundColor: cardBg, borderColor: cardBdr }]}
        onPressIn={() => { scale.value = withSpring(0.98, { mass: 0.3, stiffness: 500 }); }}
        onPressOut={() => { scale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
        onLongPress={() => onEdit(reminder)}
        accessibilityLabel={`Reminder: ${reminder.label}`}
      >
        <View style={[styles.reminderIcon, { backgroundColor: iconBg }]}>
          <Text style={styles.reminderEmoji}>{TYPE_EMOJI[reminder.type]}</Text>
        </View>
        <View style={styles.reminderContent}>
          <Text style={[styles.reminderLabel, { color: textPri }]}>{reminder.label}</Text>
          <Text style={[styles.reminderSub, { color: textSub }]}>
            {reminder.schedule_cron
              ? `Daily at ${reminder.schedule_cron.split(' ')[1]}:${reminder.schedule_cron.split(' ')[0].padStart(2, '0')}`
              : reminder.schedule_interval_minutes
              ? `Every ${reminder.schedule_interval_minutes} min`
              : 'No schedule'}
          </Text>
        </View>
        <View style={[styles.adherenceBadge, { backgroundColor: pctColor + '18' }]}>
          <Text style={[styles.adherencePct, { color: pctColor }]}>{pct}%</Text>
        </View>
        <View style={styles.actions}>
          <Pressable onPress={() => onEdit(reminder)} style={styles.actionBtn} accessibilityLabel="Edit reminder">
            <Text style={[styles.actionBtnText, { color: textSub }]}>✎</Text>
          </Pressable>
          <Pressable onPress={confirmDelete} style={styles.actionBtn} accessibilityLabel="Delete reminder">
            <Text style={[styles.actionBtnText, { color: colors.criticalRed }]}>✕</Text>
          </Pressable>
        </View>
      </Pressable>
    </Animated.View>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function RemindersScreen() {
  const qc     = useQueryClient();
  const isDark = useColorScheme() === 'dark';
  const [modalVisible, setModalVisible] = useState(false);
  const [editingReminder, setEditingReminder] = useState<Reminder | null>(null);
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

  const remindersQuery = useQuery({ queryKey: ['reminders'], queryFn: listRemindersApi });

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

  const bg = isDark ? colors.midnight : colors.skyMist;

  if (remindersQuery.isLoading) {
    return <View style={[styles.centered, { backgroundColor: bg }]}><ActivityIndicator color={colors.electricBlue} /></View>;
  }

  const reminders = remindersQuery.data?.reminders ?? [];

  return (
    <View style={[styles.container, { backgroundColor: bg }]}>
      {reminders.length === 0 ? (
        <View style={styles.emptyState}>
          <View style={[styles.emptyIconWrap, { backgroundColor: isDark ? colors.nightSurface : colors.white }]}>
            <Text style={styles.emptyIconEmoji}>⏰</Text>
          </View>
          <Text style={[styles.emptyTitle, { color: isDark ? colors.white : colors.navyDeep }]}>
            No reminders yet
          </Text>
          <Text style={[styles.emptySub, { color: isDark ? colors.slateText : colors.coolGray }]}>
            Set up water intake, medication, or supplement reminders and track your adherence.
          </Text>
          <Pressable
            style={styles.createBtn}
            onPress={openCreate}
            accessibilityLabel="Create your first reminder"
          >
            <Text style={styles.createBtnText}>Create reminder</Text>
          </Pressable>
        </View>
      ) : (
        <>
          <FlatList
            data={reminders}
            keyExtractor={r => r.id}
            renderItem={({ item }) => (
              <ReminderCard
                reminder={item}
                isDark={isDark}
                onEdit={openEdit}
                onDelete={r => deleteMutation.mutate(r.id)}
              />
            )}
            contentContainerStyle={styles.list}
            ItemSeparatorComponent={() => <View style={{ height: spacing[3] }} />}
          />
          <Pressable style={styles.fab} onPress={openCreate} accessibilityLabel="Add reminder">
            <Text style={styles.fabText}>+</Text>
          </Pressable>
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
  centered:  { flex: 1, alignItems: 'center', justifyContent: 'center' },

  list: { paddingHorizontal: spacing[4], paddingTop: spacing[4], paddingBottom: 100 },

  card: {
    borderRadius: borderRadius.xl,
    padding: spacing[4],
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    borderWidth: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 10,
    elevation: 2,
  },
  reminderIcon: {
    width: 44,
    height: 44,
    borderRadius: borderRadius.xl,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  reminderEmoji: { fontSize: 22 },
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
    bottom: spacing[8],
    right: spacing[6],
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.navyDeep,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: colors.navyDeep,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.30,
    shadowRadius: 16,
    elevation: 8,
  },
  fabText: { fontSize: 28, color: colors.white, lineHeight: 32 },

  emptyState: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: spacing[8], gap: spacing[4] },
  emptyIconWrap: {
    width: 80,
    height: 80,
    borderRadius: 40,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.08,
    shadowRadius: 14,
    elevation: 4,
  },
  emptyIconEmoji: { fontSize: 36 },
  emptyTitle: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700', textAlign: 'center' },
  emptySub:   { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center', lineHeight: 22 },
  createBtn: {
    height: 52,
    paddingHorizontal: spacing[6],
    backgroundColor: colors.navyDeep,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: spacing[2],
    shadowColor: colors.navyDeep,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.25,
    shadowRadius: 12,
    elevation: 5,
  },
  createBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.white, fontWeight: '700' },
});
