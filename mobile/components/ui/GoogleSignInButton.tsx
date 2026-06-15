import { Ionicons } from '@expo/vector-icons';
import * as Google from 'expo-auth-session/providers/google';
import * as WebBrowser from 'expo-web-browser';
import { useEffect } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { HapticPressable } from './HapticPressable';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

// Completes the auth session when the browser redirects back (no-op on native
// where it isn't needed, required on web).
WebBrowser.maybeCompleteAuthSession();

// EXPO_PUBLIC_* vars are substituted at bundle time. One client ID per platform.
declare const process: { env: Record<string, string | undefined> };

interface Props {
  onToken: (idToken: string) => void | Promise<void>;
  onError?: (message: string) => void;
  busy?: boolean;
}

/**
 * "Sign in with Google" button. Obtains a Google ID token via expo-auth-session
 * and hands it to `onToken`, which posts it to POST /v1/auth/google. The button
 * is only rendered by the parent when the admin has enabled Google sign-in.
 */
export function GoogleSignInButton({ onToken, onError, busy }: Props) {
  const [request, response, promptAsync] = Google.useIdTokenAuthRequest({
    clientId: process.env['EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID'],
    iosClientId: process.env['EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID'],
    androidClientId: process.env['EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID'],
  });

  useEffect(() => {
    if (response?.type === 'success') {
      const idToken = response.params?.['id_token'];
      if (idToken) {
        void onToken(idToken);
      } else {
        onError?.('Could not read your Google sign-in. Please try again.');
      }
    } else if (response?.type === 'error') {
      onError?.('Google sign-in failed. Please try again.');
    }
  }, [response, onToken, onError]);

  return (
    <HapticPressable
      haptic="light"
      containerStyle={styles.fullWidth}
      style={styles.button}
      disabled={!request || busy}
      onPress={() => {
        void promptAsync();
      }}
      accessibilityLabel="Sign in with Google"
    >
      {busy ? (
        <ActivityIndicator color={colors.navyDeep} size="small" />
      ) : (
        <View style={styles.row}>
          <Ionicons name="logo-google" size={20} color={colors.navyDeep} />
          <Text style={styles.text}>Sign in with Google</Text>
        </View>
      )}
    </HapticPressable>
  );
}

const styles = StyleSheet.create({
  fullWidth: { width: '100%' },
  button: {
    width: '100%',
    height: 56,
    backgroundColor: colors.white,
    borderRadius: borderRadius.xxl,
    borderWidth: 1,
    borderColor: colors.borderLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  row: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  text: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.navyDeep,
    fontWeight: '600',
  },
});
