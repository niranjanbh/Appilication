import { Stack } from 'expo-router';
import { useColorScheme } from 'react-native';
import { colors } from '../../lib/design-tokens';

export default function OnboardingLayout() {
  const isDark = useColorScheme() === 'dark';
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: isDark ? colors.midnight : colors.skyMist },
        // Prevent back gesture during onboarding
        gestureEnabled: false,
      }}
    />
  );
}
