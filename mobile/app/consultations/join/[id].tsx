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
import { useLocalSearchParams, useRouter } from 'expo-router';
import { HMSPrebuilt } from '@100mslive/react-native-room-kit';
import { apiFetch } from '../../../lib/api/client';
import { colors, fontFamily, fontSize, spacing, borderRadius } from '../../../lib/design-tokens';

// ── Types ──────────────────────────────────────────────────────────────────────

interface JoinResponse {
  room_id: string;
  token: string;
  endpoint: string;
}

type ScreenState =
  | { phase: 'loading' }
  | { phase: 'consent'; joinResp: JoinResponse }
  | { phase: 'call'; joinResp: JoinResponse }
  | { phase: 'error'; message: string };

// ── Constants ──────────────────────────────────────────────────────────────────

const POLL_INTERVAL_MS = 5000;
const MAX_POLL_ATTEMPTS = 24; // ~2 minutes of polling

// ── Component ──────────────────────────────────────────────────────────────────

export default function JoinScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [state, setState] = useState<ScreenState>({ phase: 'loading' });
  const pollAttempts = useRef(0);
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchToken = useCallback(async () => {
    try {
      const joinResp = await apiFetch<JoinResponse>(
        `/v1/clinic/patient/consultations/${id}/join`,
        { method: 'GET' },
      );
      setState({ phase: 'consent', joinResp });
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : '';
      if (errMsg.includes('503')) {
        // Room not provisioned yet — poll
        pollAttempts.current += 1;
        if (pollAttempts.current >= MAX_POLL_ATTEMPTS) {
          setState({ phase: 'error', message: 'Video room is taking longer than expected. Please try again in a moment.' });
          return;
        }
        pollTimer.current = setTimeout(fetchToken, POLL_INTERVAL_MS);
        return;
      }
      if (errMsg.includes('404')) {
        setState({ phase: 'error', message: 'Consultation not found.' });
        return;
      }
      setState({ phase: 'error', message: 'Could not connect to the call. Please try again.' });
    }
  }, [id]);

  useEffect(() => {
    fetchToken();
    return () => {
      if (pollTimer.current) clearTimeout(pollTimer.current);
    };
  }, [fetchToken]);

  const handleConsentAllow = useCallback(async (joinResp: JoinResponse) => {
    try {
      await apiFetch(
        `/v1/clinic/patient/consultations/${id}/recording-consent`,
        { method: 'POST' },
      );
    } catch {
      // Non-critical: consent capture failure does not block joining
    }
    setState({ phase: 'call', joinResp });
  }, [id]);

  const handleConsentSkip = useCallback((joinResp: JoinResponse) => {
    setState({ phase: 'call', joinResp });
  }, []);

  const handleLeave = useCallback(() => {
    router.replace(`/consultations/${id}` as never);
  }, [id, router]);

  // ── Render ───────────────────────────────────────────────────────────────────

  if (state.phase === 'loading') {
    return <WaitingRoom />;
  }

  if (state.phase === 'error') {
    return <ErrorState message={state.message} onBack={() => router.back()} />;
  }

  if (state.phase === 'consent') {
    const joinResp = state.joinResp;
    return (
      <RecordingConsentDialog
        onAllow={() => handleConsentAllow(joinResp)}
        onSkip={() => handleConsentSkip(joinResp)}
      />
    );
  }

  // phase === 'call'
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

// ── Sub-components ─────────────────────────────────────────────────────────────

function WaitingRoom() {
  return (
    <View style={styles.centered}>
      <ActivityIndicator size="large" color={colors.forest} />
      <Text style={styles.waitingTitle}>Preparing your consultation…</Text>
      <Text style={styles.waitingSubtitle}>
        Your video room is being set up. This takes a moment.
      </Text>
    </View>
  );
}

function ErrorState({ message, onBack }: { message: string; onBack: () => void }) {
  return (
    <View style={styles.centered}>
      <Text style={styles.errorTitle}>Unable to join</Text>
      <Text style={styles.errorBody}>{message}</Text>
      <Pressable style={styles.button} onPress={onBack} accessibilityLabel="Go back">
        <Text style={styles.buttonText}>Go back</Text>
      </Pressable>
    </View>
  );
}

function RecordingConsentDialog({
  onAllow,
  onSkip,
}: {
  onAllow: () => void;
  onSkip: () => void;
}) {
  return (
    <Modal transparent animationType="fade" visible>
      <View style={styles.overlay}>
        <View style={styles.dialogCard}>
          <Text style={styles.dialogTitle}>Recording consent</Text>
          <Text style={styles.dialogBody}>
            Would you like this consultation to be recorded? The recording is stored securely
            and used only to support your care.
          </Text>
          <Pressable
            style={styles.button}
            onPress={onAllow}
            accessibilityLabel="Allow recording"
          >
            <Text style={styles.buttonText}>Allow recording</Text>
          </Pressable>
          <Pressable
            style={styles.buttonSecondary}
            onPress={onSkip}
            accessibilityLabel="Join without recording"
          >
            <Text style={styles.buttonTextSecondary}>No thanks, join without recording</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

// ── Styles ─────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  callContainer: {
    flex: 1,
    backgroundColor: '#000',
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing[6],
    backgroundColor: colors.ivory,
  },
  waitingTitle: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h3,
    color: colors.ink,
    marginTop: spacing[4],
    textAlign: 'center',
  },
  waitingSubtitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    marginTop: spacing[2],
    textAlign: 'center',
  },
  errorTitle: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h3,
    color: colors.ink,
    marginBottom: spacing[2],
    textAlign: 'center',
  },
  errorBody: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    textAlign: 'center',
    marginBottom: spacing[6],
  },
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing[4],
  },
  dialogCard: {
    backgroundColor: colors.white,
    borderRadius: borderRadius.lg,
    padding: spacing[6],
    width: '100%',
    maxWidth: 400,
  },
  dialogTitle: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h3,
    color: colors.ink,
    marginBottom: spacing[3],
  },
  dialogBody: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    lineHeight: 22,
    marginBottom: spacing[6],
  },
  button: {
    backgroundColor: colors.forest,
    borderRadius: borderRadius.lg,
    paddingVertical: spacing[3],
    paddingHorizontal: spacing[4],
    alignItems: 'center',
    marginBottom: spacing[3],
  },
  buttonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.white,
    fontWeight: '600',
  },
  buttonSecondary: {
    borderRadius: borderRadius.lg,
    paddingVertical: spacing[3],
    paddingHorizontal: spacing[4],
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.stone,
  },
  buttonTextSecondary: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    fontWeight: '500',
  },
});
