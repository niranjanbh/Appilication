import { Stack } from 'expo-router';
import { colors } from '../../lib/design-tokens';
import { useThemePreference } from '../../lib/theme-context';

export default function AuthLayout() {
  const isDark = useThemePreference().colorScheme === 'dark';
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: isDark ? colors.forestInk : colors.forest, overflow: 'hidden' },
      }}
    />
  );
}
