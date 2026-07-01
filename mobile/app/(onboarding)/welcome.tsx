import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';
import { AuthBackdrop } from '../../components/ui/AuthBackdrop';
import { HapticPressable } from '../../components/ui/HapticPressable';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

const PILLARS: { icon: IoniconName; title: string; text: string }[] = [
  { icon: 'medkit-outline',        title: 'Doctor-first care',        text: 'A specialist who reads your full history' },
  { icon: 'flask-outline',         title: 'Your labs, decoded',       text: 'Biomarkers that become a real care plan' },
  { icon: 'document-text-outline', title: 'One record, always yours', text: 'Portable, private, and always accessible' },
];

export default function WelcomeScreen() {
  const router = useRouter();

  return (
    <View style={styles.container}>
      <AuthBackdrop />

      {/* Hero */}
      <View style={styles.hero}>
        <Text style={styles.wordmark}>Baseline</Text>
        <Text style={styles.headline}>
          Doctor-first care for{'\n'}hormonal health
        </Text>
        <Text style={styles.subtext}>
          A specialist, a care plan, and a record that grows with you.
        </Text>
      </View>

      {/* Feature pillars (glass cards on the gradient) */}
      <View style={styles.pillars}>
        {PILLARS.map(({ icon, title, text }) => (
          <View key={title} style={styles.pillar}>
            <View style={styles.pillarIconWrap}>
              <Ionicons name={icon} size={22} color={colors.white} />
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
        <HapticPressable
          haptic="medium"
          style={styles.button}
          onPress={() => router.push('/(onboarding)/conditions')}
          accessibilityLabel="Get started"
        >
          <Text style={styles.buttonText}>Get started</Text>
        </HapticPressable>
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
    backgroundColor: colors.forest,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[16],
    paddingBottom: spacing[8],
    justifyContent: 'space-between',
  },

  hero: { gap: spacing[3] },
  wordmark: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    color: colors.jade,
    fontWeight: '500',
  },
  headline: {
    fontFamily: fontFamily.display,
    fontSize: 40,
    color: colors.ivoryText,
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
  pillarText: { flex: 1, gap: 2 },
  pillarTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.ivoryText,
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
    boxShadow: '0 8px 16px rgba(0,0,0,0.20)',
  },
  buttonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.ink,
    fontWeight: '700',
  },
  privacyNote: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: 'rgba(255,255,255,0.45)',
    textAlign: 'center',
  },
});
