import { useState } from 'react';
import { Ionicons } from '@expo/vector-icons';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { borderRadius, colors, fontFamily, fontSize, fontWeight, shadow, spacing, withAlpha } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';
import { AmbientBackground } from '../../components/ui/AmbientBackground';
import { GlassCard } from '../../components/ui/GlassCard';
import { ActivityRings } from '../../components/ui/ActivityRings';
import { TAB_DOCK_CLEARANCE } from '../../components/ui/GlassTabBar';
import { Button } from '../../components/Button';

type ConnectionState = 'not-connected' | 'connected';

export default function LifestyleScreen() {
  const t = useTheme();
  const [state] = useState<ConnectionState>('not-connected');

  if (state === 'not-connected') {
    return (
      <View style={[styles.container, { backgroundColor: t.background }]}>
        <AmbientBackground />
        <ScrollView contentContainerStyle={styles.scrollCenter}>
          <View style={[styles.heroCard, { backgroundColor: t.surface, boxShadow: t.isDark ? shadow.darkMd : shadow.md }]}>
            <View style={[styles.iconWrap, { backgroundColor: withAlpha(colors.sage, 0.12) }]}>
              <Ionicons name="fitness-outline" size={32} color={t.isDark ? colors.jadeGlow : colors.jade} />
            </View>
            <Text style={[styles.title, { color: t.text }]}>Track your lifestyle</Text>
            <Text style={[styles.body, { color: t.textSub }]}>
              Connect a wearable to automatically sync activity, sleep, and heart rate — or log manually.
            </Text>
            <Button label="Connect device" variant="forest" onPress={() => {}} />
            <Button label="Enter manually" variant="ghost" onPress={() => {}} />
          </View>

          {/* Ghost preview (blurred hint of connected state) */}
          <View style={styles.ghostPreview}>
            <View style={styles.ghostOverlay} />
            <ActivityRings
              rings={[
                { percent: 72, label: 'Move' },
                { percent: 55, label: 'Exercise' },
                { percent: 88, label: 'Stand' },
              ]}
              size={120}
            />
            <Text style={[styles.ghostLabel, { color: t.textSub }]}>
              Preview of your activity dashboard
            </Text>
          </View>
        </ScrollView>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: t.background }]}>
      <AmbientBackground />
      <ScrollView contentContainerStyle={styles.scroll}>
        <GlassCard>
          <View style={styles.ringsSection}>
            <ActivityRings
              rings={[
                { percent: 72, label: 'Move' },
                { percent: 55, label: 'Exercise' },
                { percent: 88, label: 'Stand' },
              ]}
              size={140}
            />
            <View style={styles.ringLabels}>
              <RingStat color={colors.forest} label="Move" value="420 cal" />
              <RingStat color={colors.saffron} label="Exercise" value="28 min" />
              <RingStat color={colors.jade} label="Stand" value="10 hr" />
            </View>
          </View>
        </GlassCard>
      </ScrollView>
    </View>
  );
}

function RingStat({ color, label, value }: { color: string; label: string; value: string }) {
  const t = useTheme();
  return (
    <View style={styles.ringStatRow}>
      <View style={[styles.ringDot, { backgroundColor: color }]} />
      <Text style={[styles.ringStatLabel, { color: t.textSub }]}>{label}</Text>
      <Text style={[styles.ringStatValue, { color: t.text }]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: {
    flexGrow: 1,
    padding: spacing[6],
    paddingBottom: TAB_DOCK_CLEARANCE,
    gap: spacing[5],
  },
  scrollCenter: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: spacing[6],
    paddingBottom: TAB_DOCK_CLEARANCE,
    gap: spacing[6],
  },
  heroCard: {
    borderRadius: borderRadius.xxl,
    padding: spacing[6],
    alignItems: 'center',
    gap: spacing[4],
  },
  iconWrap: {
    width: 64,
    height: 64,
    borderRadius: 32,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h3,
    fontWeight: fontWeight.medium,
    textAlign: 'center',
  },
  body: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    textAlign: 'center',
    lineHeight: 22,
  },
  ghostPreview: {
    alignItems: 'center',
    gap: spacing[3],
    opacity: 0.35,
  },
  ghostOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
  },
  ghostLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontStyle: 'italic',
  },
  ringsSection: {
    alignItems: 'center',
    gap: spacing[5],
  },
  ringLabels: { gap: spacing[2], width: '100%' },
  ringStatRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
  },
  ringDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  ringStatLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    flex: 1,
  },
  ringStatValue: {
    fontFamily: fontFamily.data,
    fontSize: fontSize.body,
    fontWeight: fontWeight.medium,
  },
});
