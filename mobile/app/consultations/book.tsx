/**
 * Consultation request flow — 2 steps:
 *   1. Condition picker
 *   2. Requirement notes + preferred time window → submit request
 *
 * Patients do NOT choose a doctor or a time slot. A care coordinator reviews the
 * request and assigns the right specialist based on the stated requirement. The
 * patient is then notified to pay and confirm (handled on the consultation detail
 * screen once the doctor + slot are assigned).
 */

import { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useThemePreference } from '../../lib/theme-context';
import { useRouter } from 'expo-router';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { apiFetch } from '../../lib/api/client';
import { borderRadius, colors, fontFamily, fontSize, spacing, withAlpha } from '../../lib/design-tokens';

// ── Types ──────────────────────────────────────────────────────────────────────

interface RequestResponse {
  consultation_id: string;
  status: string;
  condition_category: string;
  consultation_type: string;
  requirement_notes: string | null;
  preferred_time_window: string | null;
  created_at: string;
}

// ── Shared theme props ─────────────────────────────────────────────────────────

interface ThemeProps {
  isDark: boolean;
  textPri: string;
  textSub: string;
  cardBg: string;
  cardBdr: string;
}

// ── Condition catalogue ────────────────────────────────────────────────────────

const CONDITIONS = [
  { slug: 'thyroid',       label: 'Thyroid',               icon: '🦋' },
  { slug: 'weight',        label: 'Weight management',     icon: '⚖️' },
  { slug: 'pcos',          label: 'PCOS',                  icon: '🌿' },
  { slug: 'skin_hair',     label: 'Skin & hair',           icon: '✨' },
  { slug: 'mens_intimate', label: "Men's intimate health", icon: '🔬' },
  { slug: 'hormones_trt',  label: 'Hormones & TRT',        icon: '⚡' },
  { slug: 'longevity',     label: 'Longevity',             icon: '🌱' },
];

// Coarse preferred time windows — must match the backend's accepted set.
const TIME_WINDOWS = [
  { slug: 'weekday_morning',   label: 'Weekday mornings' },
  { slug: 'weekday_afternoon', label: 'Weekday afternoons' },
  { slug: 'weekday_evening',   label: 'Weekday evenings' },
  { slug: 'weekend_morning',   label: 'Weekend mornings' },
  { slug: 'weekend_afternoon', label: 'Weekend afternoons' },
  { slug: 'weekend_evening',   label: 'Weekend evenings' },
  { slug: 'flexible',          label: "I'm flexible" },
];

const SPRING = { mass: 0.3, stiffness: 500, damping: 20 };

// ── Step header with progress bar ──────────────────────────────────────────────

function StepHeader({ step, title, theme }: { step: number; title: string; theme: ThemeProps }) {
  const total = 2;
  return (
    <View style={sh.wrapper}>
      <View style={[sh.track, { backgroundColor: theme.isDark ? colors.forestSurfaceRaised : colors.borderLight }]}>
        <View style={[sh.fill, { width: `${(step / total) * 100}%` as never }]} />
      </View>
      <Text style={[sh.count, { color: theme.textSub }]}>Step {step} of {total}</Text>
      <View style={sh.titleRow}>
        <View style={sh.badge}>
          <Text style={sh.badgeText}>{step}</Text>
        </View>
        <Text style={[sh.title, { color: theme.textPri }]}>{title}</Text>
      </View>
    </View>
  );
}

const sh = StyleSheet.create({
  wrapper:  { gap: spacing[2], marginBottom: spacing[4] },
  track:    { height: 4, borderRadius: 2, overflow: 'hidden' },
  fill:     { height: 4, backgroundColor: colors.electricBlue, borderRadius: 2 },
  count:    { fontFamily: fontFamily.body, fontSize: fontSize.xs, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 1 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[3] },
  badge:    { width: 28, height: 28, borderRadius: 14, backgroundColor: colors.navyDeep, alignItems: 'center', justifyContent: 'center' },
  badgeText:{ fontFamily: fontFamily.body, fontSize: fontSize.sm, fontWeight: '700', color: colors.white },
  title:    { fontFamily: fontFamily.display, fontSize: fontSize.h3, fontWeight: '600', flex: 1 },
});

// ── Animated pressable card (shared) ──────────────────────────────────────────

function PressCard({ onPress, children, style, accessibilityLabel }: {
  onPress: () => void;
  children: React.ReactNode;
  style?: object;
  accessibilityLabel: string;
}) {
  const scale = useSharedValue(1);
  const anim  = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));
  return (
    <Animated.View style={anim}>
      <Pressable
        onPress={onPress}
        onPressIn={() => { scale.value = withSpring(0.97, SPRING); }}
        onPressOut={() => { scale.value = withSpring(1, SPRING); }}
        style={style}
        accessibilityLabel={accessibilityLabel}
      >
        {children}
      </Pressable>
    </Animated.View>
  );
}

// ── Step 1 — Condition ────────────────────────────────────────────────────────

function ConditionStep({ onSelect, theme }: { onSelect: (slug: string) => void; theme: ThemeProps }) {
  return (
    <ScrollView
      style={[styles.flex, { backgroundColor: theme.isDark ? colors.forestInk : colors.skyMist }]}
      contentContainerStyle={styles.stepContainer}
      showsVerticalScrollIndicator={false}
    >
      <StepHeader step={1} title="What would you like to address?" theme={theme} />
      <View style={styles.conditionGrid}>
        {CONDITIONS.map(c => (
          <PressCard
            key={c.slug}
            onPress={() => onSelect(c.slug)}
            accessibilityLabel={c.label}
            style={[styles.conditionCard, { backgroundColor: theme.cardBg, borderColor: theme.cardBdr }]}
          >
            <Text style={styles.conditionIcon}>{c.icon}</Text>
            <Text style={[styles.conditionLabel, { color: theme.textPri }]}>{c.label}</Text>
            <Text style={[styles.conditionChevron, { color: theme.textSub }]}>›</Text>
          </PressCard>
        ))}
      </View>
    </ScrollView>
  );
}

// ── Step 2 — Requirement + preferred time → submit ─────────────────────────────

function RequirementStep({ condition, onSuccess, onBack, theme }: {
  condition: string;
  onSuccess: (consultationId: string) => void;
  onBack: () => void;
  theme: ThemeProps;
}) {
  const [notes, setNotes]       = useState('');
  const [window, setWindow]     = useState<string>('flexible');
  const [submitting, setSubmit] = useState(false);

  const conditionLabel = CONDITIONS.find(c => c.slug === condition)?.label ?? condition;
  const bg = theme.isDark ? colors.forestInk : colors.skyMist;

  const handleSubmit = useCallback(async () => {
    setSubmit(true);
    try {
      const data = await apiFetch<RequestResponse>('/v1/clinic/patient/consultations', {
        method: 'POST',
        body: JSON.stringify({
          condition_category: condition,
          consultation_type: 'initial',
          requirement_notes: notes.trim() || null,
          preferred_time_window: window,
        }),
      });
      onSuccess(data.consultation_id);
    } catch {
      Alert.alert('Error', 'Could not submit your request. Please try again.');
    } finally {
      setSubmit(false);
    }
  }, [condition, notes, window, onSuccess]);

  const submitScale = useSharedValue(1);
  const submitAnim  = useAnimatedStyle(() => ({ transform: [{ scale: submitScale.value }] }));

  return (
    <ScrollView style={[styles.flex, { backgroundColor: bg }]} contentContainerStyle={styles.stepContainer} showsVerticalScrollIndicator={false}>
      <StepHeader step={2} title="Tell us what you need" theme={theme} />

      <View style={[styles.summaryCard, { backgroundColor: theme.cardBg, borderColor: theme.cardBdr }]}>
        <View style={styles.summaryRow}>
          <Text style={[styles.summaryLabel, { color: theme.textSub }]}>Concern</Text>
          <Text style={[styles.summaryValue, { color: theme.textPri }]}>{conditionLabel}</Text>
        </View>
      </View>

      <Text style={[styles.fieldLabel, { color: theme.textPri }]}>What would you like help with?</Text>
      <TextInput
        style={[styles.notesInput, {
          backgroundColor: theme.cardBg,
          borderColor: theme.cardBdr,
          color: theme.textPri,
        }]}
        placeholder="Briefly describe your symptoms or goals (optional)"
        placeholderTextColor={theme.textSub}
        value={notes}
        onChangeText={setNotes}
        multiline
        numberOfLines={4}
        maxLength={2000}
        textAlignVertical="top"
        accessibilityLabel="Describe your requirement"
      />

      <Text style={[styles.fieldLabel, { color: theme.textPri }]}>Preferred time</Text>
      <View style={styles.windowGrid}>
        {TIME_WINDOWS.map(w => {
          const active = w.slug === window;
          return (
            <Pressable
              key={w.slug}
              onPress={() => setWindow(w.slug)}
              accessibilityLabel={w.label}
              style={[
                styles.windowChip,
                {
                  backgroundColor: active ? colors.navyDeep : theme.cardBg,
                  borderColor: active ? colors.navyDeep : theme.cardBdr,
                },
              ]}
            >
              <Text style={[styles.windowChipText, { color: active ? colors.white : theme.textPri }]}>{w.label}</Text>
            </Pressable>
          );
        })}
      </View>

      <Text style={[styles.note, { color: theme.textSub }]}>
        A care coordinator will match you with the right specialist and a time, then notify you to confirm and pay.
      </Text>

      <Animated.View style={submitAnim}>
        <Pressable
          style={[styles.primaryBtn, submitting && styles.disabled]}
          onPress={handleSubmit}
          onPressIn={() => { submitScale.value = withSpring(0.97, SPRING); }}
          onPressOut={() => { submitScale.value = withSpring(1, SPRING); }}
          disabled={submitting}
          accessibilityLabel="Submit consultation request"
        >
          {submitting
            ? <ActivityIndicator color={colors.white} size="small" />
            : <Text style={styles.primaryBtnText}>Submit request</Text>}
        </Pressable>
      </Animated.View>

      <Pressable onPress={onBack} accessibilityLabel="Go back" style={styles.backBtn}>
        <Text style={[styles.backBtnText, { color: theme.textSub }]}>← Back</Text>
      </Pressable>
    </ScrollView>
  );
}

// ── Main flow ─────────────────────────────────────────────────────────────────

type Step = 'condition' | 'requirement' | 'success';

export default function RequestConsultationScreen() {
  const router  = useRouter();
  const isDark  = useThemePreference().colorScheme === 'dark';
  const [step,        setStep]        = useState<Step>('condition');
  const [condition,   setCondition]   = useState('');
  const [confirmedId, setConfirmedId] = useState('');

  const onSuccess = useCallback((consultationId: string) => {
    setConfirmedId(consultationId);
    setStep('success');
  }, []);

  const theme: ThemeProps = {
    isDark,
    textPri: isDark ? colors.white         : colors.navyDeep,
    textSub: isDark ? colors.stoneDim      : colors.coolGray,
    cardBg:  isDark ? colors.forestSurface : colors.white,
    cardBdr: isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)',
  };

  if (step === 'condition') {
    return <ConditionStep onSelect={slug => { setCondition(slug); setStep('requirement'); }} theme={theme} />;
  }
  if (step === 'requirement') {
    return <RequirementStep condition={condition} onSuccess={onSuccess} onBack={() => setStep('condition')} theme={theme} />;
  }

  // ── Success screen ────────────────────────────────────────────────────────

  const bg = isDark ? colors.forestInk : colors.skyMist;
  const successScale = useSharedValue(0.7);
  const successAnim  = useAnimatedStyle(() => ({ transform: [{ scale: successScale.value }] }));
  successScale.value = withSpring(1, { mass: 0.6, stiffness: 200 });

  return (
    <View style={[styles.successContainer, { backgroundColor: bg }]}>
      <Animated.View style={[styles.successIconWrap, successAnim]}>
        <Text style={styles.successIcon}>✓</Text>
      </Animated.View>
      <Text style={[styles.successTitle, { color: theme.textPri }]}>Request submitted!</Text>
      <Text style={[styles.successSub, { color: theme.textSub }]}>
        A care coordinator will review your needs and assign the right specialist. You'll be notified to confirm and pay once a doctor and time are set.
      </Text>
      <Pressable
        style={styles.successBtn}
        onPress={() => router.replace(`/consultations/${confirmedId}`)}
        accessibilityLabel="View request"
      >
        <Text style={styles.successBtnText}>View request</Text>
      </Pressable>
      <Pressable
        onPress={() => router.replace('/(tabs)/consultations')}
        accessibilityLabel="Back to consultations"
        style={styles.backBtn}
      >
        <Text style={[styles.backBtnText, { color: theme.textSub }]}>Back to consultations</Text>
      </Pressable>
    </View>
  );
}

// ── Styles ─────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  flex:          { flex: 1 },
  stepContainer: {
    flexGrow: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
    paddingBottom: spacing[10],
    gap: spacing[4],
  },

  // Condition grid
  conditionGrid: { gap: spacing[3] },
  conditionCard: {
    borderRadius: borderRadius.xl,
    padding: spacing[4],
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    borderWidth: 1,
    boxShadow: '0 4px 10px rgba(0,0,0,0.06)',
  },
  conditionIcon:    { fontSize: 22 },
  conditionLabel:   { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600', flex: 1 },
  conditionChevron: { fontFamily: fontFamily.body, fontSize: 22 },

  // Summary card
  summaryCard: {
    borderRadius: borderRadius.xxl,
    overflow: 'hidden',
    borderWidth: 1,
    boxShadow: '0 6px 14px rgba(0,0,0,0.07)',
  },
  summaryRow:   { flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: spacing[5], paddingVertical: spacing[4] },
  summaryLabel: { fontFamily: fontFamily.body, fontSize: fontSize.sm, flex: 1 },
  summaryValue: { fontFamily: fontFamily.body, fontSize: fontSize.sm, fontWeight: '600', flex: 2, textAlign: 'right' },

  // Fields
  fieldLabel: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '700', marginTop: spacing[2] },
  notesInput: {
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    padding: spacing[4],
    minHeight: 110,
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
  },

  // Preferred time chips
  windowGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  windowChip: {
    borderRadius: borderRadius.full,
    borderWidth: 1,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[2],
  },
  windowChipText: { fontFamily: fontFamily.body, fontSize: fontSize.sm, fontWeight: '600' },

  note: { fontFamily: fontFamily.body, fontSize: fontSize.sm, lineHeight: 20 },

  // Primary button
  primaryBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing[2],
    height: 56,
    backgroundColor: colors.navyDeep,
    borderRadius: borderRadius.xxl,
    boxShadow: `0 8px 16px ${withAlpha(colors.navyDeep, 0.30)}`,
  },
  primaryBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700', color: colors.white },
  disabled:       { opacity: 0.50 },

  // Back link
  backBtn:     { alignItems: 'center', paddingTop: spacing[2] },
  backBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.sm },

  // Success screen
  successContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing[8],
    gap: spacing[4],
  },
  successIconWrap: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: colors.successGreen,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: `0 8px 16px ${withAlpha(colors.successGreen, 0.35)}`,
    marginBottom: spacing[2],
  },
  successIcon: { fontSize: 36, color: colors.white },
  successTitle: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    fontWeight: '600',
    textAlign: 'center',
  },
  successSub: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    textAlign: 'center',
    lineHeight: 22,
  },
  successBtn: {
    height: 56,
    paddingHorizontal: spacing[8],
    backgroundColor: colors.navyDeep,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: `0 8px 16px ${withAlpha(colors.navyDeep, 0.28)}`,
    marginTop: spacing[2],
  },
  successBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700', color: colors.white },
});
