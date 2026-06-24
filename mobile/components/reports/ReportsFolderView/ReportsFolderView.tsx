import { Ionicons } from '@expo/vector-icons';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Alert } from '../../../lib/ui/alert';
import { HapticPressable } from '../../ui/HapticPressable';
import {
  borderRadius,
  colors,
  fontFamily,
  fontSize,
  spacing,
  withAlpha,
} from '../../../lib/design-tokens';
import { useTheme } from '../../../lib/theme';
import type { ReportFile, ReportFolder, ReportsFolderViewProps } from './ReportsFolderView.types';

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

// ── Folder card ────────────────────────────────────────────────────────────────

function FolderCard({ folder, onPress }: { folder: ReportFolder; onPress: () => void }) {
  const t = useTheme();
  return (
    <HapticPressable
      haptic="selection"
      scaleTo={0.97}
      onPress={onPress}
      accessibilityLabel={`Open ${folder.name}`}
      containerStyle={folder_s.wrap}
    >
      <View style={[folder_s.card, { backgroundColor: t.surface }]}>
        <Ionicons
          name={folder.iconName as IoniconName}
          size={32}
          color={t.isDark ? colors.jadeGlow : colors.forest}
        />
        <Text style={[folder_s.name, { color: t.text }]} numberOfLines={2}>
          {folder.name}
        </Text>
        <Text style={[folder_s.count, { color: t.textSub }]}>
          {folder.fileCount} {folder.fileCount === 1 ? 'file' : 'files'}
        </Text>
      </View>
    </HapticPressable>
  );
}

const folder_s = StyleSheet.create({
  wrap: { flex: 1 },
  card: {
    borderRadius: borderRadius.xl,
    padding: spacing[4],
    gap: spacing[2],
    minHeight: 120,
  },
  name: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
    flex: 1,
  },
  count: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
  },
});

// ── File thumbnail ─────────────────────────────────────────────────────────────

function FileThumbnail({
  file,
  onPress,
  onDownload,
  onDelete,
}: {
  file: ReportFile;
  onPress: () => void;
  onDownload: () => void;
  onDelete: () => void;
}) {
  const t      = useTheme();
  const isPdf  = file.fileType === 'pdf';
  const badge  = isPdf ? 'PDF' : file.fileType === 'image' ? 'IMG' : 'DOC';
  const accent = isPdf ? colors.terracotta : t.isDark ? colors.jadeGlow : colors.jade;

  function confirmDelete() {
    Alert.alert('Delete file', `Remove "${file.name}"?`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: onDelete },
    ]);
  }

  return (
    <HapticPressable
      haptic="selection"
      scaleTo={0.97}
      onPress={onPress}
      accessibilityLabel={`Open ${file.name}`}
      containerStyle={thumb.wrap}
    >
      <View style={[thumb.card, { backgroundColor: t.surface }]}>
        {/* File-type badge */}
        <View style={[thumb.badge, { backgroundColor: withAlpha(accent, 0.15) }]}>
          <Text style={[thumb.badgeText, { color: accent }]}>{badge}</Text>
        </View>

        <Text style={[thumb.name, { color: t.text }]} numberOfLines={2}>
          {file.name}
        </Text>
        <Text style={[thumb.date, { color: t.textSub }]}>{formatDate(file.uploadedAt)}</Text>

        {/* Doctor-set review chip — only if present, never app-generated */}
        {file.reviewStatus && file.reviewerName ? (
          <View style={[thumb.reviewChip, { backgroundColor: withAlpha(colors.jadeGlow, 0.12) }]}>
            <Text style={[thumb.reviewText, { color: t.isDark ? colors.jadeGlow : colors.jade }]} numberOfLines={1}>
              Reviewed by Dr. {file.reviewerName}
            </Text>
          </View>
        ) : null}

        {/* DPDP download + delete actions */}
        <View style={thumb.actions}>
          <Pressable onPress={onDownload} hitSlop={6} accessibilityLabel={`Download ${file.name}`}>
            <Ionicons name="download-outline" size={16} color={t.textSub} />
          </Pressable>
          <Pressable onPress={confirmDelete} hitSlop={6} accessibilityLabel={`Delete ${file.name}`}>
            <Ionicons name="trash-outline" size={16} color={t.isDark ? colors.alertBright : colors.alert} />
          </Pressable>
        </View>
      </View>
    </HapticPressable>
  );
}

const thumb = StyleSheet.create({
  wrap: { flex: 1 },
  card: {
    borderRadius: borderRadius.xl,
    padding: spacing[3],
    gap: spacing[2],
    minHeight: 140,
  },
  badge: {
    alignSelf: 'flex-start',
    borderRadius: borderRadius.sm,
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
  },
  badgeText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  name: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: '500',
    flex: 1,
  },
  date: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
  },
  reviewChip: {
    borderRadius: borderRadius.sm,
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
  },
  reviewText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    fontWeight: '500',
  },
  actions: { flexDirection: 'row', gap: spacing[3], paddingTop: spacing[1] },
});

// ── Section heading ────────────────────────────────────────────────────────────

function SectionHeading({ label, onViewAll, t }: { label: string; onViewAll?: () => void; t: ReturnType<typeof useTheme> }) {
  return (
    <View style={sec.row}>
      <Text style={[sec.label, { color: t.text }]}>{label}</Text>
      {onViewAll ? (
        <Pressable onPress={onViewAll} accessibilityLabel={`View all ${label}`}>
          <Text style={[sec.viewAll, { color: t.isDark ? colors.jadeGlow : colors.jade }]}>View all</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const sec = StyleSheet.create({
  row:     { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: spacing[3] },
  label:   { fontFamily: fontFamily.display, fontSize: fontSize.h3, fontWeight: '600' },
  viewAll: { fontFamily: fontFamily.body, fontSize: fontSize.sm, fontWeight: '600' },
});

// ── ReportsFolderView ──────────────────────────────────────────────────────────

export function ReportsFolderView({
  folders,
  recentFiles,
  onUpload,
  onDownload,
  onDelete,
  onOpenFolder,
  onOpenFile,
}: ReportsFolderViewProps) {
  const t = useTheme();

  const folderPairs = splitPairs(folders);
  const filePairs   = splitPairs(recentFiles);

  return (
    <ScrollView showsVerticalScrollIndicator={false}>
      {/* Folder grid */}
      <View style={main.section}>
        <SectionHeading label="Folders" t={t} />
        <View style={main.grid}>
          {folderPairs.map((pair, i) => (
            <View key={i} style={main.row}>
              {pair.map(folder =>
                folder ? (
                  <FolderCard
                    key={folder.id}
                    folder={folder}
                    onPress={() => onOpenFolder(folder)}
                  />
                ) : (
                  <View key="empty" style={{ flex: 1 }} />
                ),
              )}
            </View>
          ))}
        </View>
      </View>

      {/* Recent files grid */}
      <View style={main.section}>
        <SectionHeading label="Recent Files" t={t} />
        {recentFiles.length === 0 ? (
          <View style={main.empty}>
            <Ionicons name="document-outline" size={32} color={t.textSub} />
            <Text style={[main.emptyText, { color: t.textSub }]}>No files yet</Text>
          </View>
        ) : (
          <View style={main.grid}>
            {filePairs.map((pair, i) => (
              <View key={i} style={main.row}>
                {pair.map(file =>
                  file ? (
                    <FileThumbnail
                      key={file.id}
                      file={file}
                      onPress={() => onOpenFile(file)}
                      onDownload={() => onDownload(file)}
                      onDelete={() => onDelete(file)}
                    />
                  ) : (
                    <View key="empty" style={{ flex: 1 }} />
                  ),
                )}
              </View>
            ))}
          </View>
        )}
      </View>

      {/* Upload action */}
      <HapticPressable
        haptic="medium"
        scaleTo={0.97}
        onPress={onUpload}
        accessibilityLabel="Upload report"
        containerStyle={main.uploadWrap}
      >
        <View style={[main.uploadBtn, { backgroundColor: t.isDark ? withAlpha(colors.jadeGlow, 0.12) : withAlpha(colors.forest, 0.08), borderColor: t.isDark ? colors.jadeGlow : colors.forest }]}>
          <Ionicons name="add-circle-outline" size={20} color={t.isDark ? colors.jadeGlow : colors.forest} />
          <Text style={[main.uploadText, { color: t.isDark ? colors.jadeGlow : colors.forest }]}>
            Upload document
          </Text>
        </View>
      </HapticPressable>
    </ScrollView>
  );
}

function splitPairs<T>(items: T[]): [T | null, T | null][] {
  const pairs: [T | null, T | null][] = [];
  for (let i = 0; i < items.length; i += 2) {
    pairs.push([items[i] ?? null, items[i + 1] ?? null]);
  }
  return pairs;
}

const main = StyleSheet.create({
  section:     { paddingHorizontal: spacing[4], marginBottom: spacing[6] },
  grid:        { gap: spacing[3] },
  row:         { flexDirection: 'row', gap: spacing[3] },
  empty:       { alignItems: 'center', gap: spacing[3], paddingVertical: spacing[8] },
  emptyText:   { fontFamily: fontFamily.body, fontSize: fontSize.body },
  uploadWrap:  { paddingHorizontal: spacing[4], marginBottom: spacing[6] },
  uploadBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing[2],
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    borderStyle: 'dashed',
    paddingVertical: spacing[4],
  },
  uploadText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
});
