/**
 * Education content viewer.
 *
 * Displays article markdown, video link, or PDF link.
 * Shows ai_disclosure badge when flagged.
 * Shows reviewing doctor attribution (clinical compliance: NMC TPG).
 * "Mark as read" button on doctor-assigned content.
 */

import {
  ActivityIndicator,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import {
  getEducationContent,
  markAssignmentRead,
  type EducationContent,
} from '../../lib/api/education';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

// ── Minimal markdown renderer ─────────────────────────────────────────────────
// Handles headings, bold, bullets. Sufficient for educational articles.

function MarkdownLine({ line }: { line: string }) {
  if (line.startsWith('### ')) {
    return <Text style={md.h3}>{line.slice(4)}</Text>;
  }
  if (line.startsWith('## ')) {
    return <Text style={md.h2}>{line.slice(3)}</Text>;
  }
  if (line.startsWith('# ')) {
    return <Text style={md.h1}>{line.slice(2)}</Text>;
  }
  if (line.startsWith('- ') || line.startsWith('* ')) {
    return (
      <View style={md.bulletRow}>
        <Text style={md.bullet}>•</Text>
        <Text style={md.bulletText}>{line.slice(2)}</Text>
      </View>
    );
  }
  if (line.trim() === '') return <View style={{ height: spacing[2] }} />;

  // Inline bold: **text**
  const parts = line.split(/(\*\*[^*]+\*\*)/g);
  return (
    <Text style={md.body}>
      {parts.map((p, i) =>
        p.startsWith('**') && p.endsWith('**') ? (
          <Text key={i} style={md.bold}>{p.slice(2, -2)}</Text>
        ) : (
          p
        ),
      )}
    </Text>
  );
}

function MarkdownView({ content }: { content: string }) {
  const lines = content.split('\n');
  return (
    <View>
      {lines.map((line, i) => (
        <MarkdownLine key={i} line={line} />
      ))}
    </View>
  );
}

// ── Screen ────────────────────────────────────────────────────────────────────

export default function EducationContentScreen() {
  const { id, assignmentId } = useLocalSearchParams<{ id: string; assignmentId?: string }>();
  const router = useRouter();

  const [content, setContent] = useState<EducationContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [markedRead, setMarkedRead] = useState(false);
  const [markingRead, setMarkingRead] = useState(false);

  useEffect(() => {
    if (!id) return;
    getEducationContent(id)
      .then(setContent)
      .catch(() => setError('Content not found.'))
      .finally(() => setLoading(false));
  }, [id]);

  const handleMarkRead = async () => {
    if (!assignmentId || markedRead || markingRead) return;
    setMarkingRead(true);
    try {
      await markAssignmentRead(assignmentId);
      setMarkedRead(true);
    } finally {
      setMarkingRead(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.forest} />
      </View>
    );
  }

  if (error || !content) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{error ?? 'Content unavailable.'}</Text>
        <Pressable onPress={() => router.back()} style={{ marginTop: spacing[4] }} accessibilityLabel="Go back">
          <Text style={styles.backLink}>← Back</Text>
        </Pressable>
      </View>
    );
  }

  const isArticle = content.content_type === 'article';
  const isVideo = content.content_type === 'video';

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.contentType}>{content.content_type.toUpperCase()}</Text>
        <Text style={styles.title}>{content.title}</Text>

        {content.condition_categories.length > 0 && (
          <View style={styles.tagRow}>
            {content.condition_categories.map((cat) => (
              <View key={cat} style={styles.tag}>
                <Text style={styles.tagText}>{cat.replace('_', ' ')}</Text>
              </View>
            ))}
          </View>
        )}
      </View>

      {/* Disclosure badges */}
      {content.ai_disclosure && (
        <View style={styles.disclosureBanner}>
          <Text style={styles.disclosureText}>
            This content was AI-assisted and has been reviewed by a qualified doctor before publication.
          </Text>
        </View>
      )}

      {/* Doctor attribution — clinical compliance requirement (NMC TPG) */}
      {content.reviewed_at && (
        <View style={styles.attributionRow}>
          <Text style={styles.attributionText}>
            Reviewed & approved by Kyros clinical team · {new Date(content.reviewed_at).toLocaleDateString('en-IN')}
          </Text>
        </View>
      )}

      {/* Body */}
      <View style={styles.body}>
        {isArticle && content.body_md ? (
          <MarkdownView content={content.body_md} />
        ) : isVideo && content.content_url ? (
          <View style={styles.mediaCard}>
            <Text style={styles.mediaLabel}>Video content</Text>
            <Pressable
              onPress={() => content.content_url && Linking.openURL(content.content_url)}
              style={styles.mediaButton}
              accessibilityLabel="Watch video"
            >
              <Text style={styles.mediaButtonText}>▶ Watch video</Text>
            </Pressable>
          </View>
        ) : content.content_url ? (
          <View style={styles.mediaCard}>
            <Text style={styles.mediaLabel}>PDF document</Text>
            <Pressable
              onPress={() => content.content_url && Linking.openURL(content.content_url)}
              style={styles.mediaButton}
              accessibilityLabel="Open PDF"
            >
              <Text style={styles.mediaButtonText}>📑 Open PDF</Text>
            </Pressable>
          </View>
        ) : (
          <Text style={styles.noContent}>Content not available.</Text>
        )}
      </View>

      {/* Mark as read */}
      {assignmentId && (
        <Pressable
          onPress={handleMarkRead}
          disabled={markedRead || markingRead}
          style={[styles.readBtn, (markedRead || markingRead) && styles.readBtnDone]}
          accessibilityLabel="Mark as read"
        >
          <Text style={styles.readBtnText}>
            {markedRead ? '✓ Marked as read' : markingRead ? 'Saving…' : 'Mark as read'}
          </Text>
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
  contentType: { fontFamily: fontFamily.body, fontSize: fontSize.caption, color: colors.stone, letterSpacing: 1, marginBottom: spacing[1] },
  title: { fontFamily: fontFamily.display, fontSize: fontSize.h2, color: colors.ink, marginBottom: spacing[2] },

  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[1] },
  tag: { backgroundColor: colors.sage + '30', borderRadius: borderRadius.sm, paddingHorizontal: spacing[2], paddingVertical: 2 },
  tagText: { fontFamily: fontFamily.body, fontSize: fontSize.caption, color: colors.forest, textTransform: 'capitalize' },

  disclosureBanner: { backgroundColor: colors.saffron + '20', borderRadius: borderRadius.md, padding: spacing[3], marginBottom: spacing[3] },
  disclosureText: { fontFamily: fontFamily.body, fontSize: fontSize.caption, color: colors.ink },

  attributionRow: { marginBottom: spacing[3] },
  attributionText: { fontFamily: fontFamily.body, fontSize: fontSize.caption, color: colors.stone },

  body: { backgroundColor: colors.white, borderRadius: borderRadius.lg, padding: spacing[4], marginBottom: spacing[4] },
  noContent: { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.stone },

  mediaCard: { alignItems: 'center', paddingVertical: spacing[4] },
  mediaLabel: { fontFamily: fontFamily.body, fontSize: fontSize.caption, color: colors.stone, marginBottom: spacing[3] },
  mediaButton: { backgroundColor: colors.forest, borderRadius: borderRadius.md, paddingVertical: spacing[3], paddingHorizontal: spacing[6] },
  mediaButtonText: { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.white, fontWeight: '600' },

  readBtn: { backgroundColor: colors.forest, borderRadius: borderRadius.md, paddingVertical: spacing[3], alignItems: 'center' },
  readBtnDone: { backgroundColor: colors.stone },
  readBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.white, fontWeight: '600' },

  backLink: { fontFamily: fontFamily.body, fontSize: fontSize.caption, color: colors.forest },
  errorText: { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.terracotta, textAlign: 'center' },
});

const md = StyleSheet.create({
  h1: { fontFamily: fontFamily.display, fontSize: fontSize.h2, color: colors.ink, marginBottom: spacing[2], marginTop: spacing[3] },
  h2: { fontFamily: fontFamily.display, fontSize: fontSize.h3, color: colors.ink, marginBottom: spacing[2], marginTop: spacing[3] },
  h3: { fontFamily: fontFamily.display, fontSize: fontSize.bodyLg, color: colors.ink, marginBottom: spacing[1], marginTop: spacing[2] },
  body: { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.ink, lineHeight: 24, marginBottom: spacing[2] },
  bold: { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.ink, fontWeight: '700' },
  bulletRow: { flexDirection: 'row', gap: spacing[2], marginBottom: spacing[1] },
  bullet: { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.forest },
  bulletText: { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.ink, flex: 1 },
});
