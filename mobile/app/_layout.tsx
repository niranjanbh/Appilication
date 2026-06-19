import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import { ActivityIndicator, useColorScheme, View } from 'react-native';
import { AuthProvider } from '../lib/auth/context';
import { OpenInAppBanner } from '../components/web/OpenInAppBanner';
import { PrivacyShield } from '../components/ui/PrivacyShield';
import { ErrorBoundary } from '../components/ui/ErrorBoundary';
import { OfflineBanner } from '../components/ui/OfflineBanner';
import { colors, fontFamily, fontSize } from '../lib/design-tokens';
import { ThemeProvider, useThemePreference } from '../lib/theme-context';
// Side-effect: registers the background sync task definition before the React tree mounts.
import '../lib/native/background-sync';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 60_000, refetchOnWindowFocus: false },
  },
});

export default function RootLayout() {
  const isDark = useColorScheme() === 'dark';

  const [fontsLoaded] = useFonts({
    'CormorantGaramond-Regular': require('@expo-google-fonts/cormorant-garamond/400Regular/CormorantGaramond_400Regular.ttf'),
    'CormorantGaramond-Medium':  require('@expo-google-fonts/cormorant-garamond/500Medium/CormorantGaramond_500Medium.ttf'),
    'CormorantGaramond-Italic':  require('@expo-google-fonts/cormorant-garamond/400Regular_Italic/CormorantGaramond_400Regular_Italic.ttf'),
    'DMSans-Regular':            require('@expo-google-fonts/dm-sans/400Regular/DMSans_400Regular.ttf'),
    'DMSans-Medium':             require('@expo-google-fonts/dm-sans/500Medium/DMSans_500Medium.ttf'),
    'DMSans-SemiBold':           require('@expo-google-fonts/dm-sans/600SemiBold/DMSans_600SemiBold.ttf'),
    'TiroDevanagariHindi-Regular': require('@expo-google-fonts/tiro-devanagari-hindi/400Regular/TiroDevanagariHindi_400Regular.ttf'),
  });

  // Match the app's real background per theme so the hand-off to the first screen
  // is seamless — light: skyMist bg + navy spinner; dark: forest-ink bg + jade spinner.
  const loadingBg      = isDark ? colors.forestInk : colors.skyMist;
  const loadingSpinner = isDark ? colors.jadeGlow  : colors.navyDeep;

  if (!fontsLoaded) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: loadingBg }}>
        <ActivityIndicator color={loadingSpinner} size="large" />
      </View>
    );
  }

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <AuthProvider>
            <OpenInAppBanner />
            <OfflineBanner />
            <RootLayoutNav />
            {/* Covers PHI when the app is backgrounded (app-switcher snapshots). */}
            <PrivacyShield />
          </AuthProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

function RootLayoutNav() {
  const { colorScheme } = useThemePreference();
  const isDark = colorScheme === 'dark';

  const headerBg   = isDark ? colors.forestSurface : colors.navyDeep;
  const headerText = colors.white;

  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: headerBg },
        headerTintColor: headerText,
        headerTitleStyle: {
          fontFamily: fontFamily.display,
          fontSize: fontSize.h3,
          color: headerText,
        },
        headerShadowVisible: false,
        contentStyle: { backgroundColor: isDark ? colors.forestInk : colors.skyMist },
      }}
    >
      {/* Route groups render their own headers (or none) — hide the outer
          Stack header so its default title (the literal group segment name,
          e.g. "(tabs)" / "(auth)") never appears. */}
      <Stack.Screen name="index" options={{ headerShown: false }} />
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen name="(auth)" options={{ headerShown: false }} />
      <Stack.Screen name="(onboarding)" options={{ headerShown: false }} />
      <Stack.Screen name="notes/index" options={{ title: 'My Notes' }} />
      <Stack.Screen name="payments" options={{ title: 'Payments & refunds' }} />
    </Stack>
  );
}
