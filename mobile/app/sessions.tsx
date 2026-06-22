import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Alert } from '../lib/ui/alert';
import { useThemePreference } from '../lib/theme-context';
import { listSessions, revokeSession, type Session } from '../lib/api/sessions';
import { borderRadius, colors, fontFamily, fontSize, shadow, spacing } from '../lib/design-tokens';

// ── Helpers ─────────────────────────────────────────────────────────────────────

function formatLastUsed(iso: string): string {
  const then = new Date(iso).getTime();
  const mins = Math.floor((Date.now() - then) / 60000);
  if (mins < 1) return 'Active now';
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} hr ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days} day${days > 1 ? 's' : ''} ago`;
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function deviceLabel(userAgent: string | null): string {
  if (!userAgent) return 'Unknown device';
  // Show the leading device descriptor before the first separator.
  return userAgent.split(/[;(]/)[0].trim() || 'Unknown device';
}

// ── Session card ──────────────────────────────────────────────────────────────

function SessionCard({
  session,
  isDark,
  busy,
  onRevoke,
}: {
  session: Session;
  isDark: boolean;
  busy: boolean;
  onRevoke: () => void;
}) {
  const cardBg  = isDark ? colors.forestSurface : colors.white;
  const cardBdr = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(15,61,46,0.06)';
  const textPri = isDark ? colors.ivoryText : colors.ink;
  const textSub = isDark ? colors.stoneDim  : colors.stone;

  return (
    <View style={[styles.card, { backgroundColor: cardBg, borderColor: cardBdr }]}>
      <View style={styles.cardBody}>
        <View style={styles.titleRow}>
          <Text style={[styles.deviceName, { color: textPri }]} numberOfLines={1}>
            {deviceLabel(session.user_agent)}
          </Text>
          {session.is_current && (
            <View style={[styles.currentPill, { backgroundColor: colors.jade + '18' }]}>
              <Text style={[styles.currentText, { color: colors.jade }]}>This device</Text>
            </View>
          )}
        </View>
        <Text style={[styles.meta, { color: textSub }]}>
          {formatLastUsed(session.last_used_at)}
          {session.ip_address ? ` · ${session.ip_address}` : ''}
        </Text>
      </View>
      {!session.is_current && (
        <Pressable
          onPress={onRevoke}
          disabled={busy}
          accessibilityLabel={`Sign out ${deviceLabel(session.user_agent)}`}
          style={[styles.revokeBtn, busy && styles.disabled]}
        >
          <Text style={[styles.revokeText, { color: colors.alert }]}>Sign out</Text>
        </Pressable>
      )}
    </View>
  );
}

// ── Screen ──────────────────────────────────────────────────────────────────────

export default function SessionsScreen() {
  const isDark = useThemePreference().colorScheme === 'dark';
  const [sessions,   setSessions]   = useState<Session[]>([]);
  const [loading,    setLoading]    = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error,      setError]      = useState<string | null>(null);
  const [revoking,   setRevoking]   = useState<string | null>(null);

  const fetchSessions = useCallback(async () => {
    try {
      const data = await listSessions();
      setSessions(data.items);
      setError(null);
    } catch {
      setError('Could not load your active sessions.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { void fetchSessions(); }, [fetchSessions]);

  const handleRefresh = useCallback(() => {
    setRefreshing(true);
    void fetchSessions();
  }, [fetchSessions]);

  const handleRevoke = useCallback((session: Session) => {
    Alert.alert(
      'Sign out this device?',
      `${deviceLabel(session.user_agent)} will be signed out and need to log in again.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Sign out',
          style: 'destructive',
          onPress: async () => {
            setRevoking(session.session_id);
            try {
              await revokeSession(session.session_id);
              await fetchSessions();
            } catch {
              Alert.alert('Error', 'Could not sign out that device. Please try again.');
            } finally {
              setRevoking(null);
            }
          },
        },
      ],
    );
  }, [fetchSessions]);

  const bg      = isDark ? colors.forestInk : colors.ivory;
  const textPri = isDark ? colors.ivoryText : colors.ink;
  const textSub = isDark ? colors.stoneDim  : colors.stone;

  if (loading) {
    return <View style={[styles.center, { backgroundColor: bg }]}><ActivityIndicator color={colors.jade} /></View>;
  }

  if (error) {
    return (
      <View style={[styles.center, { backgroundColor: bg }]}>
        <Text style={[styles.errorText, { color: colors.alert }]}>{error}</Text>
        <Pressable style={styles.retryBtn} onPress={() => void fetchSessions()}>
          <Text style={[styles.retryText, { color: colors.jade }]}>Try again</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <ScrollView
      style={[styles.scroll, { backgroundColor: bg }]}
      contentContainerStyle={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor={colors.jade} />}
    >
      {sessions.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyIcon}>📱</Text>
          <Text style={[styles.emptyTitle, { color: textPri }]}>No active sessions.</Text>
          <Text style={[styles.emptySub, { color: textSub }]}>
            Devices you are signed in on will appear here so you can review and sign them out.
          </Text>
        </View>
      ) : (
        <View style={styles.section}>
          <Text style={[styles.sectionHeader, { color: textSub }]}>Signed-in devices</Text>
          {sessions.map(s => (
            <SessionCard
              key={s.session_id}
              session={s}
              isDark={isDark}
              busy={revoking === s.session_id}
              onRevoke={() => handleRevoke(s)}
            />
          ))}
        </View>
      )}
    </ScrollView>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  scroll: { flex: 1 },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[4],
    paddingTop: spacing[4],
    paddingBottom: spacing[16],
    gap: spacing[6],
  },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing[4] },
  errorText: { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center' },
  retryBtn:  { alignItems: 'center' },
  retryText: { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontWeight: '600' },

  section: { gap: spacing[2] },
  sectionHeader: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    paddingHorizontal: spacing[1],
    marginBottom: spacing[1],
  },

  card: {
    borderRadius: borderRadius.xl,
    padding: spacing[4],
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    borderWidth: 1,
    marginBottom: spacing[2],
    boxShadow: shadow.sm,
  },
  cardBody: { flex: 1, gap: spacing[1] },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  deviceName: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600', flexShrink: 1 },
  meta: { fontFamily: fontFamily.body, fontSize: fontSize.caption },

  currentPill: {
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
    borderRadius: borderRadius.full,
  },
  currentText: { fontFamily: fontFamily.body, fontSize: fontSize.xs, fontWeight: '700' },

  revokeBtn: { paddingHorizontal: spacing[2], paddingVertical: spacing[1] },
  revokeText: { fontFamily: fontFamily.body, fontSize: fontSize.sm, fontWeight: '600' },
  disabled: { opacity: 0.5 },

  emptyState: { paddingVertical: spacing[16], alignItems: 'center', gap: spacing[3] },
  emptyIcon:  { fontSize: 48 },
  emptyTitle: { fontFamily: fontFamily.display, fontSize: fontSize.h3, fontWeight: '500', textAlign: 'center' },
  emptySub:   { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center', lineHeight: 22, paddingHorizontal: spacing[4] },
});
