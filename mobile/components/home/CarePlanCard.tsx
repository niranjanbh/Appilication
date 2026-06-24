/**
 * CarePlanCard — surfaces the patient's active care plan on Home.
 *
 * Before a first consultation there is no plan, so we keep the reassuring
 * pre-consult placeholder. Once an active plan exists we summarise its title,
 * goals, and top items, linking through to the full plan.
 */

import { useQuery } from '@tanstack/react-query';
import { StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { GlassCard } from '../ui/GlassCard';
import { HapticPressable } from '../ui/HapticPressable';
import { fontFamily, fontSize, spacing } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';
import { listCarePlans, type CarePlan } from '../../lib/api/care-plans';

const MAX_ITEMS = 3;

export function CarePlanCard() {
  const t = useTheme();
  const router = useRouter();

  const { data } = useQuery({
    queryKey: ['care-plans'],
    queryFn: () => listCarePlans(1, 20),
    staleTime: 5 * 60_000,
  });

  const active: CarePlan | undefined = data?.items.find((p) => p.status === 'active');

  // ── No active plan: reassuring pre-consult placeholder ──────────────────────
  if (!active) {
    return (
      <GlassCard>
        <View style={styles.inner}>
          <Text style={[styles.eyebrow, { color: t.textSub }]}>YOUR CARE PLAN</Text>
          <Text style={[styles.title, { color: t.text }]}>Personalized care starts here</Text>
          <Text style={[styles.body, { color: t.textSub }]}>
            Talk to a Kyros specialist about your hormonal health. Your care plan —
            prescriptions, reminders, and lab orders — will appear here after your first
            consultation.
          </Text>
        </View>
      </GlassCard>
    );
  }

  // ── Active plan summary ─────────────────────────────────────────────────────
  const items = [...active.items]
    .sort((a, b) => a.order_index - b.order_index)
    .slice(0, MAX_ITEMS);

  return (
    <HapticPressable
      scaleTo={0.98}
      onPress={() => router.push(`/care-plans/${active.id}`)}
      accessibilityLabel={`Open care plan: ${active.title}`}
    >
      <GlassCard>
        <View style={styles.inner}>
          <View style={styles.headerRow}>
            <Text style={[styles.eyebrow, { color: t.textSub }]}>YOUR CARE PLAN</Text>
            <Text style={[styles.link, { color: t.primary }]}>View</Text>
          </View>
          <Text style={[styles.title, { color: t.text }]}>{active.title}</Text>
          {active.goals ? (
            <Text style={[styles.body, { color: t.textSub }]} numberOfLines={2}>
              {active.goals}
            </Text>
          ) : null}

          {items.length > 0 ? (
            <View style={styles.itemList}>
              {items.map((item) => (
                <View key={item.id} style={styles.itemRow}>
                  <View style={[styles.dot, { backgroundColor: t.primary }]} />
                  <Text style={[styles.itemText, { color: t.text }]} numberOfLines={1}>
                    {item.title}
                  </Text>
                </View>
              ))}
            </View>
          ) : null}
        </View>
      </GlassCard>
    </HapticPressable>
  );
}

const styles = StyleSheet.create({
  inner: { gap: spacing[2] },
  headerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  link: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600' },
  eyebrow: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    letterSpacing: 1.2,
    textTransform: 'uppercase',
  },
  title: {
    fontFamily: fontFamily.display,
    fontSize: 22,
    fontWeight: '500',
    lineHeight: 28,
  },
  body: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    lineHeight: 22,
  },
  itemList: { gap: spacing[2], marginTop: spacing[1] },
  itemRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  dot: { width: 6, height: 6, borderRadius: 3 },
  itemText: { fontFamily: fontFamily.body, fontSize: fontSize.body, flex: 1 },
});
