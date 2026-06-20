import { Ionicons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';
import { borderRadius, colors, fontFamily, fontSize, fontWeight, glass, shadow, spacing, withAlpha } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';
import { canLiveBlur } from '../../lib/platform/blur';

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

interface MenuItem {
  icon: IoniconName;
  label: string;
  onPress: () => void;
  destructive?: boolean;
}

interface AvatarMenuProps {
  visible: boolean;
  onClose: () => void;
  displayName?: string;
  items: MenuItem[];
}

export function AvatarMenu({ visible, onClose, displayName, items }: AvatarMenuProps) {
  const t = useTheme();

  const panelBg = canLiveBlur
    ? (t.isDark ? t.glass.surface : t.glass.surfaceStrong)
    : (t.isDark ? colors.forestSurface : colors.white);

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose}>
        <View style={styles.anchor}>
          <View
            style={[
              styles.panel,
              {
                backgroundColor: panelBg,
                borderColor: t.glass.border,
                boxShadow: t.isDark ? shadow.darkLg : shadow.lg,
              },
            ]}
          >
            {canLiveBlur && (
              <BlurView
                tint={t.isDark ? 'dark' : 'light'}
                intensity={glass.blur.card}
                style={StyleSheet.absoluteFill}
              />
            )}
            <View style={styles.content}>
              {displayName && (
                <View style={styles.header}>
                  <View style={[styles.avatarCircle, { backgroundColor: t.isDark ? colors.saffron : colors.forest }]}>
                    <Text style={[styles.avatarLetter, { color: t.isDark ? colors.forestInk : colors.ivory }]}>
                      {displayName.charAt(0).toUpperCase()}
                    </Text>
                  </View>
                  <Text style={[styles.name, { color: t.text }]} numberOfLines={1}>
                    {displayName}
                  </Text>
                </View>
              )}

              <View style={[styles.divider, { backgroundColor: t.border }]} />

              {items.map((item, i) => (
                <Pressable
                  key={i}
                  onPress={() => { item.onPress(); onClose(); }}
                  style={({ pressed }) => [
                    styles.menuItem,
                    pressed && { backgroundColor: withAlpha(t.isDark ? colors.jadeGlow : colors.forest, 0.06) },
                  ]}
                  accessibilityLabel={item.label}
                >
                  <Ionicons
                    name={item.icon}
                    size={20}
                    color={item.destructive ? t.critical : t.textSub}
                  />
                  <Text
                    style={[
                      styles.menuLabel,
                      { color: item.destructive ? t.critical : t.text },
                    ]}
                  >
                    {item.label}
                  </Text>
                </Pressable>
              ))}
            </View>
          </View>
        </View>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.25)',
    justifyContent: 'flex-start',
    alignItems: 'flex-end',
  },
  anchor: {
    marginTop: 56,
    marginRight: spacing[4],
  },
  panel: {
    width: 240,
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    overflow: 'hidden',
  },
  content: { position: 'relative' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    padding: spacing[4],
  },
  avatarCircle: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarLetter: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.bodyLg,
    fontWeight: fontWeight.medium,
  },
  name: {
    flex: 1,
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: fontWeight.medium,
  },
  divider: { height: 1, marginHorizontal: spacing[3] },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    paddingVertical: spacing[3],
    paddingHorizontal: spacing[4],
  },
  menuLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
  },
});
