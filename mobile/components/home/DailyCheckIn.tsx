import { Ionicons } from '@expo/vector-icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { GlassCard } from '../ui/GlassCard';
import { HapticPressable } from '../ui/HapticPressable';
import {
  borderRadius,
  colors,
  fontFamily,
  fontSize,
  spacing,
  tintSoft,
  withAlpha,
} from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';
import {
  getTodayCheckIn,
  submitCheckIn,
  type MoodLevel,
} from '../../lib/api/symptom-checkin';

interface MoodOption {
  level: MoodLevel;
  icon: React.ComponentProps<typeof Ionicons>['name'];
  label: string;
}

const MOOD_OPTIONS: MoodOption[] = [
  { level: 1, icon: 'sad-outline',          label: 'Rough' },
  { level: 2, icon: 'cloudy-outline',       label: 'Low' },
  { level: 3, icon: 'partly-sunny-outline', label: 'Okay' },
  { level: 4, icon: 'happy-outline',        label: 'Good' },
  { level: 5, icon: 'sunny-outline',        label: 'Great' },
];

const ENERGY_OPTIONS: MoodOption[] = [
  { level: 1, icon: 'battery-dead-outline',    label: 'Drained' },
  { level: 2, icon: 'battery-half-outline',    label: 'Low' },
  { level: 3, icon: 'battery-half-outline',    label: 'Moderate' },
  { level: 4, icon: 'battery-charging-outline', label: 'Energised' },
  { level: 5, icon: 'flash-outline',           label: 'Buzzing' },
];

function OptionChip({
  option,
  selected,
  onPress,
  isDark,
  tintName,
}: {
  option: MoodOption;
  selected: boolean;
  onPress: () => void;
  isDark: boolean;
  tintName: 'sage' | 'saffron';
}) {
  const pair = tintSoft[tintName];
  const activeBg = isDark ? pair.bgDark : pair.bgLight;
  const activeTint = isDark ? pair.tintDark : pair.tintLight;

  const bg = selected ? activeBg : 'transparent';
  const tint = selected
    ? activeTint
    : isDark
      ? withAlpha(colors.ivoryText, 0.4)
      : withAlpha(colors.stone, 0.6);

  return (
    <HapticPressable
      haptic="selection"
      onPress={onPress}
      scaleTo={0.9}
      accessibilityLabel={option.label}
      accessibilityState={{ selected }}
      containerStyle={styles.chipContainer}
      style={[
        styles.chip,
        {
          backgroundColor: bg,
          borderColor: selected ? withAlpha(activeTint, 0.3) : 'transparent',
        },
      ]}
    >
      <Ionicons name={option.icon} size={22} color={tint} />
      <Text style={[styles.chipLabel, { color: tint }]}>{option.label}</Text>
    </HapticPressable>
  );
}

export function DailyCheckIn() {
  const t = useTheme();
  const queryClient = useQueryClient();

  const [mood, setMood] = useState<MoodLevel | null>(null);
  const [energy, setEnergy] = useState<MoodLevel | null>(null);

  const { data: todayData, isLoading } = useQuery({
    queryKey: ['symptom-checkin-today'],
    queryFn: getTodayCheckIn,
    staleTime: 60_000,
  });

  const mutation = useMutation({
    mutationFn: submitCheckIn,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['symptom-checkin-today'] });
      setMood(null);
      setEnergy(null);
    },
  });

  const alreadyDone = todayData?.checked_in === true;
  const step: 'mood' | 'energy' | 'confirm' =
    mood == null ? 'mood' : energy == null ? 'energy' : 'confirm';

  if (isLoading) return null;

  if (alreadyDone) {
    const entry = todayData.entry;
    const moodEntry = entry ? MOOD_OPTIONS.find(o => o.level === entry.mood) : null;
    const energyEntry = entry ? ENERGY_OPTIONS.find(o => o.level === entry.energy) : null;

    return (
      <GlassCard>
        <View style={styles.doneRow}>
          <Ionicons name="checkmark-circle" size={20} color={t.success} />
          <Text style={[styles.doneText, { color: t.text }]}>Checked in today</Text>
        </View>
        {moodEntry && energyEntry && (
          <View style={styles.summaryRow}>
            <View style={styles.summaryChip}>
              <Ionicons name={moodEntry.icon} size={16} color={t.textSub} />
              <Text style={[styles.summaryLabel, { color: t.textSub }]}>{moodEntry.label}</Text>
            </View>
            <View style={[styles.summaryDot, { backgroundColor: t.textSub }]} />
            <View style={styles.summaryChip}>
              <Ionicons name={energyEntry.icon} size={16} color={t.textSub} />
              <Text style={[styles.summaryLabel, { color: t.textSub }]}>{energyEntry.label}</Text>
            </View>
          </View>
        )}
      </GlassCard>
    );
  }

  const question =
    step === 'mood'
      ? 'How are you feeling today?'
      : step === 'energy'
        ? "How's your energy?"
        : 'Ready to log it?';

  const options = step === 'mood' ? MOOD_OPTIONS : step === 'energy' ? ENERGY_OPTIONS : [];
  const tintName = step === 'mood' ? 'sage' as const : 'saffron' as const;

  return (
    <GlassCard>
      <View style={styles.inner}>
        <Text style={[styles.title, { color: t.text }]}>{question}</Text>

        {step !== 'confirm' && (
          <View style={styles.optionsRow}>
            {options.map(opt => (
              <OptionChip
                key={opt.level}
                option={opt}
                selected={step === 'mood' ? mood === opt.level : energy === opt.level}
                onPress={() => step === 'mood' ? setMood(opt.level) : setEnergy(opt.level)}
                isDark={t.isDark}
                tintName={tintName}
              />
            ))}
          </View>
        )}

        {step === 'confirm' && (
          <View style={styles.confirmRow}>
            <HapticPressable
              haptic="medium"
              scaleTo={0.95}
              onPress={() => {
                if (mood && energy) mutation.mutate({ mood, energy });
              }}
              accessibilityLabel="Submit daily check-in"
              style={[styles.submitBtn, { backgroundColor: t.primary }]}
            >
              <Text style={[styles.submitText, { color: t.isDark ? colors.forestInk : colors.white }]}>
                {mutation.isPending ? 'Saving…' : 'Log check-in'}
              </Text>
            </HapticPressable>
            <HapticPressable
              onPress={() => { setMood(null); setEnergy(null); }}
              accessibilityLabel="Reset check-in"
            >
              <Text style={[styles.resetText, { color: t.textSub }]}>Reset</Text>
            </HapticPressable>
          </View>
        )}

        {step !== 'mood' && step !== 'confirm' && (
          <HapticPressable
            onPress={() => { setMood(null); setEnergy(null); }}
            accessibilityLabel="Go back to mood selection"
          >
            <Text style={[styles.backText, { color: t.textSub }]}>← Back</Text>
          </HapticPressable>
        )}
      </View>
    </GlassCard>
  );
}

const styles = StyleSheet.create({
  inner: { gap: spacing[4] },
  title: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    fontWeight: '600',
  },
  optionsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: spacing[2],
  },
  chipContainer: { flex: 1 },
  chip: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing[3],
    borderRadius: borderRadius.xl,
    borderWidth: 1.5,
    gap: spacing[1],
  },
  chipLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '600',
    textAlign: 'center',
  },
  confirmRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[4],
  },
  submitBtn: {
    flex: 1,
    paddingVertical: spacing[3],
    borderRadius: borderRadius.xl,
    alignItems: 'center',
  },
  submitText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
  resetText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '500',
  },
  backText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    fontWeight: '500',
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
  summaryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
    marginTop: spacing[2],
  },
  summaryChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[1],
  },
  summaryLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
  },
  summaryDot: {
    width: 3,
    height: 3,
    borderRadius: 1.5,
  },
});
