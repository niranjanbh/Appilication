import { Ionicons } from '@expo/vector-icons';
import { useMemo, useState } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from 'react-native';
import { HapticPressable } from '../../ui/HapticPressable';
import { IconChip } from '../../ui/IconChip';
import {
  borderRadius,
  colors,
  fontFamily,
  fontSize,
  spacing,
  type TintName,
  withAlpha,
} from '../../../lib/design-tokens';
import { useTheme } from '../../../lib/theme';
import type { ReminderType } from '../../../types/wellness';
import type { ReminderListProps } from './ReminderList.types';

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

const TYPE_META: Record<ReminderType, { icon: IoniconName; tint: TintName; label: string }> = {
  water:      { icon: 'water-outline',         tint: 'blue',   label: 'Hydration' },
  supplement: { icon: 'leaf-outline',          tint: 'green',  label: 'Supplement' },
  medication: { icon: 'medical-outline',       tint: 'violet', label: 'Medication' },
  gym:        { icon: 'barbell-outline',       tint: 'amber',  label: 'Exercise' },
  custom:     { icon: 'notifications-outline', tint: 'blue',   label: 'Custom' },
};

const DAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

function formatScheduleTime(cron: string | null): string {
  if (!cron) return '';
  const parts = cron.split(' ');
  const hour = parts[1] ?? '8';
  const min  = (parts[0] ?? '0').padStart(2, '0');
  const h24  = parseInt(hour, 10);
  const ampm = h24 >= 12 ? 'PM' : 'AM';
  const h12  = h24 % 12 === 0 ? 12 : h24 % 12;
  return `${h12}:${min} ${ampm}`;
}

function formatFrequency(intervalMinutes: number | null, cron: string | null): string {
  if (intervalMinutes) return `Every ${intervalMinutes} min`;
  if (cron) return 'Every day';
  return 'As needed';
}

// ── Month calendar ─────────────────────────────────────────────────────────────

interface MonthCalendarProps {
  selectedDate: Date;
  onSelectDate: (date: Date) => void;
}

function MonthCalendar({ selectedDate, onSelectDate }: MonthCalendarProps) {
  const t = useTheme();
  const [viewDate, setViewDate] = useState(() => new Date(selectedDate.getFullYear(), selectedDate.getMonth(), 1));

  const year  = viewDate.getFullYear();
  const month = viewDate.getMonth();

  const daysInMonth  = new Date(year, month + 1, 0).getDate();
  const firstWeekday = new Date(year, month, 1).getDay();
  const today        = new Date();

  const cells: (number | null)[] = [
    ...Array<null>(firstWeekday).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];

  while (cells.length % 7 !== 0) cells.push(null);

  function prevMonth() {
    setViewDate(new Date(year, month - 1, 1));
  }
  function nextMonth() {
    setViewDate(new Date(year, month + 1, 1));
  }
  function selectDay(day: number) {
    onSelectDate(new Date(year, month, day));
  }

  const isSelectedDay = (day: number) =>
    day === selectedDate.getDate() &&
    month === selectedDate.getMonth() &&
    year === selectedDate.getFullYear();

  const isToday = (day: number) =>
    day === today.getDate() &&
    month === today.getMonth() &&
    year === today.getFullYear();

  return (
    <View style={[cal.container, { backgroundColor: t.surface }]}>
      {/* Month nav */}
      <View style={cal.header}>
        <Pressable onPress={prevMonth} accessibilityLabel="Previous month" hitSlop={8}>
          <Ionicons name="chevron-back" size={20} color={t.textSub} />
        </Pressable>
        <Text style={[cal.monthLabel, { color: t.text }]}>
          {MONTH_NAMES[month]} {year}
        </Text>
        <Pressable onPress={nextMonth} accessibilityLabel="Next month" hitSlop={8}>
          <Ionicons name="chevron-forward" size={20} color={t.textSub} />
        </Pressable>
      </View>

      {/* Day name row */}
      <View style={cal.dayNames}>
        {DAY_LABELS.map(d => (
          <Text key={d} style={[cal.dayName, { color: t.textSub }]}>{d}</Text>
        ))}
      </View>

      {/* Date grid */}
      {Array.from({ length: cells.length / 7 }, (_, row) => (
        <View key={row} style={cal.week}>
          {cells.slice(row * 7, row * 7 + 7).map((day, col) => {
            if (!day) return <View key={col} style={cal.cell} />;
            const selected = isSelectedDay(day);
            const todayMark = isToday(day);
            return (
              <Pressable
                key={col}
                style={[
                  cal.cell,
                  selected && { backgroundColor: colors.saffron, borderRadius: borderRadius.full },
                  !selected && todayMark && {
                    borderWidth: 1,
                    borderColor: colors.saffron,
                    borderRadius: borderRadius.full,
                  },
                ]}
                onPress={() => selectDay(day)}
                accessibilityLabel={`${MONTH_NAMES[month]} ${day}`}
              >
                <Text
                  style={[
                    cal.dayNum,
                    { color: selected ? colors.white : todayMark ? colors.saffron : t.text },
                    selected && { fontWeight: '700' },
                  ]}
                >
                  {day}
                </Text>
              </Pressable>
            );
          })}
        </View>
      ))}
    </View>
  );
}

const cal = StyleSheet.create({
  container: {
    borderRadius: borderRadius.xl,
    padding: spacing[4],
    marginBottom: spacing[4],
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing[3],
  },
  monthLabel: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.bodyLg,
    fontWeight: '600',
  },
  dayNames: {
    flexDirection: 'row',
    marginBottom: spacing[2],
  },
  dayName: {
    flex: 1,
    textAlign: 'center',
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  week:  { flexDirection: 'row' },
  cell: {
    flex: 1,
    aspectRatio: 1,
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 2,
  },
  dayNum: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
  },
});

// ── Reminder row ───────────────────────────────────────────────────────────────

interface ReminderRowProps {
  reminder: import('../../../types/wellness').Reminder;
  onEdit: (r: import('../../../types/wellness').Reminder) => void;
  onDelete: (r: import('../../../types/wellness').Reminder) => void;
}

function ReminderRow({ reminder, onEdit, onDelete }: ReminderRowProps) {
  const t      = useTheme();
  const meta   = TYPE_META[reminder.type] ?? TYPE_META.custom;
  const time   = formatScheduleTime(reminder.schedule_cron);
  const freq   = formatFrequency(reminder.schedule_interval_minutes ?? null, reminder.schedule_cron);
  const notifOn = reminder.notification_channels?.includes('push') ?? false;

  return (
    <HapticPressable
      haptic="selection"
      scaleTo={0.98}
      onLongPress={() => onEdit(reminder)}
      accessibilityLabel={`Reminder: ${reminder.label}`}
    >
      <View style={[row.container, { backgroundColor: t.surface }]}>
        <IconChip icon={meta.icon} tint={meta.tint} size={44} />

        <View style={row.body}>
          <Text style={[row.label, { color: t.text }]} numberOfLines={1}>
            {reminder.label}
          </Text>
          <View style={row.tags}>
            <View style={[row.freqTag, { backgroundColor: withAlpha(colors.sageDim, t.isDark ? 0.30 : 0.15) }]}>
              <Text style={[row.freqText, { color: t.isDark ? colors.ivoryText : colors.sage }]}>
                {freq}
              </Text>
            </View>
            {time ? (
              <Text style={[row.time, { color: t.textSub }]}>{time}</Text>
            ) : null}
          </View>
        </View>

        <Switch
          value={notifOn}
          trackColor={{
            false: t.isDark ? withAlpha(colors.stoneDim, 0.30) : colors.borderLight,
            true:  withAlpha(colors.jadeGlow, 0.50),
          }}
          thumbColor={notifOn ? colors.jadeGlow : (t.isDark ? colors.stoneDim : colors.white)}
          ios_backgroundColor={t.isDark ? withAlpha(colors.stoneDim, 0.30) : colors.borderLight}
          accessibilityLabel={`Remind me for ${reminder.label}`}
          onValueChange={() => onEdit(reminder)}
        />

        <Pressable
          onPress={() => onDelete(reminder)}
          hitSlop={8}
          accessibilityLabel={`Delete ${reminder.label}`}
        >
          <Ionicons name="trash-outline" size={16} color={t.textSub} />
        </Pressable>
      </View>
    </HapticPressable>
  );
}

const row = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    borderRadius: borderRadius.xl,
  },
  body: { flex: 1, gap: spacing[1] },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
  tags: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  freqTag: {
    borderRadius: borderRadius.full,
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
  },
  freqText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    fontWeight: '500',
  },
  time: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
  },
});

// ── ReminderList ───────────────────────────────────────────────────────────────

export function ReminderList({ reminders, selectedDate, onDateChange, onEdit, onDelete }: ReminderListProps) {
  const t = useTheme();

  const displayDate = useMemo(() => {
    const opts: Intl.DateTimeFormatOptions = { weekday: 'long', day: 'numeric', month: 'long' };
    return selectedDate.toLocaleDateString('en-IN', opts);
  }, [selectedDate]);

  return (
    <ScrollView
      showsVerticalScrollIndicator={false}
      contentContainerStyle={[list.scroll, { gap: spacing[3] }]}
    >
      <MonthCalendar selectedDate={selectedDate} onSelectDate={onDateChange} />

      <Text style={[list.dateHeading, { color: t.isDark ? colors.jadeGlow : colors.forest }]}>
        {displayDate}
      </Text>

      {reminders.length === 0 ? (
        <View style={list.empty}>
          <Ionicons name="alarm-outline" size={32} color={t.textSub} />
          <Text style={[list.emptyText, { color: t.textSub }]}>No reminders scheduled</Text>
        </View>
      ) : (
        reminders.map(r => (
          <ReminderRow key={r.id} reminder={r} onEdit={onEdit} onDelete={onDelete} />
        ))
      )}
    </ScrollView>
  );
}

const list = StyleSheet.create({
  scroll: { paddingHorizontal: spacing[4] },
  dateHeading: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h3,
    fontWeight: '600',
    paddingHorizontal: spacing[1],
  },
  empty: { alignItems: 'center', gap: spacing[3], paddingVertical: spacing[10] },
  emptyText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
  },
});
