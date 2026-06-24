import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useFonts } from 'expo-font';
import { Stack, useRouter, useSegments } from 'expo-router';
import { useEffect } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { AuthProvider, useAuth } from '../lib/auth/context';
import { OpenInAppBanner } from '../components/web/OpenInAppBanner';
import { PrivacyShield } from '../components/ui/PrivacyShield';
import { ErrorBoundary } from '../components/ui/ErrorBoundary';
import { ServiceBanner } from '../components/ui/ServiceBanner';
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
  const [fontsLoaded] = useFonts({
    'CormorantGaramond-Regular': require('@expo-google-fonts/cormorant-garamond/400Regular/CormorantGaramond_400Regular.ttf'),
    'CormorantGaramond-Medium':  require('@expo-google-fonts/cormorant-garamond/500Medium/CormorantGaramond_500Medium.ttf'),
    'CormorantGaramond-Italic':  require('@expo-google-fonts/cormorant-garamond/400Regular_Italic/CormorantGaramond_400Regular_Italic.ttf'),
    'DMSans-Regular':            require('@expo-google-fonts/dm-sans/400Regular/DMSans_400Regular.ttf'),
    'DMSans-Medium':             require('@expo-google-fonts/dm-sans/500Medium/DMSans_500Medium.ttf'),
    'DMSans-SemiBold':           require('@expo-google-fonts/dm-sans/600SemiBold/DMSans_600SemiBold.ttf'),
    'TiroDevanagariHindi-Regular': require('@expo-google-fonts/tiro-devanagari-hindi/400Regular/TiroDevanagariHindi_400Regular.ttf'),
    'Newsreader-Regular':        require('@expo-google-fonts/newsreader/400Regular/Newsreader_400Regular.ttf'),
    'Newsreader-Medium':         require('@expo-google-fonts/newsreader/500Medium/Newsreader_500Medium.ttf'),
    'Newsreader-Italic':         require('@expo-google-fonts/newsreader/400Regular_Italic/Newsreader_400Regular_Italic.ttf'),
  });

  // Pre-login splash is always light (auth flow is light-mode only).
  const loadingBg      = colors.ivory;
  const loadingSpinner = colors.forest;

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
        <AuthProvider>
          <ThemeProvider>
            <OpenInAppBanner />
            <ServiceBanner />
            <RootLayoutNav />
            {/* Covers PHI when the app is backgrounded (app-switcher snapshots). */}
            <PrivacyShield />
          </ThemeProvider>
        </AuthProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

function RootLayoutNav() {
  const { colorScheme } = useThemePreference();
  const isDark = colorScheme === 'dark';

  // Global auth guard: when the session ends from anywhere in the app —
  // explicit sign-out or a 401 that triggers the unauthenticated handler —
  // route back to login. index.tsx only gates the initial '/' entry, so
  // without this a logged-out user stays on whatever screen they were on.
  const { state } = useAuth();
  const router = useRouter();
  const segments = useSegments();

  useEffect(() => {
    if (state.status === 'loading') return;
    const inAuthGroup = segments[0] === '(auth)';
    const onPhoneGate = segments[0] === 'add-phone';
    if (state.status === 'unauthenticated' && !inAuthGroup) {
      router.replace('/(auth)/login');
    } else if (state.status === 'authenticated' && inAuthGroup) {
      // Already signed in but sitting on an auth screen (e.g. back-navigated to
      // login): bounce to '/' and let index.tsx route to home vs onboarding.
      router.replace('/');
    } else if (
      state.status === 'authenticated' &&
      (!state.user.phone || !state.user.phone_verified) &&
      !onPhoneGate
    ) {
      // A reachable mobile number is mandatory (Google sign-in carries none).
      // Pin the user to the capture screen no matter how they got here.
      router.replace('/add-phone');
    }
  }, [state, segments, router]);

  const headerBg   = isDark ? colors.forestSurface : colors.forest;
  const headerText = isDark ? colors.ivoryText : colors.ivory;

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
        contentStyle: { backgroundColor: isDark ? colors.forestInk : colors.ivory },
      }}
    >
      {/* Route groups render their own headers (or none) — hide the outer
          Stack header so its default title (the literal group segment name,
          e.g. "(tabs)" / "(auth)") never appears. */}
      <Stack.Screen name="index" options={{ headerShown: false }} />
      <Stack.Screen name="add-phone" options={{ headerShown: false, gestureEnabled: false }} />
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen name="(auth)" options={{ headerShown: false }} />
      <Stack.Screen name="(onboarding)" options={{ headerShown: false }} />
      <Stack.Screen name="notes/index" options={{ title: 'My Notes' }} />
      <Stack.Screen name="payments" options={{ title: 'Payments & refunds' }} />
      <Stack.Screen name="sessions" options={{ title: 'Devices & sessions' }} />
      <Stack.Screen name="emergency-contact" options={{ title: 'Emergency contact' }} />
      <Stack.Screen name="vitals" options={{ title: 'Log vitals' }} />
      <Stack.Screen name="activity" options={{ title: 'Activity' }} />
      <Stack.Screen name="chat/index" options={{ title: 'Coordinator' }} />
    </Stack>
  );
}
