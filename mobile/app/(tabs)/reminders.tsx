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
  View,
} from 'react-native';

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
import {
  borderRadius,
  colors,
  fontFamily,
  fontSize,
  spacing,
} from '../../lib/design-tokens';
import type {
  AdherenceAction,
  Reminder,
  ReminderAction,
  ReminderCreate,
  ReminderType,
} from '../../types/wellness';

const REMINDER_TYPES: { value: ReminderType; label: string }[] = [
  { value: 'water', label: 'Water' },
  { value: 'supplement', label: 'Supplement' },
  { value: 'medication', label: 'Medication' },
  { value: 'gym', label: 'Gym' },
  { value: 'custom', label: 'Custom' },
];

const TYPE_EMOJI: Record<ReminderType, string> = {
  water: '💧',
  supplement: '💊',
  medication: '💊',
  gym: '🏋️',
  custom: '🔔',
};

// ── Create/Edit modal ─────────────────────────────────────────────────────────

interface ReminderFormState {
  type: ReminderType;
  label: string;
  scheduleHour: string;
  scheduleMinute: string;
  intervalMinutes: string;
}

const DEFAULT_FORM: ReminderFormState = {
  type: 'water',
  label: '',
  scheduleHour: '08',
  scheduleMinute: '00',
  intervalMinutes: '',
};

interface ReminderFormModalProps {
  visible: boolean;
  editing: Reminder | null;
  onClose: () => void;
  onSave: (payload: ReminderCreate, editing: Reminder | null) => void;
  isSaving: boolean;
}

function ReminderFormModal({ visible, editing, onClose, onSave, isSaving }: ReminderFormModalProps) {
  const [form, setForm] = useState<ReminderFormState>(DEFAULT_FORM);

  useEffect(() => {
    if (editing) {
      const cron = editing.schedule_cron ?? '';
      const cronParts = cron.split(' ');
      setForm({
        type: editing.type,
        label: editing.label,
        scheduleHour: cronParts[1] ?? '08',
        scheduleMinute: cronParts[0] ?? '00',
        intervalMinutes: editing.schedule_interval_minutes
          ? String(editing.schedule_interval_minutes)
          : '',
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
    const hour = parseInt(form.scheduleHour, 10);
    const minute = parseInt(form.scheduleMinute, 10);
    const validHour = !isNaN(hour) && hour >= 0 && hour <= 23;
    const validMinute = !isNaN(minute) && minute >= 0 && minute <= 59;

    const payload: ReminderCreate = {
      type: form.type,
      label: form.label.trim(),
      schedule_cron:
        validHour && validMinute
          ? `${minute} ${hour} * * *`
          : null,
      schedule_interval_minutes: form.intervalMinutes
        ? parseInt(form.intervalMinutes, 10) || null
        : null,
      notification_channels: ['push'],
    };
    onSave(payload, editing);
  }

  return (
    <Modal visible={visible} animationType="slide" presentationStyle="pageSheet" onRequestClose={onClose}>
      <View style={styles.modalContainer}>
        <View style={styles.modalHeader}>
          <Pressable onPress={onClose} accessibilityLabel="Cancel">
            <Text style={styles.modalCancel}>Cancel</Text>
          </Pressable>
          <Text style={styles.modalTitle}>{editing ? 'Edit reminder' : 'New reminder'}</Text>
          <Pressable onPress={handleSave} disabled={isSaving} accessibilityLabel="Save reminder">
            {isSaving ? (
              <ActivityIndicator color={colors.forest} size="small" />
            ) : (
              <Text style={styles.modalSave}>Save</Text>
            )}
          </Pressable>
        </View>

        <ScrollView contentContainerStyle={styles.modalBody}>
          {/* Type picker */}
          <Text style={styles.fieldLabel}>Type</Text>
          <View style={styles.typeRow}>
            {REMINDER_TYPES.map((t) => (
              <Pressable
                key={t.value}
                style={[styles.typeChip, form.type === t.value && styles.typeChipActive]}
                onPress={() => setForm((f) => ({ ...f, type: t.value }))}
                accessibilityLabel={`Reminder type ${t.label}`}
              >
                <Text style={[styles.typeChipText, form.type === t.value && styles.typeChipTextActive]}>
                  {t.label}
                </Text>
              </Pressable>
            ))}
          </View>

          {/* Label */}
          <Text style={styles.fieldLabel}>Name</Text>
          <TextInput
            style={styles.input}
            value={form.label}
            onChangeText={(v) => setForm((f) => ({ ...f, label: v }))}
            placeholder="e.g. Vitamin D, 8 glasses water"
            placeholderTextColor={colors.stone}
            maxLength={255}
            accessibilityLabel="Reminder name"
          />

          {/* Schedule time */}
          <Text style={styles.fieldLabel}>Daily time (HH MM)</Text>
          <View style={styles.timeRow}>
            <TextInput
              style={[styles.input, styles.timeInput]}
              value={form.scheduleHour}
              onChangeText={(v) => setForm((f) => ({ ...f, scheduleHour: v }))}
              keyboardType="number-pad"
              maxLength={2}
              placeholder="08"
              placeholderTextColor={colors.stone}
              accessibilityLabel="Hour"
            />
            <Text style={styles.timeSep}>:</Text>
            <TextInput
              style={[styles.input, styles.timeInput]}
              value={form.scheduleMinute}
              onChangeText={(v) => setForm((f) => ({ ...f, scheduleMinute: v }))}
              keyboardType="number-pad"
              maxLength={2}
              placeholder="00"
              placeholderTextColor={colors.stone}
              accessibilityLabel="Minute"
            />
          </View>

          {/* Interval (for water) */}
          {form.type === 'water' && (
            <>
              <Text style={styles.fieldLabel}>Or repeat every (minutes)</Text>
              <TextInput
                style={styles.input}
                value={form.intervalMinutes}
                onChangeText={(v) => setForm((f) => ({ ...f, intervalMinutes: v }))}
                keyboardType="number-pad"
                placeholder="e.g. 90"
                placeholderTextColor={colors.stone}
                accessibilityLabel="Interval in minutes"
              />
            </>
          )}
        </ScrollView>
      </View>
    </Modal>
  );
}

// ── Adherence dialog ──────────────────────────────────────────────────────────

interface AdherenceDialogProps {
  visible: boolean;
  reminderId: string;
  scheduledAt: string;
  label: string;
  onLog: (reminderId: string, scheduledAt: string, action: AdherenceAction) => void;
  onClose: () => void;
}

function AdherenceDialog({ visible, reminderId, scheduledAt, label, onLog, onClose }: AdherenceDialogProps) {
  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.overlay}>
        <View style={styles.adherenceSheet}>
          <Text style={styles.adherenceTitle}>{label}</Text>
          <Text style={styles.adherenceSub}>Did you take this?</Text>
          {(
            [
              { action: 'taken' as AdherenceAction, label: 'Taken ✓', style: styles.btnTaken },
              { action: 'skipped' as AdherenceAction, label: 'Skip', style: styles.btnSkip },
              { action: 'snoozed' as AdherenceAction, label: 'Snooze 15 min', style: styles.btnSnooze },
            ] as const
          ).map(({ action, label: btnLabel, style }) => (
            <Pressable
              key={action}
              style={[styles.adherenceBtn, style]}
              onPress={() => onLog(reminderId, scheduledAt, action)}
              accessibilityLabel={btnLabel}
            >
              <Text style={styles.adherenceBtnText}>{btnLabel}</Text>
            </Pressable>
          ))}
          <Pressable onPress={onClose} accessibilityLabel="Dismiss">
            <Text style={styles.adherenceDismiss}>Dismiss</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

// ── Reminder card ─────────────────────────────────────────────────────────────

interface ReminderCardProps {
  reminder: Reminder;
  onEdit: (r: Reminder) => void;
  onDelete: (r: Reminder) => void;
}

function ReminderCard({ reminder, onEdit, onDelete }: ReminderCardProps) {
  const pct = Math.round(reminder.adherence_rate * 100);
  const badgeColor = pct >= 80 ? colors.jade : pct >= 50 ? colors.saffron : colors.terracotta;

  function confirmDelete() {
    Alert.alert(
      'Delete reminder',
      `Remove "${reminder.label}"?`,
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Delete', style: 'destructive', onPress: () => onDelete(reminder) },
      ],
    );
  }

  return (
    <View style={styles.card}>
      <View style={styles.cardLeft}>
        <Text style={styles.cardEmoji}>{TYPE_EMOJI[reminder.type]}</Text>
        <View style={styles.cardContent}>
          <Text style={styles.cardLabel}>{reminder.label}</Text>
          <Text style={styles.cardSub}>
            {reminder.schedule_cron
              ? `Daily at ${reminder.schedule_cron.split(' ')[1]}:${reminder.schedule_cron.split(' ')[0].padStart(2, '0')}`
              : reminder.schedule_interval_minutes
              ? `Every ${reminder.schedule_interval_minutes} min`
              : 'No schedule'}
          </Text>
        </View>
      </View>
      <View style={styles.cardRight}>
        <View style={[styles.adherenceBadge, { backgroundColor: badgeColor + '22' }]}>
          <Text style={[styles.adherencePct, { color: badgeColor }]}>{pct}%</Text>
        </View>
        <Pressable onPress={() => onEdit(reminder)} style={styles.iconBtn} accessibilityLabel="Edit reminder">
          <Text style={styles.iconBtnText}>✎</Text>
        </Pressable>
        <Pressable onPress={confirmDelete} style={styles.iconBtn} accessibilityLabel="Delete reminder">
          <Text style={[styles.iconBtnText, { color: colors.terracotta }]}>✕</Text>
        </Pressable>
      </View>
    </View>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function RemindersScreen() {
  const qc = useQueryClient();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingReminder, setEditingReminder] = useState<Reminder | null>(null);
  const [adherenceState, setAdherenceState] = useState<{
    visible: boolean;
    reminderId: string;
    scheduledAt: string;
    label: string;
  }>({ visible: false, reminderId: '', scheduledAt: '', label: '' });

  const notifListenerRef = useRef<{ remove: () => void } | null>(null);

  // Register notification categories and listener on mount
  useEffect(() => {
    registerNotificationCategories();
    requestNotificationPermissions();
    notifListenerRef.current = addNotificationResponseListener(
      (reminderId, scheduledAt, action) => {
        if (action === 'taken' || action === 'skipped') {
          logMutation.mutate({ reminderId, scheduledAt, action });
        } else {
          // snoozed: show adherence dialog so user confirms
          const reminder = remindersQuery.data?.reminders.find((r) => r.id === reminderId);
          setAdherenceState({
            visible: true,
            reminderId,
            scheduledAt,
            label: reminder?.label ?? 'Reminder',
          });
        }
      },
    );
    return () => {
      notifListenerRef.current?.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const remindersQuery = useQuery({
    queryKey: ['reminders'],
    queryFn: listRemindersApi,
  });

  const createMutation = useMutation({
    mutationFn: createReminderApi,
    onSuccess: async (reminder) => {
      await qc.invalidateQueries({ queryKey: ['reminders'] });
      // Schedule local notification for next occurrence
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
    mutationFn: ({ id, payload }: { id: string; payload: ReminderCreate }) =>
      updateReminderApi(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reminders'] });
      setModalVisible(false);
      setEditingReminder(null);
    },
    onError: () => Alert.alert('Error', 'Could not update reminder.'),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteReminderApi,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reminders'] }),
    onError: () => Alert.alert('Error', 'Could not delete reminder.'),
  });

  const logMutation = useMutation({
    mutationFn: ({ reminderId, scheduledAt, action }: {
      reminderId: string;
      scheduledAt: string;
      action: ReminderAction;
    }) =>
      logAdherenceApi(reminderId, {
        scheduled_at: scheduledAt,
        action,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reminders'] });
      setAdherenceState((s) => ({ ...s, visible: false }));
    },
    onError: () => Alert.alert('Error', 'Could not log adherence.'),
  });

  function handleSave(payload: ReminderCreate, editing: Reminder | null) {
    if (editing) {
      updateMutation.mutate({ id: editing.id, payload });
    } else {
      createMutation.mutate(payload);
    }
  }

  function openEdit(reminder: Reminder) {
    setEditingReminder(reminder);
    setModalVisible(true);
  }

  function openCreate() {
    setEditingReminder(null);
    setModalVisible(true);
  }

  function handleAdherenceLog(reminderId: string, scheduledAt: string, action: AdherenceAction) {
    logMutation.mutate({ reminderId, scheduledAt, action: action as ReminderAction });
  }

  if (remindersQuery.isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator color={colors.forest} />
      </View>
    );
  }

  const reminders = remindersQuery.data?.reminders ?? [];

  return (
    <View style={styles.container}>
      {reminders.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyTitle}>No reminders yet</Text>
          <Text style={styles.emptySub}>
            Set up water intake, medication, or supplement reminders and track your adherence over time.
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
            keyExtractor={(r) => r.id}
            renderItem={({ item }) => (
              <ReminderCard reminder={item} onEdit={openEdit} onDelete={(r) => deleteMutation.mutate(r.id)} />
            )}
            contentContainerStyle={styles.list}
          />
          <Pressable
            style={styles.fab}
            onPress={openCreate}
            accessibilityLabel="Add reminder"
          >
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
      />

      <AdherenceDialog
        visible={adherenceState.visible}
        reminderId={adherenceState.reminderId}
        scheduledAt={adherenceState.scheduledAt}
        label={adherenceState.label}
        onLog={handleAdherenceLog}
        onClose={() => setAdherenceState((s) => ({ ...s, visible: false }))}
      />
    </View>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.ivory },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center' },

  // Empty state
  emptyState: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing[6],
    gap: spacing[3],
  },
  emptyTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.ink,
    fontWeight: '600',
  },
  emptySub: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    textAlign: 'center',
    lineHeight: 22,
  },
  createBtn: {
    marginTop: spacing[2],
    backgroundColor: colors.forest,
    paddingVertical: spacing[3],
    paddingHorizontal: spacing[6],
    borderRadius: borderRadius.md,
  },
  createBtnText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.white,
    fontWeight: '600',
  },

  // List
  list: { paddingHorizontal: spacing[4], paddingTop: spacing[4], paddingBottom: 100 },

  // Card
  card: {
    backgroundColor: colors.white,
    borderRadius: borderRadius.md,
    padding: spacing[4],
    marginBottom: spacing[3],
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  cardLeft: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  cardEmoji: { fontSize: 24, marginRight: spacing[3] },
  cardContent: { flex: 1 },
  cardLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    fontWeight: '600',
  },
  cardSub: { fontFamily: fontFamily.body, fontSize: fontSize.caption, color: colors.stone, marginTop: 2 },
  cardRight: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  adherenceBadge: {
    borderRadius: borderRadius.sm,
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
    minWidth: 40,
    alignItems: 'center',
  },
  adherencePct: { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontWeight: '600' },
  iconBtn: { padding: spacing[1] },
  iconBtnText: { fontSize: 16, color: colors.stone },

  // FAB
  fab: {
    position: 'absolute',
    bottom: spacing[8],
    right: spacing[6],
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.forest,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: colors.ink,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 4,
  },
  fabText: { fontSize: 28, color: colors.white, lineHeight: 32 },

  // Modal
  modalContainer: { flex: 1, backgroundColor: colors.ivory },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[4],
    borderBottomWidth: 1,
    borderBottomColor: '#E5E0D8',
  },
  modalTitle: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, color: colors.ink, fontWeight: '600' },
  modalCancel: { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.stone },
  modalSave: { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.forest, fontWeight: '600' },
  modalBody: { padding: spacing[4], gap: spacing[4] },

  fieldLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    marginBottom: spacing[1],
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  input: {
    backgroundColor: colors.white,
    borderRadius: borderRadius.sm,
    padding: spacing[3],
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    borderWidth: 1,
    borderColor: '#E5E0D8',
  },
  typeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  typeChip: {
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
    borderRadius: borderRadius.sm,
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: '#E5E0D8',
  },
  typeChipActive: { backgroundColor: colors.forest, borderColor: colors.forest },
  typeChipText: { fontFamily: fontFamily.body, fontSize: fontSize.caption, color: colors.stone },
  typeChipTextActive: { color: colors.white },
  timeRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  timeInput: { flex: 1, textAlign: 'center' },
  timeSep: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, color: colors.stone },

  // Adherence dialog
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'flex-end',
  },
  adherenceSheet: {
    backgroundColor: colors.white,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    padding: spacing[6],
    gap: spacing[3],
  },
  adherenceTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.ink,
    fontWeight: '600',
    textAlign: 'center',
  },
  adherenceSub: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    textAlign: 'center',
  },
  adherenceBtn: {
    paddingVertical: spacing[3],
    borderRadius: borderRadius.md,
    alignItems: 'center',
  },
  btnTaken: { backgroundColor: colors.jade },
  btnSkip: { backgroundColor: '#E5E0D8' },
  btnSnooze: { backgroundColor: colors.saffron + '33', borderWidth: 1, borderColor: colors.saffron },
  adherenceBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600', color: colors.ink },
  adherenceDismiss: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    textAlign: 'center',
    paddingTop: spacing[2],
  },
});
