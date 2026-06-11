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
import { useThemePreference } from '../../lib/theme-context';
import { useRouter } from 'expo-router';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { listPrescriptions, type Prescription } from '../../lib/api/prescriptions';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function isActive(rx: Prescription): boolean { return rx.status === 'signed'; }

// ── Prescription card ─────────────────────────────────────────────────────────

function PrescriptionCard({
  prescription,
  isDark,
  onPress,
}: {
  prescription: Prescription;
  isDark: boolean;
  onPress: () => void;
}) {
  const scale  = useSharedValue(1);
  const anim   = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));
  const active = isActive(prescription);
  const firstDrug  = prescription.items[0]?.drug_generic_name ?? 'Prescription';
  const itemCount  = prescription.items.length;
  const dotColor   = active ? colors.successGreen : (isDark ? colors.slateText : colors.coolGray);

  const cardBg  = isDark ? colors.nightSurface : colors.white;
  const cardBdr = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)';
  const textPri = isDark ? colors.white     : colors.navyDeep;
  const textSub = isDark ? colors.slateText : colors.coolGray;

  return (
    <Animated.View style={anim}>
      <Pressable
        style={[styles.card, { backgroundColor: cardBg, borderColor: cardBdr }]}
        onPress={onPress}
        onPressIn={() => { scale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
        onPressOut={() => { scale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
        accessibilityLabel={`Prescription: ${firstDrug}${itemCount > 1 ? ` and ${itemCount - 1} more` : ''}, issued ${formatDate(prescription.signed_at)}`}
      >
        <View style={[styles.statusDot, { backgroundColor: dotColor }]} />
        <View style={styles.cardBody}>
          <Text style={[styles.cardTitle, { color: textPri }]} numberOfLines={1}>
            {firstDrug}{itemCount > 1 ? ` +${itemCount - 1}` : ''}
          </Text>
          <Text style={[styles.cardMeta, { color: textSub }]}>
            Issued {formatDate(prescription.signed_at)}{prescription.version > 1 ? ` · v${prescription.version}` : ''}
          </Text>
        </View>
        <Text style={[styles.chevron, { color: textSub }]}>›</Text>
      </Pressable>
    </Animated.View>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function PrescriptionsListScreen() {
  const router  = useRouter();
  const isDark  = useThemePreference().colorScheme === 'dark';
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [loading,    setLoading]    = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error,      setError]      = useState<string | null>(null);

  const fetchPrescriptions = useCallback(async () => {
    try {
      const data = await listPrescriptions();
      setPrescriptions(data.items);
      setError(null);
    } catch {
      setError('Could not load prescriptions.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { void fetchPrescriptions(); }, [fetchPrescriptions]);

  const handleRefresh = useCallback(() => {
    setRefreshing(true);
    void fetchPrescriptions();
  }, [fetchPrescriptions]);

  const bg = isDark ? colors.midnight : colors.skyMist;

  if (loading) {
    return <View style={[styles.center, { backgroundColor: bg }]}><ActivityIndicator color={colors.electricBlue} /></View>;
  }

  if (error) {
    return (
      <View style={[styles.center, { backgroundColor: bg }]}>
        <Text style={[styles.errorText, { color: colors.criticalRed }]}>{error}</Text>
        <Pressable style={styles.retryBtn} onPress={() => void fetchPrescriptions()}>
          <Text style={[styles.retryText, { color: colors.electricBlue }]}>Try again</Text>
        </Pressable>
      </View>
    );
  }

  const active = prescriptions.filter(isActive);
  const past   = prescriptions.filter(rx => !isActive(rx));
  const textPri = isDark ? colors.white     : colors.navyDeep;
  const textSub = isDark ? colors.slateText : colors.coolGray;

  return (
    <ScrollView
      style={[styles.scroll, { backgroundColor: bg }]}
      contentContainerStyle={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor={colors.electricBlue} />}
    >
      {prescriptions.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyIcon}>💊</Text>
          <Text style={[styles.emptyTitle, { color: textPri }]}>Your prescriptions will live here.</Text>
          <Text style={[styles.emptySub, { color: textSub }]}>
            Once your doctor issues a prescription, it stays accessible permanently.
          </Text>
        </View>
      ) : (
        <>
          {active.length > 0 && (
            <View style={styles.section}>
              <Text style={[styles.sectionHeader, { color: textSub }]}>Active</Text>
              {active.map(rx => (
                <PrescriptionCard key={rx.id} prescription={rx} isDark={isDark} onPress={() => router.push(`/prescriptions/${rx.id}`)} />
              ))}
            </View>
          )}
          {past.length > 0 && (
            <View style={styles.section}>
              <Text style={[styles.sectionHeader, { color: textSub }]}>Past</Text>
              {past.map(rx => (
                <PrescriptionCard key={rx.id} prescription={rx} isDark={isDark} onPress={() => router.push(`/prescriptions/${rx.id}`)} />
              ))}
            </View>
          )}
        </>
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
  statusDot: { width: 8, height: 8, borderRadius: 4, flexShrink: 0 },
  cardBody: { flex: 1, gap: spacing[1] },
  cardTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
  cardMeta: { fontFamily: fontFamily.body, fontSize: fontSize.caption },
  chevron: { fontFamily: fontFamily.body, fontSize: 20 },

  emptyState: { paddingVertical: spacing[16], alignItems: 'center', gap: spacing[3] },
  emptyIcon:  { fontSize: 48 },
  emptyTitle: { fontFamily: fontFamily.display, fontSize: fontSize.h3, fontWeight: '500', textAlign: 'center' },
  emptySub:   { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center', lineHeight: 22, paddingHorizontal: spacing[4] },
});
