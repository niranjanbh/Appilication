import { Ionicons } from '@expo/vector-icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Linking,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { AmbientBackground } from '../components/ui/AmbientBackground';
import { GlassCard } from '../components/ui/GlassCard';
import { HapticPressable } from '../components/ui/HapticPressable';
import {
  getDataExportApi,
  listDataExportsApi,
  requestDataExportApi,
  type DataExportStatus,
  type DataExportSummary,
} from '../lib/api/consent';
import {
  borderRadius,
  colors,
  fontFamily,
  fontSize,
  spacing,
  withAlpha,
} from '../lib/design-tokens';
import { useTheme } from '../lib/theme';

function showAlert(title: string, message: string) {
  if (Platform.OS === 'web') {
    window.alert(`${title}\n\n${message}`);
  } else {
    Alert.alert(title, message);
  }
}

const STATUS_META: Record<DataExportStatus, { label: string; color: string }> = {
  received:    { label: 'Queued',     color: colors.saffron },
  in_progress: { label: 'Preparing',  color: colors.saffron },
  completed:   { label: 'Ready',      color: colors.jade },
  rejected:    { label: 'Unavailable', color: colors.alert },
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

async function openExportDownload(id: string): Promise<void> {
  const detail = await getDataExportApi(id);
  if (!detail.download_url) {
    showAlert('Not ready', 'This export is not ready to download yet.');
    return;
  }
  if (Platform.OS === 'web') {
    window.open(detail.download_url, '_blank');
  } else {
    await Linking.openURL(detail.download_url);
  }
}

export default function DownloadDataScreen() {
  const t = useTheme();
  const queryClient = useQueryClient();

  const { data: exportsData } = useQuery({
    queryKey: ['data-exports'],
    queryFn: listDataExportsApi,
    staleTime: 30_000,
  });
  const exports = exportsData?.items ?? [];

  const downloadMutation = useMutation({
    mutationFn: openExportDownload,
    onError: () => { showAlert('Error', 'Could not start the download. Please try again.'); },
  });

  const mutation = useMutation({
    mutationFn: requestDataExportApi,
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ['data-exports'] });
      showAlert(
        'Export requested',
        data.message,
      );
    },
    onError: () => {
      showAlert('Error', 'Could not request data export. Please try again.');
    },
  });

  const handleRequest = () => {
    if (Platform.OS === 'web') {
      if (window.confirm('Request a copy of all your data?\n\nWe will compile your data and notify you when it is ready for download.')) {
        mutation.mutate();
      }
    } else {
      Alert.alert(
        'Download your data',
        'We will compile a copy of all your data and notify you when it is ready for download.',
        [
          { text: 'Cancel', style: 'cancel' },
          { text: 'Request export', onPress: () => mutation.mutate() },
        ],
      );
    }
  };

  return (
    <View style={[styles.flex, { backgroundColor: t.background }]}>
      <AmbientBackground />
      <ScrollView style={styles.flex} contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>
        <Text style={[styles.heading, { color: t.text }]}>Download my data</Text>

        <GlassCard>
          <View style={styles.infoSection}>
            <View style={[styles.iconCircle, { backgroundColor: withAlpha(colors.jade, 0.12) }]}>
              <Ionicons name="download-outline" size={28} color={colors.jade} />
            </View>
            <Text style={[styles.infoTitle, { color: t.text }]}>
              Your data, your right
            </Text>
            <Text style={[styles.infoBody, { color: t.textSub }]}>
              Under the DPDP Act 2023, you have the right to access a copy of
              all personal data we hold about you. This includes your profile,
              consultation history, lab reports, prescriptions, and consent records.
            </Text>
          </View>
        </GlassCard>

        <GlassCard>
          <View style={styles.bulletSection}>
            <Text style={[styles.bulletTitle, { color: t.text }]}>What's included</Text>
            {['Profile information', 'Consent records', 'Data subject requests'].map(item => (
              <View key={item} style={styles.bulletRow}>
                <Ionicons name="checkmark-circle" size={18} color={colors.jade} />
                <Text style={[styles.bulletText, { color: t.textSub }]}>{item}</Text>
              </View>
            ))}
          </View>
        </GlassCard>

        <HapticPressable
          haptic="medium"
          scaleTo={0.97}
          style={[styles.requestBtn, mutation.isPending && styles.btnDisabled]}
          onPress={handleRequest}
          disabled={mutation.isPending || mutation.isSuccess}
          accessibilityLabel="Request data export"
        >
          {mutation.isPending ? (
            <Text style={styles.requestBtnText}>Requesting…</Text>
          ) : mutation.isSuccess ? (
            <>
              <Ionicons name="checkmark-circle" size={20} color={colors.white} />
              <Text style={styles.requestBtnText}>Export requested</Text>
            </>
          ) : (
            <>
              <Ionicons name="download-outline" size={20} color={colors.white} />
              <Text style={styles.requestBtnText}>Request data export</Text>
            </>
          )}
        </HapticPressable>

        {mutation.isSuccess && (
          <Text style={[styles.successHint, { color: t.textSub }]}>
            You will be notified when your data is ready for download.
          </Text>
        )}

        {exports.length > 0 && (
          <GlassCard>
            <View style={styles.requestsSection}>
              <Text style={[styles.bulletTitle, { color: t.text }]}>Your requests</Text>
              {exports.map((ex: DataExportSummary) => {
                const meta = STATUS_META[ex.status];
                const downloading =
                  downloadMutation.isPending && downloadMutation.variables === ex.id;
                return (
                  <View key={ex.id} style={styles.requestRow}>
                    <View style={styles.requestInfo}>
                      <Text style={[styles.requestDate, { color: t.text }]}>
                        Requested {formatDate(ex.requested_at)}
                      </Text>
                      <View style={[styles.statusPill, { backgroundColor: meta.color + '18' }]}>
                        <Text style={[styles.statusText, { color: meta.color }]}>{meta.label}</Text>
                      </View>
                    </View>
                    {ex.status === 'completed' && (
                      <Pressable
                        onPress={() => downloadMutation.mutate(ex.id)}
                        disabled={downloading}
                        accessibilityLabel="Download export"
                        style={[styles.downloadLink, downloading && styles.btnDisabled]}
                      >
                        <Ionicons name="download-outline" size={16} color={colors.jade} />
                        <Text style={[styles.downloadLinkText, { color: colors.jade }]}>
                          {downloading ? 'Opening…' : 'Download'}
                        </Text>
                      </Pressable>
                    )}
                  </View>
                );
              })}
            </View>
          </GlassCard>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
    paddingBottom: spacing[12],
    gap: spacing[5],
  },
  heading: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    fontWeight: '600',
  },
  infoSection: { alignItems: 'center', gap: spacing[3], paddingVertical: spacing[2] },
  iconCircle: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
  },
  infoTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    fontWeight: '600',
    textAlign: 'center',
  },
  infoBody: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    lineHeight: 22,
    textAlign: 'center',
  },
  bulletSection: { gap: spacing[3] },
  bulletTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
  bulletRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  bulletText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
  },
  requestBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing[2],
    height: 52,
    backgroundColor: colors.forest,
    borderRadius: borderRadius.xxl,
    boxShadow: `0 6px 14px ${withAlpha(colors.forest, 0.30)}`,
  },
  btnDisabled: { opacity: 0.7 },
  requestBtnText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.ivoryText,
    fontWeight: '700',
  },
  successHint: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    textAlign: 'center',
  },
  requestsSection: { gap: spacing[3] },
  requestRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing[3],
  },
  requestInfo: { flex: 1, gap: spacing[1], flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap' },
  requestDate: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
  },
  statusPill: {
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
    borderRadius: borderRadius.full,
  },
  statusText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
  },
  downloadLink: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[1],
    paddingHorizontal: spacing[2],
    paddingVertical: spacing[1],
  },
  downloadLinkText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: '600',
  },
});
