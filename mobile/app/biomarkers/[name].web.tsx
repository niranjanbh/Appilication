/**
 * Biomarker trend screen — web version.
 *
 * Victory Native and Skia are native-only. On web we render a sortable table
 * of data points with inline trend indicator instead of the canvas chart.
 * Metro picks this file (.web.tsx) over [name].tsx automatically on web builds.
 */

import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
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
  { label: '7d',  value: '7d' },
  { label: '30d', value: '30d' },
  { label: '90d', value: '90d' },
  { label: '1y',  value: '1y' },
  { label: 'All', value: 'all' },
];

function flagColor(flag: BiomarkerDataPoint['flag']): string {
  if (flag === 'high') return colors.terracotta;
  if (flag === 'low') return colors.saffron;
  return colors.forest;
}

function trendLabel(t: BiomarkerTrendResponse['trend']): string {
  if (t === 'better') return '↑ Improving';
  if (t === 'worse') return '↓ Worsening';
  return '↔ Steady';
}

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  });
}

export default function BiomarkerTrendWebScreen() {
  const { name } = useLocalSearchParams<{ name: string }>();
  const router = useRouter();
  const [range, setRange] = useState<BiomarkerRange>('all');
  const [data, setData] = useState<BiomarkerTrendResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!name) return;
    setLoading(true);
    getBiomarkerTrend(name, range)
      .then(setData)
      .catch(() => setError('Unable to load trend data.'))
      .finally(() => setLoading(false));
  }, [name, range]);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Pressable onPress={() => router.back()} style={styles.backRow} accessibilityLabel="Back">
        <Text style={styles.backText}>← Back</Text>
      </Pressable>

      <Text style={styles.title}>{name ? decodeURIComponent(name as string) : '—'}</Text>

      {/* Range selector */}
      <View style={styles.rangeRow}>
        {RANGES.map((r) => (
          <Pressable
            key={r.value}
            onPress={() => setRange(r.value)}
            style={[styles.rangeBtn, range === r.value && styles.rangeBtnActive]}
            accessibilityLabel={`Show ${r.label}`}
          >
            <Text style={[styles.rangeBtnText, range === r.value && styles.rangeBtnTextActive]}>
              {r.label}
            </Text>
          </Pressable>
        ))}
      </View>

      {loading && (
        <View style={styles.center}>
          <ActivityIndicator color={colors.forest} />
        </View>
      )}

      {error && <Text style={styles.errorText}>{error}</Text>}

      {data && !loading && (
        <>
          {/* Summary */}
          <View style={styles.summaryRow}>
            <View style={styles.summaryItem}>
              <Text style={styles.summaryLabel}>Unit</Text>
              <Text style={styles.summaryValue}>{data.unit || '—'}</Text>
            </View>
            <View style={styles.summaryItem}>
              <Text style={styles.summaryLabel}>Reference</Text>
              <Text style={styles.summaryValue}>
                {data.ref_low ?? '—'} – {data.ref_high ?? '—'}
              </Text>
            </View>
            <View style={styles.summaryItem}>
              <Text style={styles.summaryLabel}>Trend</Text>
              <Text style={[styles.summaryValue, { color: data.trend === 'better' ? colors.forest : data.trend === 'worse' ? colors.terracotta : colors.stone }]}>
                {trendLabel(data.trend)}
              </Text>
            </View>
          </View>

          {/* Data table */}
          {data.data_points.length === 0 ? (
            <View style={styles.empty}>
              <Text style={styles.emptyText}>No data points for this range.</Text>
            </View>
          ) : (
            <View style={styles.table}>
              {/* Header */}
              <View style={[styles.row, styles.headerRow]}>
                <Text style={[styles.cell, styles.headerCell, { flex: 2 }]}>Date</Text>
                <Text style={[styles.cell, styles.headerCell, { flex: 1 }]}>Value</Text>
                <Text style={[styles.cell, styles.headerCell, { flex: 1.5 }]}>Lab</Text>
                <Text style={[styles.cell, styles.headerCell, { flex: 1 }]}>Status</Text>
              </View>
              {[...data.data_points].reverse().map((pt, i) => (
                <View key={pt.report_id + i} style={[styles.row, i % 2 === 1 && styles.rowAlt]}>
                  <Text style={[styles.cell, { flex: 2 }]}>{formatDate(pt.report_date)}</Text>
                  <Text style={[styles.cell, { flex: 1, color: flagColor(pt.flag), fontWeight: '600' }]}>
                    {pt.value} {pt.unit}
                  </Text>
                  <Text style={[styles.cell, { flex: 1.5 }]} numberOfLines={1}>
                    {pt.lab_name || '—'}
                  </Text>
                  <Text style={[styles.cell, { flex: 1, color: flagColor(pt.flag) }]}>
                    {pt.flag ? pt.flag.toUpperCase() : 'Normal'}
                  </Text>
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
  container: { flex: 1, backgroundColor: colors.ivory },
  content: { padding: spacing[4], paddingBottom: spacing[8], maxWidth: 800 },
  backRow: { marginBottom: spacing[3] },
  backText: { fontFamily: fontFamily.body, fontSize: fontSize.caption, color: colors.forest },
  title: { fontFamily: fontFamily.display, fontSize: fontSize.h2, color: colors.ink, marginBottom: spacing[3] },

  rangeRow: { flexDirection: 'row', gap: spacing[2], marginBottom: spacing[4] },
  rangeBtn: { paddingVertical: spacing[1], paddingHorizontal: spacing[3], borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.stone + '40' },
  rangeBtnActive: { backgroundColor: colors.forest, borderColor: colors.forest },
  rangeBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.caption, color: colors.stone },
  rangeBtnTextActive: { color: colors.white, fontWeight: '600' },

  center: { paddingVertical: spacing[8], alignItems: 'center' },
  errorText: { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.terracotta },

  summaryRow: { flexDirection: 'row', gap: spacing[4], marginBottom: spacing[4], backgroundColor: colors.white, borderRadius: borderRadius.lg, padding: spacing[4] },
  summaryItem: { flex: 1 },
  summaryLabel: { fontFamily: fontFamily.body, fontSize: fontSize.caption, color: colors.stone, marginBottom: 2 },
  summaryValue: { fontFamily: fontFamily.display, fontSize: fontSize.bodyLg, color: colors.ink },

  table: { backgroundColor: colors.white, borderRadius: borderRadius.lg, overflow: 'hidden' },
  row: { flexDirection: 'row', paddingVertical: spacing[2], paddingHorizontal: spacing[3] },
  rowAlt: { backgroundColor: colors.ivory },
  headerRow: { backgroundColor: colors.forest + '14', borderBottomWidth: 1, borderBottomColor: colors.stone + '20' },
  cell: { fontFamily: fontFamily.body, fontSize: fontSize.caption, color: colors.ink },
  headerCell: { fontWeight: '600', color: colors.ink },

  empty: { paddingVertical: spacing[6], alignItems: 'center' },
  emptyText: { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.stone },
});
