import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useThemePreference } from '../../lib/theme-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { CaptureGuard } from '../../components/ui/CaptureGuard';
import { getCarePlan, type CarePlan, type CarePlanItem } from '../../lib/api/care-plans';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

function formatDate(iso: string | null) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
}

const CATEGORY_LABELS: Record<string, string> = {
  medication: 'Medication',
  exercise: 'Exercise',
  diet: 'Diet',
  lifestyle: 'Lifestyle',
  follow_up: 'Follow-up',
  lab_test: 'Lab test',
};

const CATEGORY_ORDER = ['medication', 'exercise', 'diet', 'lifestyle', 'follow_up', 'lab_test'];

function priorityBadge(priority: string, isDark: boolean) {
  if (priority === 'normal') return null;
  const isHigh = priority === 'high';
  const bg = isHigh ? colors.criticalRed + '15' : (isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)');
  const color = isHigh ? colors.criticalRed : (isDark ? colors.stoneDim : colors.coolGray);
  return (
    <View style={[badge.container, { backgroundColor: bg }]}>
      <Text style={[badge.text, { color }]}>{priority}</Text>
    </View>
  );
}

const badge = StyleSheet.create({
  container: { borderRadius: borderRadius.full, paddingHorizontal: spacing[2], paddingVertical: 2, alignSelf: 'flex-start' },
  text: { fontFamily: fontFamily.body, fontSize: fontSize.xs, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.3 },
});

function ItemCard({ item, isDark, textPri, textSub, cardBg, cardBdr }: {
  item: CarePlanItem; isDark: boolean; textPri: string; textSub: string; cardBg: string; cardBdr: string;
}) {
  return (
    <View style={[itemStyles.card, { backgroundColor: cardBg, borderColor: cardBdr }]}>
      <View style={itemStyles.titleRow}>
        <Text style={[itemStyles.title, { color: textPri }]}>{item.title}</Text>
        {priorityBadge(item.priority, isDark)}
      </View>
      {item.description && (
        <Text style={[itemStyles.desc, { color: textSub }]}>{item.description}</Text>
      )}
      {(item.frequency || item.duration) && (
        <View style={[itemStyles.chipRow, { borderTopColor: isDark ? 'rgba(255,255,255,0.06)' : colors.borderLight }]}>
          {item.frequency && (
            <View style={itemStyles.chip}>
              <Text style={[itemStyles.chipLabel, { color: textSub }]}>Frequency</Text>
              <Text style={[itemStyles.chipValue, { color: textPri }]}>{item.frequency}</Text>
            </View>
          )}
          {item.duration && (
            <View style={itemStyles.chip}>
              <Text style={[itemStyles.chipLabel, { color: textSub }]}>Duration</Text>
              <Text style={[itemStyles.chipValue, { color: textPri }]}>{item.duration}</Text>
            </View>
          )}
        </View>
      )}
    </View>
  );
}

const itemStyles = StyleSheet.create({
  card: {
    borderRadius: borderRadius.xl,
    padding: spacing[4],
    gap: spacing[2],
    borderWidth: 1,
    boxShadow: '0 4px 10px rgba(0,0,0,0.06)',
  },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  title: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600', flex: 1 },
  desc: { fontFamily: fontFamily.body, fontSize: fontSize.caption, lineHeight: 18 },
  chipRow: {
    flexDirection: 'row',
    gap: spacing[4],
    borderTopWidth: 1,
    paddingTop: spacing[3],
    marginTop: spacing[1],
    flexWrap: 'wrap',
  },
  chip: { gap: 2 },
  chipLabel: { fontFamily: fontFamily.body, fontSize: fontSize.xs, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5 },
  chipValue: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '500' },
});

function groupByCategory(items: CarePlanItem[]): { category: string; items: CarePlanItem[] }[] {
  const sorted = [...items].sort((a, b) => a.order_index - b.order_index);
  const grouped = new Map<string, CarePlanItem[]>();
  for (const item of sorted) {
    const group = grouped.get(item.category) ?? [];
    group.push(item);
    grouped.set(item.category, group);
  }
  return CATEGORY_ORDER
    .filter(cat => grouped.has(cat))
    .map(cat => ({ category: cat, items: grouped.get(cat)! }));
}

export default function CarePlanDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const isDark = useThemePreference().colorScheme === 'dark';

  const [plan, setPlan] = useState<CarePlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPlan = useCallback(async () => {
    if (!id) return;
    try {
      const data = await getCarePlan(id as string);
      setPlan(data);
      setError(null);
    } catch {
      setError('Could not load this care plan.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { void fetchPlan(); }, [fetchPlan]);

  const bg = isDark ? colors.midnight : colors.skyMist;
  const textPri = isDark ? colors.white : colors.navyDeep;
  const textSub = isDark ? colors.slateText : colors.coolGray;
  const cardBg = isDark ? colors.nightSurface : colors.white;
  const cardBdr = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)';
  const divider = isDark ? 'rgba(255,255,255,0.08)' : colors.borderLight;

  if (loading) {
    return <View style={[styles.center, { backgroundColor: bg }]}><ActivityIndicator color={colors.electricBlue} /></View>;
  }
  if (error || !plan) {
    return (
      <View style={[styles.center, { backgroundColor: bg }]}>
        <Text style={[styles.errorText, { color: colors.criticalRed }]}>{error ?? 'Care plan not found.'}</Text>
        <Pressable onPress={() => router.back()}>
          <Text style={[styles.backLink, { color: colors.electricBlue }]}>← Back</Text>
        </Pressable>
      </View>
    );
  }

  const groups = groupByCategory(plan.items);
  const isActive = plan.status === 'active';

  return (
    <ScrollView style={[styles.scroll, { backgroundColor: bg }]} contentContainerStyle={styles.container}>
      <CaptureGuard />

      {/* Clinic letterhead */}
      <View style={[styles.letterhead, { borderBottomColor: isDark ? colors.electricBlue + '40' : colors.navyDeep }]}>
        <View>
          <Text style={[styles.clinicName, { color: isDark ? colors.electricBlue : colors.navyDeep }]}>Kyros Clinic</Text>
          <Text style={[styles.clinicSub, { color: textSub }]}>Care Plan</Text>
        </View>
        <View style={styles.clinicRight}>
          <Text style={[styles.clinicMeta, { color: textSub }]}>
            {isActive ? `Active since ${formatDate(plan.activated_at)}` : `Completed ${formatDate(plan.completed_at)}`}
          </Text>
        </View>
      </View>

      {/* Status chip */}
      <View style={[styles.statusChip, { backgroundColor: isActive ? colors.successGreen + '15' : (isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)') }]}>
        <Text style={[styles.statusText, { color: isActive ? colors.successGreen : textSub }]}>
          {isActive ? '● Active' : '○ Completed'}
        </Text>
      </View>

      {/* Title & condition */}
      <Text style={[styles.planTitle, { color: textPri }]}>{plan.title}</Text>
      {plan.condition_category && (
        <View style={[styles.condBadge, { backgroundColor: isDark ? colors.electricBlue + '15' : colors.navyDeep + '10' }]}>
          <Text style={[styles.condText, { color: isDark ? colors.electricBlue : colors.navyDeep }]}>
            {plan.condition_category.replace(/_/g, ' ')}
          </Text>
        </View>
      )}

      {/* Validity */}
      {(plan.valid_from || plan.valid_until) && (
        <Text style={[styles.validityText, { color: textSub }]}>
          {plan.valid_from ? `From ${formatDate(plan.valid_from)}` : ''}
          {plan.valid_from && plan.valid_until ? ' · ' : ''}
          {plan.valid_until ? `Until ${formatDate(plan.valid_until)}` : ''}
        </Text>
      )}

      {/* Goals */}
      {plan.goals && (
        <View style={[styles.infoBlock, { backgroundColor: cardBg, borderColor: cardBdr }]}>
          <Text style={[styles.infoLabel, { color: textSub }]}>Goals</Text>
          <Text style={[styles.infoValue, { color: textPri }]}>{plan.goals}</Text>
        </View>
      )}

      {/* Items grouped by category */}
      {groups.map(group => (
        <View key={group.category} style={styles.categorySection}>
          <Text style={[styles.categoryHeader, { color: isDark ? colors.electricBlue : colors.navyDeep }]}>
            {CATEGORY_LABELS[group.category] ?? group.category}
          </Text>
          {group.items.map(item => (
            <ItemCard key={item.id} item={item} isDark={isDark} textPri={textPri} textSub={textSub} cardBg={cardBg} cardBdr={cardBdr} />
          ))}
        </View>
      ))}

      {/* Notes */}
      {plan.notes && (
        <View style={[styles.infoBlock, { backgroundColor: cardBg, borderColor: cardBdr }]}>
          <Text style={[styles.infoLabel, { color: textSub }]}>Notes from your doctor</Text>
          <Text style={[styles.infoValue, { color: textPri }]}>{plan.notes}</Text>
        </View>
      )}

      {/* Footer */}
      <View style={[styles.footer, { borderTopColor: divider }]}>
        <Text style={[styles.footerText, { color: textSub }]}>
          This care plan was created by your Kyros Clinic doctor. Follow up with your doctor if you have questions.
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1 },
  container: { flexGrow: 1, paddingHorizontal: spacing[5], paddingTop: spacing[4], paddingBottom: spacing[16], gap: spacing[4] },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing[4], paddingHorizontal: spacing[8] },
  errorText: { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center' },
  backLink: { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontWeight: '600' },

  letterhead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', borderBottomWidth: 2, paddingBottom: spacing[3] },
  clinicName: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '800' },
  clinicSub: { fontFamily: fontFamily.body, fontSize: fontSize.caption, marginTop: 2 },
  clinicRight: { alignItems: 'flex-end', gap: 2 },
  clinicMeta: { fontFamily: fontFamily.body, fontSize: fontSize.caption },

  statusChip: { alignSelf: 'flex-start', borderRadius: borderRadius.full, paddingHorizontal: spacing[3], paddingVertical: spacing[1] },
  statusText: { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontWeight: '700' },

  planTitle: { fontFamily: fontFamily.display, fontSize: fontSize.h3, fontWeight: '600' },
  condBadge: { alignSelf: 'flex-start', borderRadius: borderRadius.full, paddingHorizontal: spacing[3], paddingVertical: spacing[1] },
  condText: { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontWeight: '600', textTransform: 'capitalize' },
  validityText: { fontFamily: fontFamily.body, fontSize: fontSize.caption },

  infoBlock: {
    borderRadius: borderRadius.xl,
    padding: spacing[4],
    gap: spacing[1],
    borderWidth: 1,
    boxShadow: '0 4px 10px rgba(0,0,0,0.06)',
  },
  infoLabel: { fontFamily: fontFamily.body, fontSize: fontSize.xs, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5 },
  infoValue: { fontFamily: fontFamily.body, fontSize: fontSize.body, lineHeight: 22 },

  categorySection: { gap: spacing[3] },
  categoryHeader: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700' },

  footer: { borderTopWidth: 1, paddingTop: spacing[3] },
  footerText: { fontFamily: fontFamily.body, fontSize: fontSize.caption, textAlign: 'center', lineHeight: 18 },
});
