import { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Alert } from '../../lib/ui/alert';
import { useQuery } from '@tanstack/react-query';
import { useThemePreference } from '../../lib/theme-context';
import { useFocusEffect, useLocalSearchParams, useRouter } from 'expo-router';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { apiFetch } from '../../lib/api/client';
import {
  confirmConsultationPayment,
  type RazorpayCheckoutResult,
} from '../../lib/api/payments';
import { useAuth } from '../../lib/auth/context';
import { RazorpayCheckout } from '../../components/ui/RazorpayCheckout';
import { borderRadius, colors, fontFamily, fontSize, spacing , withAlpha } from '../../lib/design-tokens';

// Razorpay publishable key — substituted at bundle time by Expo. The secret
// stays server-side; this key is safe to ship in the client bundle.
declare const process: { env: Record<string, string | undefined> };
const RAZORPAY_KEY_ID = process.env['EXPO_PUBLIC_RAZORPAY_KEY_ID'] ?? '';

// ── Types ──────────────────────────────────────────────────────────────────────

type ConsultationStatus =
  | 'requested' | 'scheduled' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled' | 'no_show';

interface RazorpayOrderInfo {
  payment_id: string;
  razorpay_order_id: string;
  amount_paise: number;
  currency: string;
}

interface Consultation {
  id: string;
  doctor_id: string | null;
  doctor_name: string | null;
  doctor_specialty: string[] | null;
  condition_category: string;
  consultation_type: string;
  scheduled_start_at: string | null;
  scheduled_end_at: string | null;
  actual_start_at: string | null;
  actual_end_at: string | null;
  status: ConsultationStatus;
  video_room_id: string | null;
  consultation_fee_paise: number | null;
  requirement_notes: string | null;
  preferred_time_window: string | null;
  payment_id: string | null;
  cancellation_reason: string | null;
  payment: RazorpayOrderInfo | null;
}

interface AvailableSlot {
  id: string;
  doctor_id: string;
  slot_start: string;
  slot_end: string;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-IN', {
    day: 'numeric', month: 'long', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: true,
  });
}
function formatRupees(p: number): string { return `₹${(p / 100).toFixed(0)}`; }
const CONDITION_LABEL: Record<string, string> = {
  weight: 'Weight Management',
  pcos: 'PCOS',
  thyroid: 'Thyroid',
  skin_hair: 'Skin & Hair',
  mens_intimate: 'Sexual & Intimate Health',
  hormones_trt: 'Hormones & TRT',
  longevity: 'Longevity',
};
function formatCategory(cat: string): string {
  return CONDITION_LABEL[cat] ?? cat.replace(/_/g, ' ').replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

const STATUS_LABEL: Record<ConsultationStatus, string> = {
  requested: 'Awaiting assignment', scheduled: 'Scheduled', confirmed: 'Confirmed',
  in_progress: 'In Progress', completed: 'Completed', cancelled: 'Cancelled', no_show: 'No Show',
};

const STATUS_COLOR: Record<ConsultationStatus, string> = {
  requested:   colors.saffron,
  scheduled:   colors.forest,
  confirmed:   colors.jade,
  in_progress: colors.saffron,
  completed:   colors.jade,
  cancelled:   colors.alert,
  no_show:     colors.alert,
};

function formatTimeWindow(w: string | null): string {
  if (!w) return 'Flexible';
  return w.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

const CANCELLABLE: ConsultationStatus[] = ['requested', 'scheduled', 'confirmed'];

// Reschedule requires an assigned doctor + slot, so it only applies once the
// consultation is scheduled/confirmed (a 'requested' consult has no slot yet).
const RESCHEDULABLE: ConsultationStatus[] = ['scheduled', 'confirmed'];

// Mirror the backend RESCHEDULE_NOTICE_WINDOW_HOURS (24h): only offer the action
// while the appointment is still far enough out for the server to accept it.
const RESCHEDULE_WINDOW_MS = 24 * 60 * 60 * 1000;

function formatSlotDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' });
}
function formatSlotTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
}

// ── Detail row ─────────────────────────────────────────────────────────────────

function Row({ label, value, textPri, textSub, borderColor }: {
  label: string; value: string; textPri: string; textSub: string; borderColor: string;
}) {
  return (
    <View style={[styles.row, { borderBottomColor: borderColor }]}>
      <Text style={[styles.rowLabel, { color: textSub }]}>{label}</Text>
      <Text style={[styles.rowValue, { color: textPri }]}>{value}</Text>
    </View>
  );
}

// ── Screen ─────────────────────────────────────────────────────────────────────

export default function ConsultationDetailScreen() {
  const { id }   = useLocalSearchParams<{ id: string }>();
  const router   = useRouter();
  const isDark   = useThemePreference().colorScheme === 'dark';
  const auth     = useAuth();
  const me       = auth.state.status === 'authenticated' ? auth.state.user : null;

  const [cancelling, setCancelling] = useState(false);
  const [paying,     setPaying]     = useState(false);

  // Razorpay checkout WebView visibility.
  const [checkoutVisible, setCheckoutVisible] = useState(false);

  // Reschedule panel state
  const [showReschedule, setShowReschedule] = useState(false);
  const [slots,        setSlots]        = useState<AvailableSlot[]>([]);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [slotsError,   setSlotsError]   = useState<string | null>(null);
  const [rescheduling, setRescheduling] = useState(false);

  const {
    data: consultation = null,
    isLoading: loading,
    isError,
    isFetching,
    refetch,
  } = useQuery({
    queryKey: ['consultation', id],
    queryFn: () => apiFetch<Consultation>(`/v1/clinic/patient/consultations/${id}`),
    staleTime: 30_000,
  });
  const error = isError ? 'Could not load consultation details.' : null;

  // A coordinator may assign a doctor/slot or a payment may settle server-side,
  // so refetch whenever this screen regains focus to clear stale data.
  const fetchDetail = useCallback(async () => { await refetch(); }, [refetch]);
  useFocusEffect(
    useCallback(() => { void refetch(); }, [refetch]),
  );

  // Preserve all existing cancel logic. For an unassigned request the copy is a
  // withdrawal (no slot/refund); for a scheduled/confirmed appointment it's a
  // cancellation with the refund-window note.
  const isRequest = consultation?.status === 'requested';
  const handleCancel = useCallback(() => {
    Alert.alert(
      isRequest ? 'Withdraw request?' : 'Cancel consultation?',
      isRequest
        ? 'Your request will be withdrawn and no specialist will be assigned.'
        : 'Cancellations made more than 24 hours before your appointment qualify for a full refund.',
      [
        { text: isRequest ? 'Keep request' : 'Keep appointment', style: 'cancel' },
        {
          text: isRequest ? 'Withdraw request' : 'Cancel appointment',
          style: 'destructive',
          onPress: async () => {
            setCancelling(true);
            try {
              await apiFetch(`/v1/clinic/patient/consultations/${id}/cancel`, {
                method: 'POST',
                body: JSON.stringify({ reason: 'Patient cancelled via app' }),
              });
              await fetchDetail();
            } catch {
              Alert.alert('Error', 'Could not cancel. Please try again.');
            } finally {
              setCancelling(false);
            }
          },
        },
      ],
    );
  }, [id, fetchDetail, isRequest]);

  // Pay to confirm once a coordinator has assigned a doctor + slot. The
  // patient confirms the amount, then Razorpay checkout runs inside the
  // embedded WebView.
  const handlePay = useCallback(() => {
    if (!consultation?.payment) return;
    const order = consultation.payment;
    if (!RAZORPAY_KEY_ID) {
      Alert.alert('Payments unavailable', 'Payment is not configured. Please try again later or contact support.');
      return;
    }
    Alert.alert(
      'Confirm your appointment',
      `You'll pay ${formatRupees(order.amount_paise)} via Razorpay. Your appointment is confirmed once payment succeeds.`,
      [
        { text: 'Not now', style: 'cancel' },
        { text: 'Proceed to pay', onPress: () => setCheckoutVisible(true) },
      ],
    );
  }, [consultation]);

  // Razorpay reported a signed, successful payment. The confirm-payment
  // endpoint verifies the signature server-side, captures the payment, and
  // transitions the consultation to 'confirmed' in one atomic call (it is
  // idempotent on an already-confirmed consultation).
  const handleCheckoutSuccess = useCallback(async (result: RazorpayCheckoutResult) => {
    setCheckoutVisible(false);
    if (!consultation?.payment) return;
    setPaying(true);
    try {
      await confirmConsultationPayment(consultation.id, result);
      await fetchDetail();
      Alert.alert('Payment successful', 'Your appointment is confirmed. We will see you at your scheduled time.');
    } catch {
      // Payment may have been captured even if confirmation failed; tell the
      // patient not to retry blindly.
      Alert.alert(
        'Payment received, confirmation pending',
        'Your payment went through but we could not confirm the appointment automatically. Please refresh in a moment or contact support — do not pay again.',
      );
    } finally {
      setPaying(false);
    }
  }, [consultation, fetchDetail]);

  const handleCheckoutFailure = useCallback((err: { code: string; description: string }) => {
    setCheckoutVisible(false);
    setPaying(false);
    Alert.alert(
      'Payment failed',
      err.description || 'Your payment could not be completed. No amount was charged. Please try again.',
    );
  }, []);

  const handleCheckoutDismiss = useCallback(() => {
    setCheckoutVisible(false);
    setPaying(false);
  }, []);

  const openReschedule = useCallback(async () => {
    if (!consultation) return;
    if (!consultation.doctor_id) {
      setSlotsError('No doctor assigned yet.');
      setShowReschedule(true);
      setSlotsLoading(false);
      return;
    }
    setShowReschedule(true);
    setSlotsLoading(true);
    setSlotsError(null);
    try {
      // The backend rejects slots inside the 24h reschedule window, so only
      // request slots from 24h out — patients never see slots they can't pick.
      const from   = new Date(Date.now() + RESCHEDULE_WINDOW_MS);
      const future = new Date(from.getTime() + 14 * 24 * 60 * 60 * 1000);
      const data = await apiFetch<AvailableSlot[]>(
        `/v1/clinic/patient/consultations/slots?doctor_id=${consultation.doctor_id}` +
        `&date_from=${from.toISOString()}&date_to=${future.toISOString()}`,
      );
      setSlots(data);
    } catch {
      setSlotsError('Could not load available slots.');
    } finally {
      setSlotsLoading(false);
    }
  }, [consultation]);

  const handleReschedule = useCallback(async (slot: AvailableSlot) => {
    Alert.alert(
      'Move appointment?',
      `Reschedule to ${formatSlotDate(slot.slot_start)} at ${formatSlotTime(slot.slot_start)}?`,
      [
        { text: 'Keep current time', style: 'cancel' },
        {
          text: 'Reschedule',
          onPress: async () => {
            setRescheduling(true);
            try {
              await apiFetch(`/v1/clinic/patient/consultations/${id}/reschedule`, {
                method: 'POST',
                body: JSON.stringify({ slot_id: slot.id }),
              });
              setShowReschedule(false);
              await fetchDetail();
            } catch (e: unknown) {
              const msg = e instanceof Error ? e.message : '';
              const friendly = msg.includes('reschedule_window_closed')
                ? 'Appointments can only be rescheduled more than 24 hours in advance.'
                : msg.includes('slot_not_available')
                  ? 'That slot was just taken. Please pick another time.'
                  : 'Could not reschedule. Please try again.';
              Alert.alert('Error', friendly);
            } finally {
              setRescheduling(false);
            }
          },
        },
      ],
    );
  }, [id, fetchDetail]);

  const joinScale   = useSharedValue(1);
  const joinAnim    = useAnimatedStyle(() => ({ transform: [{ scale: joinScale.value }] }));
  const payScale    = useSharedValue(1);
  const payAnim     = useAnimatedStyle(() => ({ transform: [{ scale: payScale.value }] }));
  const cancelScale = useSharedValue(1);
  const cancelAnim  = useAnimatedStyle(() => ({ transform: [{ scale: cancelScale.value }] }));

  const bg        = isDark ? colors.forestInk     : colors.ivory;
  const textPri   = isDark ? colors.ivoryText        : colors.ink;
  const textSub   = isDark ? colors.stoneDim    : colors.stone;
  const cardBg    = isDark ? colors.forestSurface : colors.white;
  const cardBdr   = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)';
  const divider   = isDark ? 'rgba(255,255,255,0.06)' : colors.borderLight;

  if (loading) {
    return <View style={[styles.center, { backgroundColor: bg }]}><ActivityIndicator color={colors.jade} /></View>;
  }

  if (error || !consultation) {
    return (
      <View style={[styles.center, { backgroundColor: bg }]}>
        <Text style={[styles.errorText, { color: colors.alert }]}>{error ?? 'Consultation not found.'}</Text>
        <Pressable onPress={() => router.back()} accessibilityLabel="Go back">
          <Text style={[styles.link, { color: colors.jade }]}>Go back</Text>
        </Pressable>
      </View>
    );
  }

  const sc        = STATUS_COLOR[consultation.status];
  const canCancel = CANCELLABLE.includes(consultation.status);
  const canReschedule =
    RESCHEDULABLE.includes(consultation.status) &&
    consultation.scheduled_start_at !== null &&
    new Date(consultation.scheduled_start_at).getTime() - Date.now() > RESCHEDULE_WINDOW_MS;

  return (
    <ScrollView
      style={[styles.flex, { backgroundColor: bg }]}
      contentContainerStyle={styles.container}
      refreshControl={
        <RefreshControl refreshing={isFetching && !loading} onRefresh={refetch} tintColor={colors.jade} />
      }
    >

      {/* Status pill */}
      <View style={[styles.statusPill, { backgroundColor: sc + '18' }]}>
        <View style={[styles.statusDot, { backgroundColor: sc }]} />
        <Text style={[styles.statusText, { color: sc }]}>{STATUS_LABEL[consultation.status]}</Text>
      </View>

      {/* Hero title */}
      <Text style={[styles.category, { color: textPri }]}>
        {formatCategory(consultation.condition_category)}
      </Text>
      <Text style={[styles.type, { color: textSub }]}>
        {consultation.consultation_type === 'initial' ? 'Initial consultation' : 'Follow-up'}
      </Text>

      {/* Pending-assignment explainer */}
      {consultation.status === 'requested' && (
        <View style={[styles.infoBanner, { backgroundColor: colors.saffron + '14', borderColor: colors.saffron + '40' }]}>
          <Text style={[styles.infoBannerText, { color: textPri }]}>
            A care coordinator is reviewing your request and will assign the right specialist. You'll be notified to confirm and pay once a doctor and time are set.
          </Text>
        </View>
      )}

      {/* Details card */}
      <View style={[styles.card, { backgroundColor: cardBg, borderColor: cardBdr }]}>
        {consultation.doctor_name && (
          <Row
            label="Doctor"
            value={
              `Dr ${consultation.doctor_name}` +
              (consultation.doctor_specialty && consultation.doctor_specialty.length > 0
                ? ` · ${formatCategory(consultation.doctor_specialty[0])}`
                : '')
            }
            textPri={textPri}
            textSub={textSub}
            borderColor={divider}
          />
        )}
        {consultation.scheduled_start_at && (
          <Row label="Scheduled" value={formatDateTime(consultation.scheduled_start_at)} textPri={textPri} textSub={textSub} borderColor={divider} />
        )}
        {consultation.status === 'requested' && (
          <Row label="Preferred time" value={formatTimeWindow(consultation.preferred_time_window)} textPri={textPri} textSub={textSub} borderColor={divider} />
        )}
        {consultation.requirement_notes && (
          <Row label="Your note" value={consultation.requirement_notes} textPri={textPri} textSub={textSub} borderColor={divider} />
        )}
        {consultation.consultation_fee_paise != null && (
          <Row label="Fee" value={formatRupees(consultation.consultation_fee_paise)} textPri={textPri} textSub={textSub} borderColor={divider} />
        )}
        {consultation.cancellation_reason && (
          <Row label="Cancellation" value={consultation.cancellation_reason} textPri={textPri} textSub={textSub} borderColor={divider} />
        )}
        {consultation.actual_start_at && (
          <Row label="Started at" value={formatDateTime(consultation.actual_start_at)} textPri={textPri} textSub={textSub} borderColor={divider} />
        )}
        {consultation.actual_end_at && (
          <Row label="Ended at" value={formatDateTime(consultation.actual_end_at)} textPri={textPri} textSub={textSub} borderColor="transparent" />
        )}
      </View>

      {/* Pay to confirm (doctor + slot assigned, awaiting payment) */}
      {consultation.status === 'scheduled' && consultation.payment && (
        <Animated.View style={payAnim}>
          <Pressable
            style={[styles.joinBtn, paying && styles.disabled]}
            onPress={handlePay}
            onPressIn={() => { payScale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
            onPressOut={() => { payScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
            disabled={paying}
            accessibilityLabel="Pay to confirm appointment"
          >
            <Text style={styles.joinBtnIcon}>💳</Text>
            <Text style={styles.joinBtnText}>
              {paying ? 'Processing…' : `Pay ${formatRupees(consultation.payment.amount_paise)} to confirm`}
            </Text>
          </Pressable>
        </Animated.View>
      )}

      {/* Join video call */}
      {(consultation.status === 'confirmed' || consultation.status === 'in_progress') && consultation.video_room_id && (
        <Animated.View style={joinAnim}>
          <Pressable
            style={styles.joinBtn}
            onPress={() => router.push(`/consultations/join/${consultation.id}`)}
            onPressIn={() => { joinScale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
            onPressOut={() => { joinScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
            accessibilityLabel="Join video consultation"
          >
            <Text style={styles.joinBtnIcon}>📹</Text>
            <Text style={styles.joinBtnText}>Join video call</Text>
          </Pressable>
        </Animated.View>
      )}

      {/* Reschedule */}
      {canReschedule && !showReschedule && (
        <Pressable
          style={[styles.secondaryBtn, { borderColor: colors.jade + '60' }]}
          onPress={openReschedule}
          accessibilityLabel="Reschedule this consultation"
        >
          <Text style={[styles.secondaryBtnText, { color: colors.jade }]}>Reschedule appointment</Text>
        </Pressable>
      )}

      {/* Reschedule slot picker */}
      {showReschedule && (
        <View style={[styles.card, { backgroundColor: cardBg, borderColor: cardBdr, padding: spacing[5] }]}>
          <Text style={[styles.panelTitle, { color: textPri }]}>Pick a new time</Text>

          {slotsLoading && <ActivityIndicator color={colors.jade} style={{ marginVertical: spacing[4] }} />}

          {slotsError && (
            <Text style={[styles.errorText, { color: colors.alert }]}>{slotsError}</Text>
          )}

          {!slotsLoading && !slotsError && slots.length === 0 && (
            <Text style={[styles.panelEmpty, { color: textSub }]}>
              No open slots in the next 14 days. Please try again later.
            </Text>
          )}

          {!slotsLoading && slots.length > 0 && (
            <View style={styles.slotGrid}>
              {slots.map(slot => (
                <Pressable
                  key={slot.id}
                  onPress={() => handleReschedule(slot)}
                  disabled={rescheduling}
                  accessibilityLabel={`Move to ${formatSlotDate(slot.slot_start)} at ${formatSlotTime(slot.slot_start)}`}
                  style={[styles.slotCard, { borderColor: cardBdr }, rescheduling && styles.disabled]}
                >
                  <Text style={[styles.slotDate, { color: textSub }]}>{formatSlotDate(slot.slot_start)}</Text>
                  <Text style={[styles.slotTime, { color: textPri }]}>{formatSlotTime(slot.slot_start)}</Text>
                </Pressable>
              ))}
            </View>
          )}

          <Pressable
            onPress={() => setShowReschedule(false)}
            disabled={rescheduling}
            accessibilityLabel="Cancel rescheduling"
            style={styles.panelBack}
          >
            <Text style={[styles.backBtnText, { color: textSub }]}>Keep current time</Text>
          </Pressable>
        </View>
      )}

      {/* Cancel */}
      {canCancel && (
        <Animated.View style={cancelAnim}>
          <Pressable
            style={[styles.cancelBtn, { borderColor: colors.alert + '60' }, cancelling && styles.disabled]}
            onPress={handleCancel}
            onPressIn={() => { cancelScale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
            onPressOut={() => { cancelScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
            disabled={cancelling}
            accessibilityLabel="Cancel this consultation"
          >
            <Text style={[styles.cancelBtnText, { color: colors.alert }]}>
              {cancelling ? 'Cancelling…' : (isRequest ? 'Withdraw request' : 'Cancel appointment')}
            </Text>
          </Pressable>
        </Animated.View>
      )}

      {/* Razorpay checkout (mounted only when paying) */}
      {consultation.payment && (
        <RazorpayCheckout
          visible={checkoutVisible}
          orderId={consultation.payment.razorpay_order_id}
          amountPaise={consultation.payment.amount_paise}
          currency={consultation.payment.currency}
          keyId={RAZORPAY_KEY_ID}
          prefill={{
            name: me?.name ?? undefined,
            email: me?.email ?? undefined,
            contact: me?.phone ?? undefined,
          }}
          onSuccess={handleCheckoutSuccess}
          onFailure={handleCheckoutFailure}
          onDismiss={handleCheckoutDismiss}
        />
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
    paddingBottom: spacing[10],
    gap: spacing[4],
  },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing[3] },

  statusPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
    alignSelf: 'flex-start',
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1],
    borderRadius: borderRadius.full,
  },
  statusDot: { width: 8, height: 8, borderRadius: 4 },
  statusText: { fontFamily: fontFamily.body, fontSize: fontSize.sm, fontWeight: '700' },

  category: { fontFamily: fontFamily.display, fontSize: fontSize.h2, fontWeight: '600', lineHeight: 32 },
  type:     { fontFamily: fontFamily.body, fontSize: fontSize.body },

  card: {
    borderRadius: borderRadius.xxl,
    overflow: 'hidden',
    borderWidth: 1,
    boxShadow: '0 6px 14px rgba(0,0,0,0.07)',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingHorizontal: spacing[5],
    paddingVertical: spacing[4],
    borderBottomWidth: 1,
    gap: spacing[3],
  },
  rowLabel: { fontFamily: fontFamily.body, fontSize: fontSize.sm, flex: 1 },
  rowValue: { fontFamily: fontFamily.body, fontSize: fontSize.sm, fontWeight: '600', flex: 2, textAlign: 'right' },

  joinBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing[2],
    height: 56,
    backgroundColor: colors.forest,
    borderRadius: borderRadius.xxl,
    boxShadow: `0 8px 16px ${withAlpha(colors.forest, 0.30)}`,
  },
  joinBtnIcon: { fontSize: 20 },
  joinBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700', color: colors.ivoryText },

  cancelBtn: {
    height: 52,
    borderWidth: 1.5,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cancelBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600' },
  disabled: { opacity: 0.50 },

  secondaryBtn: {
    height: 52,
    borderWidth: 1.5,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
  },
  secondaryBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600' },

  panelTitle: { fontFamily: fontFamily.display, fontSize: fontSize.bodyLg, fontWeight: '600', marginBottom: spacing[3] },
  panelEmpty: { fontFamily: fontFamily.body, fontSize: fontSize.sm, lineHeight: 20, paddingVertical: spacing[2] },
  panelBack:  { alignItems: 'center', paddingTop: spacing[4] },
  backBtnText:{ fontFamily: fontFamily.body, fontSize: fontSize.sm },

  slotGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
  slotCard: {
    borderRadius: borderRadius.xl,
    padding: spacing[4],
    borderWidth: 1,
    minWidth: 130,
    gap: spacing[1],
  },
  slotDate: { fontFamily: fontFamily.body, fontSize: fontSize.sm },
  slotTime: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700' },

  errorText: { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center' },
  link:      { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600' },

  infoBanner: {
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    padding: spacing[4],
  },
  infoBannerText: { fontFamily: fontFamily.body, fontSize: fontSize.sm, lineHeight: 20 },
});
