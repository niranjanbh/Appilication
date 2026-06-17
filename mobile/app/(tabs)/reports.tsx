import { useCallback, useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useThemePreference } from '../../lib/theme-context';
import { useRouter } from 'expo-router';
import { listLabReports, type LabReport } from '../../lib/api/lab-reports';
import { AmbientBackground } from '../../components/ui/AmbientBackground';
import { EmptyState } from '../../components/ui/EmptyState';
import { TAB_DOCK_CLEARANCE } from '../../components/ui/GlassTabBar';
import { SkeletonCards } from '../../components/ui/Skeleton';
import { colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';
import { ReportsFolderView } from '../../components/reports/ReportsFolderView';
import type { ReportFile, ReportFolder } from '../../components/reports/ReportsFolderView';

export default function ReportsScreen() {
  const router  = useRouter();
  const isDark  = useThemePreference().colorScheme === 'dark';
  const [reports, setReports] = useState<LabReport[]>([]);
  const [total, setTotal]     = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await listLabReports(1, 50);
      setReports(data.items);
      setTotal(data.total);
      setError(null);
    } catch {
      setError('Could not load lab reports. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const bg = isDark ? colors.forestInk : colors.skyMist;

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: bg }]}>
        <AmbientBackground />
        <View style={styles.loadingPad}>
          <SkeletonCards count={4} />
        </View>
      </View>
    );
  }

  if (error) {
    return (
      <View style={[styles.container, { backgroundColor: bg }]}>
        <AmbientBackground />
        <View style={styles.loadingPad}>
          <EmptyState
            icon="cloud-offline-outline"
            tint="amber"
            title={error}
            body="Pull down to refresh, or try again in a moment. Your reports are safe."
          />
        </View>
      </View>
    );
  }

  const folders: ReportFolder[] = [
    { id: 'lab', name: 'Lab Reports', fileCount: reports.length, iconName: 'flask-outline' },
  ];

  const recentFiles: ReportFile[] = reports.slice(0, 6).map(r => ({
    id: r.id,
    name: r.original_filename,
    fileType: r.content_type === 'application/pdf' ? 'pdf' : 'image',
    uploadedAt: r.created_at,
  }));

  return (
    <View style={[styles.container, { backgroundColor: bg }]}>
      <AmbientBackground />
      <View style={styles.header}>
        <Text style={[styles.title, { color: isDark ? colors.ivoryText : colors.navyDeep }]}>
          Reports
        </Text>
        <Text style={[styles.subtitle, { color: isDark ? colors.stoneDim : colors.coolGray }]}>
          {total > 0 ? `${total} file${total === 1 ? '' : 's'}` : 'No reports yet'}
        </Text>
      </View>
      <ReportsFolderView
        folders={folders}
        recentFiles={recentFiles}
        onUpload={() => router.push('/reports/upload')}
        onDownload={() => {}}
        onDelete={() => {}}
        onOpenFolder={() => {}}
        onOpenFile={f => router.push(`/reports/${f.id}`)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container:  { flex: 1 },
  loadingPad: {
    paddingHorizontal: spacing[4],
    paddingTop: spacing[4],
    paddingBottom: TAB_DOCK_CLEARANCE + 72,
  },
  header: {
    paddingHorizontal: spacing[4],
    paddingTop: spacing[4],
    paddingBottom: spacing[2],
    gap: spacing[1],
  },
  title: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    fontWeight: '600',
  },
  subtitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
  },
});
