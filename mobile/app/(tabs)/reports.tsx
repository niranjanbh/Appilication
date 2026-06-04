import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  useColorScheme,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { listLabReports, type LabReport } from '../../lib/api/lab-reports';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

// ── Status config ─────────────────────────────────────────────────────────────

const STATUS_LABEL: Record<string, string> = {
  upload_pending:        'Upload pending',
  ocr_pending:           'Processing…',
  ocr_processing:        'Processing…',
  ocr_complete:          'Ready',
  ocr_failed:            'Processing failed',
  patient_review_needed: 'Needs your review',
};

const STATUS_COLOR: Record<string, string> = {
  upload_pending:        colors.stone,
  ocr_pending:           colors.warningAmber,
  ocr_processing:        colors.warningAmber,
  ocr_complete:          colors.successGreen,
  ocr_failed:            colors.criticalRed,
  patient_review_needed: colors.warningAmber,
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  });
}

// ── Report card ───────────────────────────────────────────────────────────────

function ReportCard({
  report,
  onPress,
  isDark,
}: {
  report: LabReport;
  onPress: () => void;
  isDark: boolean;
}) {
  const scale  = useSharedValue(1);
  const anim   = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));
  const sColor = STATUS_COLOR[report.status] ?? colors.stone;
  const sLabel = STATUS_LABEL[report.status] ?? report.status;
  const isPdf  = report.content_type === 'application/pdf';

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
        accessibilityLabel={`View ${report.original_filename}`}
      >
        <View style={[styles.fileIcon, { backgroundColor: sColor + '18' }]}>
          <Text style={[styles.fileIconText, { color: sColor }]}>{isPdf ? 'PDF' : 'IMG'}</Text>
        </View>
        <View style={styles.cardBody}>
          <Text style={[styles.filename, { color: textPri }]} numberOfLines={1}>
            {report.original_filename}
          </Text>
          {report.lab_name ? <Text style={[styles.labName, { color: textSub }]}>{report.lab_name}</Text> : null}
          <Text style={[styles.date, { color: textSub }]}>{formatDate(report.created_at)}</Text>
        </View>
        <View style={styles.cardRight}>
          <View style={[styles.statusPill, { backgroundColor: sColor + '18' }]}>
            <Text style={[styles.statusText, { color: sColor }]}>{sLabel}</Text>
          </View>
          <Text style={[styles.chevron, { color: textSub }]}>›</Text>
        </View>
      </Pressable>
    </Animated.View>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function ReportsScreen() {
  const router  = useRouter();
  const isDark  = useColorScheme() === 'dark';
  const [reports, setReports] = useState<LabReport[]>([]);
  const [total, setTotal]     = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  const load = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      const data = await listLabReports(1, 50);
      setReports(data.items);
      setTotal(data.total);
      setError(null);
    } catch {
      setError('Could not load lab reports. Please try again.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const fabScale = useSharedValue(1);
  const fabAnim  = useAnimatedStyle(() => ({ transform: [{ scale: fabScale.value }] }));

  const bg = isDark ? colors.midnight : colors.skyMist;

  if (loading) {
    return (
      <View style={[styles.center, { backgroundColor: bg }]}>
        <ActivityIndicator color={colors.electricBlue} />
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: bg }]}>
      <FlatList
        data={reports}
        keyExtractor={(r) => r.id}
        renderItem={({ item }) => (
          <ReportCard
            report={item}
            isDark={isDark}
            onPress={() => router.push(`/reports/${item.id}`)}
          />
        )}
        contentContainerStyle={styles.list}
        ItemSeparatorComponent={() => <View style={{ height: spacing[3] }} />}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => void load(true)}
            tintColor={colors.electricBlue}
          />
        }
        ListHeaderComponent={
          <View style={styles.header}>
            <Text style={[styles.title, { color: isDark ? colors.white : colors.navyDeep }]}>
              Lab Reports
            </Text>
            <Text style={[styles.subtitle, { color: isDark ? colors.slateText : colors.coolGray }]}>
              {total > 0 ? `${total} report${total === 1 ? '' : 's'}` : 'No reports yet'}
            </Text>
          </View>
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            <View style={[styles.emptyIconWrap, { backgroundColor: isDark ? colors.nightSurface : colors.white }]}>
              <Text style={styles.emptyIconText}>🔬</Text>
            </View>
            <Text style={[styles.emptyTitle, { color: isDark ? colors.white : colors.navyDeep }]}>
              {error ?? 'No reports yet'}
            </Text>
            {!error && (
              <Text style={[styles.emptySub, { color: isDark ? colors.slateText : colors.coolGray }]}>
                Upload a lab report and we'll extract your biomarker results automatically.
              </Text>
            )}
          </View>
        }
      />

      {/* Upload FAB */}
      <Animated.View style={[styles.fab, fabAnim]}>
        <Pressable
          style={styles.uploadBtn}
          onPress={() => router.push('/reports/upload')}
          onPressIn={() => { fabScale.value = withSpring(0.95, { mass: 0.3, stiffness: 500 }); }}
          onPressOut={() => { fabScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
          accessibilityLabel="Upload lab report"
        >
          <Text style={styles.uploadIcon}>+</Text>
          <Text style={styles.uploadText}>Upload report</Text>
        </Pressable>
      </Animated.View>
    </View>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1 },
  center:    { flex: 1, alignItems: 'center', justifyContent: 'center' },
  list: { paddingHorizontal: spacing[4], paddingTop: spacing[2], paddingBottom: 100 },

  header: { paddingVertical: spacing[4], gap: spacing[1] },
  title: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    fontWeight: '600',
  },
  subtitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
  },

  card: {
    borderRadius: borderRadius.xl,
    padding: spacing[4],
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    borderWidth: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 10,
    elevation: 2,
  },
  fileIcon: {
    width: 48,
    height: 48,
    borderRadius: borderRadius.xl,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  fileIconText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  cardBody: { flex: 1, gap: 3 },
  filename: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
  labName: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
  },
  date: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
  },
  cardRight: { alignItems: 'flex-end', gap: spacing[2] },
  statusPill: {
    paddingHorizontal: spacing[2],
    paddingVertical: 3,
    borderRadius: borderRadius.full,
  },
  statusText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    fontWeight: '700',
  },
  chevron: {
    fontFamily: fontFamily.body,
    fontSize: 20,
  },

  empty: { alignItems: 'center', paddingTop: spacing[16], gap: spacing[4] },
  emptyIconWrap: {
    width: 72,
    height: 72,
    borderRadius: 36,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 3,
  },
  emptyIconText: { fontSize: 32 },
  emptyTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    fontWeight: '700',
    textAlign: 'center',
  },
  emptySub: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    textAlign: 'center',
    lineHeight: 22,
    paddingHorizontal: spacing[6],
  },

  fab: {
    position: 'absolute',
    bottom: spacing[8],
    left: spacing[6],
    right: spacing[6],
  },
  uploadBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing[2],
    height: 56,
    backgroundColor: colors.navyDeep,
    borderRadius: borderRadius.xxl,
    shadowColor: colors.navyDeep,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.30,
    shadowRadius: 16,
    elevation: 8,
  },
  uploadIcon: {
    fontFamily: fontFamily.body,
    fontSize: 22,
    color: colors.white,
    lineHeight: 26,
  },
  uploadText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.white,
    fontWeight: '700',
  },
});
