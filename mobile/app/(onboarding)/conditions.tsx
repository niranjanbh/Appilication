import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useThemePreference } from '../../lib/theme-context';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { borderRadius, colors, fontFamily, fontSize, spacing , withAlpha } from '../../lib/design-tokens';

const CONDITIONS = [
  { slug: 'thyroid',             label: 'Thyroid',              icon: '🦋' },
  { slug: 'pcos',                label: 'PCOS',                 icon: '🌿' },
  { slug: 'weight-management',   label: 'Weight management',    icon: '⚖️' },
  { slug: 'skin-and-hair',       label: 'Skin & hair',          icon: '✨' },
  { slug: 'mens-intimate-health', label: "Men's intimate health", icon: '🛡️' },
  { slug: 'hormones-trt',        label: 'Hormones & TRT',       icon: '⚡' },
  { slug: 'longevity',           label: 'Longevity & energy',   icon: '🌱' },
] as const;

const TOTAL_STEPS = 4;
const STEP = 1;

export default function ConditionsScreen() {
  const router  = useRouter();
  const isDark  = useThemePreference().colorScheme === 'dark';
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

  const btnScale = useSharedValue(1);
  const btnAnim  = useAnimatedStyle(() => ({ transform: [{ scale: btnScale.value }] }));

  const bg      = isDark ? colors.midnight     : colors.skyMist;
  const textPri = isDark ? colors.white        : colors.navyDeep;
  const textSub = isDark ? colors.slateText    : colors.coolGray;

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
        <Text style={[styles.title, { color: textPri }]}>What are you here to address?</Text>
        <Text style={[styles.subtitle, { color: textSub }]}>Select all that apply. Your doctor will review these.</Text>
      </View>

      {/* Condition chips */}
      <View style={styles.grid}>
        {CONDITIONS.map(({ slug, label, icon }) => {
          const active = selected.has(slug);
          return (
            <Pressable
              key={slug}
              style={[
                styles.chip,
                {
                  backgroundColor: active
                    ? colors.navyDeep
                    : isDark ? colors.nightSurface : colors.white,
                  borderColor: active
                    ? colors.navyDeep
                    : isDark ? 'rgba(255,255,255,0.12)' : colors.borderLight,
                },
              ]}
              onPress={() => toggle(slug)}
              accessibilityLabel={label}
              accessibilityState={{ selected: active }}
            >
              <Text style={styles.chipIcon}>{icon}</Text>
              <Text style={[styles.chipText, { color: active ? colors.white : textPri }]}>
                {label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {/* CTA */}
      <View style={styles.footer}>
        <Animated.View style={btnAnim}>
          <Pressable
            style={[styles.button, selected.size === 0 && styles.buttonMuted]}
            onPress={handleContinue}
            onPressIn={() => { btnScale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
            onPressOut={() => { btnScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
            disabled={selected.size === 0}
            accessibilityLabel="Continue"
          >
            <Text style={styles.buttonText}>Continue</Text>
          </Pressable>
        </Animated.View>
      </View>

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
    backgroundColor: colors.electricBlue,
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
    lineHeight: 34,
  },
  subtitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    lineHeight: 22,
  },

  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[3],
    marginBottom: spacing[8],
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
    borderWidth: 1.5,
    borderRadius: borderRadius.full,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[2],
    boxShadow: '0 2px 6px rgba(0,0,0,0.06)',
  },
  chipIcon: { fontSize: 16 },
  chipText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '500',
  },

  footer: { marginTop: 'auto' as never },
  button: {
    height: 56,
    backgroundColor: colors.navyDeep,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: `0 8px 16px ${withAlpha(colors.navyDeep, 0.25)}`,
  },
  buttonMuted: { opacity: 0.40 },
  buttonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.white,
    fontWeight: '600',
  },
});
