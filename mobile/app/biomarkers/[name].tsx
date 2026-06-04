/**
 * Biomarker trend screen — app/biomarkers/[name].tsx
 *
 * Victory Native XL CartesianChart with Skia rendering (60fps).
 * Reference range band, 7d/30d/90d/1y/All selector, trend badge, tap tooltip.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Animated,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useColorScheme,
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
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

// ── Constants ─────────────────────────────────────────────────────────────────

const RANGES: { label: string; value: BiomarkerRange }[] = [
  { label: '7d',  value: '7d'  },
  { label: '30d', value: '30d' },
  { label: '90d', value: '90d' },
  { label: '1y',  value: '1y'  },
  { label: 'All', value: 'all' },
];

const CHART_HEIGHT = 220;

// Skia color strings — use brand colors for chart elements
const DATA_LINE    = colors.navyDeep;          // main data line
const DATA_DOT_OOB = colors.warningAmber;      // out-of-range dot
const SAGE_BAND    = 'rgba(143,168,142,0.22)'; // normal zone fill
const SAFFRON_ZONE = 'rgba(212,131,10,0.12)';  // out-of-range zone
const BOUND_LINE   = 'rgba(107,107,104,0.12)'; // ref boundary lines
const PRESS_DOT    = colors.electricBlue;       // crosshair dot

// ── Types ─────────────────────────────────────────────────────────────────────

interface ChartDatum {
  x: number;
  y: number;
  refLow:  number;
  refHigh: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}
function trendLabel(t: TrendDirection): string {
  if (t === 'better') return '↑ Better';
  if (t === 'worse')  return '↓ Worse';
  return '→ Steady';
}
function trendColor(t: TrendDirection): string {
  if (t === 'better') return colors.successGreen;
  if (t === 'worse')  return colors.criticalRed;
  return colors.coolGray;
}
function buildChartData(pts: BiomarkerDataPoint[], refLow: number | null, refHigh: number | null): ChartDatum[] {
  const fl = refLow ?? 0; const fh = refHigh ?? 0;
  return pts.map((p, i) => ({ x: i, y: p.value, refLow: p.ref_low ?? fl, refHigh: p.ref_high ?? fh }));
}
function yDomain(data: ChartDatum[], refLow: number | null, refHigh: number | null): [number, number] {
  if (!data.length) return [0, 10];
  const vals = data.map(d => d.y);
  const min  = Math.min(...vals, refLow ?? Infinity);
  const max  = Math.max(...vals, refHigh ?? -Infinity);
  const pad  = (max - min) * 0.15 || 1;
  return [min - pad, max + pad];
}

// ── Trend badge ───────────────────────────────────────────────────────────────

function TrendBadge({ trend, isDark }: { trend: TrendDirection; isDark: boolean }) {
  const opacity = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.timing(opacity, { toValue: 1, duration: 220, useNativeDriver: true }).start();
  }, [trend, opacity]);

  const badgeBg = isDark ? colors.nightElev : colors.white;
  const badgeBdr = isDark ? 'rgba(255,255,255,0.10)' : colors.borderLight;
  return (
    <Animated.View style={[styles.trendBadge, { opacity, backgroundColor: badgeBg, borderColor: badgeBdr }]}>
      <Text style={[styles.trendLabel, { color: trendColor(trend) }]}>{trendLabel(trend)}</Text>
    </Animated.View>
  );
}

// ── Range selector ────────────────────────────────────────────────────────────

function RangeSelector({ selected, onSelect, isDark }: {
  selected: BiomarkerRange;
  onSelect: (r: BiomarkerRange) => void;
  isDark: boolean;
}) {
  const activeBg  = colors.navyDeep;
  const inactiveBg = isDark ? colors.nightElev : colors.white;
  const activeBdr  = colors.navyDeep;
  const inactiveBdr = isDark ? 'rgba(255,255,255,0.12)' : colors.borderLight;

  return (
    <View style={styles.rangeRow}>
      {RANGES.map(r => (
        <Pressable
          key={r.value}
          style={[
            styles.rangeBtn,
            {
              backgroundColor: selected === r.value ? activeBg  : inactiveBg,
              borderColor:     selected === r.value ? activeBdr : inactiveBdr,
            },
          ]}
          onPress={() => onSelect(r.value)}
          accessibilityLabel={`Show ${r.label} range`}
          accessibilityState={{ selected: selected === r.value }}
        >
          <Text style={[
            styles.rangeBtnText,
            { color: selected === r.value ? colors.white : (isDark ? colors.slateText : colors.coolGray) },
          ]}>
            {r.label}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}

// ── Tooltip ───────────────────────────────────────────────────────────────────

function Tooltip({ point, onDismiss, onOpenConsultation, isDark }: {
  point: BiomarkerDataPoint;
  onDismiss: () => void;
  onOpenConsultation: (id: string) => void;
  isDark: boolean;
}) {
  const flagText = point.flag && point.flag !== 'normal'
    ? ` · ${point.flag === 'high' ? '↑ High' : '↓ Low'}`
    : '';
  const cardBg  = isDark ? colors.nightSurface : colors.white;
  const cardBdr = isDark ? 'rgba(255,255,255,0.10)' : 'rgba(0,31,63,0.08)';
  const textPri = isDark ? colors.white     : colors.navyDeep;
  const textSub = isDark ? colors.slateText : colors.coolGray;

  return (
    <Pressable style={styles.tooltipOverlay} onPress={onDismiss} accessible={false}>
      <View style={[styles.tooltip, { backgroundColor: cardBg, borderColor: cardBdr }]}>
        <Text style={[styles.tooltipDate,  { color: textSub }]}>{formatDate(point.report_date)}</Text>
        <Text style={[styles.tooltipValue, { color: textPri }]}>{point.value} {point.unit}{flagText}</Text>
        {point.ref_low != null && point.ref_high != null && (
          <Text style={[styles.tooltipRef, { color: textSub }]}>Ref: {point.ref_low}–{point.ref_high} {point.unit}</Text>
        )}
        {point.lab_name && <Text style={[styles.tooltipLab, { color: textSub }]}>{point.lab_name}</Text>}
        {point.consultation_id && (
          <Pressable
            style={styles.tooltipConsultBtn}
            onPress={() => onOpenConsultation(point.consultation_id!)}
            accessibilityLabel="View linked consultation"
          >
            <Text style={[styles.tooltipConsultText, { color: colors.electricBlue }]}>View consultation →</Text>
          </Pressable>
        )}
      </View>
    </Pressable>
  );
}

// ── Chart ─────────────────────────────────────────────────────────────────────

function BiomarkerChart({ data, dataPoints, refLow, refHigh, onPointTap, isDark }: {
  data: ChartDatum[];
  dataPoints: BiomarkerDataPoint[];
  refLow: number | null;
  refHigh: number | null;
  onPointTap: (p: BiomarkerDataPoint) => void;
  isDark: boolean;
}) {
  const hasRef = refLow != null && refHigh != null;
  const domain = yDomain(data, refLow, refHigh);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { state, isActive } = useChartPressState({ x: 0, y: { y: 0, refLow: 0, refHigh: 0 } } as any);
  void useRef<number>(-1); // chart press ref — unused but required by Victory hook contract
  const chartBg = isDark ? colors.nightSurface : colors.white;
  const axisColor = isDark ? colors.slateText : colors.stone;

  return (
    <View style={[styles.chartContainer, { backgroundColor: chartBg }]}>
      <CartesianChart
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        data={data as any}
        // @ts-ignore Victory Native generic inference — pre-existing
        xKey="x"
        // @ts-ignore
        yKeys={['y', 'refLow', 'refHigh']}
        domain={{ y: domain }}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        chartPressState={state as any}
        padding={{ left: 8, right: 8, top: 12, bottom: 8 }}
        axisOptions={{
          tickCount: { x: 0, y: 4 },
          labelColor: axisColor,
          labelPosition: 'outset',
          axisSide: { x: 'bottom', y: 'left' },
        }}
      >
        {/* @ts-ignore Victory Native render prop — pre-existing type mismatch */}
        {({ points, chartBounds }: { points: { y: { x: number; y: number | null }[]; refHigh: { y: number | null }[]; refLow: { y: number | null }[] }; chartBounds: { left: number; right: number; top: number; bottom: number } }) => {
          const refHighY = points.refHigh[0]?.y ?? chartBounds.top;
          const refLowY  = points.refLow[0]?.y  ?? chartBounds.bottom;
          return (
            <Group>
              {hasRef && (
                <>
                  <Rect x={chartBounds.left} y={chartBounds.top} width={chartBounds.right - chartBounds.left} height={Math.max(0, refHighY - chartBounds.top)} color={SAFFRON_ZONE} />
                  <Rect x={chartBounds.left} y={refLowY} width={chartBounds.right - chartBounds.left} height={Math.max(0, chartBounds.bottom - refLowY)} color={SAFFRON_ZONE} />
                  <Rect x={chartBounds.left} y={refHighY} width={chartBounds.right - chartBounds.left} height={Math.max(0, refLowY - refHighY)} color={SAGE_BAND} />
                  <Rect x={chartBounds.left} y={refHighY} width={chartBounds.right - chartBounds.left} height={1} color={BOUND_LINE} />
                  <Rect x={chartBounds.left} y={refLowY}  width={chartBounds.right - chartBounds.left} height={1} color={BOUND_LINE} />
                </>
              )}
              {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
              <Line points={points.y as any} color={DATA_LINE} strokeWidth={2} animate={{ type: 'timing', duration: 220 }} />
              {points.y.map((p, i) => {
                if (p.y == null) return null;
                const pt = dataPoints[i];
                const isOob    = pt?.flag && pt.flag !== 'normal';
                const isLatest = i === points.y.length - 1;
                return (
                  <Circle key={i} cx={p.x} cy={p.y as number} r={isLatest ? 7 : 4}
                    color={isOob ? DATA_DOT_OOB : DATA_LINE} />
                );
              })}
              {isActive && (
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                <Circle cx={(state as any).x.position} cy={(state as any).y.y.position} r={6} color={PRESS_DOT} opacity={0.9} />
              )}
            </Group>
          );
        }}
      </CartesianChart>
      {data.map((_d, i) => {
        const pt = dataPoints[i];
        if (!pt) return null;
        const fracX = data.length > 1 ? i / (data.length - 1) : 0.5;
        return (
          <Pressable
            key={i}
            style={[styles.tapTarget, { left: `${fracX * 100}%` as unknown as number }]}
            onPress={() => onPointTap(pt)}
            accessibilityLabel={`Data point ${i + 1}: ${pt.value} ${pt.unit} on ${formatDate(pt.report_date)}`}
          />
        );
      })}
    </View>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function ChartSkeleton({ isDark }: { isDark: boolean }) {
  return (
    <View style={[styles.chartContainer, { backgroundColor: isDark ? colors.nightSurface : colors.white, alignItems: 'center', justifyContent: 'center' }]}>
      <View style={[styles.skeletonBand, { backgroundColor: isDark ? colors.nightElev : colors.borderLight }]} />
      <Text style={[styles.skeletonCaption, { color: isDark ? colors.slateText : colors.coolGray }]}>Loading trend…</Text>
    </View>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function BiomarkerTrendScreen() {
  const { name } = useLocalSearchParams<{ name: string }>();
  const router   = useRouter();
  const isDark   = useColorScheme() === 'dark';

  const [range,   setRange]   = useState<BiomarkerRange>('all');
  const [data,    setData]    = useState<BiomarkerTrendResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<BiomarkerDataPoint | null>(null);

  const fetchData = useCallback(async () => {
    if (!name) return;
    setLoading(true); setError(null);
    try {
      const result = await getBiomarkerTrend(decodeURIComponent(name as string), range);
      setData(result);
    } catch {
      setError('Could not load trend data.');
    } finally {
      setLoading(false);
    }
  }, [name, range]);

  useEffect(() => { void fetchData(); }, [fetchData]);

  const handleRangeChange = useCallback((r: BiomarkerRange) => { setRange(r); setTooltip(null); }, []);
  const handleOpenConsultation = useCallback((consultationId: string) => {
    setTooltip(null);
    router.push(`/consultations/${consultationId}`);
  }, [router]);

  const biomarkerName = data?.biomarker_name ?? decodeURIComponent(name as string ?? '');
  const unit = data?.unit ?? '';

  const bg      = isDark ? colors.midnight     : colors.skyMist;
  const textPri = isDark ? colors.white        : colors.navyDeep;
  const textSub = isDark ? colors.slateText    : colors.coolGray;
  const cardBg  = isDark ? colors.nightSurface : colors.white;
  const cardBdr = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)';

  if (error) {
    return (
      <View style={[styles.center, { backgroundColor: bg }]}>
        <Text style={[styles.errorText, { color: colors.criticalRed }]}>{error}</Text>
        <Pressable style={styles.retryBtn} onPress={() => void fetchData()}>
          <Text style={[styles.retryText, { color: colors.electricBlue }]}>Try again</Text>
        </Pressable>
      </View>
    );
  }

  const hasData      = (data?.data_points.length ?? 0) > 0;
  const tooFewPoints = (data?.data_points.length ?? 0) < 3;

  return (
    <ScrollView style={[styles.scroll, { backgroundColor: bg }]} contentContainerStyle={styles.container}>

      {/* Header */}
      <View style={styles.header}>
        <Text style={[styles.biomarkerName, { color: textPri }]}>{biomarkerName}</Text>
        {unit ? <Text style={[styles.unit, { color: textSub }]}>{unit}</Text> : null}
      </View>

      {/* Current value + trend */}
      {hasData && data && (
        <View style={styles.currentBlock}>
          <Text style={[styles.currentValue, { color: textPri }]}>
            {data.data_points[data.data_points.length - 1].value}
          </Text>
          {unit ? <Text style={[styles.currentUnit, { color: textSub }]}>{unit}</Text> : null}
          <TrendBadge trend={data.trend} isDark={isDark} />
        </View>
      )}

      {/* Range selector */}
      <RangeSelector selected={range} onSelect={handleRangeChange} isDark={isDark} />

      {/* Chart */}
      {loading ? (
        <ChartSkeleton isDark={isDark} />
      ) : hasData && data && !tooFewPoints ? (
        <>
          <BiomarkerChart
            data={buildChartData(data.data_points, data.ref_low, data.ref_high)}
            dataPoints={data.data_points}
            refLow={data.ref_low}
            refHigh={data.ref_high}
            onPointTap={setTooltip}
            isDark={isDark}
          />
          {data.ref_low != null && data.ref_high != null && (
            <Text style={[styles.refRangeLabel, { color: textSub }]}>
              Reference range: {data.ref_low}–{data.ref_high} {unit}
            </Text>
          )}
        </>
      ) : (
        <View style={[styles.emptyState, { backgroundColor: cardBg, borderColor: cardBdr }]}>
          <Text style={styles.emptyIcon}>{tooFewPoints ? '📈' : '🔬'}</Text>
          <Text style={[styles.emptyTitle, { color: textPri }]}>
            {tooFewPoints
              ? `Only ${data!.data_points.length} reading${data!.data_points.length === 1 ? '' : 's'} so far`
              : `No ${biomarkerName} values yet`}
          </Text>
          <Text style={[styles.emptySub, { color: textSub }]}>
            {tooFewPoints
              ? 'Trends become useful with three or more readings.'
              : 'Upload a lab report to start tracking this biomarker over time.'}
          </Text>
        </View>
      )}

      {/* History table */}
      {hasData && data && (
        <View style={styles.historySection}>
          <Text style={[styles.sectionTitle, { color: textPri }]}>History</Text>
          {[...data.data_points].reverse().map((pt, i) => (
            <View key={pt.report_id + i} style={[styles.historyRow, { backgroundColor: cardBg, borderColor: cardBdr }]}>
              <Text style={[styles.historyDate, { color: textSub }]}>{formatDate(pt.report_date)}</Text>
              <Text style={[styles.historyValue, { color: textPri }]}>{pt.value} {pt.unit}</Text>
              {pt.flag && pt.flag !== 'normal' && (
                <View style={[styles.flagChip, { backgroundColor: colors.warningAmber + '20' }]}>
                  <Text style={[styles.flagText, { color: colors.warningAmber }]}>
                    {pt.flag === 'high' ? '↑ High' : '↓ Low'}
                  </Text>
                </View>
              )}
              {pt.ref_low != null && pt.ref_high != null && (
                <Text style={[styles.historyRef, { color: textSub }]}>{pt.ref_low}–{pt.ref_high}</Text>
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
          isDark={isDark}
        />
      )}
    </ScrollView>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  scroll:    { flex: 1 },
  container: { flexGrow: 1, paddingHorizontal: spacing[4], paddingTop: spacing[4], paddingBottom: spacing[16], gap: spacing[4] },
  center:    { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing[4], paddingHorizontal: spacing[8] },
  errorText: { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center' },
  retryBtn:  { alignItems: 'center' },
  retryText: { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontWeight: '600' },

  header:        { gap: spacing[1] },
  biomarkerName: { fontFamily: fontFamily.display, fontSize: fontSize.h2, fontWeight: '600' },
  unit:          { fontFamily: fontFamily.body, fontSize: fontSize.caption },

  currentBlock: { flexDirection: 'row', alignItems: 'baseline', gap: spacing[2], flexWrap: 'wrap' },
  currentValue: { fontFamily: fontFamily.display, fontSize: fontSize.display, fontWeight: '500' },
  currentUnit:  { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg },

  trendBadge: {
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1],
    borderRadius: borderRadius.full,
    borderWidth: 1,
  },
  trendLabel: { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontWeight: '700' },

  rangeRow: { flexDirection: 'row', gap: spacing[2] },
  rangeBtn: {
    flex: 1,
    paddingVertical: spacing[2],
    alignItems: 'center',
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  rangeBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontWeight: '600' },

  chartContainer: {
    height: CHART_HEIGHT,
    borderRadius: borderRadius.xl,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 10,
    elevation: 2,
  },
  skeletonBand:    { position: 'absolute', left: 0, right: 0, top: '30%', height: '40%' },
  skeletonCaption: { fontFamily: fontFamily.body, fontSize: fontSize.caption },

  tapTarget: { position: 'absolute', top: 0, bottom: 0, width: 32, transform: [{ translateX: -16 }] },

  refRangeLabel: { fontFamily: fontFamily.body, fontSize: fontSize.caption, textAlign: 'center' },

  emptyState: {
    borderRadius: borderRadius.xl,
    padding: spacing[6],
    alignItems: 'center',
    gap: spacing[3],
    borderWidth: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 10,
    elevation: 2,
  },
  emptyIcon:  { fontSize: 40 },
  emptyTitle: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '700', textAlign: 'center' },
  emptySub:   { fontFamily: fontFamily.body, fontSize: fontSize.caption, textAlign: 'center', lineHeight: 20 },

  historySection: { gap: spacing[2] },
  sectionTitle:   { fontFamily: fontFamily.display, fontSize: fontSize.h3, fontWeight: '500' },
  historyRow: {
    borderRadius: borderRadius.xl,
    padding: spacing[3],
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    flexWrap: 'wrap',
    borderWidth: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.04,
    shadowRadius: 6,
    elevation: 1,
  },
  historyDate:  { fontFamily: fontFamily.body, fontSize: fontSize.caption, flex: 1 },
  historyValue: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600', fontVariant: ['tabular-nums'] },
  historyRef:   { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontVariant: ['tabular-nums'] },
  flagChip:     { paddingHorizontal: spacing[2], paddingVertical: 2, borderRadius: borderRadius.full },
  flagText:     { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontWeight: '700' },

  tooltipOverlay: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, alignItems: 'center', justifyContent: 'center' },
  tooltip: {
    borderRadius: borderRadius.xl,
    padding: spacing[4],
    marginHorizontal: spacing[8],
    gap: spacing[2],
    borderWidth: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.12,
    shadowRadius: 16,
    elevation: 6,
  },
  tooltipDate:        { fontFamily: fontFamily.body, fontSize: fontSize.caption },
  tooltipValue:       { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700', fontVariant: ['tabular-nums'] },
  tooltipRef:         { fontFamily: fontFamily.body, fontSize: fontSize.caption },
  tooltipLab:         { fontFamily: fontFamily.body, fontSize: fontSize.caption },
  tooltipConsultBtn:  { paddingTop: spacing[1] },
  tooltipConsultText: { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontWeight: '700' },
});
