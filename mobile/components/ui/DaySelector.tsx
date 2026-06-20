import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, fontFamily, fontSize, fontWeight, spacing } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';

interface DaySelectorProps {
  days: { label: string; date: string; hasData?: boolean }[];
  selectedIndex: number;
  onSelect: (index: number) => void;
}

export function DaySelector({ days, selectedIndex, onSelect }: DaySelectorProps) {
  const t = useTheme();

  return (
    <View style={styles.row} accessibilityRole="tablist">
      {days.map((day, i) => {
        const selected = i === selectedIndex;
        return (
          <Pressable
            key={i}
            onPress={() => onSelect(i)}
            accessibilityRole="tab"
            accessibilityState={{ selected }}
            accessibilityLabel={day.date}
            style={[
              styles.day,
              {
                backgroundColor: selected
                  ? (t.isDark ? colors.saffron : colors.forest)
                  : 'transparent',
              },
            ]}
          >
            <Text
              style={[
                styles.label,
                {
                  color: selected
                    ? (t.isDark ? colors.forestInk : colors.ivory)
                    : t.textSub,
                  fontWeight: selected ? fontWeight.semibold : fontWeight.normal,
                },
              ]}
            >
              {day.label}
            </Text>
            {day.hasData && !selected && (
              <View
                style={[
                  styles.dot,
                  { backgroundColor: t.isDark ? colors.jadeGlow : colors.jade },
                ]}
              />
            )}
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: spacing[1],
  },
  day: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
  },
  dot: {
    position: 'absolute',
    bottom: 4,
    width: 4,
    height: 4,
    borderRadius: 2,
  },
});
