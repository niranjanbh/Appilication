/**
 * Biomarker trend screen — web version.
 *
 * Victory Native and Skia are native-only. On web we render a sortable table
 * of data points with inline trend indicator instead of the canvas chart.
 * Metro picks this file (.web.tsx) over [name].tsx automatically on web builds.
 */

import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, useColorScheme, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import {
  getBiomarkerTrend,
  type BiomarkerDataPoint,
  type BiomarkerRange,
  type BiomarkerTrendResponse,
} from '../../lib/api/biomarker-trends';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

const RANGES: { label: string; value: BiomarkerRange }[] = [
  { label: '7d',  value: '7d'  },
  { label: '30d', value: '30d' },
  { label: '90d', value: '90d' },
  { label: '1y',  value: '1y'  },
  { label: 'All', value: 'all' },
];

function flagColor(flag: BiomarkerDataPoint['flag']): string {
  if (flag === 'high') return colors.criticalRed;
  if (flag === 'low')  return colors.warningAmber;
  return colors.successGreen;
}

function trendLabel(t: BiomarkerTrendResponse['trend']): string {
  if (t === 'better') return '↑ Improving';
  if (t === 'worse')  return '↓ Worsening';
  return '↔ Steady';
}

function trendColor(t: BiomarkerTrendResponse['trend']): string {
  if (t === 'better') return colors.successGreen;
  if (t === 'worse')  return colors.criticalRed;
  return colors.coolGray;
}

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

export default function BiomarkerTrendWebScreen() {
  const { name }  = useLocalSearchParams<{ name: string }>();
  const router    = useRouter();
  const isDark    = useColorScheme() === 'dark';
  const [range,   setRange]   = useState<BiomarkerRange>('all');
  const [data,    setData]    = useState<BiomarkerTrendResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);

  useEffect(() => {
    if (!name) return;
    setLoading(true);
    getBiomarkerTrend(decodeURIComponent(name as string), range)
      .then(setData)
      .catch(() => setError('Unable to load trend data.'))
      .finally(() => setLoading(false));
  }, [name, range]);

  const bg        = isDark ? colors.midnight     : colors.skyMist;
  const textPri   = isDark ? colors.white        : colors.navyDeep;
  const textSub   = isDark ? colors.slateText    : colors.coolGray;
  const cardBg    = isDark ? colors.nightSurface : colors.white;
  const cardBdr   = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)';
  const rowAltBg  = isDark ? colors.nightElev    : colors.skyMist;
  const headerBg  = isDark ? colors.navyMid + '30' : colors.navyDeep + '10';

  return (
    <ScrollView style={[styles.container, { backgroundColor: bg }]} contentContainerStyle={styles.content}>

      {/* Back */}
      <Pressable onPress={() => router.back()} style={styles.backRow} accessibilityLabel="Back">
        <Text style={[styles.backText, { color: colors.electricBlue }]}>← Back</Text>
      </Pressable>

      {/* Title */}
      <Text style={[styles.title, { color: textPri }]}>
        {name ? decodeURIComponent(name as string) : '—'}
      </Text>

      {/* Range selector */}
      <View style={styles.rangeRow}>
        {RANGES.map(r => (
          <Pressable
            key={r.value}
            onPress={() => setRange(r.value)}
            style={[
              styles.rangeBtn,
              {
                backgroundColor: range === r.value ? colors.navyDeep : cardBg,
                borderColor:     range === r.value ? colors.navyDeep : cardBdr,
              },
            ]}
            accessibilityLabel={`Show ${r.label}`}
          >
            <Text style={[
              styles.rangeBtnText,
              { color: range === r.value ? colors.white : textSub, fontWeight: range === r.value ? '700' : '400' },
            ]}>
              {r.label}
            </Text>
          </Pressable>
        ))}
      </View>

      {/* Loading */}
      {loading && (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={colors.electricBlue} />
        </View>
      )}

      {/* Error */}
      {error && <Text style={[styles.errorText, { color: colors.criticalRed }]}>{error}</Text>}

      {/* Data */}
      {data && !loading && (
        <>
          {/* Summary card */}
          <View style={[styles.summaryCard, { backgroundColor: cardBg, borderColor: cardBdr }]}>
            {[
              { label: 'Unit',      value: data.unit || '—',          color: textPri },
              { label: 'Reference', value: `${data.ref_low ?? '—'} – ${data.ref_high ?? '—'}`, color: textPri },
              { label: 'Trend',     value: trendLabel(data.trend),    color: trendColor(data.trend) },
            ].map(({ label, value, color }) => (
              <View key={label} style={styles.summaryItem}>
                <Text style={[styles.summaryLabel, { color: textSub }]}>{label}</Text>
                <Text style={[styles.summaryValue, { color }]}>{value}</Text>
              </View>
            ))}
          </View>

          {/* Data table */}
          {data.data_points.length === 0 ? (
            <View style={[styles.emptyState, { backgroundColor: cardBg, borderColor: cardBdr }]}>
              <Text style={styles.emptyIcon}>📊</Text>
              <Text style={[styles.emptyText, { color: textPri }]}>No data for this range</Text>
              <Text style={[styles.emptySub, { color: textSub }]}>Try selecting a wider time period.</Text>
            </View>
          ) : (
            <View style={[styles.table, { backgroundColor: cardBg, borderColor: cardBdr }]}>
              {/* Header row */}
              <View style={[styles.tableRow, styles.tableHeader, { backgroundColor: headerBg }]}>
                {['Date', 'Value', 'Lab', 'Status'].map((h, i) => (
                  <Text key={h} style={[styles.cell, styles.headerCell, { color: textSub, flex: i === 0 ? 2 : i === 2 ? 1.5 : 1 }]}>{h}</Text>
                ))}
              </View>
              {/* Data rows */}
              {[...data.data_points].reverse().map((pt, i) => (
                <View key={pt.report_id + i} style={[
                  styles.tableRow,
                  { backgroundColor: i % 2 === 1 ? rowAltBg : 'transparent' },
                ]}>
                  <Text style={[styles.cell, { flex: 2, color: textSub }]}>{formatDate(pt.report_date)}</Text>
                  <Text style={[styles.cell, { flex: 1, color: flagColor(pt.flag), fontWeight: '700' }]}>
                    {pt.value} {pt.unit}
                  </Text>
                  <Text style={[styles.cell, { flex: 1.5, color: textSub }]} numberOfLines={1}>
                    {pt.lab_name || '—'}
                  </Text>
                  <View style={[styles.statusCell, { flex: 1 }]}>
                    <View style={[styles.statusPill, { backgroundColor: flagColor(pt.flag) + '18' }]}>
                      <Text style={[styles.statusText, { color: flagColor(pt.flag) }]}>
                        {pt.flag && pt.flag !== 'normal' ? (pt.flag === 'high' ? '↑ High' : '↓ Low') : '✓ Normal'}
                      </Text>
                    </View>
                  </View>
                </View>
              ))}
            </View>
          )}
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content:   { padding: spacing[6], paddingBottom: spacing[8], maxWidth: 800 },

  backRow:  { marginBottom: spacing[4] },
  backText: { fontFamily: fontFamily.body, fontSize: fontSize.sm, fontWeight: '600' },

  title: { fontFamily: fontFamily.display, fontSize: fontSize.h2, fontWeight: '600', marginBottom: spacing[4] },

  rangeRow: { flexDirection: 'row', gap: spacing[2], marginBottom: spacing[5] },
  rangeBtn: {
    paddingVertical: spacing[2],
    paddingHorizontal: spacing[3],
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    boxShadow: '0 2px 4px rgba(0,0,0,0.04)',
  },
  rangeBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.caption },

  center:    { paddingVertical: spacing[8], alignItems: 'center' },
  errorText: { fontFamily: fontFamily.body, fontSize: fontSize.body },

  summaryCard: {
    flexDirection: 'row',
    gap: spacing[4],
    marginBottom: spacing[4],
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    padding: spacing[5],
    boxShadow: '0 4px 10px rgba(0,0,0,0.06)',
  },
  summaryItem:  { flex: 1, gap: spacing[1] },
  summaryLabel: { fontFamily: fontFamily.body, fontSize: fontSize.caption },
  summaryValue: { fontFamily: fontFamily.display, fontSize: fontSize.bodyLg, fontWeight: '600' },

  table: {
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    overflow: 'hidden',
    boxShadow: '0 4px 10px rgba(0,0,0,0.06)',
  },
  tableRow:    { flexDirection: 'row', paddingVertical: spacing[3], paddingHorizontal: spacing[4], alignItems: 'center' },
  tableHeader: { borderBottomWidth: 1, borderBottomColor: 'rgba(0,0,0,0.06)' },
  cell:        { fontFamily: fontFamily.body, fontSize: fontSize.caption },
  headerCell:  { fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5, fontSize: fontSize.xs },

  statusCell: { alignItems: 'flex-start' },
  statusPill: { borderRadius: borderRadius.full, paddingHorizontal: spacing[2], paddingVertical: 2 },
  statusText: { fontFamily: fontFamily.body, fontSize: fontSize.xs, fontWeight: '700' },

  emptyState: {
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    padding: spacing[8],
    alignItems: 'center',
    gap: spacing[3],
    boxShadow: '0 4px 10px rgba(0,0,0,0.06)',
  },
  emptyIcon: { fontSize: 40 },
  emptyText: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700', textAlign: 'center' },
  emptySub:  { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center' },
});
