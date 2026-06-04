import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  useColorScheme,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { apiFetch } from '../../lib/api/client';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

// ── Types ──────────────────────────────────────────────────────────────────────

type ConsultationStatus =
  | 'scheduled' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled' | 'no_show';

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
function isUpcoming(c: Consultation): boolean { return UPCOMING_STATUSES.includes(c.status); }
function formatDate(iso: string) { return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }); }
function formatTime(iso: string) { return new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true }); }
function formatRupees(p: number) { return `₹${(p / 100).toFixed(0)}`; }
function formatCat(cat: string)  { return cat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()); }

const STATUS_LABEL: Record<ConsultationStatus, string> = {
  scheduled: 'Scheduled', confirmed: 'Confirmed', in_progress: 'In Progress',
  completed: 'Completed', cancelled: 'Cancelled', no_show: 'No Show',
};

const STATUS_COLOR: Record<ConsultationStatus, string> = {
  scheduled:   colors.navyDeep,
  confirmed:   colors.electricBlue,
  in_progress: colors.warningAmber,
  completed:   colors.successGreen,
  cancelled:   colors.criticalRed,
  no_show:     colors.criticalRed,
};

// ── Card ───────────────────────────────────────────────────────────────────────

function ConsultationCard({
  item,
  isDark,
  onPress,
}: {
  item: Consultation;
  isDark: boolean;
  onPress: () => void;
}) {
  const scale = useSharedValue(1);
  const anim  = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));
  const sc    = STATUS_COLOR[item.status];

  const cardBg  = isDark ? colors.nightSurface : colors.white;
  const cardBdr = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)';
  const textPri = isDark ? colors.white     : colors.navyDeep;
  const textSub = isDark ? colors.slateText : colors.coolGray;

  return (
    <Animated.View style={anim}>
      <Pressable
        style={[styles.card, { backgroundColor: cardBg, borderColor: cardBdr }]}
        onPress={onPress}
        onPressIn={() => { scale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
        onPressOut={() => { scale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
        accessibilityLabel={`Consultation on ${formatDate(item.scheduled_start_at)}, ${STATUS_LABEL[item.status]}`}
      >
        <View style={styles.cardHeader}>
          <Text style={[styles.cardDate, { color: textSub }]}>
            {formatDate(item.scheduled_start_at)} · {formatTime(item.scheduled_start_at)}
          </Text>
          <View style={[styles.statusPill, { backgroundColor: sc + '18' }]}>
            <Text style={[styles.statusText, { color: sc }]}>{STATUS_LABEL[item.status]}</Text>
          </View>
        </View>
        <Text style={[styles.cardCategory, { color: textPri }]}>
          {formatCat(item.condition_category)}
        </Text>
        <Text style={[styles.cardMeta, { color: textSub }]}>
          {item.consultation_type === 'initial' ? 'Initial consultation' : 'Follow-up'} · {formatRupees(item.consultation_fee_paise)}
        </Text>
      </Pressable>
    </Animated.View>
  );
}

// ── Screen ─────────────────────────────────────────────────────────────────────

export default function ConsultationsScreen() {
  const router  = useRouter();
  const isDark  = useColorScheme() === 'dark';
  const [consultations, setConsultations] = useState<Consultation[]>([]);
  const [loading,    setLoading]    = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error,      setError]      = useState<string | null>(null);

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

  const bookScale = useSharedValue(1);
  const bookAnim  = useAnimatedStyle(() => ({ transform: [{ scale: bookScale.value }] }));

  const upcoming = consultations.filter(isUpcoming);
  const past     = consultations.filter(c => !isUpcoming(c));
  const bg       = isDark ? colors.midnight : colors.skyMist;
  const textPri  = isDark ? colors.white    : colors.navyDeep;
  const textSub  = isDark ? colors.slateText : colors.coolGray;

  if (loading) {
    return (
      <View style={[styles.center, { backgroundColor: bg }]}>
        <ActivityIndicator color={colors.electricBlue} />
      </View>
    );
  }

  return (
    <ScrollView
      style={[styles.flex, { backgroundColor: bg }]}
      contentContainerStyle={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.electricBlue} />}
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={[styles.title, { color: textPri }]}>Consultations</Text>
        <Animated.View style={bookAnim}>
          <Pressable
            style={styles.bookBtn}
            onPress={() => router.push('/consultations/book')}
            onPressIn={() => { bookScale.value = withSpring(0.94, { mass: 0.3, stiffness: 500 }); }}
            onPressOut={() => { bookScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
            accessibilityLabel="Book a consultation"
          >
            <Text style={styles.bookBtnText}>+ Book</Text>
          </Pressable>
        </Animated.View>
      </View>

      {error && <Text style={styles.error}>{error}</Text>}

      {/* Upcoming */}
      <Text style={[styles.sectionLabel, { color: textSub }]}>Upcoming</Text>
      {upcoming.length === 0 ? (
        <View style={[styles.emptyCard, { backgroundColor: isDark ? colors.nightSurface : colors.white, borderColor: isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)' }]}>
          <Text style={styles.emptyIcon}>📅</Text>
          <Text style={[styles.emptyText, { color: textPri }]}>No upcoming consultations</Text>
          <Text style={[styles.emptySub, { color: textSub }]}>Book a consultation to get started.</Text>
        </View>
      ) : (
        upcoming.map(c => (
          <ConsultationCard
            key={c.id}
            item={c}
            isDark={isDark}
            onPress={() => router.push(`/consultations/${c.id}`)}
          />
        ))
      )}

      {/* Past */}
      {past.length > 0 && (
        <>
          <Text style={[styles.sectionLabel, styles.sectionLabelLower, { color: textSub }]}>Past</Text>
          {past.map(c => (
            <ConsultationCard
              key={c.id}
              item={c}
              isDark={isDark}
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
  flex: { flex: 1 },
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
    marginBottom: spacing[6],
  },
  title: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    fontWeight: '600',
  },
  bookBtn: {
    height: 36,
    paddingHorizontal: spacing[4],
    backgroundColor: colors.navyDeep,
    borderRadius: borderRadius.full,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: colors.navyDeep,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    elevation: 4,
  },
  bookBtnText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: colors.white,
    fontWeight: '700',
  },

  sectionLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: spacing[3],
  },
  sectionLabelLower: { marginTop: spacing[6] },

  card: {
    borderRadius: borderRadius.xl,
    padding: spacing[4],
    marginBottom: spacing[3],
    gap: spacing[2],
    borderWidth: 1,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
    elevation: 2,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  cardDate: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
  },
  statusPill: {
    paddingHorizontal: spacing[2],
    paddingVertical: 3,
    borderRadius: borderRadius.full,
  },
  statusText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
  },
  cardCategory: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    fontWeight: '700',
  },
  cardMeta: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
  },

  emptyCard: {
    borderRadius: borderRadius.xl,
    padding: spacing[6],
    alignItems: 'center',
    gap: spacing[2],
    marginBottom: spacing[3],
    borderWidth: 1,
  },
  emptyIcon:  { fontSize: 32 },
  emptyText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '700',
    textAlign: 'center',
  },
  emptySub: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    textAlign: 'center',
  },

  error: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: colors.criticalRed,
    marginBottom: spacing[4],
  },
});
