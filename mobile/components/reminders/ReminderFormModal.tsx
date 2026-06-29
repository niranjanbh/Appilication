import { Ionicons } from '@expo/vector-icons';
import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from 'react-native';
import { Alert } from '../../lib/ui/alert';
import { KyrosSlider } from '../ui/KyrosSlider';
import { borderRadius, colors, fontFamily, fontSize, spacing, type TintName } from '../../lib/design-tokens';
import type { Reminder, ReminderCreate, ReminderType } from '../../types/wellness';

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

interface ReminderFormState {
  type: ReminderType;
  label: string;
  scheduleHour: string;
  scheduleMinute: string;
  intervalMinutes: string;
  // Per-type detail fields (persisted in reminder.metadata)
  amount: string;          // water: quantity per intake
  unit: 'glasses' | 'ml';  // water
  dosage: string;          // supplement / medication
  withFood: boolean;       // supplement / medication
  instructions: string;    // medication
  durationMinutes: string; // gym
  activity: string;        // gym
  notes: string;           // custom
}

const DEFAULT_FORM: ReminderFormState = {
  type: 'water', label: '', scheduleHour: '08', scheduleMinute: '00', intervalMinutes: '',
  amount: '', unit: 'glasses', dosage: '', withFood: false, instructions: '',
  durationMinutes: '', activity: '', notes: '',
};

const WATER_UNITS: { value: 'glasses' | 'ml'; label: string }[] = [
  { value: 'glasses', label: 'Glasses' },
  { value: 'ml',      label: 'ml' },
];

function metaStr(meta: Record<string, unknown> | null | undefined, key: string): string {
  const v = meta?.[key];
  return v === null || v === undefined ? '' : String(v);
}

export interface ReminderFormModalProps {
  visible: boolean;
  editing: Reminder | null;
  onClose: () => void;
  onSave: (payload: ReminderCreate, editing: Reminder | null) => void;
  isSaving: boolean;
  isDark: boolean;
}

export function ReminderFormModal({ visible, editing, onClose, onSave, isSaving, isDark }: ReminderFormModalProps) {
  const [form, setForm] = useState<ReminderFormState>(DEFAULT_FORM);

  useEffect(() => {
    if (editing) {
      const cron = editing.schedule_cron ?? '';
      const cronParts = cron.split(' ');
      const meta = editing.metadata;
      const unit = metaStr(meta, 'unit');
      setForm({
        type: editing.type, label: editing.label,
        scheduleHour: cronParts[1] ?? '08', scheduleMinute: cronParts[0] ?? '00',
        intervalMinutes: editing.schedule_interval_minutes ? String(editing.schedule_interval_minutes) : '',
        amount: metaStr(meta, 'amount'),
        unit: unit === 'ml' ? 'ml' : 'glasses',
        dosage: metaStr(meta, 'dosage'),
        withFood: meta?.with_food === true,
        instructions: metaStr(meta, 'instructions'),
        durationMinutes: metaStr(meta, 'duration_minutes'),
        activity: metaStr(meta, 'activity'),
        notes: metaStr(meta, 'notes'),
      });
    } else {
      // Default to now + 5 min (rounded to nearest 5) so the first fire lands today,
      // not tomorrow (DAILY trigger fires at next occurrence of hour:minute).
      const soon = new Date(Date.now() + 5 * 60_000);
      const rawMin = soon.getMinutes();
      const roundedMin = Math.ceil(rawMin / 5) * 5;
      const carryHour = roundedMin >= 60 ? 1 : 0;
      setForm({
        ...DEFAULT_FORM,
        scheduleHour: String((soon.getHours() + carryHour) % 24).padStart(2, '0'),
        scheduleMinute: String(roundedMin % 60).padStart(2, '0'),
      });
    }
  }, [editing, visible]);

  function handleSave() {
    if (!form.label.trim()) {
      Alert.alert('Label required', 'Please enter a name for this reminder.');
      return;
    }

    // Per-type required fields.
    const amount = parseInt(form.amount, 10);
    const duration = parseInt(form.durationMinutes, 10);
    if (form.type === 'water' && !form.intervalMinutes && (isNaN(amount) || amount <= 0)) {
      Alert.alert('Amount required', 'Enter how much water to drink each time.');
      return;
    }
    if ((form.type === 'supplement' || form.type === 'medication') && !form.dosage.trim()) {
      Alert.alert('Dosage required', 'Enter the dosage (e.g. 1 tablet, 1000 IU).');
      return;
    }
    if (form.type === 'gym' && (isNaN(duration) || duration <= 0)) {
      Alert.alert('Duration required', 'Enter the session length in minutes.');
      return;
    }

    const hour    = parseInt(form.scheduleHour, 10);
    const minute  = parseInt(form.scheduleMinute, 10);
    const validH  = !isNaN(hour)   && hour   >= 0 && hour   <= 23;
    const validM  = !isNaN(minute) && minute >= 0 && minute <= 59;
    const intervalMin = form.intervalMinutes ? parseInt(form.intervalMinutes, 10) || null : null;

    // Build per-type metadata, preserving any non-form keys already on the
    // reminder (e.g. care_plan_id / prescription_id that mark an Rx reminder,
    // or image_key / catalog_id set by the image attribute).
    const metadata: Record<string, unknown> = { ...(editing?.metadata ?? {}) };
    delete metadata.amount;
    delete metadata.unit;
    delete metadata.dosage;
    delete metadata.with_food;
    delete metadata.instructions;
    delete metadata.duration_minutes;
    delete metadata.activity;
    delete metadata.notes;
    if (form.type === 'water' && !isNaN(amount) && amount > 0) {
      metadata.amount = amount;
      metadata.unit = form.unit;
    }
    if (form.type === 'supplement' || form.type === 'medication') {
      if (form.dosage.trim()) metadata.dosage = form.dosage.trim();
      metadata.with_food = form.withFood;
    }
    if (form.type === 'medication' && form.instructions.trim()) {
      metadata.instructions = form.instructions.trim();
    }
    if (form.type === 'gym') {
      if (!isNaN(duration) && duration > 0) metadata.duration_minutes = duration;
      if (form.activity.trim()) metadata.activity = form.activity.trim();
    }
    if (form.type === 'custom' && form.notes.trim()) {
      metadata.notes = form.notes.trim();
    }

    const payload: ReminderCreate = {
      type: form.type,
      label: form.label.trim(),
      schedule_cron: intervalMin ? null : (validH && validM ? `${minute} ${hour} * * *` : null),
      schedule_interval_minutes: intervalMin,
      notification_channels: ['push'],
      metadata: Object.keys(metadata).length > 0 ? metadata : null,
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

          {/* ── Per-type details ─────────────────────────────────────────── */}

          {/* Water: amount + unit, then optional interval */}
          {form.type === 'water' && (
            <>
              <Text style={[m.fieldLabel, { color: textSub }]}>Amount each time</Text>
              <View style={m.inlineRow}>
                <View style={[m.inputWrap, m.inlineGrow, { backgroundColor: inputBg, borderColor: inputBdr }]}>
                  <TextInput
                    style={[m.input, { color: textPri }]}
                    value={form.amount}
                    onChangeText={v => setForm(f => ({ ...f, amount: v }))}
                    keyboardType="number-pad"
                    placeholder="e.g. 2"
                    placeholderTextColor={textSub}
                    accessibilityLabel="Water amount"
                  />
                </View>
                <View style={m.segment}>
                  {WATER_UNITS.map(u => {
                    const active = form.unit === u.value;
                    return (
                      <Pressable
                        key={u.value}
                        style={[m.segmentItem, { backgroundColor: active ? colors.forest : (isDark ? colors.forestSurfaceRaised : colors.white), borderColor: active ? colors.forest : inputBdr }]}
                        onPress={() => setForm(f => ({ ...f, unit: u.value }))}
                        accessibilityLabel={`Unit ${u.label}`}
                      >
                        <Text style={[m.segmentText, { color: active ? colors.white : textPri }]}>{u.label}</Text>
                      </Pressable>
                    );
                  })}
                </View>
              </View>

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

          {/* Supplement / Medication: dosage + with food (+ instructions for meds) */}
          {(form.type === 'supplement' || form.type === 'medication') && (
            <>
              <Text style={[m.fieldLabel, { color: textSub }]}>Dosage</Text>
              <View style={[m.inputWrap, { backgroundColor: inputBg, borderColor: inputBdr }]}>
                <TextInput
                  style={[m.input, { color: textPri }]}
                  value={form.dosage}
                  onChangeText={v => setForm(f => ({ ...f, dosage: v }))}
                  placeholder={form.type === 'medication' ? 'e.g. 1 tablet, 500 mg' : 'e.g. 1 capsule, 1000 IU'}
                  placeholderTextColor={textSub}
                  maxLength={120}
                  accessibilityLabel="Dosage"
                />
              </View>

              <Pressable
                style={[m.toggleRow, { backgroundColor: inputBg, borderColor: inputBdr }]}
                onPress={() => setForm(f => ({ ...f, withFood: !f.withFood }))}
                accessibilityLabel="Take with food"
              >
                <Text style={[m.toggleLabel, { color: textPri }]}>Take with food</Text>
                <Switch
                  value={form.withFood}
                  onValueChange={v => setForm(f => ({ ...f, withFood: v }))}
                  trackColor={{ false: inputBdr, true: colors.jadeGlow + '80' }}
                  thumbColor={form.withFood ? colors.jadeGlow : colors.white}
                  accessibilityLabel="Take with food toggle"
                />
              </Pressable>

              {form.type === 'medication' && (
                <>
                  <Text style={[m.fieldLabel, { color: textSub }]}>Instructions (optional)</Text>
                  <View style={[m.inputWrap, { backgroundColor: inputBg, borderColor: inputBdr }]}>
                    <TextInput
                      style={[m.input, { color: textPri }]}
                      value={form.instructions}
                      onChangeText={v => setForm(f => ({ ...f, instructions: v }))}
                      placeholder="e.g. After breakfast, avoid dairy"
                      placeholderTextColor={textSub}
                      maxLength={255}
                      multiline
                      accessibilityLabel="Instructions"
                    />
                  </View>
                </>
              )}
            </>
          )}

          {/* Gym: duration + activity */}
          {form.type === 'gym' && (
            <>
              <Text style={[m.fieldLabel, { color: textSub }]}>Duration (minutes)</Text>
              <View style={[m.inputWrap, { backgroundColor: inputBg, borderColor: inputBdr }]}>
                <TextInput
                  style={[m.input, { color: textPri }]}
                  value={form.durationMinutes}
                  onChangeText={v => setForm(f => ({ ...f, durationMinutes: v }))}
                  keyboardType="number-pad"
                  placeholder="e.g. 45"
                  placeholderTextColor={textSub}
                  accessibilityLabel="Session duration"
                />
              </View>

              <Text style={[m.fieldLabel, { color: textSub }]}>Activity (optional)</Text>
              <View style={[m.inputWrap, { backgroundColor: inputBg, borderColor: inputBdr }]}>
                <TextInput
                  style={[m.input, { color: textPri }]}
                  value={form.activity}
                  onChangeText={v => setForm(f => ({ ...f, activity: v }))}
                  placeholder="e.g. Strength, Cardio, Yoga"
                  placeholderTextColor={textSub}
                  maxLength={120}
                  accessibilityLabel="Activity"
                />
              </View>
            </>
          )}

          {/* Custom: free-form note */}
          {form.type === 'custom' && (
            <>
              <Text style={[m.fieldLabel, { color: textSub }]}>Note (optional)</Text>
              <View style={[m.inputWrap, { backgroundColor: inputBg, borderColor: inputBdr }]}>
                <TextInput
                  style={[m.input, { color: textPri }]}
                  value={form.notes}
                  onChangeText={v => setForm(f => ({ ...f, notes: v }))}
                  placeholder="Anything you want to remember"
                  placeholderTextColor={textSub}
                  maxLength={255}
                  multiline
                  accessibilityLabel="Note"
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
  inlineRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  inlineGrow: { flex: 1 },
  segment: { flexDirection: 'row', gap: spacing[1] },
  segmentItem: {
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[3],
    borderRadius: borderRadius.lg,
    borderWidth: 1,
  },
  segmentText: { fontFamily: fontFamily.body, fontSize: fontSize.sm, fontWeight: '600' },
  toggleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[2],
  },
  toggleLabel: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '500' },
});
