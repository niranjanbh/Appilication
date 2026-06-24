import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Alert } from '../lib/ui/alert';

import { AmbientBackground } from '../components/ui/AmbientBackground';
import { GlassCard } from '../components/ui/GlassCard';
import { HapticPressable } from '../components/ui/HapticPressable';
import { NeumorphInput } from '../components/ui/NeumorphInput';
import {
  listVitalsApi,
  logVitalsApi,
  type VitalReadItem,
  type VitalType,
} from '../lib/api/vitals';
import { borderRadius, colors, fontFamily, fontSize, spacing, withAlpha } from '../lib/design-tokens';
import { useTheme } from '../lib/theme';

function showAlert(title: string, message: string) {
  if (Platform.OS === 'web') window.alert(`${title}\n\n${message}`);
  else Alert.alert(title, message);
}

const TYPE_LABEL: Record<VitalType, string> = {
  weight: 'Weight',
  blood_pressure_systolic: 'BP (systolic)',
  blood_pressure_diastolic: 'BP (diastolic)',
  blood_glucose: 'Blood glucose',
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hour12: true,
  });
}

function toNum(s: string): number | null {
  const v = parseFloat(s.trim());
  return Number.isFinite(v) ? v : null;
}

export default function VitalsScreen() {
  const t = useTheme();
  const queryClient = useQueryClient();

  const [weight, setWeight] = useState('');
  const [systolic, setSystolic] = useState('');
  const [diastolic, setDiastolic] = useState('');
  const [glucose, setGlucose] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['vitals'],
    queryFn: listVitalsApi,
    staleTime: 30_000,
  });
  const items = data?.items ?? [];

  const mutation = useMutation({
    mutationFn: logVitalsApi,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['vitals'] });
      setWeight(''); setSystolic(''); setDiastolic(''); setGlucose('');
      showAlert('Saved', 'Your readings have been logged.');
    },
    onError: () => { showAlert('Error', 'Could not save your readings. Please try again.'); },
  });

  const handleSave = () => {
    const w = toNum(weight);
    const sys = toNum(systolic);
    const dia = toNum(diastolic);
    const glu = toNum(glucose);

    if (w === null && sys === null && dia === null && glu === null) {
      showAlert('Nothing to log', 'Enter at least one reading.');
      return;
    }
    if ((sys === null) !== (dia === null)) {
      showAlert('Blood pressure', 'Enter both systolic and diastolic values.');
      return;
    }
    mutation.mutate({
      measured_at: new Date().toISOString(),
      weight_kg: w,
      blood_pressure_systolic: sys,
      blood_pressure_diastolic: dia,
      blood_glucose_mg_dl: glu,
    });
  };

  return (
    <View style={[styles.flex, { backgroundColor: t.background }]}>
      <AmbientBackground />
      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView style={styles.flex} contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
          <Text style={[styles.heading, { color: t.text }]}>Log vitals</Text>
          <Text style={[styles.subtitle, { color: t.textSub }]}>
            Record readings to share trends with your doctor.
          </Text>

          <GlassCard>
            <View style={styles.form}>
              <View style={styles.field}>
                <Text style={[styles.label, { color: t.textSub }]}>Weight (kg)</Text>
                <NeumorphInput value={weight} onChangeText={setWeight} placeholder="e.g. 72.5" keyboardType="decimal-pad" />
              </View>
              <View style={styles.bpRow}>
                <View style={[styles.field, styles.bpField]}>
                  <Text style={[styles.label, { color: t.textSub }]}>BP systolic</Text>
                  <NeumorphInput value={systolic} onChangeText={setSystolic} placeholder="120" keyboardType="number-pad" />
                </View>
                <View style={[styles.field, styles.bpField]}>
                  <Text style={[styles.label, { color: t.textSub }]}>BP diastolic</Text>
                  <NeumorphInput value={diastolic} onChangeText={setDiastolic} placeholder="80" keyboardType="number-pad" />
                </View>
              </View>
              <View style={styles.field}>
                <Text style={[styles.label, { color: t.textSub }]}>Blood glucose (mg/dL)</Text>
                <NeumorphInput value={glucose} onChangeText={setGlucose} placeholder="e.g. 95" keyboardType="decimal-pad" />
              </View>

              <HapticPressable
                haptic="medium"
                scaleTo={0.97}
                style={[styles.saveBtn, mutation.isPending && styles.disabled]}
                onPress={handleSave}
                disabled={mutation.isPending}
                accessibilityLabel="Save readings"
              >
                <Text style={styles.saveBtnText}>{mutation.isPending ? 'Saving…' : 'Save readings'}</Text>
              </HapticPressable>
            </View>
          </GlassCard>

          <Text style={[styles.sectionLabel, { color: t.textSub }]}>Recent readings</Text>
          {isLoading ? (
            <ActivityIndicator color={t.primary} style={{ marginTop: spacing[4] }} />
          ) : items.length === 0 ? (
            <GlassCard>
              <Text style={[styles.empty, { color: t.textSub }]}>No readings yet.</Text>
            </GlassCard>
          ) : (
            <GlassCard>
              <View style={styles.list}>
                {items.map((it: VitalReadItem, idx) => (
                  <View key={`${it.type}-${it.measured_at}-${idx}`} style={styles.readingRow}>
                    <Text style={[styles.readingType, { color: t.text }]}>{TYPE_LABEL[it.type]}</Text>
                    <Text style={[styles.readingValue, { color: t.text }]}>
                      {it.value.value} {it.value.unit}
                    </Text>
                    <Text style={[styles.readingDate, { color: t.textSub }]}>{formatDate(it.measured_at)}</Text>
                  </View>
                ))}
              </View>
            </GlassCard>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
    paddingBottom: spacing[12],
    gap: spacing[4],
  },
  heading: { fontFamily: fontFamily.display, fontSize: fontSize.h2, fontWeight: '600' },
  subtitle: { fontFamily: fontFamily.body, fontSize: fontSize.body, lineHeight: 22 },
  form: { gap: spacing[3] },
  field: { gap: spacing[2] },
  bpRow: { flexDirection: 'row', gap: spacing[3] },
  bpField: { flex: 1 },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: '600',
    paddingHorizontal: spacing[1],
  },
  saveBtn: {
    height: 52,
    marginTop: spacing[2],
    backgroundColor: colors.forest,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: `0 6px 14px ${withAlpha(colors.forest, 0.30)}`,
  },
  saveBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, color: colors.ivoryText, fontWeight: '700' },
  disabled: { opacity: 0.5 },
  sectionLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    paddingHorizontal: spacing[1],
    marginTop: spacing[2],
  },
  empty: { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center', paddingVertical: spacing[4] },
  list: { gap: spacing[3] },
  readingRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[3] },
  readingType: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600', flex: 1 },
  readingValue: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '700' },
  readingDate: { fontFamily: fontFamily.body, fontSize: fontSize.caption, minWidth: 96, textAlign: 'right' },
});
