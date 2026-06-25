import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { useThemePreference } from '../../lib/theme-context';
import { useRouter } from 'expo-router';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { listCarePlans, type CarePlan } from '../../lib/api/care-plans';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

const CATEGORY_LABELS: Record<string, string> = {
  medication: 'Medication',
  exercise: 'Exercise',
  diet: 'Diet',
  lifestyle: 'Lifestyle',
  follow_up: 'Follow-up',
  lab_test: 'Lab test',
};

function CarePlanCard({
  plan,
  isDark,
  onPress,
}: {
  plan: CarePlan;
  isDark: boolean;
  onPress: () => void;
}) {
  const scale = useSharedValue(1);
  const anim = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));
  const active = plan.status === 'active';
  const dotColor = active ? colors.jade : (isDark ? colors.stoneDim : colors.stone);

  const cardBg = isDark ? colors.forestSurface : colors.white;
  const cardBdr = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)';
  const textPri = isDark ? colors.ivoryText : colors.ink;
  const textSub = isDark ? colors.stoneDim : colors.stone;

  const categories = [...new Set(plan.items.map(i => CATEGORY_LABELS[i.category] ?? i.category.replace(/_/g, ' ').replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())))];
  const categoryText = categories.slice(0, 3).join(', ') + (categories.length > 3 ? '...' : '');

  return (
    <Animated.View style={anim}>
      <Pressable
        style={[styles.card, { backgroundColor: cardBg, borderColor: cardBdr }]}
        onPress={onPress}
        onPressIn={() => { scale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
        onPressOut={() => { scale.value = withSpring(1, { mass: 0.3, stiffness: 500 }); }}
        accessibilityLabel={`Care plan: ${plan.title}, ${plan.items.length} items, ${plan.status}`}
      >
        <View style={[styles.statusDot, { backgroundColor: dotColor }]} />
        <View style={styles.cardBody}>
          <Text style={[styles.cardTitle, { color: textPri }]} numberOfLines={1}>
            {plan.title}
          </Text>
          <Text style={[styles.cardMeta, { color: textSub }]}>
            {categoryText} · {plan.items.length} item{plan.items.length !== 1 ? 's' : ''}
          </Text>
          <Text style={[styles.cardMeta, { color: textSub }]}>
            {active ? `Since ${formatDate(plan.activated_at)}` : `Completed ${formatDate(plan.completed_at)}`}
          </Text>
        </View>
        <Text style={[styles.chevron, { color: textSub }]}>›</Text>
      </Pressable>
    </Animated.View>
  );
}

export default function CarePlansListScreen() {
  const router = useRouter();
  const isDark = useThemePreference().colorScheme === 'dark';

  // Share the home widget's cache (`['care-plans']`) so both surfaces stay in
  // sync. The widget fetches page 1 with page size 20; mirror that exactly.
  const {
    data,
    isLoading: loading,
    isError,
    isFetching,
    refetch,
  } = useQuery({
    queryKey: ['care-plans'],
    queryFn: () => listCarePlans(1, 20),
    staleTime: 5 * 60_000,
  });

  const plans: CarePlan[] = data?.items ?? [];
  const bg = isDark ? colors.forestInk : colors.ivory;

  if (loading) {
    return <View style={[styles.center, { backgroundColor: bg }]}><ActivityIndicator color={colors.jade} /></View>;
  }

  if (isError) {
    return (
      <View style={[styles.center, { backgroundColor: bg }]}>
        <Text style={[styles.errorText, { color: colors.alert }]}>Could not load care plans.</Text>
        <Pressable style={styles.retryBtn} onPress={() => void refetch()} accessibilityLabel="Retry loading care plans">
          <Text style={[styles.retryText, { color: colors.jade }]}>Try again</Text>
        </Pressable>
      </View>
    );
  }

  const active = plans.filter(p => p.status === 'active');
  const completed = plans.filter(p => p.status === 'completed');
  const textPri = isDark ? colors.ivoryText : colors.ink;
  const textSub = isDark ? colors.stoneDim : colors.stone;

  return (
    <ScrollView
      style={[styles.scroll, { backgroundColor: bg }]}
      contentContainerStyle={styles.container}
      refreshControl={<RefreshControl refreshing={isFetching && !loading} onRefresh={refetch} tintColor={colors.jade} />}
    >
      {plans.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyIcon}>📋</Text>
          <Text style={[styles.emptyTitle, { color: textPri }]}>Your care plans will appear here.</Text>
          <Text style={[styles.emptySub, { color: textSub }]}>
            After a consultation, your doctor may create a personalised care plan covering medications, diet, exercise, and lifestyle changes.
          </Text>
        </View>
      ) : (
        <>
          {active.length > 0 && (
            <View style={styles.section}>
              <Text style={[styles.sectionHeader, { color: textSub }]}>Active</Text>
              {active.map(p => (
                <CarePlanCard key={p.id} plan={p} isDark={isDark} onPress={() => router.push(`/care-plans/${p.id}`)} />
              ))}
            </View>
          )}
          {completed.length > 0 && (
            <View style={styles.section}>
              <Text style={[styles.sectionHeader, { color: textSub }]}>Completed</Text>
              {completed.map(p => (
                <CarePlanCard key={p.id} plan={p} isDark={isDark} onPress={() => router.push(`/care-plans/${p.id}`)} />
              ))}
            </View>
          )}
        </>
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
  retryBtn: { alignItems: 'center' },
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
  emptyIcon: { fontSize: 48 },
  emptyTitle: { fontFamily: fontFamily.display, fontSize: fontSize.h3, fontWeight: '500', textAlign: 'center' },
  emptySub: { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center', lineHeight: 22, paddingHorizontal: spacing[4] },
});
