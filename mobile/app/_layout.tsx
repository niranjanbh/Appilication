import { Stack } from 'expo-router';

export default function RootLayout() {
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: '#0F3D2E' },
        headerTintColor: '#FAF1E4',
        headerTitleStyle: { fontWeight: '500' },
      }}
    />
  );
}
