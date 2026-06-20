import { Ionicons } from '@expo/vector-icons';
import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import {
  Alert,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { AmbientBackground } from '../components/ui/AmbientBackground';
import { GlassCard } from '../components/ui/GlassCard';
import { HapticPressable } from '../components/ui/HapticPressable';
import { useAuth } from '../lib/auth/context';
import { requestErasureApi } from '../lib/api/consent';
import {
  borderRadius,
  colors,
  fontFamily,
  fontSize,
  spacing,
  withAlpha,
} from '../lib/design-tokens';
import { useTheme } from '../lib/theme';

const CONFIRM_PHRASE = 'DELETE';

export default function DeleteAccountScreen() {
  const t = useTheme();
  const { signOut } = useAuth();
  const [confirmText, setConfirmText] = useState('');

  const mutation = useMutation({
    mutationFn: requestErasureApi,
    onSuccess: (data) => {
      if (Platform.OS === 'web') {
        window.alert(data.message);
      } else {
        Alert.alert('Account deletion requested', data.message);
      }
      signOut();
    },
    onError: () => {
      if (Platform.OS === 'web') {
        window.alert('Could not request account deletion. Please try again.');
      } else {
        Alert.alert('Error', 'Could not request account deletion. Please try again.');
      }
    },
  });

  const canSubmit = confirmText.trim().toUpperCase() === CONFIRM_PHRASE && !mutation.isPending;

  const handleDelete = () => {
    if (Platform.OS === 'web') {
      if (window.confirm('Are you absolutely sure?\n\nThis action cannot be undone. Your account and personal data will be permanently deleted within 30 days.')) {
        mutation.mutate();
      }
    } else {
      Alert.alert(
        'Are you absolutely sure?',
        'This action cannot be undone. Your account and personal data will be permanently deleted within 30 days.',
        [
          { text: 'Cancel', style: 'cancel' },
          { text: 'Delete permanently', style: 'destructive', onPress: () => mutation.mutate() },
        ],
      );
    }
  };

  const inputBg = t.isDark ? withAlpha(colors.white, 0.06) : withAlpha(colors.stone, 0.10);
  const inputBorder = t.isDark ? withAlpha(colors.white, 0.10) : withAlpha(colors.stone, 0.25);

  return (
    <View style={[styles.flex, { backgroundColor: t.background }]}>
      <AmbientBackground />
      <ScrollView style={styles.flex} contentContainerStyle={styles.container}>
        <Text style={[styles.heading, { color: t.text }]}>Delete my account</Text>

        <GlassCard>
          <View style={styles.warningSection}>
            <View style={[styles.iconCircle, { backgroundColor: withAlpha(colors.alert, 0.12) }]}>
              <Ionicons name="warning" size={28} color={colors.alert} />
            </View>
            <Text style={[styles.warningTitle, { color: colors.alert }]}>
              This is permanent
            </Text>
            <Text style={[styles.warningBody, { color: t.textSub }]}>
              Once you delete your account, all your personal data will be
              permanently erased within 30 days. This action cannot be undone.
            </Text>
          </View>
        </GlassCard>

        <GlassCard>
          <View style={styles.detailSection}>
            <Text style={[styles.detailTitle, { color: t.text }]}>What happens next</Text>
            {[
              'Your profile and personal information will be anonymized',
              'Active sessions will be revoked immediately',
              'Medical records are retained for 7 years per NMC regulations',
              'You will receive a confirmation notification',
            ].map(item => (
              <View key={item} style={styles.bulletRow}>
                <Ionicons name="ellipse" size={6} color={t.textSub} />
                <Text style={[styles.bulletText, { color: t.textSub }]}>{item}</Text>
              </View>
            ))}
          </View>
        </GlassCard>

        <GlassCard>
          <View style={styles.confirmSection}>
            <Text style={[styles.confirmLabel, { color: t.text }]}>
              Type <Text style={styles.confirmPhrase}>{CONFIRM_PHRASE}</Text> to confirm
            </Text>
            <TextInput
              style={[styles.confirmInput, {
                color: t.text,
                backgroundColor: inputBg,
                borderColor: confirmText.trim().toUpperCase() === CONFIRM_PHRASE
                  ? colors.alert
                  : inputBorder,
              }]}
              value={confirmText}
              onChangeText={setConfirmText}
              placeholder={CONFIRM_PHRASE}
              placeholderTextColor={t.textSub}
              autoCapitalize="characters"
              accessibilityLabel={`Type ${CONFIRM_PHRASE} to confirm account deletion`}
            />
          </View>
        </GlassCard>

        <HapticPressable
          haptic="medium"
          scaleTo={0.97}
          style={[styles.deleteBtn, !canSubmit && styles.btnDisabled]}
          onPress={handleDelete}
          disabled={!canSubmit}
          accessibilityLabel="Delete my account permanently"
        >
          {mutation.isPending ? (
            <Text style={styles.deleteBtnText}>Deleting…</Text>
          ) : (
            <>
              <Ionicons name="trash-outline" size={20} color={colors.white} />
              <Text style={styles.deleteBtnText}>Delete my account</Text>
            </>
          )}
        </HapticPressable>
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
  warningSection: { alignItems: 'center', gap: spacing[3], paddingVertical: spacing[2] },
  iconCircle: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
  },
  warningTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    fontWeight: '700',
    textAlign: 'center',
  },
  warningBody: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    lineHeight: 22,
    textAlign: 'center',
  },
  detailSection: { gap: spacing[3] },
  detailTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
  bulletRow: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing[2] },
  bulletText: {
    flex: 1,
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    lineHeight: 22,
  },
  confirmSection: { gap: spacing[3] },
  confirmLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
  },
  confirmPhrase: {
    fontWeight: '700',
    color: colors.alert,
  },
  confirmInput: {
    borderRadius: borderRadius.lg,
    borderWidth: 1,
    padding: spacing[4],
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    fontWeight: '600',
    textAlign: 'center',
    letterSpacing: 2,
  },
  deleteBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing[2],
    height: 52,
    backgroundColor: colors.alert,
    borderRadius: borderRadius.xxl,
    boxShadow: `0 6px 14px ${withAlpha(colors.alert, 0.30)}`,
  },
  btnDisabled: { opacity: 0.4 },
  deleteBtnText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.ivoryText,
    fontWeight: '700',
  },
});
