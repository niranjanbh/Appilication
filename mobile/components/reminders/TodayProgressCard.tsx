import { Ionicons } from '@expo/vector-icons';
import { useEffect } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';
import {
  borderRadius,
  colors,
  fontFamily,
  fontSize,
  spacing,
  withAlpha,
} from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';
import type { DailySummary } from '../../types/wellness';

function getStreakMessage(streak: number): string | null {
  if (streak < 1) return null;
  if (streak <= 3) return 'Great start — keep it going';
  if (streak <= 7) return 'Building a habit';
  if (streak <= 30) return "You're on a roll";
  return "Consistency is the hardest part. You're doing it.";
}

function getProgressMessage(completed: number, total: number): string | null {
  if (total === 0 || completed >= total) return null;
  if (completed === 0) return null;
  if (completed / total >= 0.5) return 'Almost there';
  return 'Good progress — keep going';
}

interface TodayProgressCardProps {
  summary: DailySummary;
}

export function TodayProgressCard({ summary }: TodayProgressCardProps) {
  const t = useTheme();
  const { total, completed, streak } = summary;
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;
  const allDone = total > 0 && completed >= total;

  // Smoothly grow/shrink the bar as completions change, instead of snapping.
  const fillPct = useSharedValue(Math.min(pct, 100));
  useEffect(() => {
    fillPct.value = withTiming(Math.min(pct, 100), { duration: 450 });
  }, [pct, fillPct]);
  const fillStyle = useAnimatedStyle(() => ({ width: `${fillPct.value}%` }));
  const streakMsg = allDone ? getStreakMessage(streak) : null;
  const progressMsg = getProgressMessage(completed, total);

  const barColor = allDone
    ? colors.jade
    : pct >= 50
      ? colors.saffron
      : t.isDark ? colors.stoneDim : colors.stone;

  return (
    <View style={[s.card, { backgroundColor: t.surface }]}>
      <View style={s.headerRow}>
        <Text style={[s.heading, { color: t.text }]}>Today's Progress</Text>
        {total > 0 && (
          <Text style={[s.pct, { color: allDone ? colors.jade : t.textSub }]}>
            {pct}%
          </Text>
        )}
      </View>

      {total > 0 ? (
        <>
          <View style={[s.trackBg, { backgroundColor: t.isDark ? withAlpha(colors.stoneDim, 0.20) : colors.borderLight }]}>
            <Animated.View
              style={[
                s.trackFill,
                { backgroundColor: barColor },
                fillStyle,
              ]}
            />
          </View>

          <Text style={[s.detail, { color: allDone ? colors.jade : t.textSub }]}>
            {allDone
              ? 'All done for today'
              : `${completed} of ${total} completed${progressMsg ? ` · ${progressMsg}` : ''}`}
          </Text>
        </>
      ) : (
        <Text style={[s.detail, { color: t.textSub }]}>
          No reminders scheduled
        </Text>
      )}

      {streak > 0 && (
        <View style={s.streakRow}>
          <Ionicons name="flame" size={16} color={colors.saffron} />
          <Text style={[s.streakText, { color: t.text }]}>
            {streak}-day streak
          </Text>
          {streakMsg && (
            <Text style={[s.streakMsg, { color: t.textSub }]}>
              {' · '}{streakMsg}
            </Text>
          )}
        </View>
      )}
    </View>
  );
}

const s = StyleSheet.create({
  card: {
    borderRadius: borderRadius.xl,
    padding: spacing[4],
    gap: spacing[3],
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  heading: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
  pct: {
    fontFamily: fontFamily.data,
    fontSize: fontSize.bodyLg,
    fontWeight: '700',
  },
  trackBg: {
    height: 8,
    borderRadius: 4,
    overflow: 'hidden',
  },
  trackFill: {
    height: 8,
    borderRadius: 4,
  },
  detail: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
  },
  streakRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[1],
    paddingTop: spacing[1],
  },
  streakText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: '600',
  },
  streakMsg: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    flexShrink: 1,
  },
});
