import { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useColorScheme,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import * as DocumentPicker from 'expo-document-picker';
import * as ImagePicker from 'expo-image-picker';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { finalizeUpload, initiateUpload, uploadToS3 } from '../../lib/api/lab-reports';
import { borderRadius, colors, fontFamily, fontSize, spacing , withAlpha } from '../../lib/design-tokens';
import { DragDropUpload } from '../../components/web/DragDropUpload';
import { useBreakpoint } from '../../lib/hooks/useBreakpoint';

interface PickedFile { uri: string; name: string; mimeType: string; size: number; }
type UploadStep = 'idle' | 'uploading' | 'finalizing' | 'done' | 'error';

function mimeLabel(m: string) { return m === 'application/pdf' ? 'PDF' : 'IMG'; }
function formatBytes(b: number) {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / (1024 * 1024)).toFixed(1)} MB`;
}

export default function UploadReportScreen() {
  const router       = useRouter();
  const isDark       = useColorScheme() === 'dark';
  const { isDesktop } = useBreakpoint();
  const [picked, setPicked]   = useState<PickedFile | null>(null);
  const [step, setStep]       = useState<UploadStep>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  // Preserve all existing pick / upload logic
  const pickDocument = useCallback(async () => {
    const result = await DocumentPicker.getDocumentAsync({ type: ['application/pdf'], copyToCacheDirectory: true });
    if (result.canceled) return;
    const asset = result.assets[0];
    if (!asset) return;
    setPicked({ uri: asset.uri, name: asset.name, mimeType: asset.mimeType ?? 'application/pdf', size: asset.size ?? 0 });
    setStep('idle'); setErrorMsg('');
  }, []);

  const pickPhoto = useCallback(async () => {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) { Alert.alert('Permission needed', 'Allow photo access to upload a lab report image.'); return; }
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.9, allowsMultipleSelection: false });
    if (result.canceled) return;
    const asset = result.assets[0];
    if (!asset) return;
    setPicked({ uri: asset.uri, name: asset.fileName ?? `lab_report_${Date.now()}.jpg`, mimeType: 'image/jpeg', size: asset.fileSize ?? 0 });
    setStep('idle'); setErrorMsg('');
  }, []);

  const takePhoto = useCallback(async () => {
    const perm = await ImagePicker.requestCameraPermissionsAsync();
    if (!perm.granted) { Alert.alert('Permission needed', 'Allow camera access to photograph a lab report.'); return; }
    const result = await ImagePicker.launchCameraAsync({ quality: 0.9, allowsEditing: false });
    if (result.canceled) return;
    const asset = result.assets[0];
    if (!asset) return;
    setPicked({ uri: asset.uri, name: `lab_report_${Date.now()}.jpg`, mimeType: 'image/jpeg', size: asset.fileSize ?? 0 });
    setStep('idle'); setErrorMsg('');
  }, []);

  const handleWebFilePicked = useCallback((file: File) => {
    setPicked({ uri: URL.createObjectURL(file), name: file.name, mimeType: file.type || 'application/pdf', size: file.size });
    setStep('idle'); setErrorMsg('');
  }, []);

  const handleUpload = useCallback(async () => {
    if (!picked) return;
    setStep('uploading'); setErrorMsg('');
    try {
      const initiated = await initiateUpload({ original_filename: picked.name, content_type: picked.mimeType, file_size_bytes: picked.size || 1 });
      await uploadToS3({ upload_url: initiated.upload_url, fields: initiated.fields, file_uri: picked.uri, content_type: picked.mimeType, filename: picked.name });
      setStep('finalizing');
      await finalizeUpload(initiated.lab_report_id);
      setStep('done');
      router.replace(`/reports/${initiated.lab_report_id}`);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Upload failed. Please try again.');
      setStep('error');
    }
  }, [picked, router]);

  const isWorking = step === 'uploading' || step === 'finalizing';

  const uploadScale = useSharedValue(1);
  const uploadAnim  = useAnimatedStyle(() => ({ transform: [{ scale: uploadScale.value }] }));

  const bg      = isDark ? colors.midnight     : colors.skyMist;
  const textPri = isDark ? colors.white        : colors.navyDeep;
  const textSub = isDark ? colors.slateText    : colors.coolGray;
  const cardBg  = isDark ? colors.nightSurface : colors.white;
  const cardBdr = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)';

  return (
    <ScrollView
      style={[styles.scroll, { backgroundColor: bg }]}
      contentContainerStyle={styles.container}
      keyboardShouldPersistTaps="handled"
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={[styles.heading, { color: textPri }]}>Upload Lab Report</Text>
        <Text style={[styles.sub, { color: textSub }]}>
          Accepted: PDF, JPEG, PNG · Max 10 MB
        </Text>
      </View>

      {/* Drag-drop — desktop web */}
      {isDesktop && Platform.OS === 'web' && (
        <DragDropUpload onFilePicked={handleWebFilePicked} disabled={isWorking} />
      )}

      {/* Pick source buttons */}
      <View style={styles.pickRow}>
        {[
          { icon: '📄', label: 'PDF from files',   onPress: pickDocument,  a11y: 'Pick PDF from files' },
          { icon: '🖼️', label: 'Photo from gallery', onPress: pickPhoto,    a11y: 'Pick photo from gallery' },
          { icon: '📷', label: 'Take a photo',     onPress: takePhoto,     a11y: 'Take photo with camera' },
        ].map(({ icon, label, onPress, a11y }) => (
          <Pressable
            key={label}
            style={[styles.pickBtn, { backgroundColor: cardBg, borderColor: cardBdr }]}
            onPress={onPress}
            disabled={isWorking}
            accessibilityLabel={a11y}
          >
            <Text style={styles.pickIcon}>{icon}</Text>
            <Text style={[styles.pickLabel, { color: textPri }]}>{label}</Text>
          </Pressable>
        ))}
      </View>

      {/* Selected file preview */}
      {picked && (
        <View style={[styles.preview, { backgroundColor: cardBg, borderColor: cardBdr }]}>
          <View style={[styles.previewIconWrap, { backgroundColor: colors.electricBlue + '18' }]}>
            <Text style={[styles.previewIconText, { color: colors.electricBlue }]}>{mimeLabel(picked.mimeType)}</Text>
          </View>
          <View style={styles.previewMeta}>
            <Text style={[styles.previewName, { color: textPri }]} numberOfLines={2}>{picked.name}</Text>
            <Text style={[styles.previewSize, { color: textSub }]}>{formatBytes(picked.size)}</Text>
          </View>
          {!isWorking && (
            <Pressable onPress={() => setPicked(null)} accessibilityLabel="Remove selected file">
              <Text style={[styles.removeText, { color: textSub }]}>✕</Text>
            </Pressable>
          )}
        </View>
      )}

      {/* Upload progress */}
      {isWorking && (
        <View style={[styles.progressBox, { backgroundColor: colors.electricBlue + '12', borderColor: colors.electricBlue + '30' }]}>
          <ActivityIndicator color={colors.electricBlue} />
          <Text style={[styles.progressLabel, { color: colors.electricBlue }]}>
            {step === 'uploading' ? 'Uploading file…' : 'Queuing OCR scan…'}
          </Text>
        </View>
      )}

      {/* Error */}
      {step === 'error' && errorMsg && (
        <View style={[styles.errorBox, { backgroundColor: colors.criticalRed + '12', borderColor: colors.criticalRed + '30' }]}>
          <Text style={[styles.errorText, { color: colors.criticalRed }]}>{errorMsg}</Text>
        </View>
      )}

      {/* Upload CTA */}
      <Animated.View style={uploadAnim}>
        <Pressable
          style={[styles.uploadBtn, (!picked || isWorking) && styles.disabled]}
          onPress={() => void handleUpload()}
          onPressIn={() => { uploadScale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
          onPressOut={() => { uploadScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
          disabled={!picked || isWorking}
          accessibilityLabel="Upload report"
        >
          {isWorking ? (
            <ActivityIndicator color={colors.white} size="small" />
          ) : (
            <Text style={styles.uploadBtnText}>Upload report</Text>
          )}
        </Pressable>
      </Animated.View>

      <Pressable
        style={styles.cancelLink}
        onPress={() => router.back()}
        disabled={isWorking}
        accessibilityLabel="Cancel"
      >
        <Text style={[styles.cancelText, { color: textSub }]}>Cancel</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1 },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
    paddingBottom: spacing[12],
    gap: spacing[4],
  },

  header: { gap: spacing[1] },
  heading: { fontFamily: fontFamily.display, fontSize: fontSize.h2, fontWeight: '600' },
  sub:     { fontFamily: fontFamily.body, fontSize: fontSize.caption, lineHeight: 20 },

  pickRow: { flexDirection: 'row', gap: spacing[3] },
  pickBtn: {
    flex: 1,
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    paddingVertical: spacing[5],
    alignItems: 'center',
    gap: spacing[2],
    boxShadow: '0 4px 10px rgba(0,0,0,0.06)',
  },
  pickIcon:  { fontSize: 26 },
  pickLabel: { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontWeight: '600', textAlign: 'center' },

  preview: {
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    padding: spacing[4],
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    boxShadow: '0 4px 10px rgba(0,0,0,0.06)',
  },
  previewIconWrap: {
    width: 48,
    height: 48,
    borderRadius: borderRadius.xl,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  previewIconText: { fontFamily: fontFamily.body, fontSize: fontSize.xs, fontWeight: '700', letterSpacing: 0.5 },
  previewMeta:     { flex: 1, gap: 2 },
  previewName:     { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600' },
  previewSize:     { fontFamily: fontFamily.body, fontSize: fontSize.caption },
  removeText:      { fontFamily: fontFamily.body, fontSize: 18, paddingHorizontal: spacing[2] },

  progressBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    padding: spacing[4],
  },
  progressLabel: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600' },

  errorBox: {
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    padding: spacing[4],
  },
  errorText: { fontFamily: fontFamily.body, fontSize: fontSize.caption, lineHeight: 20 },

  uploadBtn: {
    height: 56,
    backgroundColor: colors.navyDeep,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: `0 8px 16px ${withAlpha(colors.navyDeep, 0.30)}`,
  },
  disabled:       { opacity: 0.45 },
  uploadBtnText:  { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700', color: colors.white },

  cancelLink: { alignItems: 'center' },
  cancelText: { fontFamily: fontFamily.body, fontSize: fontSize.caption },
});
