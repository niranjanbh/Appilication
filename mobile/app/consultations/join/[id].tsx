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
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useThemePreference } from '../../../lib/theme-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { HMSPrebuilt } from '@100mslive/react-native-room-kit';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { apiFetch } from '../../../lib/api/client';
import { borderRadius, colors, fontFamily, fontSize, spacing , withAlpha } from '../../../lib/design-tokens';

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

// ── Waiting room ──────────────────────────────────────────────────────────────

function WaitingRoom({ isDark }: { isDark: boolean }) {
  const bg = isDark ? colors.midnight : colors.skyMist;
  const textPri = isDark ? colors.white : colors.navyDeep;
  const textSub = isDark ? colors.slateText : colors.coolGray;
  return (
    <View style={[wr.container, { backgroundColor: bg }]}>
      <View style={[wr.iconWrap, { backgroundColor: isDark ? colors.nightSurface : colors.white }]}>
        <ActivityIndicator size="large" color={colors.electricBlue} />
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
  const bg     = isDark ? colors.midnight     : colors.skyMist;
  const cardBg = isDark ? colors.nightSurface : colors.white;
  const textPri = isDark ? colors.white     : colors.navyDeep;
  const textSub = isDark ? colors.slateText : colors.coolGray;
  return (
    <View style={[er.container, { backgroundColor: bg }]}>
      <View style={[er.card, { backgroundColor: cardBg, borderColor: isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)' }]}>
        <View style={[er.iconWrap, { backgroundColor: colors.criticalRed + '15' }]}>
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
    backgroundColor: colors.navyDeep,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonText: { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.white, fontWeight: '700' },
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

  const sheetBg = isDark ? colors.nightSurface : colors.white;
  const textPri = isDark ? colors.white     : colors.navyDeep;
  const textSub = isDark ? colors.slateText : colors.coolGray;

  return (
    <Modal transparent animationType="fade" visible>
      <View style={cd.overlay}>
        <View style={[cd.sheet, { backgroundColor: sheetBg }]}>
          <View style={cd.handle} />
          <View style={[cd.iconWrap, { backgroundColor: colors.navyDeep + '15' }]}>
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
    backgroundColor: colors.navyDeep,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: `0 8px 16px ${withAlpha(colors.navyDeep, 0.28)}`,
  },
  allowBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, color: colors.white, fontWeight: '700' },
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

  // phase === 'call' — full-screen HMS SDK, keep black bg
  return (
    <View style={styles.callContainer}>
      <HMSPrebuilt
        roomCode=""
        options={{
          roomID: state.joinResp.room_id,
          authToken: state.joinResp.token,
          endPoints: { init: state.joinResp.endpoint },
          userName: 'Patient',
        }}
        onLeave={handleLeave}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  callContainer: { flex: 1, backgroundColor: '#000' },
});
