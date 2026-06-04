import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

const CONDITIONS = [
  { slug: 'thyroid', label: 'Thyroid' },
  { slug: 'pcos', label: 'PCOS' },
  { slug: 'weight-management', label: 'Weight management' },
  { slug: 'skin-and-hair', label: 'Skin & hair' },
  { slug: 'mens-intimate-health', label: "Men's intimate health" },
  { slug: 'hormones-trt', label: 'Hormones & TRT' },
  { slug: 'longevity', label: 'Longevity & energy' },
] as const;

export default function ConditionsScreen() {
  const router = useRouter();
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const toggle = (slug: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(slug)) next.delete(slug);
      else next.add(slug);
      return next;
    });
  };

  const handleContinue = () => {
    router.push({
      pathname: '/(onboarding)/intake-form',
      params: { conditions: [...selected].join(',') },
    });
  };

  return (
    <ScrollView style={styles.flex} contentContainerStyle={styles.container}>
      <View style={styles.header}>
        <Text style={styles.step}>Step 1 of 4</Text>
        <Text style={styles.title}>What are you here to address?</Text>
        <Text style={styles.subtitle}>Select all that apply. Your doctor will review these.</Text>
      </View>

      <View style={styles.grid}>
        {CONDITIONS.map(({ slug, label }) => {
          const active = selected.has(slug);
          return (
            <Pressable
              key={slug}
              style={[styles.chip, active && styles.chipActive]}
              onPress={() => toggle(slug)}
              accessibilityLabel={label}
              accessibilityState={{ selected: active }}
            >
              <Text style={[styles.chipText, active && styles.chipTextActive]}>{label}</Text>
            </Pressable>
          );
        })}
      </View>

      <View style={styles.footer}>
        <Pressable
          style={[styles.button, selected.size === 0 && styles.buttonDisabled]}
          onPress={handleContinue}
          disabled={selected.size === 0}
          accessibilityLabel="Continue"
        >
          <Text style={styles.buttonText}>Continue</Text>
        </Pressable>
      </View>
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
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[3],
    marginBottom: spacing[8],
  },
  chip: {
    borderWidth: 1.5,
    borderColor: colors.stone,
    borderRadius: 24,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[2],
    backgroundColor: colors.white,
  },
  chipActive: {
    borderColor: colors.forest,
    backgroundColor: colors.forest,
  },
  chipText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
  },
  chipTextActive: { color: colors.ivory },
  footer: { marginTop: 'auto' as never },
  button: {
    backgroundColor: colors.forest,
    borderRadius: 8,
    paddingVertical: spacing[4],
    alignItems: 'center',
  },
  buttonDisabled: { opacity: 0.4 },
  buttonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.ivory,
    fontWeight: '600',
  },
});
