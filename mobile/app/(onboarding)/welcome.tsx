import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

const PILLARS = [
  { icon: '👩‍⚕️', text: 'A real doctor who reads your history' },
  { icon: '🔬', text: 'Lab results that become a plan' },
  { icon: '📋', text: 'One record, always yours' },
];

export default function WelcomeScreen() {
  const router = useRouter();

  return (
    <View style={styles.container}>
      <View style={styles.hero}>
        <Text style={styles.wordmark}>Kyros</Text>
        <Text style={styles.headline}>
          Doctor-first care for{'\n'}hormonal health
        </Text>
        <Text style={styles.subtext}>
          A specialist, a plan, and a record that grows with you.
        </Text>
      </View>

      <View style={styles.pillars}>
        {PILLARS.map(({ icon, text }) => (
          <View key={text} style={styles.pillar}>
            <Text style={styles.pillarIcon}>{icon}</Text>
            <Text style={styles.pillarText}>{text}</Text>
          </View>
        ))}
      </View>

      <View style={styles.footer}>
        <Pressable
          style={styles.button}
          onPress={() => router.push('/(onboarding)/conditions')}
          accessibilityLabel="Get started"
        >
          <Text style={styles.buttonText}>Get started</Text>
        </Pressable>
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
    backgroundColor: colors.ivory,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[16],
    paddingBottom: spacing[8],
    justifyContent: 'space-between',
  },
  hero: { gap: spacing[3] },
  wordmark: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    color: colors.saffron,
    fontWeight: '500',
  },
  headline: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.display,
    color: colors.forest,
    fontWeight: '500',
    lineHeight: 44,
  },
  subtext: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.stone,
    lineHeight: 24,
  },
  pillars: { gap: spacing[4] },
  pillar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: spacing[4],
  },
  pillarIcon: { fontSize: 24 },
  pillarText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    flex: 1,
  },
  footer: { gap: spacing[3] },
  button: {
    backgroundColor: colors.forest,
    borderRadius: 8,
    paddingVertical: spacing[4],
    alignItems: 'center',
  },
  buttonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.ivory,
    fontWeight: '600',
  },
  privacyNote: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    textAlign: 'center',
  },
});
