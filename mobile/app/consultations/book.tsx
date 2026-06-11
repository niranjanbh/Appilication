/**
 * Consultation booking flow — 4 steps:
 *   1. Condition picker
 *   2. Doctor selection (stub list using seed data)
 *   3. Slot picker
 *   4. Payment → confirmation
 *
 * Razorpay checkout runs in the embedded WebView via Razorpay's standard
 * checkout.js flow.  The web page posts back the payment details via
 * window.ReactNativeWebView.postMessage(), which this screen handles.
 */

import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useThemePreference } from '../../lib/theme-context';
import { useRouter } from 'expo-router';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { apiFetch } from '../../lib/api/client';
import { borderRadius, colors, fontFamily, fontSize, spacing , withAlpha } from '../../lib/design-tokens';

// ── Types ──────────────────────────────────────────────────────────────────────

interface AvailableSlot {
  id: string;
  doctor_id: string;
  slot_start: string;
  slot_end: string;
}

interface BookResponse {
  consultation_id: string;
  status: string;
  scheduled_start_at: string;
  condition_category: string;
  consultation_fee_paise: number;
  payment: {
    payment_id: string;
    razorpay_order_id: string;
    amount_paise: number;
    currency: string;
  };
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

// ── Seed doctor ────────────────────────────────────────────────────────────────

const SEED_DOCTORS = [
  { id: '00000000-0000-0000-0000-000000000001', name: 'Dr. Meera Krishnan', specialty: 'Endocrinologist', fee_paise: 60000, duration_minutes: 20 },
  { id: '00000000-0000-0000-0000-000000000002', name: 'Dr. Arjun Patel',    specialty: 'General Medicine', fee_paise: 45000, duration_minutes: 20 },
];

// ── Helpers ────────────────────────────────────────────────────────────────────

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' });
}
function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
}
function formatRupees(paise: number) { return `₹${(paise / 100).toFixed(0)}`; }
function getInitials(name: string) {
  return name.split(' ').filter(w => /^[A-Za-z]/.test(w)).map(w => w[0]).join('').toUpperCase().slice(0, 2);
}

const SPRING = { mass: 0.3, stiffness: 500, damping: 20 };

// ── Step header with progress bar ──────────────────────────────────────────────

function StepHeader({ step, title, theme }: { step: number; title: string; theme: ThemeProps }) {
  const total = 4;
  return (
    <View style={sh.wrapper}>
      {/* Progress bar */}
      <View style={[sh.track, { backgroundColor: theme.isDark ? colors.nightElev : colors.borderLight }]}>
        <View style={[sh.fill, { width: `${(step / total) * 100}%` as never }]} />
      </View>
      {/* Step count */}
      <Text style={[sh.count, { color: theme.textSub }]}>Step {step} of {total}</Text>
      {/* Title */}
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
      style={[styles.flex, { backgroundColor: theme.isDark ? colors.midnight : colors.skyMist }]}
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

// ── Step 2 — Doctor ───────────────────────────────────────────────────────────

function DoctorStep({ onSelect, theme }: { onSelect: (d: typeof SEED_DOCTORS[0]) => void; theme: ThemeProps }) {
  return (
    <ScrollView
      style={[styles.flex, { backgroundColor: theme.isDark ? colors.midnight : colors.skyMist }]}
      contentContainerStyle={styles.stepContainer}
      showsVerticalScrollIndicator={false}
    >
      <StepHeader step={2} title="Choose a specialist" theme={theme} />
      {SEED_DOCTORS.map(d => (
        <PressCard
          key={d.id}
          onPress={() => onSelect(d)}
          accessibilityLabel={`Select ${d.name}`}
          style={[styles.doctorCard, { backgroundColor: theme.cardBg, borderColor: theme.cardBdr }]}
        >
          <View style={styles.doctorAvatar}>
            <Text style={styles.doctorAvatarText}>{getInitials(d.name)}</Text>
          </View>
          <View style={styles.doctorInfo}>
            <Text style={[styles.doctorName, { color: theme.textPri }]}>{d.name}</Text>
            <Text style={[styles.doctorSpecialty, { color: theme.textSub }]}>{d.specialty}</Text>
            <View style={[styles.feePill, { backgroundColor: colors.electricBlue + '15' }]}>
              <Text style={[styles.feeText, { color: colors.electricBlue }]}>{formatRupees(d.fee_paise)}</Text>
            </View>
          </View>
          <Text style={[styles.chevron, { color: theme.textSub }]}>›</Text>
        </PressCard>
      ))}
    </ScrollView>
  );
}

// ── Step 3 — Slot ─────────────────────────────────────────────────────────────

function SlotStep({ doctorId, onSelect, onBack, theme }: {
  doctorId: string;
  onSelect: (s: AvailableSlot) => void;
  onBack: () => void;
  theme: ThemeProps;
}) {
  const [slots,   setSlots]   = useState<AvailableSlot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);

  useEffect(() => {
    const now    = new Date();
    const future = new Date(now.getTime() + 14 * 24 * 60 * 60 * 1000);
    apiFetch<AvailableSlot[]>(
      `/v1/clinic/patient/consultations/slots?doctor_id=${doctorId}&date_from=${now.toISOString()}&date_to=${future.toISOString()}`,
    )
      .then(data => { setSlots(data); setError(null); })
      .catch(() => setError('Could not load available slots.'))
      .finally(() => setLoading(false));
  }, [doctorId]);

  const bg = theme.isDark ? colors.midnight : colors.skyMist;

  if (loading) {
    return <View style={[styles.center, { backgroundColor: bg }]}><ActivityIndicator color={colors.electricBlue} /></View>;
  }

  return (
    <ScrollView style={[styles.flex, { backgroundColor: bg }]} contentContainerStyle={styles.stepContainer} showsVerticalScrollIndicator={false}>
      <StepHeader step={3} title="Pick a time slot" theme={theme} />

      {error && (
        <View style={[styles.errorBox, { backgroundColor: colors.criticalRed + '12', borderColor: colors.criticalRed + '30' }]}>
          <Text style={[styles.errorText, { color: colors.criticalRed }]}>{error}</Text>
        </View>
      )}

      {!error && slots.length === 0 && (
        <View style={[styles.emptyState, { backgroundColor: theme.cardBg, borderColor: theme.cardBdr }]}>
          <Text style={styles.emptyIcon}>📅</Text>
          <Text style={[styles.emptyText, { color: theme.textPri }]}>No slots available</Text>
          <Text style={[styles.emptySub, { color: theme.textSub }]}>No available slots in the next 14 days.</Text>
        </View>
      )}

      <View style={styles.slotGrid}>
        {slots.map(slot => (
          <PressCard
            key={slot.id}
            onPress={() => onSelect(slot)}
            accessibilityLabel={`Select slot ${formatDate(slot.slot_start)} at ${formatTime(slot.slot_start)}`}
            style={[styles.slotCard, { backgroundColor: theme.cardBg, borderColor: theme.cardBdr }]}
          >
            <Text style={[styles.slotDate, { color: theme.textSub }]}>{formatDate(slot.slot_start)}</Text>
            <Text style={[styles.slotTime, { color: theme.textPri }]}>{formatTime(slot.slot_start)}</Text>
          </PressCard>
        ))}
      </View>

      <Pressable onPress={onBack} accessibilityLabel="Go back" style={styles.backBtn}>
        <Text style={[styles.backBtnText, { color: theme.textSub }]}>← Back</Text>
      </Pressable>
    </ScrollView>
  );
}

// ── Step 4 — Confirm & pay ────────────────────────────────────────────────────

function PayStep({ condition, doctor, slot, onSuccess, onBack, theme }: {
  condition: string;
  doctor: typeof SEED_DOCTORS[0];
  slot: AvailableSlot;
  onSuccess: (consultationId: string) => void;
  onBack: () => void;
  theme: ThemeProps;
}) {
  const [booking, setBooking] = useState(false);

  // Preserve ALL existing booking/Razorpay logic
  const handlePay = useCallback(async () => {
    setBooking(true);
    try {
      const bookData = await apiFetch<BookResponse>('/v1/clinic/patient/consultations', {
        method: 'POST',
        body: JSON.stringify({
          doctor_id: doctor.id,
          slot_id: slot.id,
          condition_category: condition,
          consultation_type: 'initial',
          consultation_fee_paise: doctor.fee_paise,
        }),
      });
      Alert.alert(
        'Booking received',
        `Your consultation is scheduled. Complete payment via Razorpay to confirm.\n\nOrder: ${bookData.payment.razorpay_order_id}`,
        [{ text: 'OK', onPress: () => onSuccess(bookData.consultation_id) }],
      );
    } catch (e: unknown) {
      const msg =
        e instanceof Error && e.message.includes('slot_not_available')
          ? 'This slot was just booked. Please pick another time.'
          : 'Booking failed. Please try again.';
      Alert.alert('Error', msg);
    } finally {
      setBooking(false);
    }
  }, [condition, doctor, slot, onSuccess]);

  const conditionLabel = CONDITIONS.find(c => c.slug === condition)?.label ?? condition;
  const bg = theme.isDark ? colors.midnight : colors.skyMist;

  const payScale = useSharedValue(1);
  const payAnim  = useAnimatedStyle(() => ({ transform: [{ scale: payScale.value }] }));

  return (
    <ScrollView style={[styles.flex, { backgroundColor: bg }]} contentContainerStyle={styles.stepContainer} showsVerticalScrollIndicator={false}>
      <StepHeader step={4} title="Review & pay" theme={theme} />

      {/* Summary card */}
      <View style={[styles.summaryCard, { backgroundColor: theme.cardBg, borderColor: theme.cardBdr }]}>
        {[
          { label: 'Condition', value: conditionLabel },
          { label: 'Doctor',    value: doctor.name },
          { label: 'Date',      value: formatDate(slot.slot_start) },
          { label: 'Time',      value: formatTime(slot.slot_start) },
        ].map(({ label, value }, i, arr) => (
          <View key={label}>
            <View style={styles.summaryRow}>
              <Text style={[styles.summaryLabel, { color: theme.textSub }]}>{label}</Text>
              <Text style={[styles.summaryValue, { color: theme.textPri }]}>{value}</Text>
            </View>
            {i < arr.length - 1 && (
              <View style={[styles.summarySep, { backgroundColor: theme.isDark ? 'rgba(255,255,255,0.06)' : colors.borderLight }]} />
            )}
          </View>
        ))}
        {/* Fee row (highlighted) */}
        <View style={[styles.feeRow, { backgroundColor: colors.electricBlue + '10', borderRadius: borderRadius.lg }]}>
          <Text style={[styles.feeRowLabel, { color: theme.textSub }]}>Consultation fee</Text>
          <Text style={[styles.feeRowValue, { color: colors.electricBlue }]}>{formatRupees(doctor.fee_paise)}</Text>
        </View>
      </View>

      <Text style={[styles.payNote, { color: theme.textSub }]}>
        You will be redirected to Razorpay to complete payment. Your appointment is confirmed once payment succeeds.
      </Text>

      <Animated.View style={payAnim}>
        <Pressable
          style={[styles.payBtn, booking && styles.disabled]}
          onPress={handlePay}
          onPressIn={() => { payScale.value = withSpring(0.97, SPRING); }}
          onPressOut={() => { payScale.value = withSpring(1, SPRING); }}
          disabled={booking}
          accessibilityLabel="Pay and confirm booking"
        >
          {booking ? (
            <ActivityIndicator color={colors.white} size="small" />
          ) : (
            <>
              <Text style={styles.payBtnIcon}>💳</Text>
              <Text style={styles.payBtnText}>Pay {formatRupees(doctor.fee_paise)}</Text>
            </>
          )}
        </Pressable>
      </Animated.View>

      <Pressable onPress={onBack} accessibilityLabel="Change slot" style={styles.backBtn}>
        <Text style={[styles.backBtnText, { color: theme.textSub }]}>← Change slot</Text>
      </Pressable>
    </ScrollView>
  );
}

// ── Main flow ─────────────────────────────────────────────────────────────────

type Step = 'condition' | 'doctor' | 'slot' | 'pay' | 'success';

export default function BookConsultationScreen() {
  const router  = useRouter();
  const isDark  = useThemePreference().colorScheme === 'dark';
  const [step,        setStep]        = useState<Step>('condition');
  const [condition,   setCondition]   = useState('');
  const [doctor,      setDoctor]      = useState<typeof SEED_DOCTORS[0] | null>(null);
  const [slot,        setSlot]        = useState<AvailableSlot | null>(null);
  const [confirmedId, setConfirmedId] = useState('');

  const onSuccess = useCallback((consultationId: string) => {
    setConfirmedId(consultationId);
    setStep('success');
  }, []);

  const theme: ThemeProps = {
    isDark,
    textPri: isDark ? colors.white        : colors.navyDeep,
    textSub: isDark ? colors.slateText    : colors.coolGray,
    cardBg:  isDark ? colors.nightSurface : colors.white,
    cardBdr: isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)',
  };

  if (step === 'condition') {
    return <ConditionStep onSelect={slug => { setCondition(slug); setStep('doctor'); }} theme={theme} />;
  }
  if (step === 'doctor') {
    return <DoctorStep onSelect={d => { setDoctor(d); setStep('slot'); }} theme={theme} />;
  }
  if (step === 'slot' && doctor) {
    return <SlotStep doctorId={doctor.id} onSelect={s => { setSlot(s); setStep('pay'); }} onBack={() => setStep('doctor')} theme={theme} />;
  }
  if (step === 'pay' && doctor && slot) {
    return <PayStep condition={condition} doctor={doctor} slot={slot} onSuccess={onSuccess} onBack={() => setStep('slot')} theme={theme} />;
  }

  // ── Success screen ────────────────────────────────────────────────────────

  const bg = isDark ? colors.midnight : colors.skyMist;
  const successScale = useSharedValue(0.7);
  const successAnim  = useAnimatedStyle(() => ({ transform: [{ scale: successScale.value }] }));

  // Kick the scale animation on mount
  successScale.value = withSpring(1, { mass: 0.6, stiffness: 200 });

  return (
    <View style={[styles.successContainer, { backgroundColor: bg }]}>
      <Animated.View style={[styles.successIconWrap, successAnim]}>
        <Text style={styles.successIcon}>✓</Text>
      </Animated.View>
      <Text style={[styles.successTitle, { color: theme.textPri }]}>Booking received!</Text>
      <Text style={[styles.successSub, { color: theme.textSub }]}>
        Complete payment to confirm your appointment. You will receive a confirmation once payment is processed.
      </Text>
      <Pressable
        style={styles.successBtn}
        onPress={() => router.replace(`/consultations/${confirmedId}`)}
        accessibilityLabel="View booking"
      >
        <Text style={styles.successBtnText}>View booking</Text>
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
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },

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

  // Doctor card
  doctorCard: {
    borderRadius: borderRadius.xl,
    padding: spacing[4],
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[4],
    borderWidth: 1,
    boxShadow: '0 6px 12px rgba(0,0,0,0.07)',
  },
  doctorAvatar: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: colors.navyDeep,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    boxShadow: `0 4px 8px ${withAlpha(colors.navyDeep, 0.25)}`,
  },
  doctorAvatarText: { fontFamily: fontFamily.display, fontSize: fontSize.bodyLg, color: colors.white, fontWeight: '700' },
  doctorInfo:       { flex: 1, gap: spacing[1] },
  doctorName:       { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700' },
  doctorSpecialty:  { fontFamily: fontFamily.body, fontSize: fontSize.sm },
  feePill:          { alignSelf: 'flex-start', borderRadius: borderRadius.full, paddingHorizontal: spacing[2], paddingVertical: 2 },
  feeText:          { fontFamily: fontFamily.body, fontSize: fontSize.sm, fontWeight: '700' },
  chevron:          { fontFamily: fontFamily.body, fontSize: 22 },

  // Slot grid
  slotGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
  slotCard: {
    borderRadius: borderRadius.xl,
    padding: spacing[4],
    borderWidth: 1,
    minWidth: 140,
    gap: spacing[1],
    boxShadow: '0 4px 10px rgba(0,0,0,0.06)',
  },
  slotDate: { fontFamily: fontFamily.body, fontSize: fontSize.sm },
  slotTime: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700' },

  // Empty + error
  errorBox:   { borderRadius: borderRadius.xl, borderWidth: 1, padding: spacing[4] },
  errorText:  { fontFamily: fontFamily.body, fontSize: fontSize.sm, fontWeight: '600' },
  emptyState: {
    borderRadius: borderRadius.xxl,
    padding: spacing[8],
    borderWidth: 1,
    alignItems: 'center',
    gap: spacing[3],
    boxShadow: '0 4px 10px rgba(0,0,0,0.06)',
  },
  emptyIcon: { fontSize: 40 },
  emptyText: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700', textAlign: 'center' },
  emptySub:  { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center', lineHeight: 22 },

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
  summarySep:   { height: 1, marginHorizontal: spacing[5] },
  feeRow:       { flexDirection: 'row', justifyContent: 'space-between', margin: spacing[3], paddingHorizontal: spacing[3], paddingVertical: spacing[3] },
  feeRowLabel:  { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600' },
  feeRowValue:  { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '800' },

  payNote: { fontFamily: fontFamily.body, fontSize: fontSize.sm, lineHeight: 20 },

  // Pay button
  payBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing[2],
    height: 56,
    backgroundColor: colors.navyDeep,
    borderRadius: borderRadius.xxl,
    boxShadow: `0 8px 16px ${withAlpha(colors.navyDeep, 0.30)}`,
  },
  payBtnIcon: { fontSize: 20 },
  payBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700', color: colors.white },
  disabled:   { opacity: 0.50 },

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
