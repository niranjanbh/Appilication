import { Stack } from 'expo-router';
import { useColorScheme } from 'react-native';
import { colors } from '../../lib/design-tokens';

export default function AuthLayout() {
  const isDark = useColorScheme() === 'dark';
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: isDark ? colors.midnight : colors.navyDeep },
      }}
    />
  );
}
