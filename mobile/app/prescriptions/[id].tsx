/**
 * Prescription detail screen — app/prescriptions/[id].tsx
 *
 * Shows the full clinical prescription document:
 *   - Clinic header strip (Kyros letterhead)
 *   - Doctor block (name, NMC reg, signed chip)
 *   - Patient block
 *   - Each medication in structured card format
 *   - General instructions
 *   - Dosage change history (previous versions)
 *   - Download PDF button
 */

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
import { useLocalSearchParams, useRouter } from 'expo-router';

import {
  getPrescription,
  getPrescriptionPdfUrl,
  type Prescription,
  type PrescriptionItem,
} from '../../lib/api/prescriptions';
import {
  borderRadius,
  colors,
  fontFamily,
  fontSize,
  spacing,
} from '../../lib/design-tokens';

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

// ── Medication row ────────────────────────────────────────────────────────────

function MedicationCard({ item }: { item: PrescriptionItem }) {
  const duration = item.duration_days != null
    ? `${item.duration_days} days`
    : 'Ongoing (continues)';

  return (
    <View style={styles.medCard}>
      <Text style={styles.medName}>{item.drug_generic_name}</Text>
      <Text style={styles.medForm}>{capitalize(item.drug_form)}</Text>
      <View style={styles.medDetailRow}>
        <Text style={styles.medDetail}>
          <Text style={styles.medLabel}>Dose: </Text>{item.dosage}
          {'  '}
          <Text style={styles.medLabel}>Frequency: </Text>{item.frequency}
          {'  '}
          <Text style={styles.medLabel}>Duration: </Text>{duration}
        </Text>
      </View>
      {item.instructions ? (
        <Text style={styles.medInstructions}>{item.instructions}</Text>
      ) : null}
      {item.refill_allowed && (
        <Text style={styles.refillNote}>Refill allowed</Text>
      )}
    </View>
  );
}

// ── Dosage change timeline ────────────────────────────────────────────────────

function DosageTimeline({ version }: { version: number }) {
  if (version <= 1) return null;

  return (
    <View style={styles.timelineSection}>
      <Text style={styles.sectionTitle}>Dosage history</Text>
      <View style={styles.timelineItem}>
        <View style={styles.timelineDot} />
        <Text style={styles.timelineText}>
          This is version {version} of this prescription.
          Previous versions are preserved in your records.
        </Text>
      </View>
    </View>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function PrescriptionDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();

  const [prescription, setPrescription] = useState<Prescription | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
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

  useEffect(() => {
    void fetchPrescription();
  }, [fetchPrescription]);

  const handleDownloadPdf = useCallback(async () => {
    if (!prescription) return;
    setPdfLoading(true);
    try {
      const { download_url } = await getPrescriptionPdfUrl(prescription.id);
      await Linking.openURL(download_url);
    } catch {
      Alert.alert(
        'PDF not ready',
        'The PDF is still being generated. Please try again in a few seconds.',
      );
    } finally {
      setPdfLoading(false);
    }
  }, [prescription]);

  // ── Loading ────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.forest} />
      </View>
    );
  }

  if (error || !prescription) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{error ?? 'Prescription not found.'}</Text>
        <Pressable onPress={() => router.back()} style={styles.backLink}>
          <Text style={styles.backLinkText}>← Back</Text>
        </Pressable>
      </View>
    );
  }

  const sortedItems = [...prescription.items].sort((a, b) => a.order_index - b.order_index);

  return (
    <ScrollView style={styles.scroll} contentContainerStyle={styles.container}>
      {/* Download PDF button — top */}
      <Pressable
        style={[styles.pdfBtn, pdfLoading && styles.disabled]}
        onPress={() => void handleDownloadPdf()}
        disabled={pdfLoading}
        accessibilityLabel="Download prescription PDF"
      >
        {pdfLoading ? (
          <ActivityIndicator color={colors.forest} size="small" />
        ) : (
          <Text style={styles.pdfBtnText}>↓ Download PDF</Text>
        )}
      </Pressable>

      {/* Clinic header */}
      <View style={styles.clinicHeader}>
        <View>
          <Text style={styles.clinicName}>Kyros Clinic</Text>
          <Text style={styles.clinicSub}>Digital Health Clinic · kyros.clinic</Text>
        </View>
        <View style={styles.clinicRight}>
          <Text style={styles.clinicMeta}>
            Issued {formatDate(prescription.signed_at)}
          </Text>
          {prescription.version > 1 && (
            <Text style={styles.clinicMeta}>Version {prescription.version}</Text>
          )}
        </View>
      </View>

      {/* Signed chip */}
      <View style={styles.signedChip}>
        <Text style={styles.signedChipText}>✓ Digitally signed {formatDateTime(prescription.signed_at)}</Text>
      </View>

      {/* Diagnosis */}
      {prescription.diagnosis_note ? (
        <View style={styles.infoBlock}>
          <Text style={styles.infoLabel}>Diagnosis / Chief Complaint</Text>
          <Text style={styles.infoValue}>{prescription.diagnosis_note}</Text>
        </View>
      ) : null}

      {/* Medications */}
      <View style={styles.rxSection}>
        <Text style={styles.rxSymbol}>℞</Text>
        {sortedItems.map((item) => (
          <MedicationCard key={item.id} item={item} />
        ))}
      </View>

      {/* General instructions */}
      {prescription.general_instructions ? (
        <View style={styles.infoBlock}>
          <Text style={styles.infoLabel}>General Instructions</Text>
          <Text style={styles.infoValue}>{prescription.general_instructions}</Text>
        </View>
      ) : null}

      {/* Dosage change timeline */}
      <DosageTimeline version={prescription.version} />

      {/* Footer */}
      <View style={styles.footer}>
        <Text style={styles.footerText}>
          Original digital prescription. Verify at kyros.clinic/verify/{prescription.id}
        </Text>
      </View>

      {/* Download PDF button — bottom */}
      <Pressable
        style={[styles.pdfBtn, pdfLoading && styles.disabled]}
        onPress={() => void handleDownloadPdf()}
        disabled={pdfLoading}
        accessibilityLabel="Download prescription PDF"
      >
        <Text style={styles.pdfBtnText}>↓ Download PDF</Text>
      </Pressable>
    </ScrollView>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  scroll: {
    flex: 1,
    backgroundColor: colors.white,
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
    backgroundColor: colors.white,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing[4],
    paddingHorizontal: spacing[8],
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
  pdfBtn: {
    borderWidth: 1,
    borderColor: colors.forest,
    borderRadius: borderRadius.md,
    paddingVertical: spacing[3],
    alignItems: 'center',
  },
  pdfBtnText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.forest,
    fontWeight: '600',
  },
  disabled: { opacity: 0.45 },
  clinicHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    borderBottomWidth: 2,
    borderBottomColor: colors.forest,
    paddingBottom: spacing[3],
  },
  clinicName: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.forest,
    fontWeight: '700',
  },
  clinicSub: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    marginTop: 2,
  },
  clinicRight: {
    alignItems: 'flex-end',
    gap: 2,
  },
  clinicMeta: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
  },
  signedChip: {
    backgroundColor: colors.sage + '22',
    borderRadius: borderRadius.sm,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1],
    alignSelf: 'flex-start',
  },
  signedChipText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.forest,
    fontWeight: '600',
  },
  infoBlock: {
    gap: spacing[1],
  },
  infoLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },
  infoValue: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    lineHeight: 22,
  },
  rxSection: {
    gap: spacing[3],
  },
  rxSymbol: {
    fontFamily: fontFamily.body,
    fontSize: 28,
    color: colors.forest,
    fontWeight: '700',
  },
  medCard: {
    borderWidth: 1,
    borderColor: colors.ivory,
    borderRadius: borderRadius.md,
    padding: spacing[3],
    gap: spacing[1],
    backgroundColor: colors.white,
  },
  medName: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.ink,
    fontWeight: '600',
  },
  medForm: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
  },
  medDetailRow: {
    marginTop: spacing[1],
  },
  medDetail: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    lineHeight: 22,
    fontVariant: ['tabular-nums'],
  },
  medLabel: {
    fontWeight: '600',
  },
  medInstructions: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    fontStyle: 'italic',
    marginTop: spacing[1],
  },
  refillNote: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.forest,
    fontWeight: '600',
    marginTop: spacing[1],
  },
  timelineSection: {
    gap: spacing[2],
  },
  sectionTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    fontWeight: '600',
  },
  timelineItem: {
    flexDirection: 'row',
    gap: spacing[3],
    alignItems: 'flex-start',
  },
  timelineDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.forest,
    marginTop: 6,
  },
  timelineText: {
    flex: 1,
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    lineHeight: 22,
  },
  footer: {
    borderTopWidth: 1,
    borderTopColor: colors.ivory,
    paddingTop: spacing[3],
  },
  footerText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    textAlign: 'center',
    lineHeight: 18,
  },
});
