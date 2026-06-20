import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { colors, fontFamily, fontSize, fontWeight } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';
import { useThemePreference } from '../../lib/theme-context';
import { useAuth } from '../../lib/auth/context';
import { AvatarMenu } from './AvatarMenu';

export function HeaderAvatar() {
  const t = useTheme();
  const router = useRouter();
  const { state, signOut } = useAuth();
  const { setPreference, colorScheme } = useThemePreference();
  const [menuVisible, setMenuVisible] = useState(false);

  const userName = state.status === 'authenticated' ? state.user.name : '';
  const initial = userName.charAt(0).toUpperCase() || '?';

  const avatarBg = t.isDark ? colors.saffron : colors.forest;
  const avatarText = t.isDark ? colors.forestInk : colors.ivory;

  return (
    <>
      <Pressable
        onPress={() => setMenuVisible(true)}
        accessibilityLabel="Profile menu"
        style={styles.button}
      >
        <View style={[styles.circle, { backgroundColor: avatarBg }]}>
          <Text style={[styles.initial, { color: avatarText }]}>{initial}</Text>
        </View>
      </Pressable>

      <AvatarMenu
        visible={menuVisible}
        onClose={() => setMenuVisible(false)}
        displayName={userName}
        items={[
          { icon: 'person-outline', label: 'Profile', onPress: () => router.push('/(tabs)/profile' as Parameters<typeof router.push>[0]) },
          { icon: 'card-outline', label: 'Payments', onPress: () => router.push('/payments' as Parameters<typeof router.push>[0]) },
          { icon: 'phone-portrait-outline', label: 'Devices', onPress: () => router.push('/sessions' as Parameters<typeof router.push>[0]) },
          { icon: 'moon-outline', label: t.isDark ? 'Light mode' : 'Dark mode', onPress: () => setPreference(colorScheme === 'dark' ? 'light' : 'dark') },
          { icon: 'log-out-outline', label: 'Sign out', onPress: signOut, destructive: true },
        ]}
      />
    </>
  );
}

const styles = StyleSheet.create({
  button: {
    width: 36,
    height: 36,
    alignItems: 'center',
    justifyContent: 'center',
  },
  circle: {
    width: 30,
    height: 30,
    borderRadius: 15,
    alignItems: 'center',
    justifyContent: 'center',
  },
  initial: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.sm,
    fontWeight: fontWeight.medium,
  },
});
