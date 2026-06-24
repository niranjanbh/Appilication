/**
 * Thin wrapper around expo-image-picker for reminder photos.
 *
 * expo-image-picker supports web (file input) and native, so no platform guard
 * is needed. Returns a normalized PickedImage or null when the user cancels or
 * denies permission. Only the image MIME types the backend accepts are emitted.
 */

import * as ImagePicker from 'expo-image-picker';

export interface PickedImage {
  uri: string;
  mimeType: string;
  fileName: string;
  fileSize: number | null;
}

const ALLOWED = ['image/jpeg', 'image/png', 'image/webp'];

function normalizeMime(uri: string, provided?: string | null): string {
  if (provided && ALLOWED.includes(provided)) return provided;
  const lower = uri.toLowerCase();
  if (lower.endsWith('.png')) return 'image/png';
  if (lower.endsWith('.webp')) return 'image/webp';
  return 'image/jpeg';
}

function toPicked(asset: ImagePicker.ImagePickerAsset): PickedImage {
  const mimeType = normalizeMime(asset.uri, asset.mimeType);
  const ext = mimeType.split('/')[1] ?? 'jpg';
  return {
    uri: asset.uri,
    mimeType,
    fileName: asset.fileName ?? `reminder-${Date.now()}.${ext}`,
    fileSize: asset.fileSize ?? null,
  };
}

export async function pickReminderImageFromLibrary(): Promise<PickedImage | null> {
  const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
  if (!perm.granted) return null;
  const result = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ['images'],
    allowsEditing: true,
    quality: 0.7,
  });
  if (result.canceled || result.assets.length === 0) return null;
  return toPicked(result.assets[0]);
}

export async function captureReminderImage(): Promise<PickedImage | null> {
  const perm = await ImagePicker.requestCameraPermissionsAsync();
  if (!perm.granted) return null;
  const result = await ImagePicker.launchCameraAsync({
    mediaTypes: ['images'],
    allowsEditing: true,
    quality: 0.7,
  });
  if (result.canceled || result.assets.length === 0) return null;
  return toPicked(result.assets[0]);
}
