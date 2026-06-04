/**
 * Consultation join screen — web fallback.
 *
 * Live video via 100ms is not supported in the web portal. Patients must use
 * the native app or a supported browser with the dedicated 100ms room URL.
 * Metro picks this file (.web.tsx) over [id].tsx automatically on web builds.
 */

import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../../lib/design-tokens';

export default function JoinConsultationWebScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.title}>Open the Kyros app to join</Text>
        <Text style={styles.body}>
          Live video consultations require the Kyros mobile app. Download it to join your
          appointment on your phone or tablet.
        </Text>
        <Pressable
          onPress={() => router.replace(`/consultations/${id}`)}
          style={styles.btn}
          accessibilityLabel="View consultation details"
        >
          <Text style={styles.btnText}>View consultation details</Text>
        </Pressable>
        <Pressable
          onPress={() => router.back()}
          style={styles.backBtn}
          accessibilityLabel="Go back"
        >
          <Text style={styles.backBtnText}>← Go back</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.ivory, padding: spacing[4] },
  card: { backgroundColor: colors.white, borderRadius: borderRadius.lg, padding: spacing[6], maxWidth: 440, width: '100%', gap: spacing[4] },
  title: { fontFamily: fontFamily.display, fontSize: fontSize.h3, color: colors.ink },
  body: { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.stone, lineHeight: 22 },
  btn: { backgroundColor: colors.forest, borderRadius: borderRadius.md, paddingVertical: spacing[3], alignItems: 'center' },
  btnText: { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.white, fontWeight: '600' },
  backBtn: { alignItems: 'center' },
  backBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.caption, color: colors.stone },
});
