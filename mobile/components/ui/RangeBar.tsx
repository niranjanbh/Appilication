import { StyleSheet, Text, View } from 'react-native';
import { borderRadius, colors, fontFamily, fontSize, fontWeight, spacing, withAlpha } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';

type RangeStatus = 'low' | 'normal' | 'high';

interface RangeBarProps {
  value: number;
  low: number;
  high: number;
  unit?: string;
  label?: string;
  accessibilityLabel?: string;
}

function getStatus(value: number, low: number, high: number): RangeStatus {
  if (value < low) return 'low';
  if (value > high) return 'high';
  return 'normal';
}

export function RangeBar({ value, low, high, unit, label, accessibilityLabel }: RangeBarProps) {
  const t = useTheme();
  const status = getStatus(value, low, high);

  const rangeSpan = high - low;
  const padding = rangeSpan * 0.3;
  const displayMin = Math.max(0, low - padding);
  const displayMax = high + padding;
  const displaySpan = displayMax - displayMin;

  const normalStart = ((low - displayMin) / displaySpan) * 100;
  const normalWidth = (rangeSpan / displaySpan) * 100;
  const markerPos = Math.max(0, Math.min(100, ((value - displayMin) / displaySpan) * 100));

  const statusColor = status === 'normal'
    ? (t.isDark ? colors.jadeGlow : colors.jade)
    : status === 'high'
    ? colors.saffron
    : colors.terracotta;

  const a11yLabel = accessibilityLabel ?? `${label ?? 'Value'}: ${value}${unit ?? ''}, ${status === 'normal' ? 'in range' : `${status}`}`;

  return (
    <View style={styles.container} accessibilityLabel={a11yLabel}>
      {label && <Text style={[styles.label, { color: t.text }]}>{label}</Text>}
      <View style={styles.barRow}>
        <View style={[styles.track, { backgroundColor: t.isDark ? 'rgba(79,163,131,0.10)' : 'rgba(60,52,30,0.06)' }]}>
          <View
            style={[
              styles.normalBand,
              {
                left: `${normalStart}%`,
                width: `${normalWidth}%`,
                backgroundColor: t.isDark ? withAlpha(colors.jade, 0.25) : withAlpha(colors.sage, 0.30),
              },
            ]}
          />
          <View
            style={[
              styles.marker,
              {
                left: `${markerPos}%`,
                backgroundColor: statusColor,
                boxShadow: `0 2px 6px ${withAlpha(statusColor, 0.35)}`,
              },
            ]}
          />
        </View>
      </View>
      <View style={styles.valuesRow}>
        <Text style={[styles.bound, { color: t.textSub }]}>{low}{unit}</Text>
        <Text style={[styles.value, { color: statusColor }]}>{value}{unit}</Text>
        <Text style={[styles.bound, { color: t.textSub }]}>{high}{unit}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: spacing[1] },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: fontWeight.medium,
    marginBottom: spacing[1],
  },
  barRow: { paddingHorizontal: spacing[1] },
  track: {
    height: 8,
    borderRadius: borderRadius.full,
    position: 'relative',
    overflow: 'visible',
  },
  normalBand: {
    position: 'absolute',
    top: 0,
    height: '100%',
    borderRadius: borderRadius.full,
  },
  marker: {
    position: 'absolute',
    top: -3,
    width: 14,
    height: 14,
    borderRadius: 7,
    marginLeft: -7,
    borderWidth: 2,
    borderColor: colors.white,
  },
  valuesRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  bound: {
    fontFamily: fontFamily.data,
    fontSize: fontSize.xs,
  },
  value: {
    fontFamily: fontFamily.data,
    fontSize: fontSize.sm,
    fontWeight: fontWeight.semibold,
  },
});
