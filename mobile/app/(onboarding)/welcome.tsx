import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

const PILLARS = [
  { icon: '👩‍⚕️', title: 'Doctor-first care', text: 'A specialist who reads your full history' },
  { icon: '🔬',   title: 'Your labs, decoded', text: 'Biomarkers that become a real care plan' },
  { icon: '📋',   title: 'One record, always yours', text: 'Portable, private, and always accessible' },
];

export default function WelcomeScreen() {
  const router = useRouter();

  const btnScale = useSharedValue(1);
  const btnAnim  = useAnimatedStyle(() => ({ transform: [{ scale: btnScale.value }] }));

  return (
    <View style={styles.container}>

      {/* Hero */}
      <View style={styles.hero}>
        <Text style={styles.wordmark}>Kyros</Text>
        <Text style={styles.headline}>
          Doctor-first care for{'\n'}hormonal health
        </Text>
        <Text style={styles.subtext}>
          A specialist, a care plan, and a record that grows with you.
        </Text>
      </View>

      {/* Feature pillars (glass cards on navy bg) */}
      <View style={styles.pillars}>
        {PILLARS.map(({ icon, title, text }) => (
          <View key={title} style={styles.pillar}>
            <View style={styles.pillarIconWrap}>
              <Text style={styles.pillarIcon}>{icon}</Text>
            </View>
            <View style={styles.pillarText}>
              <Text style={styles.pillarTitle}>{title}</Text>
              <Text style={styles.pillarBody}>{text}</Text>
            </View>
          </View>
        ))}
      </View>

      {/* Footer CTA */}
      <View style={styles.footer}>
        <Animated.View style={btnAnim}>
          <Pressable
            style={styles.button}
            onPress={() => router.push('/(onboarding)/conditions')}
            onPressIn={() => { btnScale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
            onPressOut={() => { btnScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
            accessibilityLabel="Get started"
          >
            <Text style={styles.buttonText}>Get started</Text>
          </Pressable>
        </Animated.View>
        <Text style={styles.privacyNote}>
          Your health data stays in India and is never sold.
        </Text>
      </View>

    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.navyDeep,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[16],
    paddingBottom: spacing[8],
    justifyContent: 'space-between',
  },

  hero: { gap: spacing[3] },
  wordmark: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    color: colors.electricBlue,
    fontWeight: '500',
  },
  headline: {
    fontFamily: fontFamily.display,
    fontSize: 40,
    color: colors.white,
    fontWeight: '600',
    lineHeight: 48,
  },
  subtext: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: 'rgba(255,255,255,0.65)',
    lineHeight: 24,
  },

  pillars: { gap: spacing[3] },
  pillar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[4],
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.10)',
    padding: spacing[4],
  },
  pillarIconWrap: {
    width: 44,
    height: 44,
    borderRadius: 14,
    backgroundColor: 'rgba(255,255,255,0.12)',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  pillarIcon: { fontSize: 22 },
  pillarText: { flex: 1, gap: 2 },
  pillarTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.white,
    fontWeight: '600',
  },
  pillarBody: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: 'rgba(255,255,255,0.60)',
    lineHeight: 18,
  },

  footer: { gap: spacing[3] },
  button: {
    height: 56,
    backgroundColor: colors.white,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.20,
    shadowRadius: 16,
    elevation: 6,
  },
  buttonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.navyDeep,
    fontWeight: '700',
  },
  privacyNote: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: 'rgba(255,255,255,0.45)',
    textAlign: 'center',
  },
});
