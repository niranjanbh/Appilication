import { Stack } from 'expo-router';
import { colors } from '../../lib/design-tokens';

export default function OnboardingLayout() {
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.ivory },
        // Prevent back gesture during onboarding
        gestureEnabled: false,
      }}
    />
  );
}
