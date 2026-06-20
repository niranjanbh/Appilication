import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';
import { colors, fontFamily, fontSize, fontWeight, spacing, withAlpha } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';

type StepStatus = 'completed' | 'active' | 'upcoming';

interface Step {
  label: string;
  status: StepStatus;
}

interface PipelineStepperProps {
  steps: Step[];
  accessibilityLabel?: string;
}

const CARE_PIPELINE: string[] = [
  'Request',
  'Awaiting',
  'Payment',
  'Confirmed',
  'Join',
  'Rx Pending',
];

export function PipelineStepper({ steps, accessibilityLabel }: PipelineStepperProps) {
  const t = useTheme();

  const activeIndex = steps.findIndex(s => s.status === 'active');
  const a11yLabel = accessibilityLabel
    ?? `Care pipeline: step ${activeIndex + 1} of ${steps.length}, ${steps[activeIndex]?.label ?? 'none'} active`;

  return (
    <View style={styles.container} accessibilityLabel={a11yLabel}>
      {steps.map((step, i) => {
        const isLast = i === steps.length - 1;
        const dotColor = step.status === 'completed'
          ? (t.isDark ? colors.jadeGlow : colors.jade)
          : step.status === 'active'
          ? (t.isDark ? colors.saffron : colors.forest)
          : (t.isDark ? colors.stoneDim : colors.stone);

        const lineColor = step.status === 'completed'
          ? (t.isDark ? colors.jadeGlow : colors.jade)
          : (t.isDark ? 'rgba(79,163,131,0.15)' : withAlpha(colors.forest, 0.10));

        return (
          <View key={i} style={styles.stepWrap}>
            <View style={styles.dotCol}>
              <View style={[styles.dot, { backgroundColor: dotColor }]}>
                {step.status === 'completed' && (
                  <Ionicons name="checkmark" size={10} color={colors.white} />
                )}
              </View>
              {!isLast && <View style={[styles.line, { backgroundColor: lineColor }]} />}
            </View>
            <Text
              style={[
                styles.label,
                {
                  color: step.status === 'upcoming' ? t.textSub : t.text,
                  fontWeight: step.status === 'active' ? fontWeight.semibold : fontWeight.normal,
                },
              ]}
              numberOfLines={1}
            >
              {step.label}
            </Text>
          </View>
        );
      })}
    </View>
  );
}

export function carePipelineSteps(activeStep: number): Step[] {
  return CARE_PIPELINE.map((label, i) => ({
    label,
    status: i < activeStep ? 'completed' : i === activeStep ? 'active' : 'upcoming',
  }));
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 0,
  },
  stepWrap: {
    flex: 1,
    alignItems: 'center',
    gap: spacing[1],
  },
  dotCol: {
    alignItems: 'center',
    flexDirection: 'row',
    width: '100%',
    justifyContent: 'center',
  },
  dot: {
    width: 20,
    height: 20,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1,
  },
  line: {
    position: 'absolute',
    height: 2,
    left: '50%',
    right: '-50%',
    top: 9,
  },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    textAlign: 'center',
  },
});
