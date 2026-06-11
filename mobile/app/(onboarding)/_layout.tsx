import { Stack } from 'expo-router';
import { colors } from '../../lib/design-tokens';
import { useThemePreference } from '../../lib/theme-context';

export default function OnboardingLayout() {
  const isDark = useThemePreference().colorScheme === 'dark';
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
