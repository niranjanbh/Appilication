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
import { useThemePreference } from '../lib/theme-context';
import { listActivityApi, type ActivityItem } from '../lib/api/activity';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../lib/design-tokens';

function formatWhen(iso: string): string {
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: true,
  });
}

function ActivityRow({ item, isDark }: { item: ActivityItem; isDark: boolean }) {
  const cardBg  = isDark ? colors.forestSurface : colors.white;
  const cardBdr = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)';
  const textPri = isDark ? colors.ivoryText     : colors.ink;
  const textSub = isDark ? colors.stoneDim : colors.stone;

  return (
    <View style={[styles.card, { backgroundColor: cardBg, borderColor: cardBdr }]}>
      <View style={[styles.dot, { backgroundColor: item.allowed ? colors.jade : colors.alert }]} />
      <View style={styles.body}>
        <Text style={[styles.desc, { color: textPri }]}>{item.description}</Text>
        <Text style={[styles.meta, { color: textSub }]}>
          {formatWhen(item.timestamp)}
          {item.ip_address ? ` · ${item.ip_address}` : ''}
          {!item.allowed ? ' · Blocked' : ''}
        </Text>
      </View>
    </View>
  );
}

export default function ActivityScreen() {
  const isDark = useThemePreference().colorScheme === 'dark';
  const [items,      setItems]      = useState<ActivityItem[]>([]);
  const [loading,    setLoading]    = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error,      setError]      = useState<string | null>(null);

  const fetchActivity = useCallback(async () => {
    try {
      const data = await listActivityApi();
      setItems(data.items);
      setError(null);
    } catch {
      setError('Could not load your activity.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { void fetchActivity(); }, [fetchActivity]);

  const handleRefresh = useCallback(() => {
    setRefreshing(true);
    void fetchActivity();
  }, [fetchActivity]);

  const bg      = isDark ? colors.forestInk  : colors.ivory;
  const textPri = isDark ? colors.ivoryText     : colors.ink;
  const textSub = isDark ? colors.stoneDim : colors.stone;

  if (loading) {
    return <View style={[styles.center, { backgroundColor: bg }]}><ActivityIndicator color={colors.jade} /></View>;
  }

  if (error) {
    return (
      <View style={[styles.center, { backgroundColor: bg }]}>
        <Text style={[styles.errorText, { color: colors.alert }]}>{error}</Text>
        <Pressable style={styles.retryBtn} onPress={() => void fetchActivity()}>
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
      {items.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyIcon}>🛡️</Text>
          <Text style={[styles.emptyTitle, { color: textPri }]}>No recent activity.</Text>
          <Text style={[styles.emptySub, { color: textSub }]}>
            Account and data activity — consents, uploads, sign-ins — will appear here.
          </Text>
        </View>
      ) : (
        <View style={styles.section}>
          <Text style={[styles.sectionHeader, { color: textSub }]}>Recent activity</Text>
          {items.map((it, idx) => (
            <ActivityRow key={`${it.action}-${it.timestamp}-${idx}`} item={it} isDark={isDark} />
          ))}
        </View>
      )}
    </ScrollView>
  );
}

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
    boxShadow: '0 4px 10px rgba(0,0,0,0.06)',
  },
  dot: { width: 8, height: 8, borderRadius: 4, flexShrink: 0 },
  body: { flex: 1, gap: spacing[1] },
  desc: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600' },
  meta: { fontFamily: fontFamily.body, fontSize: fontSize.caption },

  emptyState: { paddingVertical: spacing[16], alignItems: 'center', gap: spacing[3] },
  emptyIcon:  { fontSize: 48 },
  emptyTitle: { fontFamily: fontFamily.display, fontSize: fontSize.h3, fontWeight: '500', textAlign: 'center' },
  emptySub:   { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center', lineHeight: 22, paddingHorizontal: spacing[4] },
});
