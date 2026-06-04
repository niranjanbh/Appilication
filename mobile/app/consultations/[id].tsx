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
import { useLocalSearchParams, useRouter } from 'expo-router';
import { apiFetch } from '../../lib/api/client';
import { colors, fontFamily, fontSize, spacing, borderRadius } from '../../lib/design-tokens';

// ── Types ──────────────────────────────────────────────────────────────────────

type ConsultationStatus =
  | 'scheduled'
  | 'confirmed'
  | 'in_progress'
  | 'completed'
  | 'cancelled'
  | 'no_show';

interface Consultation {
  id: string;
  doctor_id: string;
  condition_category: string;
  consultation_type: string;
  scheduled_start_at: string;
  scheduled_end_at: string;
  actual_start_at: string | null;
  actual_end_at: string | null;
  status: ConsultationStatus;
  video_room_id: string | null;
  consultation_fee_paise: number;
  payment_id: string | null;
  cancellation_reason: string | null;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString('en-IN', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });
}

function formatRupees(paise: number): string {
  return `₹${(paise / 100).toFixed(0)}`;
}

function formatCategory(cat: string): string {
  return cat.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

const STATUS_LABEL: Record<ConsultationStatus, string> = {
  scheduled: 'Scheduled',
  confirmed: 'Confirmed',
  in_progress: 'In Progress',
  completed: 'Completed',
  cancelled: 'Cancelled',
  no_show: 'No Show',
};

const STATUS_COLOR: Record<ConsultationStatus, string> = {
  scheduled: colors.forest,
  confirmed: '#2563EB',
  in_progress: '#D97706',
  completed: colors.stone,
  cancelled: '#DC2626',
  no_show: '#DC2626',
};

const CANCELLABLE: ConsultationStatus[] = ['scheduled', 'confirmed'];

// ── Detail row ─────────────────────────────────────────────────────────────────

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

// ── Screen ─────────────────────────────────────────────────────────────────────

export default function ConsultationDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();

  const [consultation, setConsultation] = useState<Consultation | null>(null);
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  const handleCancel = useCallback(() => {
    Alert.alert(
      'Cancel consultation?',
      'Cancellations made more than 24 hours before your appointment qualify for a full refund.',
      [
        { text: 'Keep appointment', style: 'cancel' },
        {
          text: 'Cancel appointment',
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
              Alert.alert('Error', 'Could not cancel the appointment. Please try again.');
            } finally {
              setCancelling(false);
            }
          },
        },
      ],
    );
  }, [id, fetchDetail]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.forest} />
      </View>
    );
  }

  if (error || !consultation) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{error ?? 'Consultation not found.'}</Text>
        <Pressable onPress={() => router.back()} accessibilityLabel="Go back">
          <Text style={styles.link}>Go back</Text>
        </Pressable>
      </View>
    );
  }

  const statusColor = STATUS_COLOR[consultation.status];
  const canCancel = CANCELLABLE.includes(consultation.status);

  return (
    <ScrollView style={styles.flex} contentContainerStyle={styles.container}>
      {/* Status banner */}
      <View style={[styles.statusBanner, { backgroundColor: statusColor + '18' }]}>
        <Text style={[styles.statusText, { color: statusColor }]}>
          {STATUS_LABEL[consultation.status]}
        </Text>
      </View>

      {/* Category + type */}
      <Text style={styles.category}>{formatCategory(consultation.condition_category)}</Text>
      <Text style={styles.type}>
        {consultation.consultation_type === 'initial' ? 'Initial consultation' : 'Follow-up'}
      </Text>

      {/* Details */}
      <View style={styles.section}>
        <Row label="Scheduled" value={formatDateTime(consultation.scheduled_start_at)} />
        <Row label="Fee" value={formatRupees(consultation.consultation_fee_paise)} />
        {consultation.cancellation_reason ? (
          <Row label="Cancellation reason" value={consultation.cancellation_reason} />
        ) : null}
        {consultation.actual_start_at ? (
          <Row label="Started at" value={formatDateTime(consultation.actual_start_at)} />
        ) : null}
        {consultation.actual_end_at ? (
          <Row label="Ended at" value={formatDateTime(consultation.actual_end_at)} />
        ) : null}
      </View>

      {/* Join button for confirmed / in-progress */}
      {(consultation.status === 'confirmed' || consultation.status === 'in_progress') &&
        consultation.video_room_id ? (
        <Pressable
          style={styles.joinButton}
          onPress={() => router.push(`/consultations/join/${consultation.id}`)}
          accessibilityLabel="Join video consultation"
        >
          <Text style={styles.joinButtonText}>Join video call</Text>
        </Pressable>
      ) : null}

      {/* Cancel */}
      {canCancel ? (
        <Pressable
          style={[styles.cancelButton, cancelling && styles.disabled]}
          onPress={handleCancel}
          disabled={cancelling}
          accessibilityLabel="Cancel this consultation"
        >
          <Text style={styles.cancelButtonText}>
            {cancelling ? 'Cancelling…' : 'Cancel appointment'}
          </Text>
        </Pressable>
      ) : null}
    </ScrollView>
  );
}

// ── Styles ─────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.ivory },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
    paddingBottom: spacing[10],
    gap: spacing[4],
  },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing[3] },
  statusBanner: {
    alignSelf: 'flex-start',
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1],
    borderRadius: borderRadius.full,
  },
  statusText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: '700',
  },
  category: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    color: colors.forest,
    fontWeight: '500',
    marginTop: spacing[1],
  },
  type: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
  },
  section: {
    backgroundColor: colors.white,
    borderRadius: borderRadius.lg,
    padding: spacing[4],
    gap: spacing[3],
    marginTop: spacing[2],
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: spacing[3],
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
  joinButton: {
    backgroundColor: colors.forest,
    borderRadius: borderRadius.lg,
    paddingVertical: spacing[4],
    alignItems: 'center',
    marginTop: spacing[2],
  },
  joinButtonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '700',
    color: colors.white,
  },
  cancelButton: {
    borderWidth: 1,
    borderColor: '#DC2626',
    borderRadius: borderRadius.lg,
    paddingVertical: spacing[4],
    alignItems: 'center',
    marginTop: spacing[2],
  },
  cancelButtonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
    color: '#DC2626',
  },
  disabled: { opacity: 0.5 },
  errorText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    textAlign: 'center',
  },
  link: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.forest,
    fontWeight: '600',
  },
});
