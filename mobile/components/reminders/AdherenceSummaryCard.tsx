import { StyleSheet, Text, View } from 'react-native';
import {
  borderRadius,
  colors,
  fontFamily,
  fontSize,
  spacing,
} from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';
import type { AdherenceSummary } from '../../types/wellness';

function rateColor(rate: number): string {
  if (rate >= 0.9) return colors.jade;
  if (rate >= 0.7) return colors.saffron;
  return colors.terracotta;
}

interface AdherenceSummaryCardProps {
  summary: AdherenceSummary;
}

/**
 * Longer-horizon adherence snapshot for the patient: 30-day rate plus longest
 * streak and how many reminders came from their doctor. Current streak / today's
 * progress live in TodayProgressCard, so this card intentionally omits them.
 */
export function AdherenceSummaryCard({ summary }: AdherenceSummaryCardProps) {
  const t = useTheme();

  // Motivational surface (unlike the doctor's clinical view): don't show a
  // discouraging 0% to a patient with no adherence history yet.
  const hasHistory =
    summary.adherence_rate_30d > 0 ||
    summary.current_streak > 0 ||
    summary.longest_streak > 0;
  if (!hasHistory) return null;

  const pct = Math.round(summary.adherence_rate_30d * 100);
  const color = rateColor(summary.adherence_rate_30d);

  return (
    <View style={[s.card, { backgroundColor: t.surface }]}>
      <Text style={[s.heading, { color: t.textSub }]}>30-Day Adherence</Text>
      <View style={s.row}>
        <Text style={[s.pct, { color }]}>{pct}%</Text>
        <View style={s.stats}>
          <View style={s.statRow}>
            <Text style={[s.statLabel, { color: t.textSub }]}>Longest streak</Text>
            <Text style={[s.statValue, { color: t.text }]}>
              {summary.longest_streak} day{summary.longest_streak !== 1 ? 's' : ''}
            </Text>
          </View>
          {summary.active_prescription_reminders > 0 && (
            <View style={s.statRow}>
              <Text style={[s.statLabel, { color: t.textSub }]}>From your doctor</Text>
              <Text style={[s.statValue, { color: t.text }]}>
                {summary.active_prescription_reminders} reminder
                {summary.active_prescription_reminders !== 1 ? 's' : ''}
              </Text>
            </View>
          )}
        </View>
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  card: {
    borderRadius: borderRadius.xl,
    padding: spacing[4],
    gap: spacing[3],
  },
  heading: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[4],
  },
  pct: {
    fontFamily: fontFamily.data,
    fontSize: fontSize.h1,
    fontWeight: '700',
  },
  stats: {
    flex: 1,
    gap: spacing[1],
  },
  statRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    gap: spacing[2],
  },
  statLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
  },
  statValue: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
});
