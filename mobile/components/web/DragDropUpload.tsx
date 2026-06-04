/**
 * Drag-and-drop lab report upload for desktop web.
 *
 * Default: dashed Forest 2px border, upload icon, "Drag a file here or click to browse".
 * Drag-over: solid Forest border, Saffron 4% bg, "Drop to upload".
 * After drop / file select: shows file name and calls onFilePicked.
 *
 * Platform: web only. Never rendered on native — callers should gate with
 *   Platform.OS === 'web' before rendering this component.
 */

import { Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { useCallback, useRef, useState } from 'react';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

interface DragDropUploadProps {
  onFilePicked: (file: File) => void;
  accept?: string; // e.g. "application/pdf,image/*"
  disabled?: boolean;
}

export function DragDropUpload({
  onFilePicked,
  accept = 'application/pdf,image/*',
  disabled = false,
}: DragDropUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [pickedName, setPickedName] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const handleFile = useCallback((file: File) => {
    setPickedName(file.name);
    onFilePicked(file);
  }, [onFilePicked]);

  if (Platform.OS !== 'web') return null;

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) setIsDragOver(true);
  };
  const onDragLeave = () => setIsDragOver(false);
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled) return;
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };
  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };
  const openFilePicker = () => {
    if (disabled) return;
    inputRef.current?.click();
  };

  return (
    <View
      style={[styles.zone, isDragOver && styles.zoneDragOver, disabled && styles.zoneDisabled]}
      // @ts-ignore — RNW forwards drag events to the DOM
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      {/* Hidden native file input — valid DOM element in RNW */}
      {/* @ts-ignore */}
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        style={{ display: 'none' }}
        onChange={onInputChange}
      />

      <Text style={styles.icon}>☁</Text>

      {pickedName ? (
        <>
          <Text style={styles.fileName} numberOfLines={1}>{pickedName}</Text>
          <Pressable onPress={openFilePicker} style={styles.changeBtn} accessibilityLabel="Change file">
            <Text style={styles.changeBtnText}>Change file</Text>
          </Pressable>
        </>
      ) : (
        <>
          <Text style={styles.label}>
            {isDragOver ? 'Drop to upload' : 'Drag a file here or click to browse'}
          </Text>
          <Text style={styles.hint}>PDF or image · max 20 MB</Text>
          <Pressable
            onPress={openFilePicker}
            style={styles.browseBtn}
            disabled={disabled}
            accessibilityLabel="Browse files"
          >
            <Text style={styles.browseBtnText}>Browse files</Text>
          </Pressable>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  zone: {
    borderWidth: 2,
    borderStyle: 'dashed' as unknown as undefined,
    borderColor: colors.forest,
    borderRadius: borderRadius.lg,
    padding: spacing[6],
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 200,
    backgroundColor: colors.white,
    gap: spacing[2],
    cursor: 'pointer' as unknown as undefined,
  },
  zoneDragOver: {
    borderStyle: 'solid' as unknown as undefined,
    backgroundColor: colors.saffron + '0a', // Saffron 4%
  },
  zoneDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed' as unknown as undefined,
  },
  icon: {
    fontSize: 32,
    color: colors.forest,
    marginBottom: spacing[2],
  },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    textAlign: 'center',
  },
  hint: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
  },
  fileName: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.forest,
    maxWidth: 260,
    textAlign: 'center',
  },
  browseBtn: {
    marginTop: spacing[2],
    paddingVertical: spacing[2],
    paddingHorizontal: spacing[4],
    borderRadius: borderRadius.md,
    borderWidth: 1,
    borderColor: colors.forest,
  },
  browseBtnText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.forest,
    fontWeight: '600',
  },
  changeBtn: {
    marginTop: spacing[1],
  },
  changeBtnText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
  },
});
