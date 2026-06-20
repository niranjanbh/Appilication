/**
 * Consultation join screen — web fallback.
 * Live video via 100ms is not supported in the web portal.
 * Metro picks this file (.web.tsx) over [id].tsx automatically on web builds.
 */

import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useThemePreference } from '../../../lib/theme-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { borderRadius, colors, fontFamily, fontSize, spacing , withAlpha } from '../../../lib/design-tokens';

export default function JoinConsultationWebScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const isDark = useThemePreference().colorScheme === 'dark';

  const btnScale = useSharedValue(1);
  const btnAnim  = useAnimatedStyle(() => ({ transform: [{ scale: btnScale.value }] }));
  const SPRING   = { mass: 0.3, stiffness: 500, damping: 20 };

  const bg      = isDark ? colors.forestInk     : colors.ivory;
  const cardBg  = isDark ? colors.forestSurface : colors.white;
  const cardBdr = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)';
  const textPri = isDark ? colors.ivoryText     : colors.ink;
  const textSub = isDark ? colors.stoneDim : colors.stone;

  return (
    <View style={[styles.container, { backgroundColor: bg }]}>
      <View style={[styles.card, { backgroundColor: cardBg, borderColor: cardBdr }]}>
        <View style={[styles.iconWrap, { backgroundColor: colors.forest + '15' }]}>
          <Text style={styles.icon}>📱</Text>
        </View>
        <Text style={[styles.title, { color: textPri }]}>Open the Kyros app to join</Text>
        <Text style={[styles.body, { color: textSub }]}>
          Live video consultations require the Kyros mobile app. Download it to join your appointment on your phone or tablet.
        </Text>
        <Animated.View style={[btnAnim, { width: '100%' }]}>
          <Pressable
            onPress={() => router.replace(`/consultations/${id}`)}
            onPressIn={() => { btnScale.value = withSpring(0.97, SPRING); }}
            onPressOut={() => { btnScale.value = withSpring(1, SPRING); }}
            style={styles.btn}
            accessibilityLabel="View consultation details"
          >
            <Text style={styles.btnText}>View consultation details</Text>
          </Pressable>
        </Animated.View>
        <Pressable
          onPress={() => router.back()}
          style={styles.backBtn}
          accessibilityLabel="Go back"
        >
          <Text style={[styles.backBtnText, { color: textSub }]}>← Go back</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing[6],
  },
  card: {
    width: '100%',
    maxWidth: 440,
    borderRadius: borderRadius.xxl,
    padding: spacing[6],
    gap: spacing[4],
    alignItems: 'center',
    borderWidth: 1,
    boxShadow: '0 8px 20px rgba(0,0,0,0.10)',
  },
  iconWrap: {
    width: 72,
    height: 72,
    borderRadius: 36,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing[1],
  },
  icon:  { fontSize: 32 },
  title: { fontFamily: fontFamily.display, fontSize: fontSize.h3, fontWeight: '600', textAlign: 'center' },
  body:  { fontFamily: fontFamily.body, fontSize: fontSize.body, lineHeight: 22, textAlign: 'center' },
  btn: {
    width: '100%',
    height: 56,
    backgroundColor: colors.forest,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: `0 8px 16px ${withAlpha(colors.forest, 0.28)}`,
  },
  btnText:     { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, color: colors.ivoryText, fontWeight: '700' },
  backBtn:     { paddingVertical: spacing[2] },
  backBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.caption },
});
