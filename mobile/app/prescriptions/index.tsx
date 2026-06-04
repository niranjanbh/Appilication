/**
 * Prescription list screen — app/prescriptions/index.tsx
 *
 * Shows active and past prescriptions. Reached from Plan → Medications
 * and from consultation detail.  Not a separate tab.
 */

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
import { useRouter } from 'expo-router';

import {
  listPrescriptions,
  type Prescription,
} from '../../lib/api/prescriptions';
import {
  borderRadius,
  colors,
  fontFamily,
  fontSize,
  spacing,
} from '../../lib/design-tokens';

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

function isActive(rx: Prescription): boolean {
  return rx.status === 'signed';
}

// ── Prescription card ─────────────────────────────────────────────────────────

function PrescriptionCard({
  prescription,
  onPress,
}: {
  prescription: Prescription;
  onPress: () => void;
}) {
  const active = isActive(prescription);
  const firstDrug = prescription.items[0]?.drug_generic_name ?? 'Prescription';
  const itemCount = prescription.items.length;

  return (
    <Pressable
      style={styles.card}
      onPress={onPress}
      accessibilityLabel={`Prescription: ${firstDrug}${itemCount > 1 ? ` and ${itemCount - 1} more` : ''}, issued ${formatDate(prescription.signed_at)}`}
    >
      <View style={styles.cardLeft}>
        <View style={[styles.statusDot, { backgroundColor: active ? colors.forest : colors.stone }]} />
      </View>
      <View style={styles.cardBody}>
        <Text style={styles.cardTitle} numberOfLines={1}>
          {firstDrug}
          {itemCount > 1 ? ` +${itemCount - 1}` : ''}
        </Text>
        <Text style={styles.cardMeta}>
          Issued {formatDate(prescription.signed_at)}
          {prescription.version > 1 ? `  ·  v${prescription.version}` : ''}
        </Text>
      </View>
      <Text style={styles.cardChevron}>›</Text>
    </Pressable>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function PrescriptionsListScreen() {
  const router = useRouter();
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  useEffect(() => {
    void fetchPrescriptions();
  }, [fetchPrescriptions]);

  const handleRefresh = useCallback(() => {
    setRefreshing(true);
    void fetchPrescriptions();
  }, [fetchPrescriptions]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.forest} />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{error}</Text>
        <Pressable style={styles.retryBtn} onPress={() => void fetchPrescriptions()}>
          <Text style={styles.retryText}>Try again</Text>
        </Pressable>
      </View>
    );
  }

  const active = prescriptions.filter(isActive);
  const past = prescriptions.filter((rx) => !isActive(rx));

  return (
    <ScrollView
      style={styles.scroll}
      contentContainerStyle={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor={colors.forest} />
      }
    >
      {prescriptions.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyTitle}>Your prescriptions will live here.</Text>
          <Text style={styles.emptySub}>
            Once your doctor issues a prescription, it stays accessible permanently.
          </Text>
        </View>
      ) : (
        <>
          {active.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.sectionHeader}>Active</Text>
              {active.map((rx) => (
                <PrescriptionCard
                  key={rx.id}
                  prescription={rx}
                  onPress={() => router.push(`/prescriptions/${rx.id}`)}
                />
              ))}
            </View>
          )}

          {past.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.sectionHeader}>Past</Text>
              {past.map((rx) => (
                <PrescriptionCard
                  key={rx.id}
                  prescription={rx}
                  onPress={() => router.push(`/prescriptions/${rx.id}`)}
                />
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
  scroll: {
    flex: 1,
    backgroundColor: colors.ivory,
  },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[4],
    paddingTop: spacing[4],
    paddingBottom: spacing[16],
    gap: spacing[4],
  },
  center: {
    flex: 1,
    backgroundColor: colors.ivory,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing[4],
  },
  errorText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.terracotta,
    textAlign: 'center',
  },
  retryBtn: { alignItems: 'center' },
  retryText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.forest,
  },
  section: {
    gap: spacing[2],
  },
  sectionHeader: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    paddingHorizontal: spacing[1],
  },
  card: {
    backgroundColor: colors.white,
    borderRadius: borderRadius.lg,
    padding: spacing[4],
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
  },
  cardLeft: {
    width: 8,
    alignItems: 'center',
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  cardBody: {
    flex: 1,
    gap: spacing[1],
  },
  cardTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    fontWeight: '600',
  },
  cardMeta: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
  },
  cardChevron: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.stone,
  },
  emptyState: {
    paddingVertical: spacing[16],
    alignItems: 'center',
    gap: spacing[2],
  },
  emptyTitle: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h3,
    color: colors.forest,
    fontWeight: '500',
    textAlign: 'center',
  },
  emptySub: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    textAlign: 'center',
    lineHeight: 22,
    paddingHorizontal: spacing[4],
  },
});
