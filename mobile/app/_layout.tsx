import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import { ActivityIndicator, View } from 'react-native';
import { AuthProvider } from '../lib/auth/context';
import { OpenInAppBanner } from '../components/web/OpenInAppBanner';
import { colors, fontFamily, fontSize } from '../lib/design-tokens';
// Side-effect: registers the background sync task definition before the React tree mounts.
// TaskManager.defineTask must be called at module load time for the OS to be able to
// wake the app and execute the task even when the UI is not in the foreground.
import '../lib/native/background-sync';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
});

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    'CormorantGaramond-Regular': {
      uri: 'https://fonts.gstatic.com/s/cormorantgaramond/v22/co3YmX5slCNuHLi8bLeY9MK7whWMhyjQEl1HZQAA.ttf',
    },
    'CormorantGaramond-Medium': {
      uri: 'https://fonts.gstatic.com/s/cormorantgaramond/v22/co3XmX5slCNuHLi8bLeY9MK7whWMhyjYqXtKxQAA.ttf',
    },
    'CormorantGaramond-Italic': {
      uri: 'https://fonts.gstatic.com/s/cormorantgaramond/v22/co3WmX5slCNuHLi8bLeY9MK7whWMhyjornFLsQAA.ttf',
    },
    'DMSans-Regular': {
      uri: 'https://fonts.gstatic.com/s/dmsans/v15/rP2tp2ywxg089UriI5-g4vlH9VoD8CmnqA.ttf',
    },
    'DMSans-Medium': {
      uri: 'https://fonts.gstatic.com/s/dmsans/v15/rP2tp2ywxg089UriI5-g4vlH9VoD8Dmkqw.ttf',
    },
    'DMSans-SemiBold': {
      uri: 'https://fonts.gstatic.com/s/dmsans/v15/rP2tp2ywxg089UriI5-g4vlH9VoD8LekqA.ttf',
    },
    'TiroDevanagariHindi-Regular': {
      uri: 'https://fonts.gstatic.com/s/tirodevanagarihindu/v6/55xyezMfnuiTmFNjvECeQjDanASeyhf5LuQQ6AVA.ttf',
    },
  });

  if (!fontsLoaded) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.ivory }}>
        <ActivityIndicator color={colors.forest} />
      </View>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <OpenInAppBanner />
        <Stack
          screenOptions={{
            headerStyle: { backgroundColor: colors.forest },
            headerTintColor: colors.ivory,
            headerTitleStyle: {
              fontFamily: fontFamily.display,
              fontSize: fontSize.h3,
            },
          }}
        />
      </AuthProvider>
    </QueryClientProvider>
  );
}
