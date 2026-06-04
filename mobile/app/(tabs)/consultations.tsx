import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
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
  status: ConsultationStatus;
  consultation_fee_paise: number;
  payment_id: string | null;
  cancellation_reason: string | null;
}

interface ListResponse {
  items: Consultation[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

const UPCOMING_STATUSES: ConsultationStatus[] = ['scheduled', 'confirmed', 'in_progress'];

function isUpcoming(c: Consultation): boolean {
  return UPCOMING_STATUSES.includes(c.status);
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
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

// ── Card component ─────────────────────────────────────────────────────────────

function ConsultationCard({
  item,
  onPress,
}: {
  item: Consultation;
  onPress: () => void;
}) {
  const statusColor = STATUS_COLOR[item.status];
  return (
    <Pressable
      style={styles.card}
      onPress={onPress}
      accessibilityLabel={`Consultation on ${formatDate(item.scheduled_start_at)}, status ${STATUS_LABEL[item.status]}`}
    >
      <View style={styles.cardHeader}>
        <Text style={styles.cardDate}>
          {formatDate(item.scheduled_start_at)} · {formatTime(item.scheduled_start_at)}
        </Text>
        <View style={[styles.statusPill, { backgroundColor: statusColor + '18' }]}>
          <Text style={[styles.statusText, { color: statusColor }]}>
            {STATUS_LABEL[item.status]}
          </Text>
        </View>
      </View>
      <Text style={styles.cardCategory}>{formatCategory(item.condition_category)}</Text>
      <Text style={styles.cardType}>
        {item.consultation_type === 'initial' ? 'Initial consultation' : 'Follow-up'} ·{' '}
        {formatRupees(item.consultation_fee_paise)}
      </Text>
    </Pressable>
  );
}

// ── Screen ─────────────────────────────────────────────────────────────────────

export default function ConsultationsScreen() {
  const router = useRouter();
  const [consultations, setConsultations] = useState<Consultation[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchConsultations = useCallback(async () => {
    try {
      const data = await apiFetch<ListResponse>('/v1/clinic/patient/consultations?page_size=50');
      setConsultations(data.items);
      setError(null);
    } catch {
      setError('Could not load consultations. Please try again.');
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    fetchConsultations().finally(() => setLoading(false));
  }, [fetchConsultations]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchConsultations();
    setRefreshing(false);
  }, [fetchConsultations]);

  const upcoming = consultations.filter(isUpcoming);
  const past = consultations.filter((c) => !isUpcoming(c));

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.forest} />
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.flex}
      contentContainerStyle={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>Consultations</Text>
        <Pressable
          style={styles.bookButton}
          onPress={() => router.push('/consultations/book')}
          accessibilityLabel="Book a consultation"
        >
          <Text style={styles.bookButtonText}>+ Book</Text>
        </Pressable>
      </View>

      {error && <Text style={styles.error}>{error}</Text>}

      {/* Upcoming */}
      <Text style={styles.sectionLabel}>Upcoming</Text>
      {upcoming.length === 0 ? (
        <View style={styles.emptyCard}>
          <Text style={styles.emptyText}>No upcoming consultations</Text>
          <Text style={styles.emptySub}>Book a consultation to get started.</Text>
        </View>
      ) : (
        upcoming.map((c) => (
          <ConsultationCard
            key={c.id}
            item={c}
            onPress={() => router.push(`/consultations/${c.id}`)}
          />
        ))
      )}

      {/* Past */}
      {past.length > 0 && (
        <>
          <Text style={[styles.sectionLabel, styles.sectionLabelLower]}>Past</Text>
          {past.map((c) => (
            <ConsultationCard
              key={c.id}
              item={c}
              onPress={() => router.push(`/consultations/${c.id}`)}
            />
          ))}
        </>
      )}
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
  },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing[5],
  },
  title: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    color: colors.forest,
    fontWeight: '500',
  },
  bookButton: {
    backgroundColor: colors.forest,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[2],
    borderRadius: borderRadius.full,
  },
  bookButtonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: colors.white,
    fontWeight: '600',
  },
  sectionLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: '700',
    color: colors.stone,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: spacing[3],
    marginTop: spacing[1],
  },
  sectionLabelLower: { marginTop: spacing[6] },
  card: {
    backgroundColor: colors.white,
    borderRadius: borderRadius.lg,
    padding: spacing[4],
    marginBottom: spacing[3],
    gap: spacing[1],
    shadowColor: '#000',
    shadowOpacity: 0.04,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 1,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing[1],
  },
  cardDate: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: colors.stone,
  },
  statusPill: {
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
    borderRadius: borderRadius.full,
  },
  statusText: {
    fontFamily: fontFamily.body,
    fontSize: 11,
    fontWeight: '600',
  },
  cardCategory: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.ink,
    fontWeight: '600',
  },
  cardType: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: colors.stone,
  },
  emptyCard: {
    backgroundColor: colors.white,
    borderRadius: borderRadius.lg,
    padding: spacing[5],
    alignItems: 'center',
    gap: spacing[2],
    marginBottom: spacing[3],
  },
  emptyText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    fontWeight: '600',
  },
  emptySub: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: colors.stone,
    textAlign: 'center',
  },
  error: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: '#DC2626',
    marginBottom: spacing[4],
  },
});
