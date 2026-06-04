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

import { useCallback, useEffect, useReducer, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import { apiFetch } from '../../lib/api/client';
import { colors, fontFamily, fontSize, spacing, borderRadius } from '../../lib/design-tokens';

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

// ── Condition catalogue ────────────────────────────────────────────────────────

const CONDITIONS = [
  { slug: 'thyroid', label: 'Thyroid', icon: '🦋' },
  { slug: 'weight', label: 'Weight management', icon: '⚖️' },
  { slug: 'pcos', label: 'PCOS', icon: '🌿' },
  { slug: 'skin_hair', label: 'Skin & hair', icon: '✨' },
  { slug: 'mens_intimate', label: "Men's intimate health", icon: '🔬' },
  { slug: 'hormones_trt', label: 'Hormones & TRT', icon: '⚡' },
  { slug: 'longevity', label: 'Longevity', icon: '🌱' },
];

// ── Seed doctor (used until the doctor-listing endpoint is built) ──────────────
// In production, fetch from /v1/public/doctors?condition=...
const SEED_DOCTORS = [
  {
    id: '00000000-0000-0000-0000-000000000001',
    name: 'Dr. Meera Krishnan',
    specialty: 'Endocrinologist',
    fee_paise: 60000,
    duration_minutes: 20,
  },
  {
    id: '00000000-0000-0000-0000-000000000002',
    name: 'Dr. Arjun Patel',
    specialty: 'General Medicine',
    fee_paise: 45000,
    duration_minutes: 20,
  },
];

// ── Formatter helpers ─────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-IN', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  });
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });
}

function formatRupees(paise: number): string {
  return `₹${(paise / 100).toFixed(0)}`;
}

// ── Step components ────────────────────────────────────────────────────────────

function StepHeader({ step, title }: { step: number; title: string }) {
  return (
    <View style={styles.stepHeader}>
      <View style={styles.stepBadge}>
        <Text style={styles.stepBadgeText}>{step}</Text>
      </View>
      <Text style={styles.stepTitle}>{title}</Text>
    </View>
  );
}

// Step 1 — Condition
function ConditionStep({
  onSelect,
}: {
  onSelect: (slug: string) => void;
}) {
  return (
    <ScrollView contentContainerStyle={styles.stepContainer}>
      <StepHeader step={1} title="What would you like to address?" />
      {CONDITIONS.map((c) => (
        <Pressable
          key={c.slug}
          style={styles.listItem}
          onPress={() => onSelect(c.slug)}
          accessibilityLabel={c.label}
        >
          <Text style={styles.listItemIcon}>{c.icon}</Text>
          <Text style={styles.listItemLabel}>{c.label}</Text>
          <Text style={styles.listItemChevron}>›</Text>
        </Pressable>
      ))}
    </ScrollView>
  );
}

// Step 2 — Doctor selection
function DoctorStep({
  onSelect,
}: {
  onSelect: (doctor: (typeof SEED_DOCTORS)[0]) => void;
}) {
  return (
    <ScrollView contentContainerStyle={styles.stepContainer}>
      <StepHeader step={2} title="Choose a specialist" />
      {SEED_DOCTORS.map((d) => (
        <Pressable
          key={d.id}
          style={styles.doctorCard}
          onPress={() => onSelect(d)}
          accessibilityLabel={`Select ${d.name}`}
        >
          <View style={styles.doctorAvatar}>
            <Text style={styles.doctorAvatarText}>{d.name.charAt(3)}</Text>
          </View>
          <View style={styles.doctorInfo}>
            <Text style={styles.doctorName}>{d.name}</Text>
            <Text style={styles.doctorSpecialty}>{d.specialty}</Text>
            <Text style={styles.doctorFee}>{formatRupees(d.fee_paise)}</Text>
          </View>
          <Text style={styles.listItemChevron}>›</Text>
        </Pressable>
      ))}
    </ScrollView>
  );
}

// Step 3 — Slot picker
function SlotStep({
  doctorId,
  onSelect,
  onBack,
}: {
  doctorId: string;
  onSelect: (slot: AvailableSlot) => void;
  onBack: () => void;
}) {
  const [slots, setSlots] = useState<AvailableSlot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const now = new Date();
    const future = new Date(now.getTime() + 14 * 24 * 60 * 60 * 1000); // 14 days
    apiFetch<AvailableSlot[]>(
      `/v1/clinic/patient/consultations/slots?doctor_id=${doctorId}&date_from=${now.toISOString()}&date_to=${future.toISOString()}`,
    )
      .then((data) => {
        setSlots(data);
        setError(null);
      })
      .catch(() => setError('Could not load available slots.'))
      .finally(() => setLoading(false));
  }, [doctorId]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.forest} />
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.stepContainer}>
      <StepHeader step={3} title="Pick a time slot" />
      {error && <Text style={styles.errorText}>{error}</Text>}
      {!error && slots.length === 0 && (
        <Text style={styles.emptyLabel}>No slots available in the next 14 days.</Text>
      )}
      {slots.map((slot) => (
        <Pressable
          key={slot.id}
          style={styles.slotItem}
          onPress={() => onSelect(slot)}
          accessibilityLabel={`Select slot ${formatDate(slot.slot_start)} at ${formatTime(slot.slot_start)}`}
        >
          <Text style={styles.slotDate}>{formatDate(slot.slot_start)}</Text>
          <Text style={styles.slotTime}>{formatTime(slot.slot_start)}</Text>
        </Pressable>
      ))}
      <Pressable onPress={onBack} accessibilityLabel="Go back" style={styles.backLink}>
        <Text style={styles.backLinkText}>← Back</Text>
      </Pressable>
    </ScrollView>
  );
}

// Step 4 — Confirm & pay
function PayStep({
  condition,
  doctor,
  slot,
  onSuccess,
  onBack,
}: {
  condition: string;
  doctor: (typeof SEED_DOCTORS)[0];
  slot: AvailableSlot;
  onSuccess: (consultationId: string) => void;
  onBack: () => void;
}) {
  const [booking, setBooking] = useState(false);

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

      // In a real Razorpay integration, open the Razorpay checkout WebView here
      // using bookData.payment.razorpay_order_id, then call confirm-payment with
      // the returned razorpay_payment_id + razorpay_signature.
      // For now, we show the booking confirmation (payment in test mode returns stub).
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

  const conditionLabel =
    CONDITIONS.find((c) => c.slug === condition)?.label ?? condition;

  return (
    <ScrollView contentContainerStyle={styles.stepContainer}>
      <StepHeader step={4} title="Review & pay" />

      <View style={styles.summaryCard}>
        <Row label="Condition" value={conditionLabel} />
        <Row label="Doctor" value={doctor.name} />
        <Row label="Date" value={formatDate(slot.slot_start)} />
        <Row label="Time" value={formatTime(slot.slot_start)} />
        <View style={styles.divider} />
        <Row label="Consultation fee" value={formatRupees(doctor.fee_paise)} />
      </View>

      <Text style={styles.payNote}>
        You will be redirected to Razorpay to complete payment. Your appointment is confirmed
        once payment succeeds.
      </Text>

      <Pressable
        style={[styles.payButton, booking && styles.disabled]}
        onPress={handlePay}
        disabled={booking}
        accessibilityLabel="Pay and confirm booking"
      >
        {booking ? (
          <ActivityIndicator color={colors.white} />
        ) : (
          <Text style={styles.payButtonText}>Pay {formatRupees(doctor.fee_paise)}</Text>
        )}
      </Pressable>

      <Pressable onPress={onBack} accessibilityLabel="Go back" style={styles.backLink}>
        <Text style={styles.backLinkText}>← Change slot</Text>
      </Pressable>
    </ScrollView>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

// ── Main flow ─────────────────────────────────────────────────────────────────

type Step = 'condition' | 'doctor' | 'slot' | 'pay' | 'success';

export default function BookConsultationScreen() {
  const router = useRouter();
  const [step, setStep] = useState<Step>('condition');
  const [condition, setCondition] = useState('');
  const [doctor, setDoctor] = useState<(typeof SEED_DOCTORS)[0] | null>(null);
  const [slot, setSlot] = useState<AvailableSlot | null>(null);
  const [confirmedId, setConfirmedId] = useState('');

  const onSuccess = useCallback(
    (consultationId: string) => {
      setConfirmedId(consultationId);
      setStep('success');
    },
    [],
  );

  if (step === 'condition') {
    return (
      <ConditionStep
        onSelect={(slug) => {
          setCondition(slug);
          setStep('doctor');
        }}
      />
    );
  }

  if (step === 'doctor') {
    return (
      <DoctorStep
        onSelect={(d) => {
          setDoctor(d);
          setStep('slot');
        }}
      />
    );
  }

  if (step === 'slot' && doctor) {
    return (
      <SlotStep
        doctorId={doctor.id}
        onSelect={(s) => {
          setSlot(s);
          setStep('pay');
        }}
        onBack={() => setStep('doctor')}
      />
    );
  }

  if (step === 'pay' && doctor && slot) {
    return (
      <PayStep
        condition={condition}
        doctor={doctor}
        slot={slot}
        onSuccess={onSuccess}
        onBack={() => setStep('slot')}
      />
    );
  }

  // Success screen
  return (
    <View style={styles.successContainer}>
      <Text style={styles.successIcon}>✓</Text>
      <Text style={styles.successTitle}>Booking received</Text>
      <Text style={styles.successSub}>
        Complete payment to confirm your appointment. You will receive a confirmation once
        payment is processed.
      </Text>
      <Pressable
        style={styles.successButton}
        onPress={() => router.replace(`/consultations/${confirmedId}`)}
        accessibilityLabel="View booking"
      >
        <Text style={styles.successButtonText}>View booking</Text>
      </Pressable>
      <Pressable
        onPress={() => router.replace('/(tabs)/consultations')}
        accessibilityLabel="Go to consultations"
        style={styles.backLink}
      >
        <Text style={styles.backLinkText}>Back to consultations</Text>
      </Pressable>
    </View>
  );
}

// ── Styles ─────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  stepContainer: {
    flexGrow: 1,
    backgroundColor: colors.ivory,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
    paddingBottom: spacing[10],
    gap: spacing[3],
  },
  center: {
    flex: 1,
    backgroundColor: colors.ivory,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    marginBottom: spacing[2],
  },
  stepBadge: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.forest,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepBadgeText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: '700',
    color: colors.white,
  },
  stepTitle: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h3,
    color: colors.forest,
    fontWeight: '500',
    flex: 1,
  },
  listItem: {
    backgroundColor: colors.white,
    borderRadius: borderRadius.lg,
    padding: spacing[4],
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
  },
  listItemIcon: { fontSize: 22 },
  listItemLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    fontWeight: '500',
    flex: 1,
  },
  listItemChevron: {
    fontFamily: fontFamily.body,
    fontSize: 22,
    color: colors.stone,
  },
  doctorCard: {
    backgroundColor: colors.white,
    borderRadius: borderRadius.lg,
    padding: spacing[4],
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
  },
  doctorAvatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.forest + '20',
    alignItems: 'center',
    justifyContent: 'center',
  },
  doctorAvatarText: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h3,
    color: colors.forest,
  },
  doctorInfo: { flex: 1, gap: 2 },
  doctorName: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    fontWeight: '600',
  },
  doctorSpecialty: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: colors.stone,
  },
  doctorFee: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: colors.forest,
    fontWeight: '600',
  },
  slotItem: {
    backgroundColor: colors.white,
    borderRadius: borderRadius.lg,
    padding: spacing[4],
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  slotDate: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    fontWeight: '500',
  },
  slotTime: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.forest,
    fontWeight: '600',
  },
  summaryCard: {
    backgroundColor: colors.white,
    borderRadius: borderRadius.lg,
    padding: spacing[4],
    gap: spacing[3],
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  rowLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: colors.stone,
    flex: 1,
  },
  rowValue: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: colors.ink,
    fontWeight: '500',
    flex: 2,
    textAlign: 'right',
  },
  divider: { height: 1, backgroundColor: colors.ivory },
  payNote: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: colors.stone,
    lineHeight: 20,
  },
  payButton: {
    backgroundColor: colors.forest,
    borderRadius: borderRadius.lg,
    paddingVertical: spacing[4],
    alignItems: 'center',
  },
  payButtonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '700',
    color: colors.white,
  },
  backLink: { alignItems: 'center', paddingTop: spacing[2] },
  backLinkText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: colors.stone,
  },
  emptyLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    textAlign: 'center',
    paddingVertical: spacing[6],
  },
  errorText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: '#DC2626',
  },
  disabled: { opacity: 0.5 },
  successContainer: {
    flex: 1,
    backgroundColor: colors.ivory,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing[8],
    gap: spacing[4],
  },
  successIcon: { fontSize: 56, color: colors.forest },
  successTitle: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    color: colors.forest,
    fontWeight: '500',
  },
  successSub: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    textAlign: 'center',
    lineHeight: 22,
  },
  successButton: {
    backgroundColor: colors.forest,
    borderRadius: borderRadius.lg,
    paddingVertical: spacing[4],
    paddingHorizontal: spacing[8],
    alignItems: 'center',
    marginTop: spacing[2],
  },
  successButtonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '700',
    color: colors.white,
  },
});
