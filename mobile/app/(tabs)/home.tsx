import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { AmbientBackground } from '../../components/ui/AmbientBackground';
import { TAB_DOCK_CLEARANCE } from '../../components/ui/GlassTabBar';
import { AdaptiveHero } from '../../components/home/AdaptiveHero';
import { BiomarkerSparkStrip } from '../../components/home/BiomarkerSparkStrip';
import { CarePlanCard } from '../../components/home/CarePlanCard';
import { DailyCheckIn } from '../../components/home/DailyCheckIn';
import { RequestedConsultBanner } from '../../components/home/RequestedConsultBanner';
import { useAuth } from '../../lib/auth/context';
import { listConsultations, type Consultation } from '../../lib/api/consultations';
import {
  fontFamily, fontSize, spacing,
} from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';

const H_PAD = spacing[6];

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

// ─── Upcoming-consult derivation ────────────────────────────────────────────────

/** First consult still awaiting coordinator assignment, if any. */
function findRequested(items: Consultation[]): Consultation | null {
  return items.find(c => c.status === 'requested') ?? null;
}

/** The soonest upcoming (or currently in-progress) consult that has a slot.
 *  We now fetch all consults, so exclude scheduled/confirmed slots already in
 *  the past; an in-progress consult is kept regardless (it's happening now). */
function findNextScheduled(items: Consultation[]): Consultation | null {
  const now = Date.now();
  const withSlot = items
    .filter(c => {
      if (c.scheduled_start_at == null) return false;
      if (c.status === 'in_progress') return true;
      if (c.status === 'scheduled' || c.status === 'confirmed') {
        return new Date(c.scheduled_start_at).getTime() >= now;
      }
      return false;
    })
    .sort((a, b) =>
      new Date(a.scheduled_start_at!).getTime() - new Date(b.scheduled_start_at!).getTime(),
    );
  return withSlot[0] ?? null;
}

// ─── Main screen ──────────────────────────────────────────────────────────────

export default function HomeScreen() {
  const { state } = useAuth();
  const router    = useRouter();
  const t         = useTheme();

  const {
    data: consultData,
    refetch: refetchConsults,
    isFetching: consultFetching,
    isLoading: consultLoading,
  } = useQuery({
    queryKey: ['consultations', 'home'],
    queryFn: () => listConsultations({ pageSize: 50 }),
    staleTime: 60_000,
  });

  const onRefresh = useCallback(() => {
    void refetchConsults();
  }, [refetchConsults]);

  // A coordinator assigns the consult server-side, so the patient app only
  // learns of it on a refetch. Refetch whenever Home regains focus, so a stale
  // "request under review" banner clears without a manual pull-to-refresh.
  useFocusEffect(
    useCallback(() => {
      void refetchConsults();
    }, [refetchConsults]),
  );

  const consults      = consultData?.items ?? [];
  const requested     = findRequested(consults);
  const nextScheduled = findNextScheduled(consults);
  const hasAnyConsult = consults.length > 0;

  const firstName = state.status === 'authenticated' ? state.user.name.split(' ')[0] : '';

  return (
    <View style={[styles.flex, { backgroundColor: t.background }]}>
      <AmbientBackground />
      <ScrollView
        style={styles.flex}
        contentContainerStyle={styles.container}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={consultFetching && !consultLoading}
            onRefresh={onRefresh}
            tintColor={t.primary}
          />
        }
      >

        {/* ── Header ─────────────────────────────────────────────────────── */}
        <View style={styles.header}>
          <View>
            <Text style={[styles.greeting, { color: t.textSub }]}>{getGreeting()}</Text>
            <Text style={[styles.heroName, { color: t.text }]}>{firstName || 'Welcome'}</Text>
          </View>
        </View>

        {/* ── Coordinator "request under review" banner ──────────────────── */}
        {requested && (
          <RequestedConsultBanner onPress={() => router.push('/(tabs)/consultations')} />
        )}

        {/* ── Adaptive hero — countdown or booking CTA ───────────────────── */}
        <AdaptiveHero
          consult={nextScheduled}
          hasAnyConsult={hasAnyConsult}
          onBook={() => router.push('/consultations/book')}
          onOpenConsult={(id) => router.push(`/consultations/${id}`)}
        />

        {/* ── Biomarker spark-strip ──────────────────────────────────────── */}
        <BiomarkerSparkStrip />

        {/* ── Daily symptom check-in ────────────────────────────────────── */}
        <DailyCheckIn />

        {/* ── Care plan card ──────────────────────────────────────────────── */}
        <CarePlanCard />

      </ScrollView>
    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flexGrow: 1,
    paddingHorizontal: H_PAD,
    paddingTop: spacing[6],
    paddingBottom: TAB_DOCK_CLEARANCE,
    gap: spacing[6],
  },

  // Header
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  greeting: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
  },
  heroName: {
    fontFamily: fontFamily.display,
    fontSize: 28,
    fontWeight: '600',
    marginTop: 2,
  },

});
