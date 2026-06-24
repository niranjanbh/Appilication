/**
 * Video join screen — three states in one route:
 *   1. Waiting room: fetch token, poll if room not yet provisioned
 *   2. Recording consent dialog: shown once per consultation if not already consented
 *   3. In-call: HMSPrebuilt from @100mslive/react-native-room-kit
 *
 * On leave → navigate back to /consultations/[id].
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Modal,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import type { ComponentType } from 'react';
import { useThemePreference } from '../../../lib/theme-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { apiFetch } from '../../../lib/api/client';
import { borderRadius, colors, fontFamily, fontSize, spacing , withAlpha } from '../../../lib/design-tokens';

// Expo Go never bundles native modules, so requiring 100ms there makes its
// react-native-hms dependency log "module was not found" (a console.error → red
// LogBox) before it throws. Detect Expo Go and skip the require entirely to keep
// the dev console clean; the call phase shows a fallback when HMSPrebuilt is null.
function isExpoGo(): boolean {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const Constants = require('expo-constants').default;
    return Constants?.executionEnvironment === 'storeClient';
  } catch {
    return false;
  }
}

// 100ms room kit is a native-only SDK. Importing it on web triggers a
// "react-native-hms module was not found" crash, so load it lazily on a real
// native build only. Web and Expo Go show a "join on the app" fallback instead.
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- third-party SDK has no typed web fallback
let HMSPrebuilt: ComponentType<any> | null = null;
if (Platform.OS !== 'web' && !isExpoGo()) {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    HMSPrebuilt = require('@100mslive/react-native-room-kit').HMSPrebuilt;
  } catch {
    // Native 100ms SDK isn't present. Leave HMSPrebuilt null so the call phase
    // renders the "join from a real build" fallback instead of crashing.
    HMSPrebuilt = null;
  }
}

// ── Types ──────────────────────────────────────────────────────────────────────

interface JoinResponse { room_id: string; token: string; endpoint: string; }

type ScreenState =
  | { phase: 'loading' }
  | { phase: 'consent'; joinResp: JoinResponse }
  | { phase: 'call';    joinResp: JoinResponse }
  | { phase: 'error';   message: string };

const POLL_INTERVAL_MS  = 5000;
const MAX_POLL_ATTEMPTS = 24;
const SPRING = { mass: 0.3, stiffness: 500, damping: 20 };

// 100ms token + layout services (data residency: media stays in-region via the
// auth token / room template; the init endpoint is the India cluster supplied
// by the backend in JoinResponse.endpoint).
const HMS_TOKEN_ENDPOINT  = 'https://auth.100ms.live/v2/token';
const HMS_LAYOUT_ENDPOINT = 'https://api.100ms.live/v2/layouts/ui';

// ── Waiting room ──────────────────────────────────────────────────────────────

function WaitingRoom({ isDark }: { isDark: boolean }) {
  const bg = isDark ? colors.forestInk : colors.ivory;
  const textPri = isDark ? colors.ivoryText : colors.ink;
  const textSub = isDark ? colors.stoneDim : colors.stone;
  return (
    <View style={[wr.container, { backgroundColor: bg }]}>
      <View style={[wr.iconWrap, { backgroundColor: isDark ? colors.forestSurface : colors.white }]}>
        <ActivityIndicator size="large" color={colors.jade} />
      </View>
      <Text style={[wr.title, { color: textPri }]}>Preparing your consultation…</Text>
      <Text style={[wr.sub, { color: textSub }]}>
        Your video room is being set up. This takes a moment.
      </Text>
    </View>
  );
}

const wr = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing[8], gap: spacing[5] },
  iconWrap: {
    width: 88,
    height: 88,
    borderRadius: 44,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 8px 20px rgba(0,0,0,0.10)',
  },
  title: { fontFamily: fontFamily.display, fontSize: fontSize.h3, fontWeight: '600', textAlign: 'center' },
  sub:   { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center', lineHeight: 22 },
});

// ── Error state ───────────────────────────────────────────────────────────────

function ErrorState({ message, onBack, isDark }: { message: string; onBack: () => void; isDark: boolean }) {
  const scale = useSharedValue(1);
  const anim  = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));
  const bg     = isDark ? colors.forestInk     : colors.ivory;
  const cardBg = isDark ? colors.forestSurface : colors.white;
  const textPri = isDark ? colors.ivoryText     : colors.ink;
  const textSub = isDark ? colors.stoneDim : colors.stone;
  return (
    <View style={[er.container, { backgroundColor: bg }]}>
      <View style={[er.card, { backgroundColor: cardBg, borderColor: isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)' }]}>
        <View style={[er.iconWrap, { backgroundColor: colors.alert + '15' }]}>
          <Text style={er.icon}>⚠️</Text>
        </View>
        <Text style={[er.title, { color: textPri }]}>Unable to join</Text>
        <Text style={[er.body, { color: textSub }]}>{message}</Text>
        <Animated.View style={anim}>
          <Pressable
            style={er.button}
            onPress={onBack}
            onPressIn={() => { scale.value = withSpring(0.97, SPRING); }}
            onPressOut={() => { scale.value = withSpring(1, SPRING); }}
            accessibilityLabel="Go back"
          >
            <Text style={er.buttonText}>Go back</Text>
          </Pressable>
        </Animated.View>
      </View>
    </View>
  );
}

const er = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing[6] },
  card: {
    width: '100%',
    maxWidth: 400,
    borderRadius: borderRadius.xxl,
    padding: spacing[6],
    alignItems: 'center',
    gap: spacing[4],
    borderWidth: 1,
    boxShadow: '0 8px 20px rgba(0,0,0,0.10)',
  },
  iconWrap: { width: 64, height: 64, borderRadius: 32, alignItems: 'center', justifyContent: 'center' },
  icon:     { fontSize: 30 },
  title:    { fontFamily: fontFamily.display, fontSize: fontSize.h3, fontWeight: '600', textAlign: 'center' },
  body:     { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center', lineHeight: 22 },
  button: {
    height: 52,
    paddingHorizontal: spacing[8],
    backgroundColor: colors.forest,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonText: { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.ivoryText, fontWeight: '700' },
});

// ── Recording consent dialog ───────────────────────────────────────────────────

function RecordingConsentDialog({
  onAllow,
  onSkip,
  isDark,
}: {
  onAllow: () => void;
  onSkip:  () => void;
  isDark:  boolean;
}) {
  const allowScale = useSharedValue(1);
  const allowAnim  = useAnimatedStyle(() => ({ transform: [{ scale: allowScale.value }] }));
  const skipScale  = useSharedValue(1);
  const skipAnim   = useAnimatedStyle(() => ({ transform: [{ scale: skipScale.value }] }));

  const sheetBg = isDark ? colors.forestSurface : colors.white;
  const textPri = isDark ? colors.ivoryText     : colors.ink;
  const textSub = isDark ? colors.stoneDim : colors.stone;

  return (
    <Modal transparent animationType="fade" visible>
      <View style={cd.overlay}>
        <View style={[cd.sheet, { backgroundColor: sheetBg }]}>
          <View style={cd.handle} />
          <View style={[cd.iconWrap, { backgroundColor: colors.forest + '15' }]}>
            <Text style={cd.icon}>📹</Text>
          </View>
          <Text style={[cd.title, { color: textPri }]}>Recording consent</Text>
          <Text style={[cd.body, { color: textSub }]}>
            Would you like this consultation to be recorded? The recording is stored securely and used only to support your care.
          </Text>
          <Animated.View style={allowAnim}>
            <Pressable
              style={cd.allowBtn}
              onPress={onAllow}
              onPressIn={() => { allowScale.value = withSpring(0.97, SPRING); }}
              onPressOut={() => { allowScale.value = withSpring(1, SPRING); }}
              accessibilityLabel="Allow recording"
            >
              <Text style={cd.allowBtnText}>Allow recording</Text>
            </Pressable>
          </Animated.View>
          <Animated.View style={skipAnim}>
            <Pressable
              style={[cd.skipBtn, { borderColor: isDark ? 'rgba(255,255,255,0.12)' : colors.borderLight }]}
              onPress={onSkip}
              onPressIn={() => { skipScale.value = withSpring(0.97, SPRING); }}
              onPressOut={() => { skipScale.value = withSpring(1, SPRING); }}
              accessibilityLabel="Join without recording"
            >
              <Text style={[cd.skipBtnText, { color: textSub }]}>No thanks, join without recording</Text>
            </Pressable>
          </Animated.View>
        </View>
      </View>
    </Modal>
  );
}

const cd = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.55)', justifyContent: 'flex-end' },
  sheet: {
    borderTopLeftRadius: borderRadius.xxl,
    borderTopRightRadius: borderRadius.xxl,
    padding: spacing[6],
    paddingBottom: spacing[10],
    gap: spacing[4],
    alignItems: 'center',
  },
  handle:  { width: 36, height: 4, backgroundColor: colors.borderLight, borderRadius: 2, marginBottom: spacing[2] },
  iconWrap:{ width: 64, height: 64, borderRadius: 32, alignItems: 'center', justifyContent: 'center', marginBottom: spacing[1] },
  icon:    { fontSize: 30 },
  title:   { fontFamily: fontFamily.display, fontSize: fontSize.h3, fontWeight: '600', textAlign: 'center' },
  body:    { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center', lineHeight: 22 },
  allowBtn: {
    width: '100%',
    height: 56,
    backgroundColor: colors.forest,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: `0 8px 16px ${withAlpha(colors.forest, 0.28)}`,
  },
  allowBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, color: colors.ivoryText, fontWeight: '700' },
  skipBtn:  { width: '100%', height: 52, borderWidth: 1, borderRadius: borderRadius.xxl, alignItems: 'center', justifyContent: 'center' },
  skipBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '500' },
});

// ── Main screen ───────────────────────────────────────────────────────────────

export default function JoinScreen() {
  const { id }  = useLocalSearchParams<{ id: string }>();
  const router  = useRouter();
  const isDark  = useThemePreference().colorScheme === 'dark';
  const [state, setState] = useState<ScreenState>({ phase: 'loading' });
  const pollAttempts = useRef(0);
  const pollTimer    = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Preserve ALL existing token fetch + polling logic
  const fetchToken = useCallback(async () => {
    try {
      const joinResp = await apiFetch<JoinResponse>(`/v1/clinic/patient/consultations/${id}/join`, { method: 'GET' });
      setState({ phase: 'consent', joinResp });
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : '';
      if (errMsg.includes('503')) {
        pollAttempts.current += 1;
        if (pollAttempts.current >= MAX_POLL_ATTEMPTS) {
          setState({ phase: 'error', message: 'Video room is taking longer than expected. Please try again in a moment.' });
          return;
        }
        pollTimer.current = setTimeout(fetchToken, POLL_INTERVAL_MS);
        return;
      }
      if (errMsg.includes('404')) { setState({ phase: 'error', message: 'Consultation not found.' }); return; }
      setState({ phase: 'error', message: 'Could not connect to the call. Please try again.' });
    }
  }, [id]);

  useEffect(() => {
    fetchToken();
    return () => { if (pollTimer.current) clearTimeout(pollTimer.current); };
  }, [fetchToken]);

  const handleConsentAllow = useCallback(async (joinResp: JoinResponse) => {
    try {
      await apiFetch(`/v1/clinic/patient/consultations/${id}/recording-consent`, { method: 'POST' });
    } catch {
      // Non-critical
    }
    setState({ phase: 'call', joinResp });
  }, [id]);

  const handleConsentSkip = useCallback((joinResp: JoinResponse) => {
    setState({ phase: 'call', joinResp });
  }, []);

  const handleLeave = useCallback(() => {
    router.replace(`/consultations/${id}` as never);
  }, [id, router]);

  if (state.phase === 'loading') return <WaitingRoom isDark={isDark} />;
  if (state.phase === 'error')   return <ErrorState message={state.message} onBack={() => router.back()} isDark={isDark} />;

  if (state.phase === 'consent') {
    const joinResp = state.joinResp;
    return (
      <RecordingConsentDialog
        isDark={isDark}
        onAllow={() => handleConsentAllow(joinResp)}
        onSkip={() => handleConsentSkip(joinResp)}
      />
    );
  }

  // phase === 'call' — full-screen HMS SDK, keep black bg.
  // The 100ms SDK is native-only; on the web portal, direct patients to the app.
  if (!HMSPrebuilt) {
    const message =
      Platform.OS === 'web'
        ? 'Video consultations are available in the Kyros mobile app. Please open this consultation on your phone to join the call.'
        : 'Video calling needs the full Kyros app build. Please update to the latest version of the app to join your consultation.';
    return <ErrorState message={message} onBack={() => router.back()} isDark={isDark} />;
  }

  return (
    <View style={styles.callContainer}>
      <HMSPrebuilt
        token={state.joinResp.token}
        options={{
          userName: 'Patient',
          endPoints: {
            init: state.joinResp.endpoint,
            token: HMS_TOKEN_ENDPOINT,
            layout: HMS_LAYOUT_ENDPOINT,
          },
        }}
        onLeave={handleLeave}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  callContainer: { flex: 1, backgroundColor: '#000' },
});
