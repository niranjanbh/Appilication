import { Ionicons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { AmbientBackground } from '../components/ui/AmbientBackground';
import { EmptyState } from '../components/ui/EmptyState';
import { GlassCard } from '../components/ui/GlassCard';
import { HapticPressable } from '../components/ui/HapticPressable';
import {
  listBiomarkers,
  type BiomarkerSummary,
} from '../lib/api/biomarker-trends';
import {
  borderRadius,
  colors,
  fontFamily,
  fontSize,
  spacing,
} from '../lib/design-tokens';
import { useTheme } from '../lib/theme';

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

const FLAG_CONFIG: Record<string, { color: string; label: string; icon: IoniconName }> = {
  normal: { color: colors.jade, label: 'Normal', icon: 'checkmark-circle' },
  high:   { color: colors.alert,  label: 'High',   icon: 'arrow-up-circle' },
  low:    { color: colors.saffron,  label: 'Low',    icon: 'arrow-down-circle' },
};

function formatDate(iso: string | null): string {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'Asia/Kolkata',
  });
}

function BiomarkerCard({
  biomarker,
  onPress,
}: {
  biomarker: BiomarkerSummary;
  onPress: () => void;
}) {
  const t = useTheme();
  const flag = FLAG_CONFIG[biomarker.flag ?? 'normal'] ?? FLAG_CONFIG.normal;

  return (
    <HapticPressable
      haptic="selection"
      scaleTo={0.98}
      onPress={onPress}
      accessibilityLabel={`${biomarker.name}, ${flag.label}`}
    >
      <GlassCard>
        <View style={styles.cardRow}>
          <View style={[styles.flagDot, { backgroundColor: flag.color + '18' }]}>
            <Ionicons name={flag.icon} size={20} color={flag.color} />
          </View>
          <View style={styles.cardBody}>
            <Text style={[styles.biomarkerName, { color: t.text }]}>{biomarker.name}</Text>
            <View style={styles.valueRow}>
              {biomarker.latest_value != null && (
                <Text style={[styles.valueText, { color: t.text }]}>
                  {biomarker.latest_value} {biomarker.unit}
                </Text>
              )}
              {biomarker.ref_low != null && biomarker.ref_high != null && (
                <Text style={[styles.refText, { color: t.textSub }]}>
                  Ref: {biomarker.ref_low}–{biomarker.ref_high}
                </Text>
              )}
            </View>
            {biomarker.report_date && (
              <Text style={[styles.dateText, { color: t.textSub }]}>
                {formatDate(biomarker.report_date)}
              </Text>
            )}
          </View>
          <View style={styles.cardRight}>
            <View style={[styles.statusPill, { backgroundColor: flag.color + '18' }]}>
              <Text style={[styles.statusText, { color: flag.color }]}>{flag.label}</Text>
            </View>
            <Ionicons name="chevron-forward" size={16} color={t.textSub} />
          </View>
        </View>
      </GlassCard>
    </HapticPressable>
  );
}

export default function InsightsScreen() {
  const t = useTheme();
  const router = useRouter();

  const { data, isLoading } = useQuery({
    queryKey: ['biomarkers-list'],
    queryFn: listBiomarkers,
    staleTime: 60_000,
  });

  const biomarkers = data?.biomarkers ?? [];

  const abnormal = biomarkers.filter(b => b.flag === 'high' || b.flag === 'low');
  const normal = biomarkers.filter(b => !b.flag || b.flag === 'normal');

  return (
    <View style={[styles.flex, { backgroundColor: t.background }]}>
      <AmbientBackground />
      <ScrollView
        style={styles.flex}
        contentContainerStyle={styles.container}
        showsVerticalScrollIndicator={false}
      >
        <Text style={[styles.heading, { color: t.text }]}>Insights & Trends</Text>
        <Text style={[styles.subtitle, { color: t.textSub }]}>
          Your biomarker results across all lab reports. Tap any marker to see its trend over time.
        </Text>

        {isLoading ? (
          <ActivityIndicator size="large" color={t.primary} style={styles.loader} />
        ) : biomarkers.length === 0 ? (
          <EmptyState
            icon="flask-outline"
            tint="violet"
            title="No biomarker data yet"
            body="Upload a lab report and we'll extract your biomarker values automatically. Your trends will appear here."
            ctaLabel="Upload a report"
            onCtaPress={() => router.push('/reports/upload')}
          />
        ) : (
          <>
            {abnormal.length > 0 && (
              <View style={styles.section}>
                <Text style={[styles.sectionLabel, { color: t.textSub }]}>Needs attention</Text>
                <View style={styles.cardList}>
                  {abnormal.map(b => (
                    <BiomarkerCard
                      key={b.name}
                      biomarker={b}
                      onPress={() => router.push(`/biomarkers/${encodeURIComponent(b.name)}`)}
                    />
                  ))}
                </View>
              </View>
            )}

            {normal.length > 0 && (
              <View style={styles.section}>
                <Text style={[styles.sectionLabel, { color: t.textSub }]}>Within range</Text>
                <View style={styles.cardList}>
                  {normal.map(b => (
                    <BiomarkerCard
                      key={b.name}
                      biomarker={b}
                      onPress={() => router.push(`/biomarkers/${encodeURIComponent(b.name)}`)}
                    />
                  ))}
                </View>
              </View>
            )}
          </>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
    paddingBottom: spacing[12],
    gap: spacing[4],
  },
  heading: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    fontWeight: '600',
  },
  subtitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    lineHeight: 22,
  },
  loader: { marginTop: spacing[10] },
  section: { gap: spacing[3], marginTop: spacing[2] },
  sectionLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
    paddingHorizontal: spacing[2],
  },
  cardList: { gap: spacing[3] },
  cardRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
  },
  flagDot: {
    width: 40,
    height: 40,
    borderRadius: borderRadius.xl,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  cardBody: { flex: 1, gap: 2 },
  biomarkerName: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
  valueRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  valueText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: '500',
  },
  refText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
  },
  dateText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
  },
  cardRight: { alignItems: 'flex-end', gap: spacing[2] },
  statusPill: {
    paddingHorizontal: spacing[2],
    paddingVertical: 3,
    borderRadius: borderRadius.full,
  },
  statusText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
  },
});
