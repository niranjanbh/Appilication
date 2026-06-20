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
import { listRefunds, type Refund, type RefundStatus } from '../lib/api/payments';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../lib/design-tokens';

// ── Helpers ─────────────────────────────────────────────────────────────────────

function formatRupees(paise: number): string {
  return `₹${(paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 0 })}`;
}
function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

const STATUS_META: Record<RefundStatus, { label: string; color: string }> = {
  pending:   { label: 'Processing', color: colors.saffron },
  processed: { label: 'Refunded',   color: colors.jade },
  failed:    { label: 'Failed',     color: colors.alert },
};

// ── Refund card ───────────────────────────────────────────────────────────────

function RefundCard({ refund, isDark }: { refund: Refund; isDark: boolean }) {
  const meta    = STATUS_META[refund.status];
  const cardBg  = isDark ? colors.forestSurface : colors.white;
  const cardBdr = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)';
  const textPri = isDark ? colors.ivoryText     : colors.ink;
  const textSub = isDark ? colors.stoneDim : colors.stone;

  return (
    <View
      style={[styles.card, { backgroundColor: cardBg, borderColor: cardBdr }]}
      accessibilityLabel={`Refund of ${formatRupees(refund.amount_paise)}, ${meta.label}, ${formatDate(refund.created_at)}`}
    >
      <View style={styles.cardBody}>
        <Text style={[styles.cardAmount, { color: textPri }]}>{formatRupees(refund.amount_paise)}</Text>
        <Text style={[styles.cardMeta, { color: textSub }]}>
          {formatDate(refund.created_at)}{refund.reason ? ` · ${refund.reason}` : ''}
        </Text>
      </View>
      <View style={[styles.statusPill, { backgroundColor: meta.color + '18' }]}>
        <View style={[styles.statusDot, { backgroundColor: meta.color }]} />
        <Text style={[styles.statusText, { color: meta.color }]}>{meta.label}</Text>
      </View>
    </View>
  );
}

// ── Screen ──────────────────────────────────────────────────────────────────────

export default function PaymentsScreen() {
  const isDark = useThemePreference().colorScheme === 'dark';
  const [refunds,    setRefunds]    = useState<Refund[]>([]);
  const [loading,    setLoading]    = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error,      setError]      = useState<string | null>(null);

  const fetchRefunds = useCallback(async () => {
    try {
      const data = await listRefunds();
      setRefunds(data.items);
      setError(null);
    } catch {
      setError('Could not load your refunds.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { void fetchRefunds(); }, [fetchRefunds]);

  const handleRefresh = useCallback(() => {
    setRefreshing(true);
    void fetchRefunds();
  }, [fetchRefunds]);

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
        <Pressable style={styles.retryBtn} onPress={() => void fetchRefunds()}>
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
      {refunds.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyIcon}>🧾</Text>
          <Text style={[styles.emptyTitle, { color: textPri }]}>No refunds yet.</Text>
          <Text style={[styles.emptySub, { color: textSub }]}>
            Refunds from cancelled appointments appear here, with their status as they are processed.
          </Text>
        </View>
      ) : (
        <View style={styles.section}>
          <Text style={[styles.sectionHeader, { color: textSub }]}>Refunds</Text>
          {refunds.map(r => (
            <RefundCard key={r.id} refund={r} isDark={isDark} />
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
    boxShadow: '0 4px 10px rgba(0,0,0,0.06)',
  },
  cardBody:   { flex: 1, gap: spacing[1] },
  cardAmount: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700' },
  cardMeta:   { fontFamily: fontFamily.body, fontSize: fontSize.caption },

  statusPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1],
    borderRadius: borderRadius.full,
  },
  statusDot:  { width: 7, height: 7, borderRadius: 4 },
  statusText: { fontFamily: fontFamily.body, fontSize: fontSize.sm, fontWeight: '700' },

  emptyState: { paddingVertical: spacing[16], alignItems: 'center', gap: spacing[3] },
  emptyIcon:  { fontSize: 48 },
  emptyTitle: { fontFamily: fontFamily.display, fontSize: fontSize.h3, fontWeight: '500', textAlign: 'center' },
  emptySub:   { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center', lineHeight: 22, paddingHorizontal: spacing[4] },
});
