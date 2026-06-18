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
import { useLocalSearchParams, useRouter } from 'expo-router';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { apiFetch } from '../../lib/api/client';
import { borderRadius, colors, fontFamily, fontSize, spacing , withAlpha } from '../../lib/design-tokens';

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

// ── Helpers ────────────────────────────────────────────────────────────────────

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-IN', {
    day: 'numeric', month: 'long', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: true,
  });
}
function formatRupees(p: number): string { return `₹${(p / 100).toFixed(0)}`; }
function formatCategory(cat: string): string {
  return cat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

const STATUS_LABEL: Record<ConsultationStatus, string> = {
  requested: 'Awaiting assignment', scheduled: 'Scheduled', confirmed: 'Confirmed',
  in_progress: 'In Progress', completed: 'Completed', cancelled: 'Cancelled', no_show: 'No Show',
};

const STATUS_COLOR: Record<ConsultationStatus, string> = {
  requested:   colors.warningAmber,
  scheduled:   colors.navyDeep,
  confirmed:   colors.electricBlue,
  in_progress: colors.warningAmber,
  completed:   colors.successGreen,
  cancelled:   colors.criticalRed,
  no_show:     colors.criticalRed,
};

function formatTimeWindow(w: string | null): string {
  if (!w) return 'Flexible';
  return w.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

const CANCELLABLE: ConsultationStatus[] = ['requested', 'scheduled', 'confirmed'];

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

  const [consultation, setConsultation] = useState<Consultation | null>(null);
  const [loading,    setLoading]    = useState(true);
  const [cancelling, setCancelling] = useState(false);
  const [paying,     setPaying]     = useState(false);
  const [error,      setError]      = useState<string | null>(null);

  const fetchDetail = useCallback(async () => {
    try {
      const data = await apiFetch<Consultation>(`/v1/clinic/patient/consultations/${id}`);
      setConsultation(data);
      setError(null);
    } catch {
      setError('Could not load consultation details.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { fetchDetail(); }, [fetchDetail]);

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

  // Pay to confirm once a coordinator has assigned a doctor + slot. Razorpay
  // checkout runs via the embedded WebView; on success the order details are
  // posted back and verified through the confirm-payment endpoint.
  const handlePay = useCallback(() => {
    if (!consultation?.payment) return;
    const order = consultation.payment;
    setPaying(true);
    Alert.alert(
      'Confirm your appointment',
      `Amount: ₹${(order.amount_paise / 100).toFixed(0)}\n\nYou'll be redirected to Razorpay to complete payment. Your appointment is confirmed once payment succeeds.\n\nOrder: ${order.razorpay_order_id}`,
      [{ text: 'OK', onPress: () => setPaying(false) }],
    );
  }, [consultation]);

  const joinScale   = useSharedValue(1);
  const joinAnim    = useAnimatedStyle(() => ({ transform: [{ scale: joinScale.value }] }));
  const payScale    = useSharedValue(1);
  const payAnim     = useAnimatedStyle(() => ({ transform: [{ scale: payScale.value }] }));
  const cancelScale = useSharedValue(1);
  const cancelAnim  = useAnimatedStyle(() => ({ transform: [{ scale: cancelScale.value }] }));

  const bg        = isDark ? colors.midnight     : colors.skyMist;
  const textPri   = isDark ? colors.white        : colors.navyDeep;
  const textSub   = isDark ? colors.slateText    : colors.coolGray;
  const cardBg    = isDark ? colors.nightSurface : colors.white;
  const cardBdr   = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)';
  const divider   = isDark ? 'rgba(255,255,255,0.06)' : colors.borderLight;

  if (loading) {
    return <View style={[styles.center, { backgroundColor: bg }]}><ActivityIndicator color={colors.electricBlue} /></View>;
  }

  if (error || !consultation) {
    return (
      <View style={[styles.center, { backgroundColor: bg }]}>
        <Text style={[styles.errorText, { color: colors.criticalRed }]}>{error ?? 'Consultation not found.'}</Text>
        <Pressable onPress={() => router.back()} accessibilityLabel="Go back">
          <Text style={[styles.link, { color: colors.electricBlue }]}>Go back</Text>
        </Pressable>
      </View>
    );
  }

  const sc        = STATUS_COLOR[consultation.status];
  const canCancel = CANCELLABLE.includes(consultation.status);

  return (
    <ScrollView style={[styles.flex, { backgroundColor: bg }]} contentContainerStyle={styles.container}>

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
        <View style={[styles.infoBanner, { backgroundColor: colors.warningAmber + '14', borderColor: colors.warningAmber + '40' }]}>
          <Text style={[styles.infoBannerText, { color: textPri }]}>
            A care coordinator is reviewing your request and will assign the right specialist. You'll be notified to confirm and pay once a doctor and time are set.
          </Text>
        </View>
      )}

      {/* Details card */}
      <View style={[styles.card, { backgroundColor: cardBg, borderColor: cardBdr }]}>
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

      {/* Cancel */}
      {canCancel && (
        <Animated.View style={cancelAnim}>
          <Pressable
            style={[styles.cancelBtn, { borderColor: colors.criticalRed + '60' }, cancelling && styles.disabled]}
            onPress={handleCancel}
            onPressIn={() => { cancelScale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
            onPressOut={() => { cancelScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
            disabled={cancelling}
            accessibilityLabel="Cancel this consultation"
          >
            <Text style={[styles.cancelBtnText, { color: colors.criticalRed }]}>
              {cancelling ? 'Cancelling…' : (isRequest ? 'Withdraw request' : 'Cancel appointment')}
            </Text>
          </Pressable>
        </Animated.View>
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
    backgroundColor: colors.navyDeep,
    borderRadius: borderRadius.xxl,
    boxShadow: `0 8px 16px ${withAlpha(colors.navyDeep, 0.30)}`,
  },
  joinBtnIcon: { fontSize: 20 },
  joinBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700', color: colors.white },

  cancelBtn: {
    height: 52,
    borderWidth: 1.5,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cancelBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600' },
  disabled: { opacity: 0.50 },

  errorText: { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center' },
  link:      { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600' },

  infoBanner: {
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    padding: spacing[4],
  },
  infoBannerText: { fontFamily: fontFamily.body, fontSize: fontSize.sm, lineHeight: 20 },
});
