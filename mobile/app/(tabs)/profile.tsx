import { useRouter } from 'expo-router';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useAuth } from '../../lib/auth/context';
import { colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

export default function ProfileScreen() {
  const router = useRouter();
  const { state, signOut } = useAuth();
  const user = state.status === 'authenticated' ? state.user : null;

  return (
    <ScrollView style={styles.flex} contentContainerStyle={styles.container}>
      {user && (
        <View style={styles.identityCard}>
          <Text style={styles.name}>{user.name}</Text>
          {user.phone && <Text style={styles.detail}>{user.phone}</Text>}
          {user.email && <Text style={styles.detail}>{user.email}</Text>}
        </View>
      )}

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Privacy & data</Text>
        <MenuItem label="My consents" onPress={() => {}} />
        <MenuItem label="Health Records (ABHA)" onPress={() => router.push('/abha-settings')} />
        <MenuItem label="Download my data" onPress={() => {}} />
        <MenuItem label="Delete my account" onPress={() => {}} destructive />
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Account</Text>
        <MenuItem label="Notification preferences" onPress={() => router.push('/notification-preferences')} />
      </View>

      <Pressable
        style={styles.signOutButton}
        onPress={signOut}
        accessibilityLabel="Sign out"
      >
        <Text style={styles.signOutText}>Sign out</Text>
      </Pressable>
    </ScrollView>
  );
}

function MenuItem({
  label,
  onPress,
  destructive = false,
}: {
  label: string;
  onPress: () => void;
  destructive?: boolean;
}) {
  return (
    <Pressable
      style={menuStyles.item}
      onPress={onPress}
      accessibilityLabel={label}
    >
      <Text style={[menuStyles.label, destructive && menuStyles.destructive]}>{label}</Text>
      <Text style={menuStyles.chevron}>›</Text>
    </Pressable>
  );
}

const menuStyles = StyleSheet.create({
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: spacing[3],
    borderBottomWidth: 1,
    borderBottomColor: '#F0EDE8',
  },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
  },
  destructive: { color: colors.alert },
  chevron: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.stone,
  },
});

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.ivory },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
    paddingBottom: spacing[8],
    gap: spacing[6],
  },
  identityCard: {
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: spacing[4],
    gap: spacing[1],
  },
  name: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.forest,
    fontWeight: '600',
  },
  detail: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
  },
  section: {
    backgroundColor: colors.white,
    borderRadius: 12,
    paddingHorizontal: spacing[4],
    paddingTop: spacing[3],
    paddingBottom: spacing[1],
  },
  sectionTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: spacing[2],
  },
  signOutButton: {
    borderWidth: 1,
    borderColor: colors.stone,
    borderRadius: 8,
    paddingVertical: spacing[3],
    alignItems: 'center',
    marginTop: spacing[4],
  },
  signOutText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
  },
});
