import { Stack } from 'expo-router';
import { colors } from '../../lib/design-tokens';

export default function AuthLayout() {
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.ivory },
      }}
    />
  );
}
