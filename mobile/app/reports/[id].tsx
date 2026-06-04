/**
 * Lab report detail screen.
 *
 * Shows:
 *   - Report metadata (lab name, date, file type)
 *   - OCR processing indicator while status is ocr_pending/ocr_processing
 *   - Parsed biomarker table when OCR is complete
 *   - Correction form for low-confidence fields (confidence < 0.60 block save)
 *   - Download button
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import {
  correctLabReport,
  getDownloadUrl,
  getLabReport,
  type Biomarker,
  type LabReport,
  type ParsedLabReport,
} from '../../lib/api/lab-reports';
import { colors, fontFamily, fontSize, spacing, borderRadius } from '../../lib/design-tokens';

// ── Constants ─────────────────────────────────────────────────────────────────

const POLL_INTERVAL_MS = 4000;
const PROCESSING_STATUSES = new Set(['ocr_pending', 'ocr_processing']);

// ── Helpers ───────────────────────────────────────────────────────────────────

function confidenceColor(c: number): string {
  if (c >= 0.85) return colors.forest;
  if (c >= 0.60) return colors.saffron;
  return colors.terracotta;
}

function flagLabel(flag: Biomarker['flag']): string {
  if (flag === 'high') return '↑';
  if (flag === 'low') return '↓';
  return '';
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

// ── Biomarker row ─────────────────────────────────────────────────────────────

function BiomarkerRow({
  biomarker,
  correctionValue,
  onChangeCorrectionValue,
}: {
  biomarker: Biomarker;
  correctionValue: string;
  onChangeCorrectionValue: (v: string) => void;
}) {
  const needsCorrection = biomarker.confidence < 0.60 || biomarker.needs_patient_correction;
  const lowConfidence = biomarker.confidence < 0.85;

  return (
    <View style={[styles.bioRow, needsCorrection && styles.bioRowHighlight]}>
      <View style={styles.bioHeader}>
        <Text style={styles.bioName}>{biomarker.name}</Text>
        {flagLabel(biomarker.flag) ? (
          <Text style={[styles.bioFlag, { color: biomarker.flag === 'high' ? colors.terracotta : colors.saffron }]}>
            {flagLabel(biomarker.flag)}
          </Text>
        ) : null}
        {lowConfidence && (
          <View style={[styles.confidenceBadge, { backgroundColor: confidenceColor(biomarker.confidence) + '20' }]}>
            <Text style={[styles.confidenceText, { color: confidenceColor(biomarker.confidence) }]}>
              {Math.round(biomarker.confidence * 100)}% confidence
            </Text>
          </View>
        )}
      </View>

      <View style={styles.bioValueRow}>
        {needsCorrection ? (
          <View style={styles.correctionField}>
            <Text style={styles.correctionLabel}>
              {biomarker.confidence < 0.60
                ? 'Please verify this value before saving:'
                : 'Low confidence — verify:'}
            </Text>
            <TextInput
              style={styles.correctionInput}
              value={correctionValue}
              onChangeText={onChangeCorrectionValue}
              placeholder={biomarker.value || '—'}
              placeholderTextColor={colors.stone}
              keyboardType="decimal-pad"
              accessibilityLabel={`Correct value for ${biomarker.name}`}
            />
            <Text style={styles.correctionUnit}>
              {biomarker.unit}
              {biomarker.ref_low && biomarker.ref_high
                ? `  ·  Ref: ${biomarker.ref_low}–${biomarker.ref_high}`
                : ''}
            </Text>
          </View>
        ) : (
          <>
            <Text style={styles.bioValue}>
              {biomarker.value} {biomarker.unit}
            </Text>
            {biomarker.ref_low && biomarker.ref_high && (
              <Text style={styles.bioRef}>
                Ref: {biomarker.ref_low}–{biomarker.ref_high}
              </Text>
            )}
          </>
        )}
      </View>
    </View>
  );
}

// ── Correction state builder ──────────────────────────────────────────────────

function buildInitialCorrections(parsed: ParsedLabReport): Record<number, string> {
  const map: Record<number, string> = {};
  parsed.biomarkers.forEach((b, i) => {
    if (b.confidence < 0.60 || b.needs_patient_correction) {
      map[i] = b.value;
    }
  });
  return map;
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function ReportDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();

  const [report, setReport] = useState<LabReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [corrections, setCorrections] = useState<Record<number, string>>({});
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchReport = useCallback(async () => {
    if (!id) return;
    try {
      const data = await getLabReport(id);
      setReport(data);
      if (data.parsed_json) {
        setCorrections((prev) =>
          Object.keys(prev).length === 0 ? buildInitialCorrections(data.parsed_json!) : prev,
        );
      }
      setError(null);
    } catch {
      setError('Could not load this report.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  // Poll while OCR is in progress
  useEffect(() => {
    void fetchReport();
  }, [fetchReport]);

  useEffect(() => {
    if (!report) return;
    if (PROCESSING_STATUSES.has(report.status)) {
      pollRef.current = setInterval(() => {
        void fetchReport();
      }, POLL_INTERVAL_MS);
    } else {
      if (pollRef.current) clearInterval(pollRef.current);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [report?.status, fetchReport]);

  const handleSaveCorrections = useCallback(async () => {
    if (!report?.parsed_json) return;

    // Build corrected parsed_json
    const updated: ParsedLabReport = {
      ...report.parsed_json,
      biomarkers: report.parsed_json.biomarkers.map((b, i) => {
        const corrected = corrections[i];
        if (corrected !== undefined) {
          return { ...b, value: corrected, needs_patient_correction: false };
        }
        return b;
      }),
    };

    // Block save if any confidence < 0.60 field is still blank
    const blocking = report.parsed_json.biomarkers.some(
      (b, i) => b.confidence < 0.60 && !corrections[i]?.trim(),
    );
    if (blocking) {
      Alert.alert(
        'Correction required',
        'Please fill in all highlighted fields before saving.',
      );
      return;
    }

    setSaving(true);
    try {
      const saved = await correctLabReport(report.id, updated);
      setReport(saved);
      Alert.alert('Saved', 'Your corrections have been saved.');
    } catch {
      Alert.alert('Error', 'Could not save corrections. Please try again.');
    } finally {
      setSaving(false);
    }
  }, [report, corrections]);

  const handleDownload = useCallback(async () => {
    if (!report) return;
    try {
      const { download_url } = await getDownloadUrl(report.id);
      await Linking.openURL(download_url);
    } catch {
      Alert.alert('Error', 'Could not generate download link.');
    }
  }, [report]);

  // ── Loading ────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.forest} />
      </View>
    );
  }

  if (error || !report) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{error ?? 'Report not found.'}</Text>
        <Pressable onPress={() => router.back()} style={styles.backLink}>
          <Text style={styles.backLinkText}>← Back</Text>
        </Pressable>
      </View>
    );
  }

  // ── OCR in progress ────────────────────────────────────────────────────────

  if (PROCESSING_STATUSES.has(report.status)) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.forest} />
        <Text style={styles.processingTitle}>Analysing your report…</Text>
        <Text style={styles.processingSub}>
          Our system is extracting your lab values. This usually takes under 60 seconds.
        </Text>
      </View>
    );
  }

  // ── OCR failed ─────────────────────────────────────────────────────────────

  if (report.status === 'ocr_failed') {
    return (
      <ScrollView style={styles.scroll} contentContainerStyle={styles.container}>
        <MetaSection report={report} onDownload={() => void handleDownload()} />
        <View style={styles.failedBox}>
          <Text style={styles.failedTitle}>Processing failed</Text>
          <Text style={styles.failedSub}>
            We couldn't automatically read this report. You can still download the original file
            above and share it with your doctor.
          </Text>
        </View>
      </ScrollView>
    );
  }

  // ── Results ────────────────────────────────────────────────────────────────

  const parsed = report.parsed_json;
  const hasCorrections = Object.keys(corrections).length > 0;

  return (
    <ScrollView style={styles.scroll} contentContainerStyle={styles.container}>
      <MetaSection report={report} onDownload={() => void handleDownload()} />

      {parsed ? (
        <>
          {parsed.lab_name ? (
            <View style={styles.labInfo}>
              <Text style={styles.labInfoLabel}>Lab</Text>
              <Text style={styles.labInfoValue}>{parsed.lab_name}</Text>
            </View>
          ) : null}

          {report.status === 'patient_review_needed' && (
            <View style={styles.reviewBanner}>
              <Text style={styles.reviewBannerText}>
                Some values need your confirmation before they're saved to your health record.
              </Text>
            </View>
          )}

          <Text style={styles.sectionTitle}>Biomarker Results</Text>

          {parsed.biomarkers.map((b, i) => (
            <BiomarkerRow
              key={`${b.name}-${i}`}
              biomarker={b}
              correctionValue={corrections[i] ?? b.value}
              onChangeCorrectionValue={(v) =>
                setCorrections((prev) => ({ ...prev, [i]: v }))
              }
            />
          ))}

          {parsed.biomarkers.length === 0 && (
            <Text style={styles.emptyBio}>No biomarker values were extracted.</Text>
          )}

          {(hasCorrections || report.status === 'patient_review_needed') && !report.patient_corrected && (
            <Pressable
              style={[styles.saveButton, saving && styles.disabled]}
              onPress={() => void handleSaveCorrections()}
              disabled={saving}
              accessibilityLabel="Save corrections"
            >
              {saving ? (
                <ActivityIndicator color={colors.white} />
              ) : (
                <Text style={styles.saveButtonText}>Save corrections</Text>
              )}
            </Pressable>
          )}

          {report.patient_corrected && (
            <View style={styles.correctedBadge}>
              <Text style={styles.correctedText}>✓ You've reviewed and corrected this report</Text>
            </View>
          )}

          {typeof parsed.overall_confidence === 'number' && (
            <Text style={styles.confidence}>
              Overall OCR confidence: {Math.round(parsed.overall_confidence * 100)}%
            </Text>
          )}
        </>
      ) : (
        <View style={styles.emptyState}>
          <Text style={styles.emptyStateText}>
            This report hasn't been processed yet. Pull down to refresh.
          </Text>
        </View>
      )}
    </ScrollView>
  );
}

// ── Meta section (shared between states) ──────────────────────────────────────

function MetaSection({ report, onDownload }: { report: LabReport; onDownload: () => void }) {
  return (
    <View style={styles.metaCard}>
      <View style={styles.metaRow}>
        <Text style={styles.metaLabel}>File</Text>
        <Text style={styles.metaValue} numberOfLines={1}>{report.original_filename}</Text>
      </View>
      {report.report_date && (
        <View style={styles.metaRow}>
          <Text style={styles.metaLabel}>Report date</Text>
          <Text style={styles.metaValue}>{report.report_date}</Text>
        </View>
      )}
      <View style={styles.metaRow}>
        <Text style={styles.metaLabel}>Uploaded</Text>
        <Text style={styles.metaValue}>{formatDate(report.created_at)}</Text>
      </View>
      <Pressable
        style={styles.downloadButton}
        onPress={onDownload}
        accessibilityLabel="Download original file"
      >
        <Text style={styles.downloadButtonText}>↓ Download original</Text>
      </Pressable>
    </View>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  scroll: {
    flex: 1,
    backgroundColor: colors.ivory,
  },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[4],
    paddingTop: spacing[4],
    paddingBottom: spacing[16],
    gap: spacing[4],
  },
  center: {
    flex: 1,
    backgroundColor: colors.ivory,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing[8],
    gap: spacing[4],
  },
  errorText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.terracotta,
    textAlign: 'center',
  },
  backLink: { alignItems: 'center' },
  backLinkText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
  },
  processingTitle: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h3,
    color: colors.forest,
    fontWeight: '500',
    textAlign: 'center',
  },
  processingSub: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    textAlign: 'center',
    lineHeight: 22,
  },
  metaCard: {
    backgroundColor: colors.white,
    borderRadius: borderRadius.lg,
    padding: spacing[4],
    gap: spacing[3],
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  metaLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    flex: 1,
  },
  metaValue: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.ink,
    fontWeight: '500',
    flex: 2,
    textAlign: 'right',
  },
  downloadButton: {
    borderWidth: 1,
    borderColor: colors.forest,
    borderRadius: borderRadius.md,
    paddingVertical: spacing[2],
    alignItems: 'center',
    marginTop: spacing[1],
  },
  downloadButtonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.forest,
    fontWeight: '600',
  },
  labInfo: {
    flexDirection: 'row',
    gap: spacing[3],
    alignItems: 'center',
  },
  labInfoLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
  },
  labInfoValue: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    fontWeight: '500',
  },
  reviewBanner: {
    backgroundColor: colors.saffron + '22',
    borderRadius: borderRadius.md,
    padding: spacing[4],
  },
  reviewBannerText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.ink,
    lineHeight: 20,
  },
  sectionTitle: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h3,
    color: colors.forest,
    fontWeight: '500',
  },
  bioRow: {
    backgroundColor: colors.white,
    borderRadius: borderRadius.lg,
    padding: spacing[4],
    gap: spacing[2],
  },
  bioRowHighlight: {
    borderWidth: 1,
    borderColor: colors.saffron + '60',
  },
  bioHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
    flexWrap: 'wrap',
  },
  bioName: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    fontWeight: '600',
    flex: 1,
  },
  bioFlag: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    fontWeight: '700',
  },
  confidenceBadge: {
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
    borderRadius: borderRadius.sm,
  },
  confidenceText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    fontWeight: '600',
  },
  bioValueRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: spacing[3],
  },
  bioValue: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.ink,
    fontWeight: '500',
  },
  bioRef: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
  },
  correctionField: {
    flex: 1,
    gap: spacing[2],
  },
  correctionLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.terracotta,
  },
  correctionInput: {
    borderWidth: 1,
    borderColor: colors.saffron,
    borderRadius: borderRadius.md,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    backgroundColor: colors.ivory,
  },
  correctionUnit: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
  },
  emptyBio: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    textAlign: 'center',
    paddingVertical: spacing[4],
  },
  saveButton: {
    backgroundColor: colors.forest,
    borderRadius: borderRadius.lg,
    paddingVertical: spacing[4],
    alignItems: 'center',
  },
  saveButtonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '700',
    color: colors.white,
  },
  disabled: { opacity: 0.45 },
  correctedBadge: {
    backgroundColor: colors.forest + '18',
    borderRadius: borderRadius.md,
    padding: spacing[3],
    alignItems: 'center',
  },
  correctedText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.forest,
    fontWeight: '600',
  },
  confidence: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    textAlign: 'right',
  },
  failedBox: {
    backgroundColor: colors.terracotta + '18',
    borderRadius: borderRadius.lg,
    padding: spacing[4],
    gap: spacing[2],
  },
  failedTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.terracotta,
    fontWeight: '600',
  },
  failedSub: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    lineHeight: 22,
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: spacing[8],
  },
  emptyStateText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    textAlign: 'center',
    lineHeight: 22,
  },
});
