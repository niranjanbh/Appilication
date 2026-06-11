import { useCallback, useEffect, useState } from 'react';
import {
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useThemePreference } from '../../lib/theme-context';
import { useRouter } from 'expo-router';
import { apiFetch } from '../../lib/api/client';
import { AmbientBackground } from '../../components/ui/AmbientBackground';
import { EmptyState } from '../../components/ui/EmptyState';
import { GlassCard } from '../../components/ui/GlassCard';
import { TAB_DOCK_CLEARANCE } from '../../components/ui/GlassTabBar';
import { HapticPressable } from '../../components/ui/HapticPressable';
import { SkeletonCards } from '../../components/ui/Skeleton';
import { borderRadius, colors, fontFamily, fontSize, spacing , withAlpha } from '../../lib/design-tokens';

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
  const sc      = STATUS_COLOR[item.status];
  const textPri = isDark ? colors.white     : colors.navyDeep;
  const textSub = isDark ? colors.slateText : colors.coolGray;

  return (
    <HapticPressable
      scaleTo={0.97}
      onPress={onPress}
      containerStyle={styles.cardSpacing}
      accessibilityLabel={`Consultation on ${formatDate(item.scheduled_start_at)}, ${STATUS_LABEL[item.status]}`}
    >
      <GlassCard unpadded>
        <View style={styles.card}>
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
        </View>
      </GlassCard>
    </HapticPressable>
  );
}

// ── Screen ─────────────────────────────────────────────────────────────────────

export default function ConsultationsScreen() {
  const router  = useRouter();
  const isDark  = useThemePreference().colorScheme === 'dark';
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

  const upcoming = consultations.filter(isUpcoming);
  const past     = consultations.filter(c => !isUpcoming(c));
  const bg       = isDark ? colors.midnight : colors.skyMist;
  const textPri  = isDark ? colors.white    : colors.navyDeep;
  const textSub  = isDark ? colors.slateText : colors.coolGray;

  return (
    <View style={[styles.flex, { backgroundColor: bg }]}>
      <AmbientBackground />
      <ScrollView
        style={styles.flex}
        contentContainerStyle={styles.container}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.electricBlue} />}
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={[styles.title, { color: textPri }]}>Consultations</Text>
          <HapticPressable
            scaleTo={0.94}
            style={styles.bookBtn}
            onPress={() => router.push('/consultations/book')}
            accessibilityLabel="Book a consultation"
          >
            <Text style={styles.bookBtnText}>+ Book</Text>
          </HapticPressable>
        </View>

        {error && <Text style={styles.error}>{error}</Text>}

        {loading ? (
          <SkeletonCards count={3} />
        ) : (
          <>
            {/* Upcoming */}
            <Text style={[styles.sectionLabel, { color: textSub }]}>Upcoming</Text>
            {upcoming.length === 0 ? (
              <EmptyState
                icon="calendar-outline"
                tint="blue"
                title="No upcoming consultations"
                body="Book a consultation with a Kyros specialist to get started — your care plan begins with one conversation."
                ctaLabel="Book a consultation"
                onCtaPress={() => router.push('/consultations/book')}
              />
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
          </>
        )}
      </ScrollView>
    </View>
  );
}

// ── Styles ─────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
    paddingBottom: TAB_DOCK_CLEARANCE,
  },

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
    boxShadow: `0 4px 8px ${withAlpha(colors.navyDeep, 0.25)}`,
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

  cardSpacing: { marginBottom: spacing[3] },
  card: {
    padding: spacing[4],
    gap: spacing[2],
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

  error: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: colors.criticalRed,
    marginBottom: spacing[4],
  },
});
