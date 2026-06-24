import { Stack } from 'expo-router';
import { colors } from '../../lib/design-tokens';
import { useThemePreference } from '../../lib/theme-context';
import { OnboardingIntakeProvider } from '../../lib/onboarding/intake-context';

export default function OnboardingLayout() {
  const isDark = useThemePreference().colorScheme === 'dark';
  return (
    <OnboardingIntakeProvider>
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: isDark ? colors.forestInk : colors.ivory },
          // Prevent back gesture during onboarding
          gestureEnabled: false,
        }}
      />
    </OnboardingIntakeProvider>
  );
}
