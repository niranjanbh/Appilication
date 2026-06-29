import { Ionicons } from '@expo/vector-icons';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from 'react-native';
import ReanimatedSwipeable, { type SwipeableMethods, SwipeDirection } from 'react-native-gesture-handler/ReanimatedSwipeable';
import Animated, { interpolate, useAnimatedStyle, type SharedValue } from 'react-native-reanimated';
import { HapticPressable, triggerHaptic } from '../../ui/HapticPressable';
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
import { TAB_DOCK_CLEARANCE } from '../../ui/GlassTabBar';
import type { Reminder, ReminderType, WeekDaySummary } from '../../../types/wellness';
import type { ReminderListProps } from './ReminderList.types';
import { NextUpCard } from '../NextUpCard';
import { TodayProgressCard } from '../TodayProgressCard';

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

const TYPE_META: Record<ReminderType, { icon: IoniconName; tint: TintName; label: string }> = {
  water:      { icon: 'water-outline',         tint: 'blue',   label: 'Hydration' },
  supplement: { icon: 'leaf-outline',          tint: 'green',  label: 'Supplement' },
  medication: { icon: 'medical-outline',       tint: 'violet', label: 'Medication' },
  gym:        { icon: 'barbell-outline',       tint: 'amber',  label: 'Exercise' },
  custom:     { icon: 'notifications-outline', tint: 'blue',   label: 'Custom' },
};

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

const CAL_DAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const STRIP_DAY_LABELS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

// ── Helpers ───────────────────────────────────────────────────────────────────

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

function getCronHour(cron: string | null): number | null {
  if (!cron) return null;
  const h = parseInt(cron.split(' ')[1] ?? '', 10);
  return isNaN(h) ? null : h;
}

function cronFieldMatches(field: string, value: number, lo: number, hi: number): boolean {
  for (const part of field.split(',')) {
    let step = 1;
    let rng = part.trim();
    if (rng.includes('/')) {
      const [r, sp] = rng.split('/', 2);
      step = parseInt(sp ?? '1', 10);
      if (isNaN(step) || step <= 0) continue;
      rng = r ?? '';
    }
    let lo2: number, hi2: number;
    if (rng === '*') { lo2 = lo; hi2 = hi; }
    else if (rng.includes('-')) {
      const [a, b] = rng.split('-', 2);
      lo2 = parseInt(a ?? '', 10); hi2 = parseInt(b ?? '', 10);
      if (isNaN(lo2) || isNaN(hi2)) continue;
    } else {
      lo2 = hi2 = parseInt(rng, 10);
      if (isNaN(lo2)) continue;
    }
    if (lo2 <= value && value <= hi2 && (value - lo2) % step === 0) return true;
  }
  return false;
}

function matchesCronDate(cron: string | null, date: Date): boolean {
  if (!cron) return true;
  const parts = cron.split(' ');
  if (parts.length !== 5) return true; // malformed → show it
  const domF = parts[2] ?? '*';
  const monthF = parts[3] ?? '*';
  const dowF = parts[4] ?? '*';

  const dom = date.getDate();
  const month = date.getMonth() + 1;
  const jsDay = date.getDay(); // 0=Sun

  const monthOk = cronFieldMatches(monthF, month, 1, 12);
  if (!monthOk) return false;

  const domWild = domF === '*';
  const dowWild = dowF === '*';
  const domOk = domWild || cronFieldMatches(domF, dom, 1, 31);
  // dow: cron 0 and 7 are both Sunday
  const dowOk = dowWild || cronFieldMatches(dowF, jsDay, 0, 6) || (jsDay === 0 && cronFieldMatches(dowF, 7, 0, 7));

  // Standard cron: if both dom and dow are restricted, OR them; otherwise AND
  if (!domWild && !dowWild) return domOk || dowOk;
  return domOk && dowOk;
}

// ── Time-of-day grouping ──────────────────────────────────────────────────────

type TimeOfDay = 'morning' | 'afternoon' | 'evening' | 'anytime';

const SECTION_ORDER: TimeOfDay[] = ['morning', 'afternoon', 'evening', 'anytime'];

const SECTION_META: Record<TimeOfDay, { label: string; emoji: string }> = {
  morning:   { label: 'Morning',   emoji: '☀️' },   // ☀️
  afternoon: { label: 'Afternoon', emoji: '🌤️' }, // 🌤️
  evening:   { label: 'Evening',   emoji: '🌙' },   // 🌙
  anytime:   { label: 'As Needed', emoji: '⏱️' },   // ⏱️
};

interface TimeSection {
  key: TimeOfDay;
  label: string;
  emoji: string;
  reminders: Reminder[];
}

function getTimeOfDay(cron: string | null): TimeOfDay {
  const hour = getCronHour(cron);
  if (hour === null) return 'anytime';
  if (hour < 12) return 'morning';
  if (hour < 17) return 'afternoon';
  return 'evening';
}

function groupByTimeOfDay(reminders: Reminder[]): TimeSection[] {
  const groups: Record<TimeOfDay, Reminder[]> = {
    morning: [], afternoon: [], evening: [], anytime: [],
  };
  for (const r of reminders) {
    groups[getTimeOfDay(r.schedule_cron)].push(r);
  }
  for (const key of SECTION_ORDER) {
    groups[key].sort((a, b) => (getCronHour(a.schedule_cron) ?? 99) - (getCronHour(b.schedule_cron) ?? 99));
  }
  return SECTION_ORDER
    .filter(key => groups[key].length > 0)
    .map(key => ({ key, ...SECTION_META[key], reminders: groups[key] }));
}

// ── Temporal state (today awareness) ──────────────────────────────────────────

type TemporalState = 'past' | 'overdue' | 'upcoming' | 'future';

function getCronMinutes(cron: string | null): number | null {
  if (!cron) return null;
  const parts = cron.split(' ');
  const h = parseInt(parts[1] ?? '', 10);
  const m = parseInt(parts[0] ?? '', 10);
  if (isNaN(h) || isNaN(m)) return null;
  return h * 60 + m;
}

function getTemporalState(cron: string | null, intervalMinutes: number | null, selectedDate: Date, now: Date): TemporalState {
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const selStart   = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), selectedDate.getDate());
  if (selStart < todayStart) return 'past';
  if (selStart > todayStart) return 'future';
  if (cron === null) {
    // Interval reminder: always relevant when shown on today's view. The date
    // checks above already cover past/future days, so treat it as upcoming.
    void intervalMinutes;
    return 'upcoming';
  }
  const cronMin = getCronMinutes(cron);
  if (cronMin === null) return 'future';
  const nowMin = now.getHours() * 60 + now.getMinutes();
  if (cronMin < nowMin) return 'overdue';
  if (cronMin - nowMin <= 60) return 'upcoming';
  return 'future';
}

// ── Week strip ────────────────────────────────────────────────────────────────

function getWeekDays(anchor: Date): Date[] {
  const dow = anchor.getDay();
  const sun = new Date(anchor.getFullYear(), anchor.getMonth(), anchor.getDate() - dow);
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(sun);
    d.setDate(sun.getDate() + i);
    return d;
  });
}

function isSameDay(a: Date, b: Date): boolean {
  return a.getDate() === b.getDate() && a.getMonth() === b.getMonth() && a.getFullYear() === b.getFullYear();
}

function formatDayIso(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function getDotColor(daySummary: WeekDaySummary | undefined, isFuture: boolean): string | null {
  if (!daySummary || daySummary.total === 0 || isFuture) return null;
  if (daySummary.completed >= daySummary.total) return colors.jade;
  if (daySummary.completed > 0) return colors.saffron;
  return colors.terracotta;
}

interface WeekStripProps {
  selectedDate: Date;
  onSelectDate: (date: Date) => void;
  onToggleCalendar: () => void;
  calendarExpanded: boolean;
  weekSummary?: WeekDaySummary[] | null;
}

function WeekStrip({ selectedDate, onSelectDate, onToggleCalendar, calendarExpanded, weekSummary }: WeekStripProps) {
  const t = useTheme();
  const [today, setToday] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setToday(new Date()), 60_000);
    return () => clearInterval(id);
  }, []);
  const weekDays = useMemo(() => getWeekDays(selectedDate), [selectedDate]);

  const summaryMap = useMemo(() => {
    if (!weekSummary) return new Map<string, WeekDaySummary>();
    return new Map(weekSummary.map(d => [d.date, d]));
  }, [weekSummary]);

  function shiftWeek(delta: number) {
    const next = new Date(selectedDate);
    next.setDate(next.getDate() + delta * 7);
    onSelectDate(next);
  }

  return (
    <View style={[ws.container, { backgroundColor: t.surface }]}>
      <View style={ws.header}>
        <Pressable onPress={() => shiftWeek(-1)} hitSlop={8} accessibilityLabel="Previous week">
          <Ionicons name="chevron-back" size={18} color={t.textSub} />
        </Pressable>
        <Text style={[ws.monthLabel, { color: t.text }]}>
          {MONTH_NAMES[selectedDate.getMonth()]} {selectedDate.getFullYear()}
        </Text>
        <View style={ws.headerRight}>
          <Pressable onPress={() => shiftWeek(1)} hitSlop={8} accessibilityLabel="Next week">
            <Ionicons name="chevron-forward" size={18} color={t.textSub} />
          </Pressable>
          <Pressable onPress={onToggleCalendar} hitSlop={8} accessibilityLabel={calendarExpanded ? 'Collapse calendar' : 'Expand calendar'}>
            <Ionicons name={calendarExpanded ? 'chevron-up' : 'calendar-outline'} size={18} color={t.textSub} />
          </Pressable>
        </View>
      </View>

      <View style={ws.row}>
        {weekDays.map((day, i) => {
          const selected = isSameDay(day, selectedDate);
          const todayMark = isSameDay(day, today);
          const isFuture = day > today;
          const dotColor = getDotColor(summaryMap.get(formatDayIso(day)), isFuture);
          return (
            <Pressable
              key={i}
              style={ws.dayCol}
              onPress={() => onSelectDate(day)}
              accessibilityLabel={`${STRIP_DAY_LABELS[day.getDay()]} ${day.getDate()}`}
            >
              <Text style={[ws.dayLabel, { color: t.textSub }]}>
                {STRIP_DAY_LABELS[day.getDay()]}
              </Text>
              <View
                style={[
                  ws.dayCircle,
                  selected && { backgroundColor: colors.saffron },
                  !selected && todayMark && { borderWidth: 1.5, borderColor: colors.saffron },
                ]}
              >
                <Text
                  style={[
                    ws.dayNum,
                    { color: selected ? colors.white : todayMark ? colors.saffron : t.text },
                    selected && { fontWeight: '700' },
                  ]}
                >
                  {day.getDate()}
                </Text>
              </View>
              {dotColor ? (
                <View style={[ws.dot, { backgroundColor: dotColor }]} />
              ) : (
                <View style={ws.dotSpacer} />
              )}
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const ws = StyleSheet.create({
  container: {
    borderRadius: borderRadius.xl,
    padding: spacing[4],
    paddingBottom: spacing[3],
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing[3],
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[4],
  },
  monthLabel: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  dayCol: {
    flex: 1,
    alignItems: 'center',
    gap: spacing[1],
  },
  dayLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  dayCircle: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dayNum: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: '500',
  },
  dot: {
    width: 5,
    height: 5,
    borderRadius: 2.5,
  },
  dotSpacer: {
    width: 5,
    height: 5,
  },
});

// ── Month calendar (expandable) ───────────────────────────────────────────────

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

  const isSelectedDay = (day: number) =>
    day === selectedDate.getDate() && month === selectedDate.getMonth() && year === selectedDate.getFullYear();
  const isToday = (day: number) =>
    day === today.getDate() && month === today.getMonth() && year === today.getFullYear();

  return (
    <View style={[cal.container, { backgroundColor: t.surface }]}>
      <View style={cal.header}>
        <Pressable onPress={() => setViewDate(new Date(year, month - 1, 1))} accessibilityLabel="Previous month" hitSlop={8}>
          <Ionicons name="chevron-back" size={20} color={t.textSub} />
        </Pressable>
        <Text style={[cal.monthLabel, { color: t.text }]}>
          {MONTH_NAMES[month]} {year}
        </Text>
        <Pressable onPress={() => setViewDate(new Date(year, month + 1, 1))} accessibilityLabel="Next month" hitSlop={8}>
          <Ionicons name="chevron-forward" size={20} color={t.textSub} />
        </Pressable>
      </View>

      <View style={cal.dayNames}>
        {CAL_DAY_LABELS.map(d => (
          <Text key={d} style={[cal.dayName, { color: t.textSub }]}>{d}</Text>
        ))}
      </View>

      {Array.from({ length: cells.length / 7 }, (_, r) => (
        <View key={r} style={cal.week}>
          {cells.slice(r * 7, r * 7 + 7).map((day, col) => {
            if (!day) return <View key={col} style={cal.cell} />;
            const selected = isSelectedDay(day);
            const todayMark = isToday(day);
            return (
              <Pressable
                key={col}
                style={[
                  cal.cell,
                  selected && { backgroundColor: colors.saffron, borderRadius: borderRadius.full },
                  !selected && todayMark && { borderWidth: 1, borderColor: colors.saffron, borderRadius: borderRadius.full },
                ]}
                onPress={() => onSelectDate(new Date(year, month, day))}
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
  week: { flexDirection: 'row' },
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

// ── Section header ────────────────────────────────────────────────────────────

function SectionHeader({ label, emoji, isDark }: { label: string; emoji: string; isDark: boolean }) {
  return (
    <View style={sec.container}>
      <Text style={sec.emoji}>{emoji}</Text>
      <Text style={[sec.label, { color: isDark ? colors.stoneDim : colors.stone }]}>
        {label}
      </Text>
    </View>
  );
}

const sec = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
    paddingHorizontal: spacing[1],
    paddingTop: spacing[2],
  },
  emoji: { fontSize: 14 },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
});

// ── Reminder row ──────────────────────────────────────────────────────────────

interface ReminderRowProps {
  reminder: Reminder;
  temporalState: TemporalState;
  onEdit: (r: Reminder) => void;
  onAdherence: (r: Reminder) => void;
  onDelete: (r: Reminder) => void;
  onToggle: (r: Reminder) => void;
  onTakeNow: (r: Reminder) => void;
}

function getAdherenceColor(rate: number): string {
  if (rate >= 0.90) return colors.jade;
  if (rate >= 0.70) return colors.saffron;
  return colors.terracotta;
}

function isRxReminder(metadata: Record<string, unknown> | null): boolean {
  if (!metadata) return false;
  return !!(metadata.care_plan_id || metadata.prescription_id);
}

// Build a short, type-specific detail string from the reminder's metadata,
// e.g. "2 glasses", "1 tablet · with food", "45 min · Strength".
function formatDetail(type: ReminderType, metadata: Record<string, unknown> | null): string {
  if (!metadata) return '';
  const parts: string[] = [];
  switch (type) {
    case 'water': {
      const amount = metadata.amount;
      if (amount) parts.push(`${amount} ${metadata.unit === 'ml' ? 'ml' : 'glasses'}`);
      break;
    }
    case 'supplement':
    case 'medication': {
      if (metadata.dosage) parts.push(String(metadata.dosage));
      if (metadata.with_food === true) parts.push('with food');
      break;
    }
    case 'gym': {
      if (metadata.duration_minutes) parts.push(`${metadata.duration_minutes} min`);
      if (metadata.activity) parts.push(String(metadata.activity));
      break;
    }
    case 'custom': {
      if (metadata.notes) parts.push(String(metadata.notes));
      break;
    }
  }
  return parts.join(' · ');
}

const SWIPE_ACTION_WIDTH = 80;

function SwipeLeftAction({ progress }: { progress: SharedValue<number> }) {
  const animStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: interpolate(progress.value, [0, 1], [-SWIPE_ACTION_WIDTH, 0]) }],
    opacity: interpolate(progress.value, [0, 0.5, 1], [0, 0.8, 1]),
  }));

  return (
    <Animated.View style={[swipe.actionContainer, animStyle]}>
      <View style={swipe.actionContent}>
        <Ionicons name="checkmark" size={22} color={colors.white} />
        <Text style={swipe.actionText}>Taken</Text>
      </View>
    </Animated.View>
  );
}

function ReminderRow({ reminder, temporalState, onEdit, onAdherence, onDelete, onToggle, onTakeNow }: ReminderRowProps) {
  const t    = useTheme();
  const meta = TYPE_META[reminder.type] ?? TYPE_META.custom;
  const time = formatScheduleTime(reminder.schedule_cron);
  const freq = formatFrequency(reminder.schedule_interval_minutes ?? null, reminder.schedule_cron);
  const swipeRef = useRef<SwipeableMethods>(null);

  const isPast     = temporalState === 'past';
  const isOverdue  = temporalState === 'overdue';
  const isUpcoming = temporalState === 'upcoming';

  const hasAdherence = reminder.adherence_rate > 0;
  const adherencePct = Math.round(reminder.adherence_rate * 100);
  const rx = isRxReminder(reminder.metadata);
  const detail = formatDetail(reminder.type, reminder.metadata);

  const handleSwipeOpen = useCallback((direction: SwipeDirection) => {
    if (direction === SwipeDirection.LEFT) {
      triggerHaptic('medium');
      onTakeNow(reminder);
      setTimeout(() => swipeRef.current?.close(), 300);
    }
  }, [reminder, onTakeNow]);

  const renderLeftActions = useCallback(
    (progress: SharedValue<number>) => <SwipeLeftAction progress={progress} />,
    [],
  );

  const content = (
      <HapticPressable
        haptic="selection"
        scaleTo={0.98}
        onPress={() => onAdherence(reminder)}
        onLongPress={() => onEdit(reminder)}
        accessibilityLabel={`Reminder: ${reminder.label}${time ? ` at ${time}` : ''}${isOverdue ? ', overdue' : ''}${hasAdherence ? `, ${adherencePct}% adherence` : ''}. Tap to log, long-press to edit.`}
      >
        <View
          style={[
            row.container,
            { backgroundColor: t.surface },
            isPast && { opacity: 0.55 },
            isOverdue && { opacity: 0.75, borderLeftWidth: 3, borderLeftColor: t.isDark ? colors.terracottaSoft : colors.terracotta },
            isUpcoming && { borderLeftWidth: 3, borderLeftColor: colors.saffron },
          ]}
        >
          {time ? (
            <View style={row.timeBlock}>
              <Text
                style={[
                  row.timeText,
                  { color: isUpcoming ? colors.saffron : isOverdue ? (t.isDark ? colors.terracottaSoft : colors.terracotta) : t.text },
                ]}
              >
                {time}
              </Text>
            </View>
          ) : null}

          <IconChip icon={meta.icon} tint={meta.tint} size={38} />

          <View style={row.body}>
            <View style={row.topLine}>
              <Text style={[row.label, { color: t.text }]} numberOfLines={1}>
                {reminder.label}
              </Text>
              {hasAdherence && (
                <Text style={[row.adherenceText, { color: getAdherenceColor(reminder.adherence_rate) }]}>
                  {adherencePct}%
                </Text>
              )}
            </View>
            <View style={row.bottomLine}>
              <Text style={[row.freq, { color: t.textSub }]} numberOfLines={1}>
                {detail ? `${freq} · ${detail}` : freq}
              </Text>
              {rx && (
                <View style={[row.rxBadge, { backgroundColor: withAlpha(colors.jade, t.isDark ? 0.20 : 0.10) }]}>
                  <Text style={[row.rxText, { color: t.isDark ? colors.jadeGlow : colors.jade }]}>Rx</Text>
                </View>
              )}
            </View>
          </View>

          {/* Claim the touch so toggling / deleting / editing never bubbles up to
              the row's adherence onPress. */}
          <View
            style={row.controls}
            onStartShouldSetResponder={() => true}
            onResponderRelease={() => {}}
          >
            <Switch
              value={reminder.active}
              trackColor={{
                false: t.isDark ? withAlpha(colors.stoneDim, 0.30) : colors.borderLight,
                true:  withAlpha(colors.jadeGlow, 0.50),
              }}
              thumbColor={reminder.active ? colors.jadeGlow : (t.isDark ? colors.stoneDim : colors.white)}
              ios_backgroundColor={t.isDark ? withAlpha(colors.stoneDim, 0.30) : colors.borderLight}
              accessibilityLabel={`${reminder.active ? 'Disable' : 'Enable'} ${reminder.label}`}
              onValueChange={() => onToggle(reminder)}
            />

            <Pressable
              onPress={() => onEdit(reminder)}
              hitSlop={8}
              accessibilityLabel={`Edit ${reminder.label}`}
            >
              <Ionicons name="create-outline" size={16} color={t.textSub} />
            </Pressable>

            <Pressable
              onPress={() => onDelete(reminder)}
              hitSlop={8}
              accessibilityLabel={`Delete ${reminder.label}`}
            >
              <Ionicons name="trash-outline" size={16} color={t.textSub} />
            </Pressable>
          </View>
        </View>
      </HapticPressable>
  );

  // Past rows are read-only history — no swipe-to-take affordance.
  if (isPast) {
    return content;
  }

  return (
    <ReanimatedSwipeable
      ref={swipeRef}
      friction={2}
      leftThreshold={40}
      overshootLeft={false}
      renderLeftActions={renderLeftActions}
      onSwipeableOpen={handleSwipeOpen}
      containerStyle={swipe.swipeContainer}
    >
      {content}
    </ReanimatedSwipeable>
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
  timeBlock: {
    minWidth: 64,
  },
  timeText: {
    fontFamily: fontFamily.data,
    fontSize: fontSize.body,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  body: { flex: 1, gap: 2 },
  controls: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
  },
  topLine: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
  },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
    flexShrink: 1,
  },
  adherenceText: {
    fontFamily: fontFamily.data,
    fontSize: fontSize.caption,
    fontWeight: '700',
  },
  bottomLine: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
  },
  freq: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    flexShrink: 1,
  },
  rxBadge: {
    paddingHorizontal: spacing[2],
    paddingVertical: 1,
    borderRadius: borderRadius.full,
  },
  rxText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
});

const swipe = StyleSheet.create({
  swipeContainer: {
    borderRadius: borderRadius.xl,
    overflow: 'hidden',
  },
  actionContainer: {
    width: SWIPE_ACTION_WIDTH,
    backgroundColor: colors.jade,
    justifyContent: 'center',
    alignItems: 'center',
    borderTopLeftRadius: borderRadius.xl,
    borderBottomLeftRadius: borderRadius.xl,
  },
  actionContent: {
    alignItems: 'center',
    gap: 2,
  },
  actionText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    color: colors.white,
  },
});

// ── ReminderList ──────────────────────────────────────────────────────────────

export function ReminderList({ reminders, selectedDate, onDateChange, onEdit, onAdherence, onDelete, onToggle, onTakeNow, dailySummary, weekSummary, refreshControl }: ReminderListProps) {
  const t = useTheme();
  const [calendarExpanded, setCalendarExpanded] = useState(false);
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(id);
  }, []);

  const displayDate = useMemo(() => {
    const opts: Intl.DateTimeFormatOptions = { weekday: 'long', day: 'numeric', month: 'long' };
    return selectedDate.toLocaleDateString('en-IN', opts);
  }, [selectedDate]);

  const filtered = useMemo(
    () => reminders.filter(r => matchesCronDate(r.schedule_cron, selectedDate)),
    [reminders, selectedDate],
  );

  const sections = useMemo(() => groupByTimeOfDay(filtered), [filtered]);

  function handleCalendarSelect(date: Date) {
    onDateChange(date);
    setCalendarExpanded(false);
  }

  return (
    <ScrollView
      showsVerticalScrollIndicator={false}
      contentContainerStyle={list.scroll}
      refreshControl={refreshControl}
    >
      {dailySummary && <TodayProgressCard summary={dailySummary} />}



      <WeekStrip
        selectedDate={selectedDate}
        onSelectDate={onDateChange}
        onToggleCalendar={() => setCalendarExpanded(v => !v)}
        calendarExpanded={calendarExpanded}
        weekSummary={weekSummary}
      />

      {calendarExpanded && (
        <MonthCalendar selectedDate={selectedDate} onSelectDate={handleCalendarSelect} />
      )}
      <NextUpCard
          reminders={filtered}
          selectedDate={selectedDate}
          onTakeNow={onTakeNow}
      />
      <Text style={[list.dateHeading, { color: t.isDark ? colors.jadeGlow : colors.forest }]}>
        {displayDate}
      </Text>

      {sections.length === 0 ? (
        <View style={list.empty}>
          <Ionicons name="alarm-outline" size={32} color={t.textSub} />
          <Text style={[list.emptyText, { color: t.textSub }]}>No reminders for this day</Text>
        </View>
      ) : (
        sections.map(section => (
          <View key={section.key} style={list.section}>
            <SectionHeader label={section.label} emoji={section.emoji} isDark={t.isDark} />
            <View style={list.sectionRows}>
              {section.reminders.map(r => (
                <ReminderRow
                  key={r.id}
                  reminder={r}
                  temporalState={getTemporalState(r.schedule_cron, r.schedule_interval_minutes ?? null, selectedDate, now)}
                  onEdit={onEdit}
                  onAdherence={onAdherence}
                  onDelete={onDelete}
                  onToggle={onToggle}
                  onTakeNow={onTakeNow}
                />
              ))}
            </View>
          </View>
        ))
      )}
    </ScrollView>
  );
}

const list = StyleSheet.create({
  scroll: {
    paddingHorizontal: spacing[4],
    paddingBottom: TAB_DOCK_CLEARANCE + 72,
    gap: spacing[3],
  },
  dateHeading: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h3,
    fontWeight: '600',
    paddingHorizontal: spacing[1],
  },
  section: {
    gap: spacing[2],
  },
  sectionRows: {
    gap: spacing[2],
  },
  empty: {
    alignItems: 'center',
    gap: spacing[3],
    paddingVertical: spacing[10],
  },
  emptyText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
  },
});
