import { useState, type ComponentProps } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Ionicons } from '@expo/vector-icons';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { borderRadius, colors, fontFamily, fontSize, fontWeight, shadow, spacing, withAlpha } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';
import { Alert } from '../../lib/ui/alert';
import { requestHealthPermissions } from '../../lib/native/health';
import { getHealthSummaryApi } from '../../lib/api/health-sync';
import { listVitalsApi, type VitalReadItem, type VitalType } from '../../lib/api/vitals';
import { AmbientBackground } from '../../components/ui/AmbientBackground';
import { GlassCard } from '../../components/ui/GlassCard';
import { ActivityRings } from '../../components/ui/ActivityRings';
import { TAB_DOCK_CLEARANCE } from '../../components/ui/GlassTabBar';
import { Button } from '../../components/Button';

type ConnectionState = 'not-connected' | 'connected';

const STEP_GOAL = 10000;

export default function LifestyleScreen() {
  const t = useTheme();
  const router = useRouter();
  const [state, setState] = useState<ConnectionState>('not-connected');
  const [connecting, setConnecting] = useState(false);

  const handleConnect = async () => {
    setConnecting(true);
    try {
      const result = await requestHealthPermissions();
      if (result.granted) {
        setState('connected');
      } else if (result.reason === 'unsupported_platform') {
        Alert.alert(
          'Not available here',
          'Wearable sync needs the Baseline mobile app. You can still log your activity manually.',
        );
      } else {
        Alert.alert(
          'Permission needed',
          'We could not access your health data. You can grant access in your device settings, or log activity manually.',
        );
      }
    } finally {
      setConnecting(false);
    }
  };

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
            <Button label="Connect device" variant="forest" isLoading={connecting} onPress={handleConnect} />
            <Button label="Enter manually" variant="ghost" onPress={() => router.push('/vitals')} />
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

  return <ConnectedDashboard />;
}

/** Connected lifestyle dashboard — real data from the wellness endpoints. */
function ConnectedDashboard() {
  const t = useTheme();
  const { data, isLoading, isError } = useQuery({
    queryKey: ['health-summary'],
    queryFn: getHealthSummaryApi,
    staleTime: 60_000,
  });

  const steps = data?.steps_today ?? null;
  const rhr = data?.resting_heart_rate_bpm ?? null;
  const hrv = data?.hrv_ms ?? null;
  const stepPct = steps != null ? Math.min(100, Math.round((steps / STEP_GOAL) * 100)) : 0;

  const stepsCaption = isLoading
    ? 'Syncing your latest activity…'
    : isError
      ? 'Couldn’t load activity. Pull to refresh or try again later.'
      : steps != null
        ? `Goal ${STEP_GOAL.toLocaleString('en-IN')} · ${stepPct}%`
        : 'No steps synced yet today.';

  return (
    <View style={[styles.container, { backgroundColor: t.background }]}>
      <AmbientBackground />
      <ScrollView contentContainerStyle={styles.scroll}>
        {/* Steps-toward-goal hero */}
        <GlassCard>
          <View style={styles.stepsHero}>
            <View style={[styles.tileIcon, { backgroundColor: withAlpha(colors.jade, 0.12) }]}>
              <Ionicons name="footsteps-outline" size={20} color={colors.jade} />
            </View>
            <View style={styles.stepsValueRow}>
              <Text style={[styles.stepsValue, { color: t.text }]}>
                {steps != null ? steps.toLocaleString('en-IN') : '—'}
              </Text>
              <Text style={[styles.stepsUnit, { color: t.textSub }]}>steps today</Text>
            </View>
            <ProgressBar pct={stepPct} />
            <Text style={[styles.cardCaption, { color: t.textSub }]}>{stepsCaption}</Text>
          </View>
        </GlassCard>

        {/* Quick-glance metric tiles */}
        <View style={styles.tileRow}>
          <StatTile
            icon="heart-outline"
            tint={colors.alert}
            label="Resting HR"
            value={rhr != null ? String(rhr) : '—'}
            unit={rhr != null ? 'bpm' : undefined}
          />
          <StatTile
            icon="pulse-outline"
            tint={colors.saffron}
            label="HRV"
            value={hrv != null ? String(hrv) : '—'}
            unit={hrv != null ? 'ms' : undefined}
          />
        </View>

        {/* Sleep — not yet sourced from the sync layer */}
        <GlassCard>
          <SleepCard />
        </GlassCard>

        {/* Vitals (self-fetching) */}
        <GlassCard>
          <VitalsCard />
        </GlassCard>
      </ScrollView>
    </View>
  );
}

/** Horizontal progress bar (steps toward daily goal). */
function ProgressBar({ pct }: { pct: number }) {
  const clamped = Math.max(0, Math.min(100, pct));
  return (
    <View style={[styles.progressTrack, { backgroundColor: withAlpha(colors.jade, 0.14) }]}>
      <View style={[styles.progressFill, { width: `${clamped}%`, backgroundColor: colors.jade }]} />
    </View>
  );
}

type IoniconName = ComponentProps<typeof Ionicons>['name'];

/** Compact quick-glance metric tile. */
function StatTile({ icon, tint, label, value, unit }: {
  icon: IoniconName; tint: string; label: string; value: string; unit?: string;
}) {
  const t = useTheme();
  return (
    <GlassCard unpadded style={styles.tile}>
      <View style={styles.tileInner}>
        <View style={[styles.tileIcon, { backgroundColor: withAlpha(tint, 0.12) }]}>
          <Ionicons name={icon} size={18} color={tint} />
        </View>
        <View style={styles.tileValueRow}>
          <Text style={[styles.tileValue, { color: t.text }]}>{value}</Text>
          {unit ? <Text style={[styles.tileUnit, { color: t.textSub }]}>{unit}</Text> : null}
        </View>
        <Text style={[styles.tileLabel, { color: t.textSub }]} numberOfLines={1}>{label}</Text>
      </View>
    </GlassCard>
  );
}

function SleepCard() {
  const t = useTheme();
  return (
    <View style={styles.cardBody}>
      <View style={styles.cardHeader}>
        <View style={styles.cardHeaderLeft}>
          <Ionicons name="moon-outline" size={18} color={t.isDark ? colors.jadeGlow : colors.jade} />
          <Text style={[styles.cardTitle, { color: t.text }]}>Sleep</Text>
        </View>
      </View>
      <Text style={[styles.cardCaption, { color: t.textSub }]}>
        Sleep isn’t syncing yet. Connect a device that shares sleep data to see your nightly trend here.
      </Text>
    </View>
  );
}

/** Latest reading of a given vital type. Items are sorted newest-first defensively. */
function latestVital(items: VitalReadItem[], type: VitalType): VitalReadItem | undefined {
  return items
    .filter(i => i.type === type)
    .sort((a, b) => new Date(b.measured_at).getTime() - new Date(a.measured_at).getTime())[0];
}

function VitalsCard() {
  const t = useTheme();
  const { data, isLoading, isError } = useQuery({
    queryKey: ['vitals'],
    queryFn: listVitalsApi,
    staleTime: 60_000,
  });

  const items = data?.items ?? [];
  const weight = latestVital(items, 'weight');
  const systolic = latestVital(items, 'blood_pressure_systolic');
  const diastolic = latestVital(items, 'blood_pressure_diastolic');
  const glucose = latestVital(items, 'blood_glucose');
  const hasAny = Boolean(weight || systolic || diastolic || glucose);

  return (
    <View style={styles.cardBody}>
      <View style={styles.cardHeader}>
        <View style={styles.cardHeaderLeft}>
          <Ionicons name="analytics-outline" size={18} color={t.isDark ? colors.jadeGlow : colors.jade} />
          <Text style={[styles.cardTitle, { color: t.text }]}>Vitals</Text>
        </View>
        <Text style={[styles.cardCaption, { color: t.textSub }]}>Latest</Text>
      </View>

      {isLoading ? (
        <Text style={[styles.cardCaption, { color: t.textSub }]}>Loading your latest readings…</Text>
      ) : isError ? (
        <Text style={[styles.cardCaption, { color: t.textSub }]}>Couldn’t load vitals. Pull to refresh or try again later.</Text>
      ) : !hasAny ? (
        <Text style={[styles.cardCaption, { color: t.textSub }]}>
          No vitals logged yet. Add your weight, blood pressure, or glucose to see them here.
        </Text>
      ) : (
        <>
          {weight && (
            <VitalRow icon="body-outline" label="Weight" value={`${weight.value.value} ${weight.value.unit}`} />
          )}
          {(systolic || diastolic) && (
            <VitalRow
              icon="fitness-outline"
              label="Blood pressure"
              value={`${systolic?.value.value ?? '—'} / ${diastolic?.value.value ?? '—'} ${systolic?.value.unit ?? diastolic?.value.unit ?? ''}`.trim()}
            />
          )}
          {glucose && (
            <VitalRow icon="water-outline" label="Glucose" value={`${glucose.value.value} ${glucose.value.unit}`} />
          )}
        </>
      )}
    </View>
  );
}

function VitalRow({ icon, label, value }: { icon: IoniconName; label: string; value: string }) {
  const t = useTheme();
  return (
    <View style={styles.vitalRow}>
      <Ionicons name={icon} size={16} color={t.textSub} />
      <Text style={[styles.vitalLabel, { color: t.textSub }]}>{label}</Text>
      <Text style={[styles.vitalValue, { color: t.text }]}>{value}</Text>
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

  // ── Steps hero ───────────────────────────────────────────────────────────
  stepsHero: { gap: spacing[3] },
  stepsValueRow: { flexDirection: 'row', alignItems: 'baseline', gap: spacing[2] },
  stepsValue: {
    fontFamily: fontFamily.data,
    fontSize: fontSize.h2,
    fontWeight: fontWeight.medium,
  },
  stepsUnit: { fontFamily: fontFamily.body, fontSize: fontSize.body },
  progressTrack: {
    height: 8,
    width: '100%',
    borderRadius: borderRadius.full,
    overflow: 'hidden',
  },
  progressFill: { height: 8, borderRadius: borderRadius.full },

  // ── Quick-glance metric tiles ────────────────────────────────────────────
  tileRow: { flexDirection: 'row', gap: spacing[3] },
  tile: { flex: 1 },
  tileInner: { padding: spacing[4], gap: spacing[2], alignItems: 'flex-start' },
  tileIcon: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tileValueRow: { flexDirection: 'row', alignItems: 'baseline', gap: spacing[1] },
  tileValue: {
    fontFamily: fontFamily.data,
    fontSize: fontSize.h3,
    fontWeight: fontWeight.medium,
  },
  tileUnit: { fontFamily: fontFamily.body, fontSize: fontSize.sm },
  tileLabel: { fontFamily: fontFamily.body, fontSize: fontSize.sm },

  // ── Sleep + vitals cards ─────────────────────────────────────────────────
  cardBody: { gap: spacing[4] },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  cardHeaderLeft: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  cardTitle: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.bodyLg,
    fontWeight: fontWeight.medium,
  },
  cardCaption: { fontFamily: fontFamily.body, fontSize: fontSize.sm, lineHeight: 20 },

  // ── Vitals rows ──────────────────────────────────────────────────────────
  vitalRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  vitalLabel: { fontFamily: fontFamily.body, fontSize: fontSize.body, flex: 1 },
  vitalValue: {
    fontFamily: fontFamily.data,
    fontSize: fontSize.body,
    fontWeight: fontWeight.medium,
  },
});
