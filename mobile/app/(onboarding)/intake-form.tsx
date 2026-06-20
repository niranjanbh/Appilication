import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useThemePreference } from '../../lib/theme-context';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { borderRadius, colors, fontFamily, fontSize, spacing , withAlpha } from '../../lib/design-tokens';

const GENDER_OPTIONS           = [
  { value: 'male',   label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other',  label: 'Prefer not to say' },
];
const SYMPTOM_DURATION_OPTIONS = [
  { value: 'less_than_3_months', label: 'Less than 3 months' },
  { value: '3_to_6_months',      label: '3 – 6 months' },
  { value: 'more_than_6_months', label: 'More than 6 months' },
  { value: 'more_than_2_years',  label: 'More than 2 years' },
];
const PREVIOUS_DIAGNOSIS_OPTIONS = [
  { value: 'yes_diagnosed', label: 'Yes, I have a diagnosis' },
  { value: 'yes_suspected', label: 'Yes, it was suspected but not confirmed' },
  { value: 'no',            label: 'No previous diagnosis' },
];
const PREVIOUS_TREATMENT_OPTIONS = [
  { value: 'yes_currently',  label: 'Yes, currently on treatment' },
  { value: 'yes_previously', label: 'Yes, previously treated' },
  { value: 'no',             label: 'No treatment yet' },
];

const TOTAL_STEPS = 4;
const STEP = 2;

// ─── Option group ─────────────────────────────────────────────────────────────

interface OptionGroupProps {
  label: string;
  options: { value: string; label: string }[];
  selected: string | null;
  onSelect: (v: string) => void;
  isDark: boolean;
}

function OptionGroup({ label, options, selected, onSelect, isDark }: OptionGroupProps) {
  const textPri = isDark ? colors.ivoryText     : colors.ink;
  const textSub = isDark ? colors.stoneDim : colors.stone;
  const cardBg  = isDark ? colors.forestSurface : colors.white;
  const cardBdr = isDark ? 'rgba(255,255,255,0.07)' : colors.borderLight;

  return (
    <View style={g.container}>
      <Text style={[g.label, { color: textPri }]}>{label}</Text>
      {options.map(opt => {
        const active = selected === opt.value;
        return (
          <Pressable
            key={opt.value}
            style={[
              g.option,
              {
                backgroundColor: active
                  ? isDark ? colors.jade  : colors.ivory
                  : cardBg,
                borderColor: active ? colors.jade : cardBdr,
              },
            ]}
            onPress={() => onSelect(opt.value)}
            accessibilityLabel={opt.label}
            accessibilityState={{ selected: active }}
          >
            <View style={[g.radio, { borderColor: active ? colors.jade : textSub, backgroundColor: active ? colors.jade : 'transparent' }]} />
            <Text style={[g.optionText, { color: active ? (isDark ? colors.ivoryText : colors.ink) : textPri, fontWeight: active ? '600' : '400' }]}>
              {opt.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const g = StyleSheet.create({
  container: { marginBottom: spacing[6] },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
    marginBottom: spacing[3],
  },
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    paddingVertical: spacing[3],
    paddingHorizontal: spacing[4],
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    marginBottom: spacing[2],
    boxShadow: '0 2px 6px rgba(0,0,0,0.04)',
  },
  radio: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 2,
  },
  optionText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
  },
});

// ─── Main screen ──────────────────────────────────────────────────────────────

export default function IntakeFormScreen() {
  const router  = useRouter();
  const isDark  = useThemePreference().colorScheme === 'dark';
  const params  = useLocalSearchParams<{ conditions?: string }>();

  const [gender,    setGender]    = useState<string | null>(null);
  const [duration,  setDuration]  = useState<string | null>(null);
  const [diagnosis, setDiagnosis] = useState<string | null>(null);
  const [treatment, setTreatment] = useState<string | null>(null);

  const allAnswered = gender !== null && duration !== null && diagnosis !== null && treatment !== null;
  const canSkip     = gender !== null;

  const handleSkip = () => {
    router.push({ pathname: '/(onboarding)/consent', params: { conditions: params.conditions, gender, skipped_intake: 'true' } });
  };
  const handleContinue = () => {
    router.push({ pathname: '/(onboarding)/consent', params: { conditions: params.conditions, gender } });
  };

  const btnScale  = useSharedValue(1);
  const btnAnim   = useAnimatedStyle(() => ({ transform: [{ scale: btnScale.value }] }));
  const skipScale = useSharedValue(1);
  const skipAnim  = useAnimatedStyle(() => ({ transform: [{ scale: skipScale.value }] }));

  const bg      = isDark ? colors.forestInk  : colors.ivory;
  const textSub = isDark ? colors.stoneDim : colors.stone;

  return (
    <ScrollView style={[styles.flex, { backgroundColor: bg }]} contentContainerStyle={styles.container}>

      {/* Step progress */}
      <View style={styles.stepRow}>
        <View style={styles.progressTrack}>
          <View style={[styles.progressFill, { width: `${(STEP / TOTAL_STEPS) * 100}%` as never }]} />
        </View>
        <Text style={[styles.stepLabel, { color: textSub }]}>Step {STEP} of {TOTAL_STEPS}</Text>
      </View>

      {/* Header */}
      <View style={styles.header}>
        <Text style={[styles.title, { color: isDark ? colors.ivoryText : colors.ink }]}>A few quick questions</Text>
        <Text style={[styles.subtitle, { color: textSub }]}>Your doctor reviews these before your first consultation.</Text>
      </View>

      <OptionGroup label="Your gender *"                                        options={GENDER_OPTIONS}             selected={gender}    onSelect={setGender}    isDark={isDark} />
      <OptionGroup label="How long have you had these symptoms?"                options={SYMPTOM_DURATION_OPTIONS}   selected={duration}  onSelect={setDuration}  isDark={isDark} />
      <OptionGroup label="Have you been diagnosed with a related condition?" options={PREVIOUS_DIAGNOSIS_OPTIONS} selected={diagnosis} onSelect={setDiagnosis} isDark={isDark} />
      <OptionGroup label="Have you received treatment for this before?"         options={PREVIOUS_TREATMENT_OPTIONS} selected={treatment} onSelect={setTreatment} isDark={isDark} />

      <Animated.View style={btnAnim}>
        <Pressable
          style={[styles.button, !allAnswered && styles.buttonMuted]}
          onPress={handleContinue}
          onPressIn={() => { btnScale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
          onPressOut={() => { btnScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
          disabled={!allAnswered}
          accessibilityLabel="Continue"
        >
          <Text style={styles.buttonText}>Continue</Text>
        </Pressable>
      </Animated.View>

      <Animated.View style={skipAnim}>
        <Pressable
          style={[styles.skipBtn, !canSkip && styles.skipMuted, { borderColor: canSkip ? (isDark ? colors.jade : colors.forest) : colors.borderLight }]}
          onPress={handleSkip}
          onPressIn={() => { skipScale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
          onPressOut={() => { skipScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
          disabled={!canSkip}
          accessibilityLabel="Skip — speak to a coordinator directly"
        >
          <Text style={[styles.skipText, { color: canSkip ? (isDark ? colors.jade : colors.ink) : colors.borderLight }]}>
            Skip — speak to a coordinator directly
          </Text>
        </Pressable>
      </Animated.View>

      {!canSkip && (
        <Text style={[styles.skipHint, { color: textSub }]}>Select your gender above to enable skip</Text>
      )}

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
    paddingBottom: spacing[8],
  },

  stepRow: { gap: spacing[2], marginBottom: spacing[6] },
  progressTrack: {
    height: 4,
    backgroundColor: colors.borderLight,
    borderRadius: 2,
    overflow: 'hidden',
  },
  progressFill: {
    height: 4,
    backgroundColor: colors.jade,
    borderRadius: 2,
  },
  stepLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },

  header: { gap: spacing[2], marginBottom: spacing[6] },
  title: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    fontWeight: '600',
  },
  subtitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    lineHeight: 22,
  },

  button: {
    height: 56,
    backgroundColor: colors.forest,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing[3],
    boxShadow: `0 8px 16px ${withAlpha(colors.forest, 0.25)}`,
  },
  buttonMuted: { opacity: 0.40 },
  buttonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.ivoryText,
    fontWeight: '600',
  },

  skipBtn: {
    height: 52,
    borderWidth: 1.5,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
  },
  skipMuted:  { opacity: 0.40 },
  skipText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '500',
  },
  skipHint: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    textAlign: 'center',
    marginTop: spacing[2],
  },
});
