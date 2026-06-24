import { Ionicons } from '@expo/vector-icons';
import { useEffect, useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { IconChip } from '../ui/IconChip';
import {
  borderRadius,
  colors,
  fontFamily,
  fontSize,
  spacing,
  type TintName,
  withAlpha,
} from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';
import type { Reminder, ReminderType } from '../../types/wellness';

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

const TYPE_META: Record<ReminderType, { icon: IoniconName; tint: TintName }> = {
  water:      { icon: 'water-outline',         tint: 'blue' },
  supplement: { icon: 'leaf-outline',          tint: 'green' },
  medication: { icon: 'medical-outline',       tint: 'violet' },
  gym:        { icon: 'barbell-outline',       tint: 'amber' },
  custom:     { icon: 'notifications-outline', tint: 'blue' },
};

function getCronMinutesOfDay(cron: string | null): number | null {
  if (!cron) return null;
  const parts = cron.split(' ');
  const h = parseInt(parts[1] ?? '', 10);
  const m = parseInt(parts[0] ?? '', 10);
  if (isNaN(h) || isNaN(m)) return null;
  return h * 60 + m;
}

function formatScheduleTime(cron: string | null): string {
  if (!cron) return '';
  const parts = cron.split(' ');
  const h24 = parseInt(parts[1] ?? '8', 10);
  const min = (parts[0] ?? '0').padStart(2, '0');
  const ampm = h24 >= 12 ? 'PM' : 'AM';
  const h12 = h24 % 12 === 0 ? 12 : h24 % 12;
  return `${h12}:${min} ${ampm}`;
}

function formatCountdown(diffMinutes: number): string {
  if (diffMinutes <= 0) return 'now';
  if (diffMinutes < 60) return `in ${diffMinutes} min`;
  const h = Math.floor(diffMinutes / 60);
  const m = diffMinutes % 60;
  return m > 0 ? `in ${h}h ${m}m` : `in ${h}h`;
}

function findNextReminder(reminders: Reminder[], nowMinutes: number): Reminder | null {
  let best: Reminder | null = null;
  let bestDiff = Infinity;

  for (const r of reminders) {
    if (!r.active) continue;
    const rMin = getCronMinutesOfDay(r.schedule_cron);
    if (rMin === null) continue;
    const diff = rMin - nowMinutes;
    if (diff > 0 && diff < bestDiff) {
      bestDiff = diff;
      best = r;
    }
  }
  return best;
}

function findFirstReminder(reminders: Reminder[]): Reminder | null {
  let best: Reminder | null = null;
  let bestMin = Infinity;
  for (const r of reminders) {
    if (!r.active) continue;
    const rMin = getCronMinutesOfDay(r.schedule_cron);
    if (rMin !== null && rMin < bestMin) {
      bestMin = rMin;
      best = r;
    }
  }
  return best;
}

interface NextUpCardProps {
  reminders: Reminder[];
  selectedDate: Date;
  onTakeNow: (reminder: Reminder) => void;
}

export function NextUpCard({ reminders, selectedDate, onTakeNow }: NextUpCardProps) {
  const t = useTheme();
  const [tick, setTick] = useState(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setTick(new Date()), 60_000);
    return () => clearInterval(id);
  }, []);

  const isToday = useMemo(() => {
    const now = new Date();
    return (
      selectedDate.getDate() === now.getDate() &&
      selectedDate.getMonth() === now.getMonth() &&
      selectedDate.getFullYear() === now.getFullYear()
    );
  }, [selectedDate]);

  const nowMinutes = tick.getHours() * 60 + tick.getMinutes();
  const next = isToday ? findNextReminder(reminders, nowMinutes) : null;
  const allPast = isToday && !next;

  if (!isToday) return null;

  const meta = next ? (TYPE_META[next.type] ?? TYPE_META.custom) : null;
  const time = next ? formatScheduleTime(next.schedule_cron) : '';
  const nextMin = next ? getCronMinutesOfDay(next.schedule_cron) : null;
  const countdown = nextMin !== null ? formatCountdown(nextMin - nowMinutes) : '';

  if (allPast) {
    const tomorrow = findFirstReminder(reminders);
    const tomorrowTime = tomorrow ? formatScheduleTime(tomorrow.schedule_cron) : '';
    return (
      <View style={[s.card, { backgroundColor: t.surface }]}>
        <View style={s.doneRow}>
          <Ionicons name="checkmark-circle" size={22} color={colors.jade} />
          <Text style={[s.doneText, { color: t.text }]}>All caught up</Text>
        </View>
        {tomorrow && (
          <Text style={[s.tomorrowText, { color: t.textSub }]}>
            Next: {tomorrow.label} · Tomorrow {tomorrowTime}
          </Text>
        )}
      </View>
    );
  }

  if (!next || !meta) return null;

  return (
    <View style={[s.card, { backgroundColor: t.surface }]}>
      <Text style={[s.heading, { color: t.textSub }]}>Next Up</Text>
      <View style={s.body}>
        <IconChip icon={meta.icon} tint={meta.tint} size={40} />
        <View style={s.info}>
          <Text style={[s.label, { color: t.text }]} numberOfLines={1}>
            {next.label}
          </Text>
          <Text style={[s.timeLine, { color: t.textSub }]}>
            {time}
            {countdown ? ` · ${countdown}` : ''}
          </Text>
        </View>
        <Pressable
          style={[s.takeBtn, { backgroundColor: withAlpha(colors.jade, t.isDark ? 0.20 : 0.12) }]}
          onPress={() => onTakeNow(next)}
          accessibilityLabel={`Take ${next.label} now`}
        >
          <Text style={[s.takeBtnText, { color: colors.jade }]}>Take Now</Text>
        </Pressable>
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  card: {
    borderRadius: borderRadius.xl,
    padding: spacing[4],
    gap: spacing[2],
  },
  heading: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  body: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
  },
  info: {
    flex: 1,
    gap: 2,
  },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
  timeLine: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
  },
  takeBtn: {
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[2],
    borderRadius: borderRadius.full,
  },
  takeBtnText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: '700',
  },
  doneRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
  },
  doneText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
  tomorrowText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    paddingLeft: 30,
  },
});
