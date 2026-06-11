import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import { ActivityIndicator, useColorScheme, View } from 'react-native';
import { AuthProvider } from '../lib/auth/context';
import { OpenInAppBanner } from '../components/web/OpenInAppBanner';
import { PrivacyShield } from '../components/ui/PrivacyShield';
import { colors, fontFamily, fontSize } from '../lib/design-tokens';
import { ThemeProvider, useThemePreference } from '../lib/theme-context';
// Side-effect: registers the background sync task definition before the React tree mounts.
import '../lib/native/background-sync';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
});

export default function RootLayout() {
  const isDark = useColorScheme() === 'dark';

  const [fontsLoaded] = useFonts({
    'CormorantGaramond-Regular': { uri: 'https://fonts.gstatic.com/s/cormorantgaramond/v22/co3YmX5slCNuHLi8bLeY9MK7whWMhyjQEl1HZQAA.ttf' },
    'CormorantGaramond-Medium':  { uri: 'https://fonts.gstatic.com/s/cormorantgaramond/v22/co3XmX5slCNuHLi8bLeY9MK7whWMhyjYqXtKxQAA.ttf' },
    'CormorantGaramond-Italic':  { uri: 'https://fonts.gstatic.com/s/cormorantgaramond/v22/co3WmX5slCNuHLi8bLeY9MK7whWMhyjornFLsQAA.ttf' },
    'DMSans-Regular':            { uri: 'https://fonts.gstatic.com/s/dmsans/v15/rP2tp2ywxg089UriI5-g4vlH9VoD8CmnqA.ttf' },
    'DMSans-Medium':             { uri: 'https://fonts.gstatic.com/s/dmsans/v15/rP2tp2ywxg089UriI5-g4vlH9VoD8Dmkqw.ttf' },
    'DMSans-SemiBold':           { uri: 'https://fonts.gstatic.com/s/dmsans/v15/rP2tp2ywxg089UriI5-g4vlH9VoD8LekqA.ttf' },
    'TiroDevanagariHindi-Regular': { uri: 'https://fonts.gstatic.com/s/tirodevanagarihindu/v6/55xyezMfnuiTmFNjvECeQjDanASeyhf5LuQQ6AVA.ttf' },
  });

  const loadingBg = isDark ? colors.midnight : colors.navyDeep;

  if (!fontsLoaded) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: loadingBg }}>
        <ActivityIndicator color={colors.white} size="large" />
      </View>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <OpenInAppBanner />
          <RootLayoutNav />
          {/* Covers PHI when the app is backgrounded (app-switcher snapshots). */}
          <PrivacyShield />
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

function RootLayoutNav() {
  const { colorScheme } = useThemePreference();
  const isDark = colorScheme === 'dark';

  const headerBg   = isDark ? colors.nightSurface : colors.navyDeep;
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
        contentStyle: { backgroundColor: isDark ? colors.midnight : colors.skyMist },
      }}
    />
  );
}
