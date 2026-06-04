/**
 * Biomarker trend screen — app/biomarkers/[name].tsx
 *
 * Shows a longitudinal line chart for a single biomarker across all processed
 * lab reports.  Features:
 *   - Victory Native XL CartesianChart with Skia rendering (60fps target)
 *   - Reference range band: sage tint (normal zone) + saffron tint (out-of-range zones)
 *   - 7d / 30d / 90d / 1y / All range selector
 *   - Better / Steady / Worse trend indicator with fade-in animation
 *   - Tap a data point → tooltip (date, value, lab); consultation link if available
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Animated,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { CartesianChart, Line, useChartPressState } from 'victory-native';
import { Circle, Rect, Group } from '@shopify/react-native-skia';

import {
  getBiomarkerTrend,
  type BiomarkerDataPoint,
  type BiomarkerRange,
  type BiomarkerTrendResponse,
  type TrendDirection,
} from '../../lib/api/biomarker-trends';
import {
  borderRadius,
  colors,
  fontFamily,
  fontSize,
  spacing,
} from '../../lib/design-tokens';

// ── Constants ─────────────────────────────────────────────────────────────────

const RANGES: { label: string; value: BiomarkerRange }[] = [
  { label: '7d',  value: '7d'  },
  { label: '30d', value: '30d' },
  { label: '90d', value: '90d' },
  { label: '1y',  value: '1y'  },
  { label: 'All', value: 'all' },
];

const CHART_HEIGHT = 220;

// Skia color strings (rgba)
const SAGE_BAND   = 'rgba(143, 168, 142, 0.25)';  // sage #8FA88E at 25%
const SAFFRON_ZONE = 'rgba(224, 142, 60, 0.15)';   // saffron #E08E3C at 15%
const FOREST_LINE  = '#0F3D2E';
const STONE_LINE   = 'rgba(107, 107, 104, 0.10)';  // Stone 10% for boundary lines

// ── Types ─────────────────────────────────────────────────────────────────────

interface ChartDatum {
  x: number;       // sequential index (0-based) for even spacing
  y: number;       // biomarker value
  refLow: number;  // canonical ref_low (same across all points)
  refHigh: number; // canonical ref_high (same across all points)
}

interface TooltipState {
  point: BiomarkerDataPoint;
  chartX: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

function trendLabel(t: TrendDirection): string {
  if (t === 'better') return '↑ Better';
  if (t === 'worse')  return '↓ Worse';
  return '→ Steady';
}

function trendColor(t: TrendDirection): string {
  if (t === 'better') return colors.forest;
  if (t === 'worse')  return colors.terracotta;
  return colors.stone;
}

function buildChartData(
  points: BiomarkerDataPoint[],
  refLow: number | null,
  refHigh: number | null,
): ChartDatum[] {
  const fallbackLow  = refLow  ?? 0;
  const fallbackHigh = refHigh ?? 0;
  return points.map((p, i) => ({
    x: i,
    y: p.value,
    refLow:  p.ref_low  ?? fallbackLow,
    refHigh: p.ref_high ?? fallbackHigh,
  }));
}

function yDomain(
  data: ChartDatum[],
  refLow: number | null,
  refHigh: number | null,
): [number, number] {
  if (data.length === 0) return [0, 10];
  const values = data.map((d) => d.y);
  const min = Math.min(...values, refLow ?? Infinity);
  const max = Math.max(...values, refHigh ?? -Infinity);
  const pad = (max - min) * 0.15 || 1;
  return [min - pad, max + pad];
}

// ── Trend badge ───────────────────────────────────────────────────────────────

function TrendBadge({ trend }: { trend: TrendDirection }) {
  const opacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(opacity, {
      toValue: 1,
      duration: 220,
      useNativeDriver: true,
    }).start();
  }, [trend, opacity]);

  return (
    <Animated.View style={[styles.trendBadge, { opacity }]}>
      <Text style={[styles.trendLabel, { color: trendColor(trend) }]}>
        {trendLabel(trend)}
      </Text>
    </Animated.View>
  );
}

// ── Range selector ────────────────────────────────────────────────────────────

function RangeSelector({
  selected,
  onSelect,
}: {
  selected: BiomarkerRange;
  onSelect: (r: BiomarkerRange) => void;
}) {
  return (
    <View style={styles.rangeRow}>
      {RANGES.map((r) => (
        <Pressable
          key={r.value}
          style={[styles.rangeBtn, selected === r.value && styles.rangeBtnActive]}
          onPress={() => onSelect(r.value)}
          accessibilityLabel={`Show ${r.label} range`}
          accessibilityState={{ selected: selected === r.value }}
        >
          <Text
            style={[
              styles.rangeBtnText,
              selected === r.value && styles.rangeBtnTextActive,
            ]}
          >
            {r.label}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}

// ── Tooltip ───────────────────────────────────────────────────────────────────

function Tooltip({
  point,
  onDismiss,
  onOpenConsultation,
}: {
  point: BiomarkerDataPoint;
  onDismiss: () => void;
  onOpenConsultation: (id: string) => void;
}) {
  const flagText = point.flag && point.flag !== 'normal'
    ? ` · ${point.flag === 'high' ? '↑ High' : '↓ Low'}`
    : '';

  return (
    <Pressable style={styles.tooltipOverlay} onPress={onDismiss} accessible={false}>
      <View style={styles.tooltip}>
        <Text style={styles.tooltipDate}>{formatDate(point.report_date)}</Text>
        <Text style={styles.tooltipValue}>
          {point.value} {point.unit}
          {flagText}
        </Text>
        {point.ref_low != null && point.ref_high != null && (
          <Text style={styles.tooltipRef}>
            Ref: {point.ref_low}–{point.ref_high} {point.unit}
          </Text>
        )}
        {point.lab_name ? (
          <Text style={styles.tooltipLab}>{point.lab_name}</Text>
        ) : null}
        {point.consultation_id ? (
          <Pressable
            style={styles.tooltipConsultBtn}
            onPress={() => onOpenConsultation(point.consultation_id!)}
            accessibilityLabel="View linked consultation"
          >
            <Text style={styles.tooltipConsultText}>View consultation →</Text>
          </Pressable>
        ) : null}
      </View>
    </Pressable>
  );
}

// ── Chart ─────────────────────────────────────────────────────────────────────

function BiomarkerChart({
  data,
  dataPoints,
  refLow,
  refHigh,
  onPointTap,
}: {
  data: ChartDatum[];
  dataPoints: BiomarkerDataPoint[];
  refLow: number | null;
  refHigh: number | null;
  onPointTap: (point: BiomarkerDataPoint) => void;
}) {
  const hasRefRange = refLow != null && refHigh != null;
  const domain = yDomain(data, refLow, refHigh);
  const { state, isActive } = useChartPressState({ x: 0, y: { y: 0, refLow: 0, refHigh: 0 } });

  // When press is active, fire the tap callback
  const lastIndexRef = useRef<number>(-1);

  return (
    <View style={styles.chartContainer}>
      <CartesianChart
        data={data}
        xKey="x"
        yKeys={['y', 'refLow', 'refHigh']}
        domain={{ y: domain }}
        chartPressState={state}
        padding={{ left: 8, right: 8, top: 12, bottom: 8 }}
        axisOptions={{
          tickCount: { x: 0, y: 4 },
          labelColor: colors.stone,
          labelPosition: 'outset',
          axisSide: { x: 'bottom', y: 'left' },
        }}
      >
        {({ points, chartBounds }) => {
          const refHighY = points.refHigh[0]?.y ?? chartBounds.top;
          const refLowY  = points.refLow[0]?.y  ?? chartBounds.bottom;

          return (
            <Group>
              {/* Out-of-range zones (saffron) — drawn below the normal band */}
              {hasRefRange && (
                <>
                  <Rect
                    x={chartBounds.left}
                    y={chartBounds.top}
                    width={chartBounds.right - chartBounds.left}
                    height={Math.max(0, refHighY - chartBounds.top)}
                    color={SAFFRON_ZONE}
                  />
                  <Rect
                    x={chartBounds.left}
                    y={refLowY}
                    width={chartBounds.right - chartBounds.left}
                    height={Math.max(0, chartBounds.bottom - refLowY)}
                    color={SAFFRON_ZONE}
                  />
                </>
              )}

              {/* Normal range band (sage) */}
              {hasRefRange && (
                <Rect
                  x={chartBounds.left}
                  y={refHighY}
                  width={chartBounds.right - chartBounds.left}
                  height={Math.max(0, refLowY - refHighY)}
                  color={SAGE_BAND}
                />
              )}

              {/* Reference range boundary lines (Stone 10%) */}
              {hasRefRange && (
                <>
                  <Rect
                    x={chartBounds.left}
                    y={refHighY}
                    width={chartBounds.right - chartBounds.left}
                    height={1}
                    color={STONE_LINE}
                  />
                  <Rect
                    x={chartBounds.left}
                    y={refLowY}
                    width={chartBounds.right - chartBounds.left}
                    height={1}
                    color={STONE_LINE}
                  />
                </>
              )}

              {/* Data line */}
              <Line
                points={points.y}
                color={FOREST_LINE}
                strokeWidth={2}
                animate={{ type: 'timing', duration: 220 }}
              />

              {/* Data dots */}
              {points.y.map((p, i) => {
                if (p.y == null) return null;
                const pt = dataPoints[i];
                const isOutOfRange = pt?.flag && pt.flag !== 'normal';
                const isLatest = i === points.y.length - 1;
                const r = isLatest ? 7 : 4;
                return (
                  <Circle
                    key={i}
                    cx={p.x}
                    cy={p.y}
                    r={r}
                    color={isOutOfRange ? colors.saffron : FOREST_LINE}
                  />
                );
              })}

              {/* Press crosshair dot */}
              {isActive && (
                <Circle
                  cx={state.x.position}
                  cy={state.y.y.position}
                  r={6}
                  color={FOREST_LINE}
                  opacity={0.8}
                />
              )}
            </Group>
          );
        }}
      </CartesianChart>

      {/* Invisible tap targets over each data point */}
      {data.map((d, i) => {
        const pt = dataPoints[i];
        if (!pt) return null;
        // approximate x position as fraction of chart width
        const fracX = data.length > 1 ? i / (data.length - 1) : 0.5;
        return (
          <Pressable
            key={i}
            style={[
              styles.tapTarget,
              {
                left: `${fracX * 100}%` as unknown as number,
              },
            ]}
            onPress={() => onPointTap(pt)}
            accessibilityLabel={`Data point ${i + 1}: ${pt.value} ${pt.unit} on ${formatDate(pt.report_date)}`}
          />
        );
      })}
    </View>
  );
}

// ── Loading skeleton ──────────────────────────────────────────────────────────

function ChartSkeleton() {
  return (
    <View style={[styles.chartContainer, styles.skeleton]}>
      {/* Sage band placeholder */}
      <View style={styles.skeletonBand} />
      <Text style={styles.skeletonCaption}>Loading trend…</Text>
    </View>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function BiomarkerTrendScreen() {
  const { name } = useLocalSearchParams<{ name: string }>();
  const router = useRouter();

  const [range, setRange] = useState<BiomarkerRange>('all');
  const [data, setData] = useState<BiomarkerTrendResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<BiomarkerDataPoint | null>(null);

  const fetchData = useCallback(async () => {
    if (!name) return;
    setLoading(true);
    setError(null);
    try {
      const result = await getBiomarkerTrend(decodeURIComponent(name as string), range);
      setData(result);
    } catch {
      setError('Could not load trend data.');
    } finally {
      setLoading(false);
    }
  }, [name, range]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  const handleRangeChange = useCallback(
    (r: BiomarkerRange) => {
      setRange(r);
      setTooltip(null);
    },
    [],
  );

  const handleOpenConsultation = useCallback(
    (consultationId: string) => {
      setTooltip(null);
      router.push(`/consultations/${consultationId}`);
    },
    [router],
  );

  const biomarkerName = data?.biomarker_name ?? decodeURIComponent(name as string ?? '');
  const unit = data?.unit ?? '';

  // ── Error state ──────────────────────────────────────────────────────────

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{error}</Text>
        <Pressable style={styles.retryBtn} onPress={() => void fetchData()}>
          <Text style={styles.retryText}>Try again</Text>
        </Pressable>
      </View>
    );
  }

  // ── Empty state (<3 readings) ─────────────────────────────────────────────

  const hasData = (data?.data_points.length ?? 0) > 0;
  const tooFewPoints = (data?.data_points.length ?? 0) < 3;

  return (
    <ScrollView style={styles.scroll} contentContainerStyle={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.biomarkerName}>{biomarkerName}</Text>
        {unit ? <Text style={styles.unit}>{unit}</Text> : null}
      </View>

      {/* Current value block (latest data point) */}
      {hasData && data && (
        <View style={styles.currentBlock}>
          <Text style={styles.currentValue}>
            {data.data_points[data.data_points.length - 1].value}
          </Text>
          {unit ? <Text style={styles.currentUnit}>{unit}</Text> : null}
          <TrendBadge trend={data.trend} />
        </View>
      )}

      {/* Range selector */}
      <RangeSelector selected={range} onSelect={handleRangeChange} />

      {/* Chart or skeleton */}
      {loading ? (
        <ChartSkeleton />
      ) : hasData && data && !tooFewPoints ? (
        <>
          <BiomarkerChart
            data={buildChartData(data.data_points, data.ref_low, data.ref_high)}
            dataPoints={data.data_points}
            refLow={data.ref_low}
            refHigh={data.ref_high}
            onPointTap={setTooltip}
          />
          {data.ref_low != null && data.ref_high != null && (
            <Text style={styles.refRangeLabel}>
              Reference range: {data.ref_low}–{data.ref_high} {unit}
            </Text>
          )}
        </>
      ) : hasData && tooFewPoints ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyTitle}>
            Only {data!.data_points.length} {biomarkerName} value{data!.data_points.length === 1 ? '' : 's'} so far.
          </Text>
          <Text style={styles.emptySub}>
            Trends become useful with three or more readings.
          </Text>
        </View>
      ) : (
        <View style={styles.emptyState}>
          <Text style={styles.emptyTitle}>No {biomarkerName} values yet.</Text>
          <Text style={styles.emptySub}>
            Upload a lab report to start tracking this biomarker over time.
          </Text>
        </View>
      )}

      {/* History table */}
      {hasData && data && (
        <View style={styles.historySection}>
          <Text style={styles.sectionTitle}>History</Text>
          {[...data.data_points].reverse().map((pt, i) => (
            <View key={pt.report_id + i} style={styles.historyRow}>
              <Text style={styles.historyDate}>{formatDate(pt.report_date)}</Text>
              <Text style={styles.historyValue}>
                {pt.value} {pt.unit}
              </Text>
              {pt.flag && pt.flag !== 'normal' && (
                <View
                  style={[
                    styles.flagChip,
                    { backgroundColor: colors.saffron + '22' },
                  ]}
                >
                  <Text style={[styles.flagText, { color: colors.saffron }]}>
                    {pt.flag === 'high' ? '↑ High' : '↓ Low'}
                  </Text>
                </View>
              )}
              {pt.ref_low != null && pt.ref_high != null && (
                <Text style={styles.historyRef}>
                  {pt.ref_low}–{pt.ref_high}
                </Text>
              )}
            </View>
          ))}
        </View>
      )}

      {/* Tooltip overlay */}
      {tooltip && (
        <Tooltip
          point={tooltip}
          onDismiss={() => setTooltip(null)}
          onOpenConsultation={handleOpenConsultation}
        />
      )}
    </ScrollView>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  scroll: {
    flex: 1,
    backgroundColor: colors.ivory,
  },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[4],
    paddingTop: spacing[4],
    paddingBottom: spacing[16],
    gap: spacing[4],
  },
  center: {
    flex: 1,
    backgroundColor: colors.ivory,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing[4],
    paddingHorizontal: spacing[8],
  },
  errorText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.terracotta,
    textAlign: 'center',
  },
  retryBtn: { alignItems: 'center' },
  retryText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.forest,
  },
  header: {
    gap: spacing[1],
  },
  biomarkerName: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    color: colors.forest,
    fontWeight: '500',
  },
  unit: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
  },
  currentBlock: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: spacing[2],
    flexWrap: 'wrap',
  },
  currentValue: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.display,
    color: colors.forest,
    fontWeight: '500',
  },
  currentUnit: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.stone,
  },
  trendBadge: {
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1],
    borderRadius: borderRadius.sm,
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.ivory,
  },
  trendLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    fontWeight: '600',
  },
  rangeRow: {
    flexDirection: 'row',
    gap: spacing[1],
  },
  rangeBtn: {
    flex: 1,
    paddingVertical: spacing[2],
    alignItems: 'center',
    borderRadius: borderRadius.sm,
    borderWidth: 1,
    borderColor: colors.forest,
  },
  rangeBtnActive: {
    backgroundColor: colors.forest,
  },
  rangeBtnText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.forest,
    fontWeight: '500',
  },
  rangeBtnTextActive: {
    color: colors.ivory,
  },
  chartContainer: {
    height: CHART_HEIGHT,
    backgroundColor: colors.white,
    borderRadius: borderRadius.lg,
    overflow: 'hidden',
  },
  skeleton: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  skeletonBand: {
    position: 'absolute',
    left: 0,
    right: 0,
    top: '30%',
    height: '40%',
    backgroundColor: colors.sage + '40',
  },
  skeletonCaption: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
  },
  tapTarget: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    width: 32,
    transform: [{ translateX: -16 }],
  },
  refRangeLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    textAlign: 'center',
  },
  emptyState: {
    backgroundColor: colors.white,
    borderRadius: borderRadius.lg,
    padding: spacing[6],
    alignItems: 'center',
    gap: spacing[2],
  },
  emptyTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    fontWeight: '500',
    textAlign: 'center',
  },
  emptySub: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    textAlign: 'center',
    lineHeight: 20,
  },
  historySection: {
    gap: spacing[2],
  },
  sectionTitle: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h3,
    color: colors.forest,
    fontWeight: '500',
  },
  historyRow: {
    backgroundColor: colors.white,
    borderRadius: borderRadius.md,
    padding: spacing[3],
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    flexWrap: 'wrap',
  },
  historyDate: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    flex: 1,
  },
  historyValue: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    fontWeight: '500',
    fontVariant: ['tabular-nums'],
  },
  historyRef: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    fontVariant: ['tabular-nums'],
  },
  flagChip: {
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
    borderRadius: borderRadius.sm,
  },
  flagText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    fontWeight: '600',
  },
  tooltipOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tooltip: {
    backgroundColor: colors.white,
    borderRadius: borderRadius.lg,
    padding: spacing[4],
    marginHorizontal: spacing[8],
    gap: spacing[2],
    shadowColor: colors.ink,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 3,
  },
  tooltipDate: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
  },
  tooltipValue: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.ink,
    fontWeight: '600',
    fontVariant: ['tabular-nums'],
  },
  tooltipRef: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
  },
  tooltipLab: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
  },
  tooltipConsultBtn: {
    paddingTop: spacing[1],
  },
  tooltipConsultText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.forest,
    fontWeight: '600',
  },
});
