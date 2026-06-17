import { Redirect } from 'expo-router';
import { ActivityIndicator, View } from 'react-native';
import { useAuth } from '../lib/auth/context';
import { useThemePreference } from '../lib/theme-context';
import { colors } from '../lib/design-tokens';

export default function Index() {
  const { state } = useAuth();
  const isDark = useThemePreference().colorScheme === 'dark';
  const bg = isDark ? colors.forestInk : colors.navyDeep;

  if (state.status === 'loading') {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: bg }}>
        <ActivityIndicator color={colors.white} size="large" />
      </View>
    );
  }

  if (state.status === 'unauthenticated') {
    return <Redirect href="/(auth)/login" />;
  }

  if (!state.onboardingComplete) {
    return <Redirect href="/(onboarding)/welcome" />;
  }

  return <Redirect href="/(tabs)/home" />;
}
