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
import { useThemePreference } from '../../lib/theme-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { CaptureGuard } from '../../components/ui/CaptureGuard';
import {
  correctLabReport,
  getDownloadUrl,
  getLabReport,
  type Biomarker,
  type LabReport,
  type ParsedLabReport,
} from '../../lib/api/lab-reports';
import { borderRadius, colors, fontFamily, fontSize, shadow, spacing, withAlpha } from '../../lib/design-tokens';

const POLL_INTERVAL_MS = 4000;
const PROCESSING_STATUSES = new Set(['ocr_pending', 'ocr_processing']);

function confidenceColor(c: number): string {
  if (c >= 0.85) return colors.jade;
  if (c >= 0.60) return colors.saffron;
  return colors.alert;
}
function flagLabel(f: Biomarker['flag']): string {
  if (f === 'high') return '↑';
  if (f === 'low') return '↓';
  return '';
}
function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
}
function buildInitialCorrections(p: ParsedLabReport): Record<number, string> {
  const m: Record<number, string> = {};
  p.biomarkers.forEach((b, i) => { if (b.confidence < 0.60 || b.needs_patient_correction) m[i] = b.value; });
  return m;
}

// ── Biomarker row ─────────────────────────────────────────────────────────────

function BiomarkerRow({
  biomarker, correctionValue, onChangeCorrectionValue,
  isDark, textPri, textSub, cardBg, cardBdr,
}: {
  biomarker: Biomarker; correctionValue: string;
  onChangeCorrectionValue: (v: string) => void;
  isDark: boolean; textPri: string; textSub: string; cardBg: string; cardBdr: string;
}) {
  const needsCorrection = biomarker.confidence < 0.60 || biomarker.needs_patient_correction;
  const lowConfidence   = biomarker.confidence < 0.85;
  const flagColor = biomarker.flag === 'high' ? colors.alert : colors.saffron;

  return (
    <View style={[b.row, { backgroundColor: cardBg, borderColor: needsCorrection ? colors.saffron + '50' : cardBdr, borderWidth: needsCorrection ? 1.5 : 1 }]}>
      <View style={b.header}>
        <Text style={[b.name, { color: textPri }]}>{biomarker.name}</Text>
        {flagLabel(biomarker.flag) ? (
          <Text style={[b.flag, { color: flagColor }]}>{flagLabel(biomarker.flag)}</Text>
        ) : null}
        {lowConfidence && (
          <View style={[b.confBadge, { backgroundColor: confidenceColor(biomarker.confidence) + '20' }]}>
            <Text style={[b.confText, { color: confidenceColor(biomarker.confidence) }]}>
              {Math.round(biomarker.confidence * 100)}% confidence
            </Text>
          </View>
        )}
      </View>
      {needsCorrection ? (
        <View style={b.correction}>
          <Text style={[b.corrLabel, { color: colors.saffron }]}>
            {biomarker.confidence < 0.60 ? 'Please verify this value:' : 'Low confidence — verify:'}
          </Text>
          <TextInput
            style={[b.corrInput, { backgroundColor: isDark ? colors.forestSurfaceRaised : colors.ivory, borderColor: colors.saffron + '60', color: textPri }]}
            value={correctionValue}
            onChangeText={onChangeCorrectionValue}
            placeholder={biomarker.value || '—'}
            placeholderTextColor={textSub}
            keyboardType="decimal-pad"
            accessibilityLabel={`Correct value for ${biomarker.name}`}
          />
          <Text style={[b.corrUnit, { color: textSub }]}>
            {biomarker.unit}{biomarker.ref_low && biomarker.ref_high ? `  ·  Ref: ${biomarker.ref_low}–${biomarker.ref_high}` : ''}
          </Text>
        </View>
      ) : (
        <View style={b.valueRow}>
          <Text style={[b.value, { color: textPri }]}>{biomarker.value} {biomarker.unit}</Text>
          {biomarker.ref_low && biomarker.ref_high && (
            <Text style={[b.ref, { color: textSub }]}>Ref: {biomarker.ref_low}–{biomarker.ref_high}</Text>
          )}
        </View>
      )}
    </View>
  );
}

const b = StyleSheet.create({
  row:       { borderRadius: borderRadius.xl, padding: spacing[4], gap: spacing[2] },
  header:    { flexDirection: 'row', alignItems: 'center', gap: spacing[2], flexWrap: 'wrap' },
  name:      { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600', flex: 1 },
  flag:      { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700' },
  confBadge: { paddingHorizontal: spacing[2], paddingVertical: 2, borderRadius: borderRadius.full },
  confText:  { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontWeight: '700' },
  valueRow:  { flexDirection: 'row', alignItems: 'baseline', gap: spacing[3] },
  value:     { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '500' },
  ref:       { fontFamily: fontFamily.body, fontSize: fontSize.caption },
  correction: { gap: spacing[2] },
  corrLabel:  { fontFamily: fontFamily.body, fontSize: fontSize.caption },
  corrInput:  { borderWidth: 1, borderRadius: borderRadius.xl, paddingHorizontal: spacing[4], paddingVertical: spacing[3], fontFamily: fontFamily.body, fontSize: fontSize.body },
  corrUnit:   { fontFamily: fontFamily.body, fontSize: fontSize.caption },
});

// ── Meta card ─────────────────────────────────────────────────────────────────

function MetaCard({ report, onDownload, isDark, textPri, textSub, cardBg, cardBdr }: {
  report: LabReport; onDownload: () => void;
  isDark: boolean; textPri: string; textSub: string; cardBg: string; cardBdr: string;
}) {
  const dlScale = useSharedValue(1);
  const dlAnim  = useAnimatedStyle(() => ({ transform: [{ scale: dlScale.value }] }));
  return (
    <View style={[styles.card, { backgroundColor: cardBg, borderColor: cardBdr }]}>
      <View style={styles.metaRow}>
        <Text style={[styles.metaLabel, { color: textSub }]}>File</Text>
        <Text style={[styles.metaValue, { color: textPri }]} numberOfLines={1}>{report.original_filename}</Text>
      </View>
      {report.report_date && (
        <View style={styles.metaRow}>
          <Text style={[styles.metaLabel, { color: textSub }]}>Report date</Text>
          <Text style={[styles.metaValue, { color: textPri }]}>{report.report_date}</Text>
        </View>
      )}
      <View style={styles.metaRow}>
        <Text style={[styles.metaLabel, { color: textSub }]}>Uploaded</Text>
        <Text style={[styles.metaValue, { color: textPri }]}>{formatDate(report.created_at)}</Text>
      </View>
      <Animated.View style={dlAnim}>
        <Pressable
          style={[styles.dlBtn, { borderColor: isDark ? 'rgba(255,255,255,0.12)' : colors.borderLight }]}
          onPress={onDownload}
          onPressIn={() => { dlScale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
          onPressOut={() => { dlScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
          accessibilityLabel="Download original file"
        >
          <Text style={[styles.dlBtnText, { color: textPri }]}>↓ Download original</Text>
        </Pressable>
      </Animated.View>
    </View>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function ReportDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const isDark = useThemePreference().colorScheme === 'dark';

  const [report,      setReport]      = useState<LabReport | null>(null);
  const [loading,     setLoading]     = useState(true);
  const [saving,      setSaving]      = useState(false);
  const [error,       setError]       = useState<string | null>(null);
  const [corrections, setCorrections] = useState<Record<number, string>>({});
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchReport = useCallback(async () => {
    if (!id) return;
    try {
      const data = await getLabReport(id);
      setReport(data);
      if (data.parsed_json) {
        setCorrections(prev => Object.keys(prev).length === 0 ? buildInitialCorrections(data.parsed_json!) : prev);
      }
      setError(null);
    } catch {
      setError('Could not load this report.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { void fetchReport(); }, [fetchReport]);
  useEffect(() => {
    if (!report) return;
    if (PROCESSING_STATUSES.has(report.status)) {
      pollRef.current = setInterval(() => { void fetchReport(); }, POLL_INTERVAL_MS);
    } else {
      if (pollRef.current) clearInterval(pollRef.current);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [report?.status, fetchReport]);

  const handleSaveCorrections = useCallback(async () => {
    if (!report?.parsed_json) return;
    const updated: ParsedLabReport = {
      ...report.parsed_json,
      biomarkers: report.parsed_json.biomarkers.map((bm, i) => {
        const corrected = corrections[i];
        return corrected !== undefined ? { ...bm, value: corrected, needs_patient_correction: false } : bm;
      }),
    };
    const blocking = report.parsed_json.biomarkers.some((bm, i) => bm.confidence < 0.60 && !corrections[i]?.trim());
    if (blocking) { Alert.alert('Correction required', 'Please fill in all highlighted fields before saving.'); return; }
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

  const saveScale = useSharedValue(1);
  const saveAnim  = useAnimatedStyle(() => ({ transform: [{ scale: saveScale.value }] }));

  const bg      = isDark ? colors.forestInk       : colors.ivory;
  const textPri = isDark ? colors.ivoryText       : colors.ink;
  const textSub = isDark ? colors.stoneDim        : colors.stone;
  const cardBg  = isDark ? colors.forestSurface   : colors.white;
  const cardBdr = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(15,61,46,0.06)';

  if (loading) {
    return <View style={[styles.center, { backgroundColor: bg }]}><ActivityIndicator color={colors.jade} /></View>;
  }
  if (error || !report) {
    return (
      <View style={[styles.center, { backgroundColor: bg }]}>
        <Text style={[styles.errorText, { color: colors.alert }]}>{error ?? 'Report not found.'}</Text>
        <Pressable onPress={() => router.back()}><Text style={[styles.backLink, { color: colors.jade }]}>← Back</Text></Pressable>
      </View>
    );
  }
  if (PROCESSING_STATUSES.has(report.status)) {
    return (
      <View style={[styles.center, { backgroundColor: bg }]}>
        <ActivityIndicator size="large" color={colors.jade} />
        <Text style={[styles.processingTitle, { color: textPri }]}>Analysing your report…</Text>
        <Text style={[styles.processingSub, { color: textSub }]}>
          Our system is extracting your lab values. This usually takes under 60 seconds.
        </Text>
      </View>
    );
  }
  if (report.status === 'ocr_failed') {
    return (
      <ScrollView style={[styles.scroll, { backgroundColor: bg }]} contentContainerStyle={styles.container}>
        <MetaCard report={report} onDownload={() => void handleDownload()} isDark={isDark} textPri={textPri} textSub={textSub} cardBg={cardBg} cardBdr={cardBdr} />
        <View style={[styles.failedBox, { backgroundColor: colors.alert + '12', borderColor: colors.alert + '30' }]}>
          <Text style={[styles.failedTitle, { color: colors.alert }]}>Processing failed</Text>
          <Text style={[styles.failedSub, { color: textSub }]}>
            We couldn't automatically read this report. You can still download the original file and share it with your doctor.
          </Text>
        </View>
      </ScrollView>
    );
  }

  const parsed        = report.parsed_json;
  const hasCorrections = Object.keys(corrections).length > 0;

  return (
    <ScrollView style={[styles.scroll, { backgroundColor: bg }]} contentContainerStyle={styles.container}>
      {/* Lab values are PHI — block screen capture while focused */}
      <CaptureGuard />
      <MetaCard report={report} onDownload={() => void handleDownload()} isDark={isDark} textPri={textPri} textSub={textSub} cardBg={cardBg} cardBdr={cardBdr} />

      {parsed ? (
        <>
          {parsed.lab_name && (
            <View style={styles.labInfo}>
              <Text style={[styles.labLabel, { color: textSub }]}>Lab</Text>
              <Text style={[styles.labValue, { color: textPri }]}>{parsed.lab_name}</Text>
            </View>
          )}

          {report.status === 'patient_review_needed' && (
            <View style={[styles.reviewBanner, { backgroundColor: colors.saffron + '15', borderColor: colors.saffron + '40' }]}>
              <Text style={[styles.reviewText, { color: textPri }]}>
                Some values need your confirmation before they're saved to your health record.
              </Text>
            </View>
          )}

          <Text style={[styles.sectionTitle, { color: textPri }]}>Biomarker Results</Text>

          <View style={styles.bioList}>
            {parsed.biomarkers.map((bm, i) => (
              <BiomarkerRow
                key={`${bm.name}-${i}`}
                biomarker={bm}
                correctionValue={corrections[i] ?? bm.value}
                onChangeCorrectionValue={v => setCorrections(prev => ({ ...prev, [i]: v }))}
                isDark={isDark} textPri={textPri} textSub={textSub} cardBg={cardBg} cardBdr={cardBdr}
              />
            ))}
            {parsed.biomarkers.length === 0 && (
              <Text style={[styles.emptyBio, { color: textSub }]}>No biomarker values were extracted.</Text>
            )}
          </View>

          {(hasCorrections || report.status === 'patient_review_needed') && !report.patient_corrected && (
            <Animated.View style={saveAnim}>
              <Pressable
                style={[styles.saveBtn, saving && styles.disabled]}
                onPress={() => void handleSaveCorrections()}
                onPressIn={() => { saveScale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
                onPressOut={() => { saveScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
                disabled={saving}
                accessibilityLabel="Save corrections"
              >
                {saving ? <ActivityIndicator color={colors.ivoryText} size="small" /> : <Text style={styles.saveBtnText}>Save corrections</Text>}
              </Pressable>
            </Animated.View>
          )}

          {report.patient_corrected && (
            <View style={[styles.correctedBadge, { backgroundColor: colors.jade + '15' }]}>
              <Text style={[styles.correctedText, { color: colors.jade }]}>✓ You've reviewed and corrected this report</Text>
            </View>
          )}

          {typeof parsed.overall_confidence === 'number' && (
            <Text style={[styles.confidence, { color: textSub }]}>
              Overall OCR confidence: {Math.round(parsed.overall_confidence * 100)}%
            </Text>
          )}
        </>
      ) : (
        <Text style={[styles.emptyState, { color: textSub }]}>This report hasn't been processed yet. Pull down to refresh.</Text>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1 },
  container: { flexGrow: 1, paddingHorizontal: spacing[4], paddingTop: spacing[4], paddingBottom: spacing[16], gap: spacing[4] },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: spacing[8], gap: spacing[4] },

  card: {
    borderRadius: borderRadius.xxl,
    overflow: 'hidden',
    borderWidth: 1,
    boxShadow: shadow.md,
  },
  metaRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', paddingHorizontal: spacing[5], paddingVertical: spacing[3] },
  metaLabel: { fontFamily: fontFamily.body, fontSize: fontSize.caption, flex: 1 },
  metaValue: { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontWeight: '600', flex: 2, textAlign: 'right' },
  dlBtn: { marginHorizontal: spacing[5], marginBottom: spacing[4], height: 44, borderWidth: 1, borderRadius: borderRadius.xl, alignItems: 'center', justifyContent: 'center' },
  dlBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.sm, fontWeight: '600' },

  labInfo: { flexDirection: 'row', gap: spacing[3], alignItems: 'center' },
  labLabel: { fontFamily: fontFamily.body, fontSize: fontSize.caption },
  labValue: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600' },

  reviewBanner: { borderRadius: borderRadius.xl, borderWidth: 1, padding: spacing[4] },
  reviewText:   { fontFamily: fontFamily.body, fontSize: fontSize.caption, lineHeight: 20 },

  sectionTitle: { fontFamily: fontFamily.display, fontSize: fontSize.h3, fontWeight: '500' },

  bioList: { gap: spacing[3] },
  emptyBio: { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center', paddingVertical: spacing[4] },

  saveBtn: {
    height: 56, backgroundColor: colors.forest, borderRadius: borderRadius.xxl,
    alignItems: 'center', justifyContent: 'center',
    boxShadow: `0 8px 16px ${withAlpha(colors.forest, 0.30)}`,
  },
  disabled:    { opacity: 0.45 },
  saveBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700', color: colors.ivoryText },

  correctedBadge: { borderRadius: borderRadius.xl, padding: spacing[3], alignItems: 'center' },
  correctedText:  { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontWeight: '700' },

  confidence: { fontFamily: fontFamily.body, fontSize: fontSize.caption, textAlign: 'right' },

  failedBox:   { borderRadius: borderRadius.xl, borderWidth: 1, padding: spacing[4], gap: spacing[2] },
  failedTitle: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700' },
  failedSub:   { fontFamily: fontFamily.body, fontSize: fontSize.body, lineHeight: 22 },

  emptyState:       { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center', lineHeight: 22, paddingVertical: spacing[8] },
  processingTitle:  { fontFamily: fontFamily.display, fontSize: fontSize.h3, fontWeight: '500', textAlign: 'center' },
  processingSub:    { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center', lineHeight: 22 },
  errorText:        { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center' },
  backLink:         { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontWeight: '600' },
});
