/**
 * Pre-consultation report screen — read-only patient view.
 *
 * Shows: lab summary with trend indicators, medication adherence, wearable stats,
 * patient-flagged concerns, and a PDF download button.
 * Low-confidence OCR biomarker fields (flag ≠ null) are highlighted.
 */

import { ActivityIndicator, Linking, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import {
  getPreConsultReport,
  type BiomarkerSummary,
  type PreConsultReport,
} from '../../lib/api/pre-consult-reports';
import { apiFetch } from '../../lib/api/client';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

// Convenience aliases for tokens that exist under different names in mobile
const F = fontSize;

// ── Helpers ───────────────────────────────────────────────────────────────────

function trendSymbol(t: BiomarkerSummary['trend']): string {
  if (t === 'up') return '↑';
  if (t === 'down') return '↓';
  return '↔';
}

function trendColor(t: BiomarkerSummary['trend']): string {
  if (t === 'up') return colors.terracotta;
  if (t === 'down') return colors.forest;
  return colors.stone;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('en-IN', {
    day: 'numeric', month: 'long', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: true,
    timeZone: 'Asia/Kolkata',
  });
}

// ── Section wrapper ───────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

// ── Lab summary ───────────────────────────────────────────────────────────────

function LabSummarySection({ summary }: { summary: PreConsultReport['lab_summary'] }) {
  if (!summary || !summary.biomarkers || summary.biomarkers.length === 0) {
    return (
      <Section title="Lab Summary (last 90 days)">
        <Text style={styles.emptyText}>No lab data available yet.</Text>
      </Section>
    );
  }

  return (
    <Section title={`Lab Summary (last ${summary.window_days} days)`}>
      {summary.biomarkers.map((bm) => (
        <View key={bm.name} style={[styles.biomarkerRow, bm.flag && styles.biomarkerFlagged]}>
          <View style={styles.biomarkerLeft}>
            <Text style={styles.biomarkerName}>{bm.name}</Text>
            <Text style={styles.biomarkerRef}>
              Ref: {bm.ref_low ?? '—'} – {bm.ref_high ?? '—'} {bm.unit ?? ''}
            </Text>
          </View>
          <View style={styles.biomarkerRight}>
            <Text style={[styles.biomarkerValue, bm.flag === 'high' && styles.valueFlagHigh, bm.flag === 'low' && styles.valueFlagLow]}>
              {bm.value ?? '—'} {bm.unit ?? ''}
            </Text>
            <Text style={[styles.trendSymbol, { color: trendColor(bm.trend) }]}>
              {trendSymbol(bm.trend)}
            </Text>
          </View>
        </View>
      ))}
      {summary.biomarkers.some((b) => b.flag) && (
        <Text style={styles.flagNote}>Highlighted rows have out-of-range values.</Text>
      )}
    </Section>
  );
}

// ── Adherence section ─────────────────────────────────────────────────────────

function AdherenceSection({ summary }: { summary: PreConsultReport['adherence_summary'] }) {
  if (!summary || summary.compliance_pct === null) {
    return (
      <Section title="Medication Adherence">
        <Text style={styles.emptyText}>No medication reminder data yet.</Text>
      </Section>
    );
  }

  const pct = summary.compliance_pct;
  const barColor = pct >= 80 ? colors.forest : pct >= 50 ? colors.saffron : colors.terracotta;

  return (
    <Section title={`Medication Adherence (last ${summary.window_days} days)`}>
      <View style={styles.adherenceBar}>
        <View style={[styles.adherenceFill, { width: `${pct}%` as `${number}%`, backgroundColor: barColor }]} />
      </View>
      <Text style={[styles.adherencePct, { color: barColor }]}>{pct}%</Text>
      <View style={styles.adherenceStats}>
        <Text style={styles.adherenceStat}>Taken: {summary.taken}</Text>
        <Text style={styles.adherenceStat}>Skipped: {summary.skipped}</Text>
        <Text style={styles.adherenceStat}>Snoozed: {summary.snoozed}</Text>
      </View>
    </Section>
  );
}

// ── Wearable section ──────────────────────────────────────────────────────────

function WearableSection({ summary }: { summary: PreConsultReport['wearable_summary'] }) {
  if (!summary) {
    return (
      <Section title="Health Summary">
        <Text style={styles.emptyText}>No wearable data available.</Text>
      </Section>
    );
  }

  const stats = [
    { label: 'Avg Daily Steps', value: summary.avg_steps ? summary.avg_steps.toLocaleString('en-IN') : '—' },
    { label: 'Avg Resting HR', value: summary.avg_resting_hr ? `${summary.avg_resting_hr} bpm` : '—' },
    { label: 'Avg Sleep', value: summary.avg_sleep_hours ? `${summary.avg_sleep_hours} hrs` : '—' },
  ];

  return (
    <Section title={`Health Summary (last ${summary.window_days} days)`}>
      <View style={styles.statsRow}>
        {stats.map((s) => (
          <View key={s.label} style={styles.statCard}>
            <Text style={styles.statValue}>{s.value}</Text>
            <Text style={styles.statLabel}>{s.label}</Text>
          </View>
        ))}
      </View>
    </Section>
  );
}

// ── Flags section ─────────────────────────────────────────────────────────────

function FlagsSection({ flags }: { flags: PreConsultReport['patient_flags'] }) {
  const items = flags?.flags ?? [];
  return (
    <Section title="Your Flagged Concerns">
      {items.length === 0 ? (
        <Text style={styles.emptyText}>No concerns flagged for this consultation.</Text>
      ) : (
        items.map((f, i) => (
          <View key={i} style={styles.flagItem}>
            <Text style={styles.flagBullet}>•</Text>
            <Text style={styles.flagText}>{f}</Text>
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
  const [report, setReport] = useState<PreConsultReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getPreConsultReport(id)
      .then(setReport)
      .catch(() => setError('Unable to load your pre-consultation report.'))
      .finally(() => setLoading(false));
  }, [id]);

  const handleDownload = async () => {
    if (!report?.pdf_url) return;
    try {
      const { url } = await apiFetch<{ url: string }>(
        `/v1/clinic/patient/consultations/${id}/pre-consult-report/download`,
      );
      await Linking.openURL(url);
    } catch {
      // Graceful — user can try again
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.forest} />
      </View>
    );
  }

  if (error || !report) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{error ?? 'Report not available yet.'}</Text>
        <Pressable onPress={() => router.back()} style={styles.backBtn} accessibilityLabel="Go back">
          <Text style={styles.backBtnText}>Go back</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Text style={styles.title}>Pre-Consultation Report</Text>
        <Text style={styles.generated}>Generated {formatDate(report.generated_at)}</Text>
      </View>

      <LabSummarySection summary={report.lab_summary} />
      <AdherenceSection summary={report.adherence_summary} />
      <WearableSection summary={report.wearable_summary} />
      <FlagsSection flags={report.patient_flags} />

      {report.pdf_url && (
        <Pressable
          onPress={handleDownload}
          style={styles.downloadBtn}
          accessibilityLabel="Download PDF report"
        >
          <Text style={styles.downloadBtnText}>Download PDF</Text>
        </Pressable>
      )}
    </ScrollView>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.ivory },
  content: { padding: spacing[4], paddingBottom: spacing[8] },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing[6] },
  header: { marginBottom: spacing[4] },
  title: { fontFamily: fontFamily.display, fontSize: F.h2, color: colors.ink },
  generated: { fontFamily: fontFamily.body, fontSize: F.caption, color: colors.stone, marginTop: spacing[1] },

  section: {
    backgroundColor: colors.white,
    borderRadius: borderRadius.lg,
    padding: spacing[4],
    marginBottom: spacing[4],
  },
  sectionTitle: {
    fontFamily: fontFamily.display,
    fontSize: F.bodyLg,
    color: colors.ink,
    marginBottom: spacing[3],
    borderBottomWidth: 1,
    borderBottomColor: colors.stone + '30',
    paddingBottom: spacing[2],
  },
  emptyText: { fontFamily: fontFamily.body, fontSize: F.caption, color: colors.stone },

  // Lab summary
  biomarkerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing[2],
    borderBottomWidth: 1,
    borderBottomColor: colors.stone + '20',
  },
  biomarkerFlagged: { backgroundColor: colors.saffron + '15', borderRadius: borderRadius.sm, paddingHorizontal: spacing[2] },
  biomarkerLeft: { flex: 1 },
  biomarkerName: { fontFamily: fontFamily.body, fontSize: F.caption, color: colors.ink, textTransform: 'capitalize' },
  biomarkerRef: { fontFamily: fontFamily.body, fontSize: F.caption, color: colors.stone, marginTop: 2 },
  biomarkerRight: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  biomarkerValue: { fontFamily: fontFamily.body, fontSize: F.caption, color: colors.ink },
  valueFlagHigh: { color: colors.terracotta },
  valueFlagLow: { color: colors.forest },
  trendSymbol: { fontFamily: fontFamily.body, fontSize: F.body, fontWeight: '600' },
  flagNote: { fontFamily: fontFamily.body, fontSize: F.caption, color: colors.stone, marginTop: spacing[2] },

  // Adherence
  adherenceBar: { height: 10, backgroundColor: colors.stone + '30', borderRadius: 999, overflow: 'hidden', marginBottom: spacing[2] },
  adherenceFill: { height: '100%', borderRadius: 999 },
  adherencePct: { fontFamily: fontFamily.display, fontSize: F.h2, marginBottom: spacing[2] },
  adherenceStats: { flexDirection: 'row', gap: spacing[4] },
  adherenceStat: { fontFamily: fontFamily.body, fontSize: F.caption, color: colors.stone },

  // Wearable
  statsRow: { flexDirection: 'row', gap: spacing[3] },
  statCard: { flex: 1, backgroundColor: colors.sage + '20', borderRadius: borderRadius.md, padding: spacing[3], alignItems: 'center' },
  statValue: { fontFamily: fontFamily.display, fontSize: F.h3, color: colors.ink },
  statLabel: { fontFamily: fontFamily.body, fontSize: F.caption, color: colors.stone, marginTop: spacing[1], textAlign: 'center' },

  // Flags
  flagItem: { flexDirection: 'row', gap: spacing[2], marginBottom: spacing[1] },
  flagBullet: { fontFamily: fontFamily.body, fontSize: F.caption, color: colors.forest },
  flagText: { fontFamily: fontFamily.body, fontSize: F.caption, color: colors.ink, flex: 1 },

  // Buttons
  downloadBtn: {
    backgroundColor: colors.forest,
    borderRadius: borderRadius.md,
    paddingVertical: spacing[3],
    alignItems: 'center',
    marginTop: spacing[2],
  },
  downloadBtnText: { fontFamily: fontFamily.body, fontSize: F.body, color: colors.white, fontWeight: '600' },
  backBtn: { marginTop: spacing[4] },
  backBtnText: { fontFamily: fontFamily.body, fontSize: F.caption, color: colors.forest },
  errorText: { fontFamily: fontFamily.body, fontSize: F.body, color: colors.terracotta, textAlign: 'center' },
});
