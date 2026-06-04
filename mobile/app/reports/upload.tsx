/**
 * Lab report upload screen.
 *
 * Steps:
 *   1. Pick a PDF (document picker) or photo (camera / library)
 *   2. Initiate upload → get presigned POST URL
 *   3. Upload file directly to S3
 *   4. Finalize → backend HEAD-verifies and queues OCR task
 *   5. Navigate to the report detail screen
 */

import { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import * as DocumentPicker from 'expo-document-picker';
import * as ImagePicker from 'expo-image-picker';
import {
  finalizeUpload,
  initiateUpload,
  uploadToS3,
} from '../../lib/api/lab-reports';
import { colors, fontFamily, fontSize, spacing, borderRadius } from '../../lib/design-tokens';
import { DragDropUpload } from '../../components/web/DragDropUpload';
import { useBreakpoint } from '../../lib/hooks/useBreakpoint';

// ── Types ─────────────────────────────────────────────────────────────────────

interface PickedFile {
  uri: string;
  name: string;
  mimeType: string;
  size: number;
}

type UploadStep = 'idle' | 'uploading' | 'finalizing' | 'done' | 'error';

// ── Helpers ───────────────────────────────────────────────────────────────────

function mimeLabel(mimeType: string): string {
  if (mimeType === 'application/pdf') return 'PDF';
  if (mimeType.startsWith('image/')) return 'Image';
  return 'File';
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ── Screen ────────────────────────────────────────────────────────────────────

export default function UploadReportScreen() {
  const router = useRouter();
  const { isDesktop } = useBreakpoint();
  const [picked, setPicked] = useState<PickedFile | null>(null);
  const [step, setStep] = useState<UploadStep>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  const pickDocument = useCallback(async () => {
    const result = await DocumentPicker.getDocumentAsync({
      type: ['application/pdf'],
      copyToCacheDirectory: true,
    });
    if (result.canceled) return;
    const asset = result.assets[0];
    if (!asset) return;
    setPicked({
      uri: asset.uri,
      name: asset.name,
      mimeType: asset.mimeType ?? 'application/pdf',
      size: asset.size ?? 0,
    });
    setStep('idle');
    setErrorMsg('');
  }, []);

  const pickPhoto = useCallback(async () => {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) {
      Alert.alert('Permission needed', 'Allow photo access to upload a lab report image.');
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      quality: 0.9,
      allowsMultipleSelection: false,
    });
    if (result.canceled) return;
    const asset = result.assets[0];
    if (!asset) return;
    const mimeType = asset.type === 'image' ? 'image/jpeg' : 'image/jpeg';
    const filename = asset.fileName ?? `lab_report_${Date.now()}.jpg`;
    setPicked({
      uri: asset.uri,
      name: filename,
      mimeType,
      size: asset.fileSize ?? 0,
    });
    setStep('idle');
    setErrorMsg('');
  }, []);

  const takePhoto = useCallback(async () => {
    const perm = await ImagePicker.requestCameraPermissionsAsync();
    if (!perm.granted) {
      Alert.alert('Permission needed', 'Allow camera access to photograph a lab report.');
      return;
    }
    const result = await ImagePicker.launchCameraAsync({
      quality: 0.9,
      allowsEditing: false,
    });
    if (result.canceled) return;
    const asset = result.assets[0];
    if (!asset) return;
    const filename = `lab_report_${Date.now()}.jpg`;
    setPicked({
      uri: asset.uri,
      name: filename,
      mimeType: 'image/jpeg',
      size: asset.fileSize ?? 0,
    });
    setStep('idle');
    setErrorMsg('');
  }, []);

  // Web drag-and-drop: convert a browser File to the same PickedFile shape.
  const handleWebFilePicked = useCallback((file: File) => {
    const url = URL.createObjectURL(file);
    setPicked({
      uri: url,
      name: file.name,
      mimeType: file.type || 'application/pdf',
      size: file.size,
    });
    setStep('idle');
    setErrorMsg('');
  }, []);

  const handleUpload = useCallback(async () => {
    if (!picked) return;
    setStep('uploading');
    setErrorMsg('');

    try {
      const initiated = await initiateUpload({
        original_filename: picked.name,
        content_type: picked.mimeType,
        file_size_bytes: picked.size || 1,
      });

      await uploadToS3({
        upload_url: initiated.upload_url,
        fields: initiated.fields,
        file_uri: picked.uri,
        content_type: picked.mimeType,
        filename: picked.name,
      });

      setStep('finalizing');
      await finalizeUpload(initiated.lab_report_id);

      setStep('done');
      router.replace(`/reports/${initiated.lab_report_id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upload failed. Please try again.';
      setErrorMsg(msg);
      setStep('error');
    }
  }, [picked, router]);

  const isWorking = step === 'uploading' || step === 'finalizing';

  return (
    <ScrollView
      style={styles.scroll}
      contentContainerStyle={styles.container}
      keyboardShouldPersistTaps="handled"
    >
      <Text style={styles.heading}>Upload Lab Report</Text>
      <Text style={styles.sub}>
        Accepted formats: PDF, JPEG, PNG · Max size: 10 MB
      </Text>

      {/* Drag-and-drop zone — desktop web only */}
      {isDesktop && Platform.OS === 'web' && (
        <View style={styles.dndSection}>
          <DragDropUpload
            onFilePicked={handleWebFilePicked}
            disabled={step === 'uploading' || step === 'finalizing'}
          />
        </View>
      )}

      {/* Pick source buttons — mobile / mobile web */}
      <View style={styles.pickSection}>
        <Pressable
          style={styles.pickButton}
          onPress={pickDocument}
          disabled={isWorking}
          accessibilityLabel="Pick PDF from files"
        >
          <Text style={styles.pickIcon}>📄</Text>
          <Text style={styles.pickLabel}>PDF from files</Text>
        </Pressable>

        <Pressable
          style={styles.pickButton}
          onPress={pickPhoto}
          disabled={isWorking}
          accessibilityLabel="Pick photo from gallery"
        >
          <Text style={styles.pickIcon}>🖼️</Text>
          <Text style={styles.pickLabel}>Photo from gallery</Text>
        </Pressable>

        <Pressable
          style={styles.pickButton}
          onPress={takePhoto}
          disabled={isWorking}
          accessibilityLabel="Take photo with camera"
        >
          <Text style={styles.pickIcon}>📷</Text>
          <Text style={styles.pickLabel}>Take a photo</Text>
        </Pressable>
      </View>

      {/* Selected file preview */}
      {picked && (
        <View style={styles.preview}>
          <View style={styles.previewIcon}>
            <Text style={styles.previewIconText}>{mimeLabel(picked.mimeType)}</Text>
          </View>
          <View style={styles.previewMeta}>
            <Text style={styles.previewName} numberOfLines={2}>
              {picked.name}
            </Text>
            <Text style={styles.previewSize}>{formatBytes(picked.size)}</Text>
          </View>
          {!isWorking && (
            <Pressable onPress={() => setPicked(null)} accessibilityLabel="Remove selected file">
              <Text style={styles.removeText}>✕</Text>
            </Pressable>
          )}
        </View>
      )}

      {/* Progress indicator */}
      {isWorking && (
        <View style={styles.progressBox}>
          <ActivityIndicator color={colors.forest} />
          <Text style={styles.progressLabel}>
            {step === 'uploading' ? 'Uploading file…' : 'Queuing OCR scan…'}
          </Text>
        </View>
      )}

      {/* Error */}
      {step === 'error' && errorMsg ? (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{errorMsg}</Text>
        </View>
      ) : null}

      {/* Upload CTA */}
      <Pressable
        style={[styles.uploadButton, (!picked || isWorking) && styles.disabled]}
        onPress={() => void handleUpload()}
        disabled={!picked || isWorking}
        accessibilityLabel="Upload report"
      >
        {isWorking ? (
          <ActivityIndicator color={colors.white} />
        ) : (
          <Text style={styles.uploadButtonText}>Upload report</Text>
        )}
      </Pressable>

      <Pressable
        style={styles.cancelLink}
        onPress={() => router.back()}
        disabled={isWorking}
        accessibilityLabel="Cancel"
      >
        <Text style={styles.cancelText}>Cancel</Text>
      </Pressable>
    </ScrollView>
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
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
    paddingBottom: spacing[12],
    gap: spacing[4],
  },
  heading: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    color: colors.forest,
    fontWeight: '500',
  },
  sub: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    lineHeight: 20,
  },
  dndSection: {
    marginBottom: spacing[2],
  },
  pickSection: {
    flexDirection: 'row',
    gap: spacing[3],
  },
  pickButton: {
    flex: 1,
    backgroundColor: colors.white,
    borderRadius: borderRadius.lg,
    paddingVertical: spacing[4],
    alignItems: 'center',
    gap: spacing[2],
  },
  pickIcon: { fontSize: 26 },
  pickLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.ink,
    fontWeight: '500',
    textAlign: 'center',
  },
  preview: {
    backgroundColor: colors.white,
    borderRadius: borderRadius.lg,
    padding: spacing[4],
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
  },
  previewIcon: {
    width: 44,
    height: 44,
    borderRadius: borderRadius.md,
    backgroundColor: colors.forest + '18',
    alignItems: 'center',
    justifyContent: 'center',
  },
  previewIconText: {
    fontFamily: fontFamily.body,
    fontSize: 11,
    fontWeight: '700',
    color: colors.forest,
    letterSpacing: 0.5,
  },
  previewMeta: { flex: 1, gap: 2 },
  previewName: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    fontWeight: '500',
  },
  previewSize: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
  },
  removeText: {
    fontFamily: fontFamily.body,
    fontSize: 18,
    color: colors.stone,
    paddingHorizontal: spacing[2],
  },
  progressBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    backgroundColor: colors.sage + '30',
    borderRadius: borderRadius.md,
    padding: spacing[4],
  },
  progressLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.forest,
  },
  errorBox: {
    backgroundColor: colors.terracotta + '18',
    borderRadius: borderRadius.md,
    padding: spacing[4],
  },
  errorText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.terracotta,
    lineHeight: 20,
  },
  uploadButton: {
    backgroundColor: colors.forest,
    borderRadius: borderRadius.lg,
    paddingVertical: spacing[4],
    alignItems: 'center',
    marginTop: spacing[2],
  },
  uploadButtonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '700',
    color: colors.white,
  },
  disabled: { opacity: 0.45 },
  cancelLink: {
    alignItems: 'center',
  },
  cancelText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
  },
});
