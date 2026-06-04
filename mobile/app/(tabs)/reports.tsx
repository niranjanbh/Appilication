/**
 * Reports tab — shows the patient's lab report list and entry point to upload.
 */

import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import { listLabReports, type LabReport } from '../../lib/api/lab-reports';
import { colors, fontFamily, fontSize, spacing, borderRadius } from '../../lib/design-tokens';

// ── Status helpers ────────────────────────────────────────────────────────────

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
  ocr_pending:           colors.saffron,
  ocr_processing:        colors.saffron,
  ocr_complete:          colors.forest,
  ocr_failed:            colors.terracotta,
  patient_review_needed: colors.saffron,
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

// ── Report card ───────────────────────────────────────────────────────────────

function ReportCard({ report, onPress }: { report: LabReport; onPress: () => void }) {
  const statusColor = STATUS_COLOR[report.status] ?? colors.stone;
  const statusLabel = STATUS_LABEL[report.status] ?? report.status;

  return (
    <Pressable style={styles.card} onPress={onPress} accessibilityLabel={`View ${report.original_filename}`}>
      <View style={styles.cardLeft}>
        <View style={[styles.fileIcon, { backgroundColor: statusColor + '18' }]}>
          <Text style={[styles.fileIconText, { color: statusColor }]}>
            {report.content_type === 'application/pdf' ? 'PDF' : 'IMG'}
          </Text>
        </View>
      </View>
      <View style={styles.cardBody}>
        <Text style={styles.filename} numberOfLines={1}>
          {report.original_filename}
        </Text>
        {report.lab_name ? (
          <Text style={styles.labName}>{report.lab_name}</Text>
        ) : null}
        <Text style={styles.date}>{formatDate(report.created_at)}</Text>
      </View>
      <View style={styles.cardRight}>
        <View style={[styles.statusBadge, { backgroundColor: statusColor + '18' }]}>
          <Text style={[styles.statusText, { color: statusColor }]}>{statusLabel}</Text>
        </View>
        <Text style={styles.chevron}>›</Text>
      </View>
    </Pressable>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function ReportsScreen() {
  const router = useRouter();
  const [reports, setReports] = useState<LabReport[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.forest} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={reports}
        keyExtractor={(r) => r.id}
        renderItem={({ item }) => (
          <ReportCard
            report={item}
            onPress={() => router.push(`/reports/${item.id}`)}
          />
        )}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => void load(true)} tintColor={colors.forest} />
        }
        ListHeaderComponent={
          <View style={styles.header}>
            <Text style={styles.title}>Lab Reports</Text>
            <Text style={styles.subtitle}>
              {total > 0 ? `${total} report${total === 1 ? '' : 's'}` : 'No reports yet'}
            </Text>
          </View>
        }
        ListEmptyComponent={
          !error ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyTitle}>No reports yet</Text>
              <Text style={styles.emptySub}>
                Upload a lab report and our system will extract your biomarker results
                automatically.
              </Text>
            </View>
          ) : (
            <View style={styles.emptyState}>
              <Text style={[styles.emptyTitle, { color: colors.terracotta }]}>{error}</Text>
            </View>
          )
        }
      />
      <View style={styles.fab}>
        <Pressable
          style={styles.uploadButton}
          onPress={() => router.push('/reports/upload')}
          accessibilityLabel="Upload lab report"
        >
          <Text style={styles.uploadButtonText}>+ Upload report</Text>
        </Pressable>
      </View>
    </View>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.ivory,
  },
  center: {
    flex: 1,
    backgroundColor: colors.ivory,
    alignItems: 'center',
    justifyContent: 'center',
  },
  list: {
    paddingHorizontal: spacing[4],
    paddingBottom: spacing[24],
  },
  header: {
    paddingTop: spacing[6],
    paddingBottom: spacing[4],
    gap: spacing[1],
  },
  title: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    color: colors.forest,
    fontWeight: '500',
  },
  subtitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: colors.stone,
  },
  card: {
    backgroundColor: colors.white,
    borderRadius: borderRadius.lg,
    padding: spacing[4],
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing[3],
    gap: spacing[3],
  },
  cardLeft: {},
  fileIcon: {
    width: 44,
    height: 44,
    borderRadius: borderRadius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  fileIconText: {
    fontFamily: fontFamily.body,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  cardBody: {
    flex: 1,
    gap: 2,
  },
  filename: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    fontWeight: '500',
  },
  labName: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: colors.stone,
  },
  date: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
  },
  cardRight: {
    alignItems: 'flex-end',
    gap: spacing[2],
  },
  statusBadge: {
    paddingHorizontal: spacing[2],
    paddingVertical: 3,
    borderRadius: borderRadius.sm,
  },
  statusText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    fontWeight: '600',
  },
  chevron: {
    fontFamily: fontFamily.body,
    fontSize: 20,
    color: colors.stone,
  },
  emptyState: {
    alignItems: 'center',
    paddingTop: spacing[16],
    paddingHorizontal: spacing[6],
    gap: spacing[3],
  },
  emptyTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.ink,
    fontWeight: '600',
    textAlign: 'center',
  },
  emptySub: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    textAlign: 'center',
    lineHeight: 22,
  },
  fab: {
    position: 'absolute',
    bottom: spacing[8],
    left: spacing[6],
    right: spacing[6],
  },
  uploadButton: {
    backgroundColor: colors.forest,
    borderRadius: borderRadius.lg,
    paddingVertical: spacing[4],
    alignItems: 'center',
    shadowColor: colors.forest,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    elevation: 4,
  },
  uploadButtonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '700',
    color: colors.white,
  },
});
