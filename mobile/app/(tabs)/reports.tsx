import { useCallback, useEffect, useState } from 'react';
import {
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  useColorScheme,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import { listLabReports, type LabReport } from '../../lib/api/lab-reports';
import { AmbientBackground } from '../../components/ui/AmbientBackground';
import { EmptyState } from '../../components/ui/EmptyState';
import { GlassCard } from '../../components/ui/GlassCard';
import { TAB_DOCK_CLEARANCE } from '../../components/ui/GlassTabBar';
import { HapticPressable } from '../../components/ui/HapticPressable';
import { SkeletonCards } from '../../components/ui/Skeleton';
import { borderRadius, colors, fontFamily, fontSize, spacing , withAlpha } from '../../lib/design-tokens';

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
  const sColor = STATUS_COLOR[report.status] ?? colors.stone;
  const sLabel = STATUS_LABEL[report.status] ?? report.status;
  const isPdf  = report.content_type === 'application/pdf';

  const textPri = isDark ? colors.white     : colors.navyDeep;
  const textSub = isDark ? colors.slateText : colors.coolGray;

  return (
    <HapticPressable
      scaleTo={0.97}
      onPress={onPress}
      accessibilityLabel={`View ${report.original_filename}`}
    >
      <GlassCard unpadded>
        <View style={styles.card}>
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
        </View>
      </GlassCard>
    </HapticPressable>
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

  const bg = isDark ? colors.midnight : colors.skyMist;

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: bg }]}>
        <AmbientBackground />
        <View style={styles.list}>
          <View style={styles.header}>
            <Text style={[styles.title, { color: isDark ? colors.white : colors.navyDeep }]}>
              Lab Reports
            </Text>
          </View>
          <SkeletonCards count={4} />
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: bg }]}>
      <AmbientBackground />
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
          error ? (
            <EmptyState
              icon="cloud-offline-outline"
              tint="amber"
              title={error}
              body="Pull down to refresh, or try again in a moment. Your reports are safe."
            />
          ) : (
            <EmptyState
              icon="flask-outline"
              tint="green"
              title="No reports yet"
              body="Upload a lab report and we'll extract your biomarker results automatically."
              ctaLabel="Upload report"
              onCtaPress={() => router.push('/reports/upload')}
            />
          )
        }
      />

      {/* Upload FAB — floats above the tab dock */}
      <HapticPressable
        haptic="medium"
        scaleTo={0.95}
        containerStyle={styles.fab}
        style={styles.uploadBtn}
        onPress={() => router.push('/reports/upload')}
        accessibilityLabel="Upload lab report"
      >
        <Text style={styles.uploadIcon}>+</Text>
        <Text style={styles.uploadText}>Upload report</Text>
      </HapticPressable>
    </View>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1 },
  list: {
    paddingHorizontal: spacing[4],
    paddingTop: spacing[2],
    paddingBottom: TAB_DOCK_CLEARANCE + 72,
  },

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
    padding: spacing[4],
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
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

  fab: {
    position: 'absolute',
    bottom: TAB_DOCK_CLEARANCE - spacing[6],
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
    boxShadow: `0 8px 16px ${withAlpha(colors.navyDeep, 0.30)}`,
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
