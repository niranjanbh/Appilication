import { useQuery } from '@tanstack/react-query';
import {
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useThemePreference } from '../../lib/theme-context';
import { useRouter } from 'expo-router';
import {
  isUpcoming,
  listConsultations,
  type Consultation,
  type ConsultationStatus,
} from '../../lib/api/consultations';
import { AmbientBackground } from '../../components/ui/AmbientBackground';
import { EmptyState } from '../../components/ui/EmptyState';
import { TAB_DOCK_CLEARANCE } from '../../components/ui/GlassTabBar';
import { HapticPressable } from '../../components/ui/HapticPressable';
import { GlassCard } from '../../components/ui/GlassCard';
import { SkeletonCards } from '../../components/ui/Skeleton';
import { Button } from '../../components/Button';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';

// ── Helpers ────────────────────────────────────────────────────────────────────

function formatDate(iso: string) { return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }); }
function formatTime(iso: string) { return new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true }); }
function formatRupees(p: number) { return `₹${(p / 100).toFixed(0)}`; }
function formatCat(cat: string)  { return cat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()); }
// A requested consultation has no slot yet — show a friendly placeholder.
function formatWhen(iso: string | null) {
  return iso ? `${formatDate(iso)} · ${formatTime(iso)}` : 'Awaiting assignment';
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
  const textPri = isDark ? colors.ivoryText : colors.ink;
  const textSub = isDark ? colors.stoneDim  : colors.stone;

  return (
    <HapticPressable
      scaleTo={0.97}
      onPress={onPress}
      containerStyle={styles.cardSpacing}
      accessibilityLabel={`Consultation, ${formatWhen(item.scheduled_start_at)}, ${STATUS_LABEL[item.status]}`}
    >
      <GlassCard unpadded>
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Text style={[styles.cardDate, { color: textSub }]}>
              {formatWhen(item.scheduled_start_at)}
            </Text>
            <View style={[styles.statusPill, { backgroundColor: sc + '18' }]}>
              <Text style={[styles.statusText, { color: sc }]}>{STATUS_LABEL[item.status]}</Text>
            </View>
          </View>
          <Text style={[styles.cardCategory, { color: textPri }]}>
            {formatCat(item.condition_category)}
          </Text>
          {item.doctor_name ? (
            <Text style={[styles.cardDoctor, { color: textPri }]}>
              Dr {item.doctor_name}
              {item.doctor_specialty && item.doctor_specialty.length > 0
                ? ` · ${formatCat(item.doctor_specialty[0])}`
                : ''}
            </Text>
          ) : null}
          <Text style={[styles.cardMeta, { color: textSub }]}>
            {item.consultation_type === 'initial' ? 'Initial consultation' : 'Follow-up'}
            {item.consultation_fee_paise != null ? ` · ${formatRupees(item.consultation_fee_paise)}` : ''}
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
  const t       = useTheme();

  const { data, isLoading, isFetching, error, refetch } = useQuery({
    queryKey: ['consultations'],
    queryFn: () => listConsultations({ pageSize: 50 }),
    staleTime: 60_000,
  });

  const consultations = data?.items ?? [];
  const upcoming = consultations.filter(isUpcoming);
  const past     = consultations.filter(c => !isUpcoming(c));

  return (
    <View style={[styles.flex, { backgroundColor: t.background }]}>
      <AmbientBackground />
      <ScrollView
        style={styles.flex}
        contentContainerStyle={styles.container}
        refreshControl={<RefreshControl refreshing={isFetching && !isLoading} onRefresh={refetch} tintColor={t.primary} />}
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={[styles.title, { color: t.text }]}>Care</Text>
          <Button
            label="+ Book"
            variant="forest"
            onPress={() => router.push('/consultations/book')}
            accessibilityLabel="Book a consultation"
            style={{ height: 36, paddingHorizontal: spacing[4] }}
          />
        </View>

        {error && <Text style={styles.error}>Could not load consultations. Please try again.</Text>}

        {isLoading ? (
          <SkeletonCards count={3} />
        ) : (
          <>
            {/* Upcoming */}
            <Text style={[styles.sectionLabel, { color: t.textSub }]}>Upcoming</Text>
            {upcoming.length === 0 ? (
              <EmptyState
                icon="calendar-outline"
                tint="forest"
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
                <Text style={[styles.sectionLabel, styles.sectionLabelLower, { color: t.textSub }]}>Past</Text>
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
  cardDoctor: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
  cardMeta: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
  },

  error: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: colors.alert,
    marginBottom: spacing[4],
  },
});
