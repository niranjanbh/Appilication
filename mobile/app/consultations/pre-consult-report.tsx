import { ActivityIndicator, Linking, Pressable, ScrollView, StyleSheet, Text, useColorScheme, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { getPreConsultReport, type BiomarkerSummary, type PreConsultReport } from '../../lib/api/pre-consult-reports';
import { apiFetch } from '../../lib/api/client';
import { borderRadius, colors, fontFamily, fontSize, spacing , withAlpha } from '../../lib/design-tokens';

function trendSymbol(t: BiomarkerSummary['trend']): string {
  if (t === 'up') return '↑';
  if (t === 'down') return '↓';
  return '↔';
}
function trendColor(t: BiomarkerSummary['trend'], isDark: boolean): string {
  if (t === 'up') return colors.criticalRed;
  if (t === 'down') return colors.successGreen;
  return isDark ? colors.slateText : colors.coolGray;
}
function formatDate(iso: string) {
  return new Date(iso).toLocaleString('en-IN', {
    day: 'numeric', month: 'long', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: true,
    timeZone: 'Asia/Kolkata',
  });
}

// ── Section wrapper ───────────────────────────────────────────────────────────

function Section({ title, children, cardBg, cardBdr, textPri }: {
  title: string; children: React.ReactNode;
  cardBg: string; cardBdr: string; textPri: string; textSub: string;
}) {
  return (
    <View style={[sec.card, { backgroundColor: cardBg, borderColor: cardBdr }]}>
      <Text style={[sec.title, { color: textPri, borderBottomColor: cardBdr }]}>{title}</Text>
      {children}
    </View>
  );
}
const sec = StyleSheet.create({
  card: {
    borderRadius: borderRadius.xxl,
    padding: spacing[5],
    borderWidth: 1,
    gap: spacing[3],
    boxShadow: '0 6px 14px rgba(0,0,0,0.07)',
  },
  title: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.bodyLg,
    fontWeight: '600',
    borderBottomWidth: 1,
    paddingBottom: spacing[3],
  },
});

// ── Lab summary ───────────────────────────────────────────────────────────────

function LabSummarySection({ summary, isDark, cardBg, cardBdr, textPri, textSub }: {
  summary: PreConsultReport['lab_summary']; isDark: boolean;
  cardBg: string; cardBdr: string; textPri: string; textSub: string;
}) {
  if (!summary?.biomarkers?.length) {
    return (
      <Section title="Lab Summary (last 90 days)" cardBg={cardBg} cardBdr={cardBdr} textPri={textPri} textSub={textSub}>
        <Text style={[styles.emptyText, { color: textSub }]}>No lab data available yet.</Text>
      </Section>
    );
  }
  return (
    <Section title={`Lab Summary (last ${summary.window_days} days)`} cardBg={cardBg} cardBdr={cardBdr} textPri={textPri} textSub={textSub}>
      {summary.biomarkers.map(bm => (
        <View key={bm.name} style={[styles.bioRow, bm.flag && { backgroundColor: colors.warningAmber + '12', borderRadius: borderRadius.lg, paddingHorizontal: spacing[3] }]}>
          <View style={styles.bioLeft}>
            <Text style={[styles.bioName, { color: textPri }]}>{bm.name}</Text>
            <Text style={[styles.bioRef, { color: textSub }]}>Ref: {bm.ref_low ?? '—'}–{bm.ref_high ?? '—'} {bm.unit ?? ''}</Text>
          </View>
          <View style={styles.bioRight}>
            <Text style={[
              styles.bioValue,
              { color: bm.flag === 'high' ? colors.criticalRed : bm.flag === 'low' ? colors.warningAmber : textPri },
            ]}>
              {bm.value ?? '—'} {bm.unit ?? ''}
            </Text>
            <Text style={[styles.bioTrend, { color: trendColor(bm.trend, isDark) }]}>{trendSymbol(bm.trend)}</Text>
          </View>
        </View>
      ))}
      {summary.biomarkers.some(bm => bm.flag) && (
        <Text style={[styles.flagNote, { color: textSub }]}>Highlighted rows have out-of-range values.</Text>
      )}
    </Section>
  );
}

// ── Adherence section ─────────────────────────────────────────────────────────

function AdherenceSection({ summary, cardBg, cardBdr, textPri, textSub }: {
  summary: PreConsultReport['adherence_summary'];
  cardBg: string; cardBdr: string; textPri: string; textSub: string;
}) {
  if (!summary || summary.compliance_pct === null) {
    return (
      <Section title="Medication Adherence" cardBg={cardBg} cardBdr={cardBdr} textPri={textPri} textSub={textSub}>
        <Text style={[styles.emptyText, { color: textSub }]}>No medication reminder data yet.</Text>
      </Section>
    );
  }
  const pct      = summary.compliance_pct;
  const barColor = pct >= 80 ? colors.successGreen : pct >= 50 ? colors.warningAmber : colors.criticalRed;
  return (
    <Section title={`Medication Adherence (last ${summary.window_days} days)`} cardBg={cardBg} cardBdr={cardBdr} textPri={textPri} textSub={textSub}>
      <View style={[styles.adherenceTrack, { backgroundColor: colors.borderLight }]}>
        <View style={[styles.adherenceFill, { width: `${pct}%` as `${number}%`, backgroundColor: barColor }]} />
      </View>
      <Text style={[styles.adherencePct, { color: barColor }]}>{pct}%</Text>
      <View style={styles.adherenceStats}>
        {[
          { label: 'Taken',   value: summary.taken },
          { label: 'Skipped', value: summary.skipped },
          { label: 'Snoozed', value: summary.snoozed },
        ].map(({ label, value }) => (
          <View key={label} style={styles.adherenceStat}>
            <Text style={[styles.adherenceStatValue, { color: textPri }]}>{value}</Text>
            <Text style={[styles.adherenceStatLabel, { color: textSub }]}>{label}</Text>
          </View>
        ))}
      </View>
    </Section>
  );
}

// ── Wearable section ──────────────────────────────────────────────────────────

function WearableSection({ summary, cardBg, cardBdr, textPri, textSub }: {
  summary: PreConsultReport['wearable_summary'];
  cardBg: string; cardBdr: string; textPri: string; textSub: string;
}) {
  if (!summary) {
    return (
      <Section title="Health Summary" cardBg={cardBg} cardBdr={cardBdr} textPri={textPri} textSub={textSub}>
        <Text style={[styles.emptyText, { color: textSub }]}>No wearable data available.</Text>
      </Section>
    );
  }
  const stats = [
    { icon: '👟', label: 'Avg Steps',   value: summary.avg_steps ? summary.avg_steps.toLocaleString('en-IN') : '—' },
    { icon: '❤️', label: 'Resting HR',  value: summary.avg_resting_hr ? `${summary.avg_resting_hr}` : '—', unit: 'bpm' },
    { icon: '😴', label: 'Avg Sleep',   value: summary.avg_sleep_hours ? `${summary.avg_sleep_hours}` : '—', unit: 'hrs' },
  ];
  return (
    <Section title={`Health Summary (last ${summary.window_days} days)`} cardBg={cardBg} cardBdr={cardBdr} textPri={textPri} textSub={textSub}>
      <View style={styles.statsRow}>
        {stats.map(s => (
          <View key={s.label} style={[styles.statCard, { backgroundColor: colors.electricBlue + '12' }]}>
            <Text style={styles.statIcon}>{s.icon}</Text>
            <Text style={[styles.statValue, { color: textPri }]}>{s.value}</Text>
            {s.unit && <Text style={[styles.statUnit, { color: textSub }]}>{s.unit}</Text>}
            <Text style={[styles.statLabel, { color: textSub }]}>{s.label}</Text>
          </View>
        ))}
      </View>
    </Section>
  );
}

// ── Flags section ─────────────────────────────────────────────────────────────

function FlagsSection({ flags, cardBg, cardBdr, textPri, textSub }: {
  flags: PreConsultReport['patient_flags'];
  cardBg: string; cardBdr: string; textPri: string; textSub: string;
}) {
  const items = flags?.flags ?? [];
  return (
    <Section title="Your Flagged Concerns" cardBg={cardBg} cardBdr={cardBdr} textPri={textPri} textSub={textSub}>
      {items.length === 0 ? (
        <Text style={[styles.emptyText, { color: textSub }]}>No concerns flagged for this consultation.</Text>
      ) : (
        items.map((f, i) => (
          <View key={i} style={styles.flagItem}>
            <Text style={[styles.flagBullet, { color: colors.electricBlue }]}>•</Text>
            <Text style={[styles.flagText, { color: textPri }]}>{f}</Text>
          </View>
        ))
      )}
    </Section>
  );
}

// ── Screen ────────────────────────────────────────────────────────────────────

export default function PreConsultReportScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const isDark = useColorScheme() === 'dark';

  const [report,  setReport]  = useState<PreConsultReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getPreConsultReport(id)
      .then(setReport)
      .catch(() => setError('Unable to load your pre-consultation report.'))
      .finally(() => setLoading(false));
  }, [id]);

  // Preserve all existing download logic
  const handleDownload = async () => {
    if (!report?.pdf_url) return;
    try {
      const { url } = await apiFetch<{ url: string }>(`/v1/clinic/patient/consultations/${id}/pre-consult-report/download`);
      await Linking.openURL(url);
    } catch {
      // graceful
    }
  };

  const dlScale = useSharedValue(1);
  const dlAnim  = useAnimatedStyle(() => ({ transform: [{ scale: dlScale.value }] }));

  const bg      = isDark ? colors.midnight     : colors.skyMist;
  const textPri = isDark ? colors.white        : colors.navyDeep;
  const textSub = isDark ? colors.slateText    : colors.coolGray;
  const cardBg  = isDark ? colors.nightSurface : colors.white;
  const cardBdr = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)';

  if (loading) {
    return <View style={[styles.center, { backgroundColor: bg }]}><ActivityIndicator size="large" color={colors.electricBlue} /></View>;
  }
  if (error || !report) {
    return (
      <View style={[styles.center, { backgroundColor: bg }]}>
        <Text style={[styles.errorText, { color: colors.criticalRed }]}>{error ?? 'Report not available yet.'}</Text>
        <Pressable onPress={() => router.back()} style={styles.backBtn} accessibilityLabel="Go back">
          <Text style={[styles.backBtnText, { color: colors.electricBlue }]}>Go back</Text>
        </Pressable>
      </View>
    );
  }

  const sharedProps = { isDark, cardBg, cardBdr, textPri, textSub };

  return (
    <ScrollView style={[styles.scroll, { backgroundColor: bg }]} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Text style={[styles.title, { color: textPri }]}>Pre-Consultation Report</Text>
        <Text style={[styles.generated, { color: textSub }]}>Generated {formatDate(report.generated_at)}</Text>
      </View>

      <LabSummarySection  summary={report.lab_summary}       {...sharedProps} />
      <AdherenceSection   summary={report.adherence_summary} {...sharedProps} />
      <WearableSection    summary={report.wearable_summary}  {...sharedProps} />
      <FlagsSection       flags={report.patient_flags}       {...sharedProps} />

      {report.pdf_url && (
        <Animated.View style={dlAnim}>
          <Pressable
            onPress={handleDownload}
            onPressIn={() => { dlScale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
            onPressOut={() => { dlScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
            style={styles.dlBtn}
            accessibilityLabel="Download PDF report"
          >
            <Text style={styles.dlBtnText}>↓ Download PDF</Text>
          </Pressable>
        </Animated.View>
      )}
    </ScrollView>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  scroll: { flex: 1 },
  content: { padding: spacing[5], paddingBottom: spacing[10], gap: spacing[4] },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing[6] },

  header: { gap: spacing[1] },
  title:     { fontFamily: fontFamily.display, fontSize: fontSize.h2, fontWeight: '600' },
  generated: { fontFamily: fontFamily.body, fontSize: fontSize.caption },

  emptyText: { fontFamily: fontFamily.body, fontSize: fontSize.caption },

  bioRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: spacing[2] },
  bioLeft: { flex: 1 },
  bioName: { fontFamily: fontFamily.body, fontSize: fontSize.sm, fontWeight: '600', textTransform: 'capitalize' },
  bioRef:  { fontFamily: fontFamily.body, fontSize: fontSize.xs, marginTop: 2 },
  bioRight:{ flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  bioValue:{ fontFamily: fontFamily.body, fontSize: fontSize.sm, fontWeight: '600' },
  bioTrend:{ fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '700' },
  flagNote:{ fontFamily: fontFamily.body, fontSize: fontSize.caption, marginTop: spacing[1] },

  adherenceTrack: { height: 10, borderRadius: borderRadius.full, overflow: 'hidden' },
  adherenceFill:  { height: '100%', borderRadius: borderRadius.full },
  adherencePct:   { fontFamily: fontFamily.display, fontSize: fontSize.h2, fontWeight: '600' },
  adherenceStats: { flexDirection: 'row', gap: spacing[6] },
  adherenceStat:  { alignItems: 'center', gap: 2 },
  adherenceStatValue: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700' },
  adherenceStatLabel: { fontFamily: fontFamily.body, fontSize: fontSize.xs },

  statsRow: { flexDirection: 'row', gap: spacing[3] },
  statCard: { flex: 1, borderRadius: borderRadius.xl, padding: spacing[3], alignItems: 'center', gap: 2 },
  statIcon: { fontSize: 22, marginBottom: 2 },
  statValue:{ fontFamily: fontFamily.display, fontSize: fontSize.h3, fontWeight: '600' },
  statUnit: { fontFamily: fontFamily.body, fontSize: fontSize.xs },
  statLabel:{ fontFamily: fontFamily.body, fontSize: fontSize.xs, textAlign: 'center' },

  flagItem:  { flexDirection: 'row', gap: spacing[2], marginBottom: spacing[1] },
  flagBullet:{ fontFamily: fontFamily.body, fontSize: fontSize.body },
  flagText:  { fontFamily: fontFamily.body, fontSize: fontSize.body, flex: 1, lineHeight: 22 },

  dlBtn: {
    height: 56,
    backgroundColor: colors.navyDeep,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: `0 8px 16px ${withAlpha(colors.navyDeep, 0.28)}`,
  },
  dlBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, color: colors.white, fontWeight: '700' },

  backBtn:     { marginTop: spacing[4] },
  backBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontWeight: '600' },
  errorText:   { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center' },
});
