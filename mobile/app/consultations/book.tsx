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

import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { Alert } from '../../lib/ui/alert';
import { useQuery } from '@tanstack/react-query';
import { useThemePreference } from '../../lib/theme-context';
import { useRouter, useLocalSearchParams } from 'expo-router';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { apiFetch } from '../../lib/api/client';
import { listConditions, type Condition } from '../../lib/api/conditions';
import { Skeleton } from '../../components/ui/Skeleton';
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

// The condition list is fetched live from GET /v1/public/conditions. The backend
// does not return icons, so we keep a static slug→icon lookup here. Unknown slugs
// fall back to a neutral icon.
const CONDITION_ICONS: Record<string, string> = {
  'weight-management': '⚖️',
  diabetes:            '🩸',
  thyroid:             '🦋',
  pcos:                '🌿',
  'skin-and-hair':     '✨',
  'sexual-health':     '🔬',
  'hormones-trt':      '⚡',
  longevity:           '🌱',
};
const DEFAULT_CONDITION_ICON = '🩺';

interface ConditionOption {
  slug: string;
  label: string;
  icon: string;
}

function toOption(c: Condition): ConditionOption {
  return { slug: c.slug, label: c.name, icon: CONDITION_ICONS[c.slug] ?? DEFAULT_CONDITION_ICON };
}

// Static fallback used only if the live fetch fails, so booking still works.
// Slugs must match the backend's accepted set.
const FALLBACK_CONDITIONS: ConditionOption[] = [
  { slug: 'weight-management', label: 'Weight Management',         icon: CONDITION_ICONS['weight-management']! },
  { slug: 'diabetes',          label: 'Diabetes',                  icon: CONDITION_ICONS['diabetes']! },
  { slug: 'thyroid',           label: 'Thyroid',                   icon: CONDITION_ICONS['thyroid']! },
  { slug: 'pcos',              label: 'PCOS',                      icon: CONDITION_ICONS['pcos']! },
  { slug: 'skin-and-hair',     label: 'Skin & Hair',               icon: CONDITION_ICONS['skin-and-hair']! },
  { slug: 'sexual-health',     label: 'Sexual & Intimate Health',  icon: CONDITION_ICONS['sexual-health']! },
  { slug: 'hormones-trt',      label: 'Hormones & TRT',            icon: CONDITION_ICONS['hormones-trt']! },
  { slug: 'longevity',         label: 'Longevity',                 icon: CONDITION_ICONS['longevity']! },
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
  fill:     { height: 4, backgroundColor: colors.jade, borderRadius: 2 },
  count:    { fontFamily: fontFamily.body, fontSize: fontSize.xs, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 1 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[3] },
  badge:    { width: 28, height: 28, borderRadius: 14, backgroundColor: colors.forest, alignItems: 'center', justifyContent: 'center' },
  badgeText:{ fontFamily: fontFamily.body, fontSize: fontSize.sm, fontWeight: '700', color: colors.ivoryText },
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

function ConditionStep({ conditions, loading, onSelect, onClose, theme }: {
  conditions: ConditionOption[];
  loading: boolean;
  onSelect: (slug: string) => void;
  onClose: () => void;
  theme: ThemeProps;
}) {
  return (
    <ScrollView
      style={[styles.flex, { backgroundColor: theme.isDark ? colors.forestInk : colors.ivory }]}
      contentContainerStyle={styles.stepContainer}
      showsVerticalScrollIndicator={false}
    >
      <Pressable onPress={onClose} accessibilityLabel="Close and return to consultations" style={styles.closeBtn}>
        <Text style={[styles.closeBtnText, { color: theme.textSub }]}>✕ Cancel</Text>
      </Pressable>
      <StepHeader step={1} title="What would you like to address?" theme={theme} />
      {loading ? (
        <View style={styles.conditionGrid}>
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} height={64} radius={borderRadius.xl} />
          ))}
        </View>
      ) : (
        <View style={styles.conditionGrid}>
          {conditions.map(c => (
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
      )}
    </ScrollView>
  );
}

// ── Step 2 — Requirement + preferred time → submit ─────────────────────────────

function RequirementStep({ condition, conditions, followUp, onSuccess, onBack, theme }: {
  condition: string;
  conditions: ConditionOption[];
  followUp?: string;
  onSuccess: (consultationId: string) => void;
  onBack: () => void;
  theme: ThemeProps;
}) {
  const [notes, setNotes]            = useState('');
  const [timeWindow, setTimeWindow]  = useState<string>('flexible');
  const [submitting, setSubmit]      = useState(false);

  const conditionLabel = conditions.find(c => c.slug === condition)?.label ?? condition;
  const bg = theme.isDark ? colors.forestInk : colors.ivory;

  const handleSubmit = useCallback(async () => {
    setSubmit(true);
    try {
      const data = await apiFetch<RequestResponse>('/v1/clinic/patient/consultations', {
        method: 'POST',
        body: JSON.stringify({
          condition_category: condition,
          consultation_type: followUp ? 'follow_up' : 'initial',
          requirement_notes: notes.trim() || null,
          preferred_time_window: timeWindow,
          parent_consultation_id: followUp ?? null,
        }),
      });
      onSuccess(data.consultation_id);
    } catch {
      Alert.alert('Error', 'Could not submit your request. Please try again.');
    } finally {
      setSubmit(false);
    }
  }, [condition, notes, timeWindow, followUp, onSuccess]);

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
          const active = w.slug === timeWindow;
          return (
            <Pressable
              key={w.slug}
              onPress={() => setTimeWindow(w.slug)}
              accessibilityLabel={w.label}
              style={[
                styles.windowChip,
                {
                  backgroundColor: active ? colors.forest : theme.cardBg,
                  borderColor: active ? colors.forest : theme.cardBdr,
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

// ── Success screen ──────────────────────────────────────────────────────────────

function SuccessStep({ theme, onViewRequest, onBackToList }: {
  theme: ThemeProps;
  onViewRequest: () => void;
  onBackToList: () => void;
}) {
  const bg = theme.isDark ? colors.forestInk : colors.ivory;
  const successScale = useSharedValue(0.7);
  const successAnim  = useAnimatedStyle(() => ({ transform: [{ scale: successScale.value }] }));
  useEffect(() => {
    successScale.value = withSpring(1, { mass: 0.6, stiffness: 200 });
  }, [successScale]);

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
        onPress={onViewRequest}
        accessibilityLabel="View request"
      >
        <Text style={styles.successBtnText}>View request</Text>
      </Pressable>
      <Pressable
        onPress={onBackToList}
        accessibilityLabel="Back to consultations"
        style={styles.backBtn}
      >
        <Text style={[styles.backBtnText, { color: theme.textSub }]}>Back to consultations</Text>
      </Pressable>
    </View>
  );
}

// ── Main flow ─────────────────────────────────────────────────────────────────

type Step = 'condition' | 'requirement' | 'success';

export default function RequestConsultationScreen() {
  const router  = useRouter();
  const { condition: preselected, followUp } = useLocalSearchParams<{ condition?: string; followUp?: string }>();
  const isDark  = useThemePreference().colorScheme === 'dark';
  const [step,        setStep]        = useState<Step>(preselected ? 'requirement' : 'condition');
  const [condition,   setCondition]   = useState(preselected ?? '');
  const [confirmedId, setConfirmedId] = useState('');

  const conditionsQuery = useQuery({
    queryKey: ['public', 'conditions'],
    queryFn: listConditions,
    staleTime: 1000 * 60 * 60, // catalogue rarely changes
  });

  // Use the live catalogue; fall back to the static list if the fetch failed.
  const conditions: ConditionOption[] = conditionsQuery.data
    ? conditionsQuery.data.map(toOption)
    : FALLBACK_CONDITIONS;

  const onSuccess = useCallback((consultationId: string) => {
    setConfirmedId(consultationId);
    setStep('success');
  }, []);

  const theme: ThemeProps = {
    isDark,
    textPri: isDark ? colors.ivoryText         : colors.ink,
    textSub: isDark ? colors.stoneDim      : colors.stone,
    cardBg:  isDark ? colors.forestSurface : colors.white,
    cardBdr: isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)',
  };

  if (step === 'condition') {
    return (
      <ConditionStep
        conditions={conditions}
        loading={conditionsQuery.isLoading}
        onSelect={slug => { setCondition(slug); setStep('requirement'); }}
        onClose={() => router.replace('/(tabs)/consultations')}
        theme={theme}
      />
    );
  }
  if (step === 'requirement') {
    return <RequirementStep condition={condition} conditions={conditions} followUp={followUp} onSuccess={onSuccess} onBack={() => setStep('condition')} theme={theme} />;
  }

  return (
    <SuccessStep
      theme={theme}
      onViewRequest={() => router.replace(`/consultations/${confirmedId}`)}
      onBackToList={() => router.replace('/(tabs)/consultations')}
    />
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
    backgroundColor: colors.forest,
    borderRadius: borderRadius.xxl,
    boxShadow: `0 8px 16px ${withAlpha(colors.forest, 0.30)}`,
  },
  primaryBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700', color: colors.ivoryText },
  disabled:       { opacity: 0.50 },

  // Back link
  backBtn:     { alignItems: 'center', paddingTop: spacing[2] },
  backBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.sm },

  // Close / cancel link (Step 1)
  closeBtn:     { alignSelf: 'flex-start' },
  closeBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.sm, fontWeight: '600' },

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
    backgroundColor: colors.jade,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: `0 8px 16px ${withAlpha(colors.jade, 0.35)}`,
    marginBottom: spacing[2],
  },
  successIcon: { fontSize: 36, color: colors.ivoryText },
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
    backgroundColor: colors.forest,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: `0 8px 16px ${withAlpha(colors.forest, 0.28)}`,
    marginTop: spacing[2],
  },
  successBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700', color: colors.ivoryText },
});
