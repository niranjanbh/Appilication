import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useAuth } from '../../lib/auth/context';
import { colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

export default function HomeScreen() {
  const { state } = useAuth();
  const name = state.status === 'authenticated' ? state.user.name.split(' ')[0] : '';

  return (
    <ScrollView style={styles.flex} contentContainerStyle={styles.container}>
      <View style={styles.welcome}>
        <Text style={styles.greeting}>Good to have you, {name}</Text>
        <Text style={styles.subtitle}>Your care plan will appear here after your first consultation.</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Book your first consultation</Text>
        <Text style={styles.cardBody}>
          Talk to a Kyros specialist about your hormonal health. Slots available within 48 hours.
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.ivory },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
    paddingBottom: spacing[8],
    gap: spacing[6],
  },
  welcome: { gap: spacing[2] },
  greeting: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    color: colors.forest,
    fontWeight: '500',
  },
  subtitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    lineHeight: 22,
  },
  card: {
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: spacing[4],
    gap: spacing[2],
  },
  cardTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.forest,
    fontWeight: '600',
  },
  cardBody: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    lineHeight: 22,
  },
});
