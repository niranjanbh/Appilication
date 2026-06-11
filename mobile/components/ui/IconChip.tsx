import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, View } from 'react-native';
import { borderRadius, tintSoft, type TintName } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

interface IconChipProps {
  icon: IoniconName;
  tint?: TintName;
  size?: number;
}

/** Soft pastel circle with a tinted icon — replaces emoji glyphs across the app. */
export function IconChip({ icon, tint = 'blue', size = 44 }: IconChipProps) {
  const t = useTheme();
  const pair = tintSoft[tint];
  return (
    <View
      style={[
        styles.chip,
        {
          width: size,
          height: size,
          backgroundColor: t.isDark ? pair.bgDark : pair.bgLight,
        },
      ]}
    >
      <Ionicons name={icon} size={Math.round(size * 0.5)} color={t.isDark ? pair.tintDark : pair.tintLight} />
    </View>
  );
}

const styles = StyleSheet.create({
  chip: {
    borderRadius: borderRadius.full,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
