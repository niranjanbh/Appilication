import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

const GENDER_OPTIONS = [
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other', label: 'Prefer not to say' },
];

const SYMPTOM_DURATION_OPTIONS = [
  { value: 'less_than_3_months', label: 'Less than 3 months' },
  { value: '3_to_6_months', label: '3 – 6 months' },
  { value: 'more_than_6_months', label: 'More than 6 months' },
  { value: 'more_than_2_years', label: 'More than 2 years' },
];

const PREVIOUS_DIAGNOSIS_OPTIONS = [
  { value: 'yes_diagnosed', label: 'Yes, I have a diagnosis' },
  { value: 'yes_suspected', label: 'Yes, it was suspected but not confirmed' },
  { value: 'no', label: 'No previous diagnosis' },
];

const PREVIOUS_TREATMENT_OPTIONS = [
  { value: 'yes_currently', label: 'Yes, currently on treatment' },
  { value: 'yes_previously', label: 'Yes, previously treated' },
  { value: 'no', label: 'No treatment yet' },
];

interface OptionGroupProps {
  label: string;
  options: { value: string; label: string }[];
  selected: string | null;
  onSelect: (v: string) => void;
}

function OptionGroup({ label, options, selected, onSelect }: OptionGroupProps) {
  return (
    <View style={groupStyles.container}>
      <Text style={groupStyles.label}>{label}</Text>
      {options.map(opt => (
        <Pressable
          key={opt.value}
          style={[groupStyles.option, selected === opt.value && groupStyles.optionSelected]}
          onPress={() => onSelect(opt.value)}
          accessibilityLabel={opt.label}
          accessibilityState={{ selected: selected === opt.value }}
        >
          <View style={[groupStyles.radio, selected === opt.value && groupStyles.radioSelected]} />
          <Text style={[groupStyles.optionText, selected === opt.value && groupStyles.optionTextSelected]}>
            {opt.label}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}

const groupStyles = StyleSheet.create({
  container: { marginBottom: spacing[6] },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    fontWeight: '600',
    marginBottom: spacing[3],
  },
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    paddingVertical: spacing[3],
    paddingHorizontal: spacing[4],
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.stone,
    backgroundColor: colors.white,
    marginBottom: spacing[2],
  },
  optionSelected: { borderColor: colors.forest, backgroundColor: '#F0F5F2' },
  radio: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 2,
    borderColor: colors.stone,
  },
  radioSelected: { borderColor: colors.forest, backgroundColor: colors.forest },
  optionText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
  },
  optionTextSelected: { color: colors.forest, fontWeight: '500' },
});

export default function IntakeFormScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ conditions?: string }>();

  const [gender, setGender] = useState<string | null>(null);
  const [duration, setDuration] = useState<string | null>(null);
  const [diagnosis, setDiagnosis] = useState<string | null>(null);
  const [treatment, setTreatment] = useState<string | null>(null);

  const allAnswered = gender !== null && duration !== null && diagnosis !== null && treatment !== null;
  const canSkip = gender !== null;

  const handleSkip = () => {
    router.push({
      pathname: '/(onboarding)/consent',
      params: { conditions: params.conditions, gender, skipped_intake: 'true' },
    });
  };

  const handleContinue = () => {
    router.push({
      pathname: '/(onboarding)/consent',
      params: { conditions: params.conditions, gender },
    });
  };

  return (
    <ScrollView style={styles.flex} contentContainerStyle={styles.container}>
      <View style={styles.header}>
        <Text style={styles.step}>Step 2 of 4</Text>
        <Text style={styles.title}>A few quick questions</Text>
        <Text style={styles.subtitle}>
          Your doctor reviews these before your first consultation.
        </Text>
      </View>

      {/* Gender is always required — coordinator needs it even if intake is skipped */}
      <OptionGroup
        label="Your gender *"
        options={GENDER_OPTIONS}
        selected={gender}
        onSelect={setGender}
      />

      <OptionGroup
        label="How long have you had these symptoms?"
        options={SYMPTOM_DURATION_OPTIONS}
        selected={duration}
        onSelect={setDuration}
      />
      <OptionGroup
        label="Have you been diagnosed with a related condition before?"
        options={PREVIOUS_DIAGNOSIS_OPTIONS}
        selected={diagnosis}
        onSelect={setDiagnosis}
      />
      <OptionGroup
        label="Have you received treatment for this before?"
        options={PREVIOUS_TREATMENT_OPTIONS}
        selected={treatment}
        onSelect={setTreatment}
      />

      <Pressable
        style={[styles.button, !allAnswered && styles.buttonDisabled]}
        onPress={handleContinue}
        disabled={!allAnswered}
        accessibilityLabel="Continue"
      >
        <Text style={styles.buttonText}>Continue</Text>
      </Pressable>

      <Pressable
        style={[styles.skipButton, !canSkip && styles.skipButtonDisabled]}
        onPress={handleSkip}
        disabled={!canSkip}
        accessibilityLabel="Skip — speak to a coordinator directly"
      >
        <Text style={[styles.skipButtonText, !canSkip && styles.skipButtonTextDisabled]}>
          Skip — speak to a coordinator directly
        </Text>
      </Pressable>

      {!canSkip && (
        <Text style={styles.skipHint}>Select your gender above to enable skip</Text>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.ivory },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[12],
    paddingBottom: spacing[8],
  },
  header: { marginBottom: spacing[8], gap: spacing[2] },
  step: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    fontWeight: '500',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  title: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    color: colors.forest,
    fontWeight: '500',
  },
  subtitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    lineHeight: 22,
  },
  button: {
    backgroundColor: colors.forest,
    borderRadius: 8,
    paddingVertical: spacing[4],
    alignItems: 'center',
    marginTop: spacing[4],
  },
  buttonDisabled: { opacity: 0.4 },
  buttonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.ivory,
    fontWeight: '600',
  },
  skipButton: {
    borderWidth: 1.5,
    borderColor: colors.forest,
    borderRadius: 8,
    paddingVertical: spacing[3],
    alignItems: 'center',
    marginTop: spacing[3],
  },
  skipButtonDisabled: {
    borderColor: colors.stone,
  },
  skipButtonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.forest,
    fontWeight: '500',
  },
  skipButtonTextDisabled: {
    color: colors.stone,
  },
  skipHint: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    textAlign: 'center',
    marginTop: spacing[2],
  },
});