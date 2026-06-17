import { Ionicons } from '@expo/vector-icons';
import { useMutation } from '@tanstack/react-query';
import {
  Alert,
  Platform,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { AmbientBackground } from '../components/ui/AmbientBackground';
import { GlassCard } from '../components/ui/GlassCard';
import { HapticPressable } from '../components/ui/HapticPressable';
import { requestDataExportApi } from '../lib/api/consent';
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

export default function DownloadDataScreen() {
  const t = useTheme();

  const mutation = useMutation({
    mutationFn: requestDataExportApi,
    onSuccess: (data) => {
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
      <View style={styles.container}>
        <Text style={[styles.heading, { color: t.text }]}>Download my data</Text>

        <GlassCard>
          <View style={styles.infoSection}>
            <View style={[styles.iconCircle, { backgroundColor: withAlpha(colors.electricBlue, 0.12) }]}>
              <Ionicons name="download-outline" size={28} color={colors.electricBlue} />
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
                <Ionicons name="checkmark-circle" size={18} color={colors.successGreen} />
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
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flex: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
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
    backgroundColor: colors.navyDeep,
    borderRadius: borderRadius.xxl,
    boxShadow: `0 6px 14px ${withAlpha(colors.navyDeep, 0.30)}`,
  },
  btnDisabled: { opacity: 0.7 },
  requestBtnText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.white,
    fontWeight: '700',
  },
  successHint: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    textAlign: 'center',
  },
});
