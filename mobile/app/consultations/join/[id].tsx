/**
 * Video join screen — three states in one route:
 *   1. Waiting room: fetch token, poll if room not yet provisioned
 *   2. Recording consent dialog: shown once per consultation if not already consented
 *   3. In-call: LiveKit (LiveKitRoom from @livekit/react-native)
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
import { useThemePreference } from '../../../lib/theme-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { apiFetch, ApiError } from '../../../lib/api/client';
import { borderRadius, colors, fontFamily, fontSize, spacing , withAlpha } from '../../../lib/design-tokens';

// LiveKit's React Native SDK is native-only (it depends on react-native-webrtc).
// Importing it on web — or in Expo Go, which never bundles native modules —
// throws at require time, so we load it lazily on a real native build only and
// show a "join from the app" fallback everywhere else.
function isExpoGo(): boolean {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const Constants = require('expo-constants').default;
    return Constants?.executionEnvironment === 'storeClient';
  } catch {
    return false;
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- third-party SDK has no web typings
let LiveKitNative: { registerGlobals: () => void } | null = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- the call UI is composed below from these
let LK: any = null;
if (Platform.OS !== 'web' && !isExpoGo()) {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    LK = require('@livekit/react-native');
    // registerGlobals wires up WebRTC into the RN runtime; must run before use.
    LK.registerGlobals?.();
    LiveKitNative = LK;
  } catch {
    // Native LiveKit SDK isn't present (Expo Go / web). Leave null so the call
    // phase renders the fallback instead of crashing.
    LK = null;
    LiveKitNative = null;
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

// LiveKit publish defaults — high quality with simulcast layers so the SDK can
// adapt down on poor networks. Data residency is enforced by the backend's
// LiveKit deployment (ap-south-1); the endpoint comes from JoinResponse.endpoint.
const LIVEKIT_ROOM_OPTIONS = {
  adaptiveStream: true,
  dynacast: true,
  publishDefaults: {
    simulcast: true,
    videoEncoding: {
      maxBitrate: 3_000_000, // 3 Mbps for the high-quality (720p) layer
      maxFramerate: 30,
    },
    videoSimulcastLayers: [
      { width: 640, height: 360, encoding: { maxBitrate: 500_000, maxFramerate: 20 } },
      { width: 1280, height: 720, encoding: { maxBitrate: 1_500_000, maxFramerate: 30 } },
    ],
  },
};

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

// ── Call phase (LiveKit) ────────────────────────────────────────────────────────

/**
 * In-call layout rendered inside <LiveKitRoom>. Uses LiveKit hooks to lay out
 * the remote participant full-screen with the local camera as a corner PIP, plus
 * mic / camera / end-call controls. Built from @livekit/react-native primitives
 * so we keep full control over the clinical visual register (design tokens only).
 */
function CallContent({ onLeave }: { onLeave: () => void }) {
  const {
    useTracks,
    useLocalParticipant,
    VideoTrack,
    Track,
  } = LK;

  // All camera tracks in the room, excluding screen-share, with placeholders so
  // a participant with the camera off still occupies a tile.
  const tracks = useTracks(
    [{ source: Track.Source.Camera, withPlaceholder: true }],
    { onlySubscribed: false },
  );
  const { localParticipant, isMicrophoneEnabled, isCameraEnabled } = useLocalParticipant();

  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- TrackReference is SDK-typed
  const remote = tracks.find((t: any) => !t.participant?.isLocal);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const local = tracks.find((t: any) => t.participant?.isLocal);

  const toggleMic = useCallback(() => {
    localParticipant?.setMicrophoneEnabled(!isMicrophoneEnabled);
  }, [localParticipant, isMicrophoneEnabled]);

  const toggleCam = useCallback(() => {
    localParticipant?.setCameraEnabled(!isCameraEnabled);
  }, [localParticipant, isCameraEnabled]);

  return (
    <View style={call.root}>
      {/* Main view: remote participant (or waiting message). */}
      {remote ? (
        <VideoTrack trackRef={remote} style={call.remoteVideo} objectFit="cover" />
      ) : (
        <View style={call.waitingRemote}>
          <ActivityIndicator size="large" color={colors.jade} />
          <Text style={call.waitingText}>Waiting for the other participant to join…</Text>
        </View>
      )}

      {/* Local camera PIP overlay. */}
      {local && isCameraEnabled ? (
        <View style={call.pip}>
          <VideoTrack trackRef={local} style={call.pipVideo} objectFit="cover" mirror />
        </View>
      ) : null}

      {/* Bottom control bar. */}
      <View style={call.controls}>
        <Pressable
          style={[call.ctrlBtn, !isMicrophoneEnabled && call.ctrlBtnOff]}
          onPress={toggleMic}
          accessibilityLabel={isMicrophoneEnabled ? 'Mute microphone' : 'Unmute microphone'}
        >
          <Text style={call.ctrlIcon}>{isMicrophoneEnabled ? '🎙️' : '🔇'}</Text>
        </Pressable>
        <Pressable
          style={[call.ctrlBtn, !isCameraEnabled && call.ctrlBtnOff]}
          onPress={toggleCam}
          accessibilityLabel={isCameraEnabled ? 'Turn camera off' : 'Turn camera on'}
        >
          <Text style={call.ctrlIcon}>{isCameraEnabled ? '📷' : '🚫'}</Text>
        </Pressable>
        <Pressable
          style={[call.ctrlBtn, call.endBtn]}
          onPress={onLeave}
          accessibilityLabel="End call"
        >
          <Text style={call.ctrlIcon}>📞</Text>
        </Pressable>
      </View>
    </View>
  );
}

function CallPhase({ joinResp, onLeave }: { joinResp: JoinResponse; onLeave: () => void }) {
  const { LiveKitRoom } = LK;
  return (
    <LiveKitRoom
      serverUrl={joinResp.endpoint}
      token={joinResp.token}
      connect={true}
      audio={true}
      video={true}
      options={LIVEKIT_ROOM_OPTIONS}
      onDisconnected={onLeave}
    >
      <CallContent onLeave={onLeave} />
    </LiveKitRoom>
  );
}

const call = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.forestInk },
  remoteVideo: { flex: 1, backgroundColor: colors.forestInk },
  waitingRemote: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing[4],
    backgroundColor: colors.forestInk,
  },
  waitingText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ivoryText,
    textAlign: 'center',
    paddingHorizontal: spacing[8],
  },
  pip: {
    position: 'absolute',
    top: spacing[6],
    right: spacing[5],
    width: 108,
    height: 160,
    borderRadius: borderRadius.lg,
    overflow: 'hidden',
    borderWidth: 2,
    borderColor: withAlpha(colors.ivory, 0.5),
    backgroundColor: colors.forestSurface,
  },
  pipVideo: { flex: 1 },
  controls: {
    position: 'absolute',
    bottom: spacing[10],
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'center',
    gap: spacing[5],
  },
  ctrlBtn: {
    width: 60,
    height: 60,
    borderRadius: 30,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: withAlpha(colors.ivory, 0.18),
  },
  ctrlBtnOff: { backgroundColor: withAlpha(colors.alert, 0.85) },
  endBtn: { backgroundColor: colors.alert },
  ctrlIcon: { fontSize: 26 },
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
      const status = err instanceof ApiError ? err.status : 0;
      const detail =
        err instanceof ApiError && err.body && typeof err.body === 'object'
          ? String((err.body as { detail?: unknown }).detail ?? '')
          : '';

      // Video room still provisioning — retry with backoff.
      if (status === 503) {
        pollAttempts.current += 1;
        if (pollAttempts.current >= MAX_POLL_ATTEMPTS) {
          setState({ phase: 'error', message: 'Video room is taking longer than expected. Please try again in a moment.' });
          return;
        }
        pollTimer.current = setTimeout(fetchToken, POLL_INTERVAL_MS);
        return;
      }
      if (status === 404) { setState({ phase: 'error', message: 'Consultation not found.' }); return; }
      // TPG pre-flight: the call can't start until the patient is consult-ready.
      // Surface the specific, actionable reason instead of a generic failure.
      if (status === 409 && detail === 'identity_not_verified') {
        setState({ phase: 'error', message: 'Please verify your phone number in your profile before joining this consultation.' });
        return;
      }
      if (status === 409 && detail === 'telemedicine_consent_missing') {
        setState({ phase: 'error', message: 'Please accept the telemedicine consent (Profile → Privacy & security) before joining this consultation.' });
        return;
      }
      if (status === 409) {
        setState({ phase: 'error', message: 'This consultation is not open to join right now.' });
        return;
      }
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

  // phase === 'call' — full-screen LiveKit call.
  // The LiveKit RN SDK is native-only; on web / Expo Go, direct patients to the app.
  if (!LiveKitNative || !LK) {
    const message =
      Platform.OS === 'web'
        ? 'Video consultations are available in the Baseline mobile app. Please open this consultation on your phone to join the call.'
        : 'Video calling needs the full Baseline app build. Please update to the latest version of the app to join your consultation.';
    return <ErrorState message={message} onBack={() => router.back()} isDark={isDark} />;
  }

  return (
    <View style={styles.callContainer}>
      <CallPhase joinResp={state.joinResp} onLeave={handleLeave} />
    </View>
  );
}

const styles = StyleSheet.create({
  callContainer: { flex: 1, backgroundColor: colors.forestInk },
});
