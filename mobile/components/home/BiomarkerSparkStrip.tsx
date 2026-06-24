/**
 * BiomarkerSparkStrip — a horizontally-scrolling row of "latest value + trend"
 * cards for the patient's tracked biomarkers, shown on Home.
 *
 * The list endpoint returns latest value + flag only; the per-biomarker trend
 * endpoint supplies the short series we render as a mini bar sparkline. Bars are
 * drawn with plain Views (not Skia/SVG) so the strip renders identically on
 * native and the react-native-web patient portal.
 *
 * Tapping a card opens the full trend chart at /biomarkers/[name].
 */

import { useQueries, useQuery } from '@tanstack/react-query';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { GlassCard } from '../ui/GlassCard';
import { HapticPressable } from '../ui/HapticPressable';
import { Skeleton } from '../ui/Skeleton';
import {
  borderRadius,
  colors,
  fontFamily,
  fontSize,
  spacing,
  withAlpha,
} from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';
import {
  getBiomarkerTrend,
  listBiomarkers,
  type BiomarkerSummary,
} from '../../lib/api/biomarker-trends';

const MAX_CARDS = 5;
const BARS = 8;

type Flag = BiomarkerSummary['flag'];

function flagColor(flag: Flag): string {
  if (flag === 'high') return colors.alert;
  if (flag === 'low') return colors.saffron;
  return colors.jade;
}

function flagLabel(flag: Flag): string | null {
  if (flag === 'high') return '↑ High';
  if (flag === 'low') return '↓ Low';
  return null;
}

// ── Mini bar sparkline (cross-platform, plain Views) ────────────────────────

function MiniBars({ values, tint }: { values: number[]; tint: string }) {
  // Show the most recent BARS readings.
  const recent = values.slice(-BARS);
  const min = Math.min(...recent);
  const max = Math.max(...recent);
  const span = max - min || 1;

  return (
    <View style={styles.bars} accessible accessibilityLabel="Recent trend">
      {recent.map((v, i) => {
        const frac = (v - min) / span; // 0..1
        const heightPct = 25 + frac * 75; // floor so flat series still reads
        const isLatest = i === recent.length - 1;
        return (
          <View
            key={i}
            style={[
              styles.bar,
              {
                height: `${heightPct}%`,
                backgroundColor: isLatest ? tint : withAlpha(tint, 0.35),
              },
            ]}
          />
        );
      })}
    </View>
  );
}

// ── Single biomarker card ────────────────────────────────────────────────────

function SparkCard({ summary }: { summary: BiomarkerSummary }) {
  const t = useTheme();
  const router = useRouter();
  const tint = flagColor(summary.flag);
  const fl = flagLabel(summary.flag);

  const { data: trend } = useQuery({
    queryKey: ['biomarker-trend', summary.name, '30d'],
    queryFn: () => getBiomarkerTrend(summary.name, '30d'),
    staleTime: 5 * 60_000,
  });

  const series = trend?.data_points.map((p) => p.value) ?? [];

  return (
    <HapticPressable
      scaleTo={0.96}
      onPress={() => router.push(`/biomarkers/${encodeURIComponent(summary.name)}`)}
      accessibilityLabel={`${summary.name}, latest ${summary.latest_value ?? 'no'} ${summary.unit}${fl ? `, ${fl}` : ''}`}
    >
      <GlassCard unpadded style={styles.card}>
        <View style={styles.cardInner}>
          <Text numberOfLines={1} style={[styles.name, { color: t.textSub }]}>
            {summary.name}
          </Text>
          <View style={styles.valueRow}>
            <Text style={[styles.value, { color: t.text }]}>
              {summary.latest_value ?? '—'}
            </Text>
            <Text style={[styles.unit, { color: t.textSub }]} numberOfLines={1}>
              {summary.unit}
            </Text>
          </View>

          {series.length >= 2 ? (
            <MiniBars values={series} tint={tint} />
          ) : (
            <View style={styles.bars} />
          )}

          {fl ? (
            <View style={[styles.flagPill, { backgroundColor: withAlpha(tint, 0.14) }]}>
              <Text style={[styles.flagText, { color: tint }]}>{fl}</Text>
            </View>
          ) : (
            <View style={[styles.flagPill, { backgroundColor: withAlpha(colors.jade, 0.12) }]}>
              <Text style={[styles.flagText, { color: colors.jade }]}>Normal</Text>
            </View>
          )}
        </View>
      </GlassCard>
    </HapticPressable>
  );
}

// ── Strip ─────────────────────────────────────────────────────────────────────

export function BiomarkerSparkStrip() {
  const t = useTheme();

  const { data, isLoading } = useQuery({
    queryKey: ['biomarkers'],
    queryFn: listBiomarkers,
    staleTime: 5 * 60_000,
  });

  const biomarkers = (data?.biomarkers ?? []).slice(0, MAX_CARDS);

  // Warm the trend caches in parallel so cards render their sparklines together
  // rather than popping in one by one.
  useQueries({
    queries: biomarkers.map((b) => ({
      queryKey: ['biomarker-trend', b.name, '30d'],
      queryFn: () => getBiomarkerTrend(b.name, '30d'),
      staleTime: 5 * 60_000,
    })),
  });

  if (isLoading) {
    return (
      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: t.text }]}>Your biomarkers</Text>
        <View style={styles.skeletonRow}>
          <Skeleton width={150} height={132} radius={borderRadius.xxl} />
          <Skeleton width={150} height={132} radius={borderRadius.xxl} />
        </View>
      </View>
    );
  }

  // Nothing to show — render no shell at all, per clinical empty-state guidance.
  if (biomarkers.length === 0) return null;

  return (
    <View style={styles.section}>
      <Text style={[styles.sectionTitle, { color: t.text }]}>Your biomarkers</Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {biomarkers.map((b) => (
          <SparkCard key={b.name} summary={b} />
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  section: { gap: spacing[4] },
  sectionTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    fontWeight: '600',
  },
  skeletonRow: { flexDirection: 'row', gap: spacing[3] },
  scrollContent: { gap: spacing[3], paddingRight: spacing[2] },

  card: { width: 150 },
  cardInner: { padding: spacing[4], gap: spacing[2] },
  name: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    fontWeight: '600',
  },
  valueRow: { flexDirection: 'row', alignItems: 'baseline', gap: spacing[1] },
  value: {
    fontFamily: fontFamily.display,
    fontSize: 24,
    fontWeight: '600',
    fontVariant: ['tabular-nums'],
  },
  unit: { fontFamily: fontFamily.body, fontSize: fontSize.xs, flexShrink: 1 },

  bars: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    height: 34,
    gap: 3,
  },
  bar: {
    flex: 1,
    borderRadius: borderRadius.sm,
    minHeight: 3,
  },

  flagPill: {
    alignSelf: 'flex-start',
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
    borderRadius: borderRadius.full,
  },
  flagText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
  },
});
