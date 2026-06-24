/**
 * RequestedConsultBanner — shown on Home when the patient has a consultation in
 * the `requested` state. At that point the coordinator has not yet assigned a
 * doctor and time slot, so there is nothing for the patient to do but wait.
 * The banner reassures them the request is being handled.
 */

import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';
import { GlassCard } from '../ui/GlassCard';
import { HapticPressable } from '../ui/HapticPressable';
import { fontFamily, fontSize, spacing, tintSoft } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';

export function RequestedConsultBanner({ onPress }: { onPress: () => void }) {
  const t = useTheme();
  const pair = tintSoft.saffron;
  const chipBg = t.isDark ? pair.bgDark : pair.bgLight;
  const tint = t.isDark ? pair.tintDark : pair.tintLight;

  return (
    <HapticPressable
      onPress={onPress}
      scaleTo={0.98}
      accessibilityLabel="Consultation request being reviewed. View your care requests."
    >
      <GlassCard>
        <View style={styles.row}>
          <View style={[styles.iconWrap, { backgroundColor: chipBg }]}>
            <Ionicons name="hourglass-outline" size={20} color={tint} />
          </View>
          <View style={styles.content}>
            <Text style={[styles.title, { color: t.text }]}>Request under review</Text>
            <Text style={[styles.body, { color: t.textSub }]}>
              Our care team is matching you with the right specialist and time slot. We'll
              notify you as soon as it's confirmed.
            </Text>
          </View>
          <Ionicons name="chevron-forward" size={18} color={t.textSub} />
        </View>
      </GlassCard>
    </HapticPressable>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: spacing[3] },
  iconWrap: {
    width: 40,
    height: 40,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  content: { flex: 1, gap: 2 },
  title: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
  body: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    lineHeight: 18,
  },
});
