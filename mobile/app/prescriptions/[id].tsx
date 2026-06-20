import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useThemePreference } from '../../lib/theme-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { CaptureGuard } from '../../components/ui/CaptureGuard';
import { getPrescription, getPrescriptionPdfUrl, type Prescription, type PrescriptionItem } from '../../lib/api/prescriptions';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

function formatDate(iso: string | null) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
}
function formatDateTime(iso: string | null) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}
function capitalize(s: string) { return s.charAt(0).toUpperCase() + s.slice(1); }

// ── Medication card ───────────────────────────────────────────────────────────

function MedicationCard({ item, isDark, textPri, textSub, cardBg, cardBdr }: {
  item: PrescriptionItem; isDark: boolean; textPri: string; textSub: string; cardBg: string; cardBdr: string;
}) {
  const duration = item.duration_days != null ? `${item.duration_days} days` : 'Ongoing';
  // Composed timing string (frequency + time-of-day + food relation) — its own
  // full-width row since it can be longer than the short Dose/Duration chips.
  const frequency = item.frequency ?? '—';
  return (
    <View style={[med.card, { backgroundColor: cardBg, borderColor: cardBdr }]}>
      <Text style={[med.name, { color: textPri }]}>{item.drug_generic_name}</Text>
      <Text style={[med.form, { color: textSub }]}>{capitalize(item.drug_form)}</Text>
      <View style={[med.detailRow, { borderTopColor: isDark ? 'rgba(255,255,255,0.06)' : colors.borderLight }]}>
        {[
          { label: 'Dose',     value: item.dosage },
          { label: 'Duration', value: duration },
        ].map(({ label, value }) => (
          <View key={label} style={med.chip}>
            <Text style={[med.chipLabel, { color: textSub }]}>{label}</Text>
            <Text style={[med.chipValue, { color: textPri }]}>{value}</Text>
          </View>
        ))}
      </View>
      <View style={med.chip}>
        <Text style={[med.chipLabel, { color: textSub }]}>How to take</Text>
        <Text style={[med.chipValue, { color: textPri }]}>{frequency}</Text>
      </View>
      {item.instructions && <Text style={[med.instructions, { color: textSub }]}>{item.instructions}</Text>}
      {item.refill_allowed && <Text style={[med.refill, { color: colors.jade }]}>↻ Refill allowed</Text>}
    </View>
  );
}

const med = StyleSheet.create({
  card: {
    borderRadius: borderRadius.xl,
    padding: spacing[4],
    gap: spacing[2],
    borderWidth: 1,
    boxShadow: '0 4px 10px rgba(0,0,0,0.06)',
  },
  name: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700' },
  form: { fontFamily: fontFamily.body, fontSize: fontSize.caption, marginTop: -spacing[1] },
  detailRow: {
    flexDirection: 'row',
    gap: spacing[3],
    borderTopWidth: 1,
    paddingTop: spacing[3],
    marginTop: spacing[1],
    flexWrap: 'wrap',
  },
  chip: { gap: 2 },
  chipLabel: { fontFamily: fontFamily.body, fontSize: fontSize.xs, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5 },
  chipValue: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '500' },
  instructions: { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontStyle: 'italic', lineHeight: 18 },
  refill: { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontWeight: '700' },
});

// ── Main screen ───────────────────────────────────────────────────────────────

export default function PrescriptionDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const isDark = useThemePreference().colorScheme === 'dark';

  const [prescription, setPrescription] = useState<Prescription | null>(null);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);

  const fetchPrescription = useCallback(async () => {
    if (!id) return;
    try {
      const data = await getPrescription(id as string);
      setPrescription(data);
      setError(null);
    } catch {
      setError('Could not load this prescription.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { void fetchPrescription(); }, [fetchPrescription]);

  const handleDownloadPdf = useCallback(async () => {
    if (!prescription) return;
    setPdfLoading(true);
    try {
      const { download_url } = await getPrescriptionPdfUrl(prescription.id);
      await Linking.openURL(download_url);
    } catch {
      Alert.alert('PDF not ready', 'The PDF is still being generated. Please try again in a few seconds.');
    } finally {
      setPdfLoading(false);
    }
  }, [prescription]);

  const pdfScale = useSharedValue(1);
  const pdfAnim  = useAnimatedStyle(() => ({ transform: [{ scale: pdfScale.value }] }));

  const bg      = isDark ? colors.forestInk     : colors.ivory;
  const textPri = isDark ? colors.ivoryText        : colors.ink;
  const textSub = isDark ? colors.stoneDim    : colors.stone;
  const cardBg  = isDark ? colors.forestSurface : colors.white;
  const cardBdr = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)';
  const divider = isDark ? 'rgba(255,255,255,0.08)' : colors.borderLight;

  if (loading) return <View style={[styles.center, { backgroundColor: bg }]}><ActivityIndicator color={colors.jade} /></View>;
  if (error || !prescription) {
    return (
      <View style={[styles.center, { backgroundColor: bg }]}>
        <Text style={[styles.errorText, { color: colors.alert }]}>{error ?? 'Prescription not found.'}</Text>
        <Pressable onPress={() => router.back()}><Text style={[styles.backLink, { color: colors.jade }]}>← Back</Text></Pressable>
      </View>
    );
  }

  const sortedItems = [...prescription.items].sort((a, b2) => a.order_index - b2.order_index);

  return (
    <ScrollView style={[styles.scroll, { backgroundColor: bg }]} contentContainerStyle={styles.container}>
      {/* Prescription contents are PHI — block screen capture while focused */}
      <CaptureGuard />

      {/* Download PDF */}
      <Animated.View style={pdfAnim}>
        <Pressable
          style={[styles.pdfBtn, { borderColor: isDark ? 'rgba(255,255,255,0.12)' : colors.borderLight }, pdfLoading && styles.disabled]}
          onPress={() => void handleDownloadPdf()}
          onPressIn={() => { pdfScale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
          onPressOut={() => { pdfScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
          disabled={pdfLoading}
          accessibilityLabel="Download prescription PDF"
        >
          {pdfLoading ? (
            <ActivityIndicator color={textPri} size="small" />
          ) : (
            <Text style={[styles.pdfBtnText, { color: textPri }]}>↓ Download PDF</Text>
          )}
        </Pressable>
      </Animated.View>

      {/* Clinic letterhead */}
      <View style={[styles.letterhead, { borderBottomColor: isDark ? colors.jade + '40' : colors.forest }]}>
        <View>
          <Text style={[styles.clinicName, { color: isDark ? colors.jade : colors.ink }]}>Kyros Clinic</Text>
          <Text style={[styles.clinicSub, { color: textSub }]}>Digital Health Clinic · kyrosclinic.com</Text>
        </View>
        <View style={styles.clinicRight}>
          <Text style={[styles.clinicMeta, { color: textSub }]}>Issued {formatDate(prescription.signed_at)}</Text>
          {prescription.version > 1 && <Text style={[styles.clinicMeta, { color: textSub }]}>Version {prescription.version}</Text>}
        </View>
      </View>

      {/* Signed chip */}
      <View style={[styles.signedChip, { backgroundColor: colors.jade + '15' }]}>
        <Text style={[styles.signedText, { color: colors.jade }]}>
          ✓ Digitally signed {formatDateTime(prescription.signed_at)}
        </Text>
      </View>

      {/* Diagnosis */}
      {prescription.diagnosis_note && (
        <View style={[styles.infoBlock, { backgroundColor: cardBg, borderColor: cardBdr }]}>
          <Text style={[styles.infoLabel, { color: textSub }]}>Diagnosis / Chief Complaint</Text>
          <Text style={[styles.infoValue, { color: textPri }]}>{prescription.diagnosis_note}</Text>
        </View>
      )}

      {/* Medications */}
      <View style={styles.rxSection}>
        <Text style={[styles.rxSymbol, { color: isDark ? colors.jade : colors.ink }]}>℞</Text>
        {sortedItems.map(item => (
          <MedicationCard key={item.id} item={item} isDark={isDark} textPri={textPri} textSub={textSub} cardBg={cardBg} cardBdr={cardBdr} />
        ))}
      </View>

      {/* General instructions */}
      {prescription.general_instructions && (
        <View style={[styles.infoBlock, { backgroundColor: cardBg, borderColor: cardBdr }]}>
          <Text style={[styles.infoLabel, { color: textSub }]}>General Instructions</Text>
          <Text style={[styles.infoValue, { color: textPri }]}>{prescription.general_instructions}</Text>
        </View>
      )}

      {/* Version history */}
      {prescription.version > 1 && (
        <View style={styles.timelineSection}>
          <Text style={[styles.timelineTitle, { color: textPri }]}>Dosage history</Text>
          <View style={styles.timelineItem}>
            <View style={[styles.timelineDot, { backgroundColor: colors.jade }]} />
            <Text style={[styles.timelineText, { color: textSub }]}>
              This is version {prescription.version}. Previous versions are preserved in your records.
            </Text>
          </View>
        </View>
      )}

      {/* Footer */}
      <View style={[styles.footer, { borderTopColor: divider }]}>
        <Text style={[styles.footerText, { color: textSub }]}>
          Original digital prescription. Verify at kyrosclinic.com/verify/{prescription.id}
        </Text>
      </View>

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1 },
  container: { flexGrow: 1, paddingHorizontal: spacing[5], paddingTop: spacing[4], paddingBottom: spacing[16], gap: spacing[4] },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing[4], paddingHorizontal: spacing[8] },
  errorText: { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center' },
  backLink:  { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontWeight: '600' },

  pdfBtn: {
    height: 48,
    borderWidth: 1,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pdfBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600' },
  disabled: { opacity: 0.45 },

  letterhead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', borderBottomWidth: 2, paddingBottom: spacing[3] },
  clinicName: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '800' },
  clinicSub:  { fontFamily: fontFamily.body, fontSize: fontSize.caption, marginTop: 2 },
  clinicRight:{ alignItems: 'flex-end', gap: 2 },
  clinicMeta: { fontFamily: fontFamily.body, fontSize: fontSize.caption },

  signedChip: { alignSelf: 'flex-start', borderRadius: borderRadius.full, paddingHorizontal: spacing[3], paddingVertical: spacing[1] },
  signedText: { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontWeight: '700' },

  infoBlock: {
    borderRadius: borderRadius.xl,
    padding: spacing[4],
    gap: spacing[1],
    borderWidth: 1,
    boxShadow: '0 4px 10px rgba(0,0,0,0.06)',
  },
  infoLabel: { fontFamily: fontFamily.body, fontSize: fontSize.xs, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5 },
  infoValue: { fontFamily: fontFamily.body, fontSize: fontSize.body, lineHeight: 22 },

  rxSection: { gap: spacing[3] },
  rxSymbol:  { fontFamily: fontFamily.body, fontSize: 28, fontWeight: '700' },

  timelineSection: { gap: spacing[2] },
  timelineTitle:   { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '700' },
  timelineItem:    { flexDirection: 'row', gap: spacing[3], alignItems: 'flex-start' },
  timelineDot:     { width: 8, height: 8, borderRadius: 4, marginTop: 6, flexShrink: 0 },
  timelineText:    { flex: 1, fontFamily: fontFamily.body, fontSize: fontSize.body, lineHeight: 22 },

  footer:     { borderTopWidth: 1, paddingTop: spacing[3] },
  footerText: { fontFamily: fontFamily.body, fontSize: fontSize.caption, textAlign: 'center', lineHeight: 18 },
});
