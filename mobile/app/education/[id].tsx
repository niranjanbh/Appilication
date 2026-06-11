import {
  ActivityIndicator,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useColorScheme,
  View,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { getEducationContent, markAssignmentRead, type EducationContent } from '../../lib/api/education';
import { borderRadius, colors, fontFamily, fontSize, spacing , withAlpha } from '../../lib/design-tokens';

// ── Minimal markdown renderer ──────────────────────────────────────────────────

function MarkdownLine({ line, textPri }: { line: string; textPri: string; textSub: string }) {
  if (line.startsWith('### ')) return <Text style={[md.h3, { color: textPri }]}>{line.slice(4)}</Text>;
  if (line.startsWith('## '))  return <Text style={[md.h2, { color: textPri }]}>{line.slice(3)}</Text>;
  if (line.startsWith('# '))   return <Text style={[md.h1, { color: textPri }]}>{line.slice(2)}</Text>;
  if (line.startsWith('- ') || line.startsWith('* ')) {
    return (
      <View style={md.bulletRow}>
        <Text style={[md.bullet, { color: colors.electricBlue }]}>•</Text>
        <Text style={[md.bulletText, { color: textPri }]}>{line.slice(2)}</Text>
      </View>
    );
  }
  if (line.trim() === '') return <View style={{ height: spacing[2] }} />;
  const parts = line.split(/(\*\*[^*]+\*\*)/g);
  return (
    <Text style={[md.body, { color: textPri }]}>
      {parts.map((p, i) =>
        p.startsWith('**') && p.endsWith('**')
          ? <Text key={i} style={md.bold}>{p.slice(2, -2)}</Text>
          : p,
      )}
    </Text>
  );
}

function MarkdownView({ content, textPri, textSub }: { content: string; textPri: string; textSub: string }) {
  return (
    <View>
      {content.split('\n').map((line, i) => (
        <MarkdownLine key={i} line={line} textPri={textPri} textSub={textSub} />
      ))}
    </View>
  );
}

const md = StyleSheet.create({
  h1:         { fontFamily: fontFamily.display, fontSize: fontSize.h2, marginBottom: spacing[2], marginTop: spacing[3], fontWeight: '600' },
  h2:         { fontFamily: fontFamily.display, fontSize: fontSize.h3, marginBottom: spacing[2], marginTop: spacing[3], fontWeight: '600' },
  h3:         { fontFamily: fontFamily.display, fontSize: fontSize.bodyLg, marginBottom: spacing[1], marginTop: spacing[2], fontWeight: '600' },
  body:       { fontFamily: fontFamily.body, fontSize: fontSize.body, lineHeight: 26, marginBottom: spacing[2] },
  bold:       { fontFamily: fontFamily.body, fontWeight: '700' },
  bulletRow:  { flexDirection: 'row', gap: spacing[2], marginBottom: spacing[2] },
  bullet:     { fontFamily: fontFamily.body, fontSize: fontSize.body },
  bulletText: { fontFamily: fontFamily.body, fontSize: fontSize.body, flex: 1, lineHeight: 24 },
});

// ── Main screen ───────────────────────────────────────────────────────────────

export default function EducationContentScreen() {
  const { id, assignmentId } = useLocalSearchParams<{ id: string; assignmentId?: string }>();
  const router  = useRouter();
  const isDark  = useColorScheme() === 'dark';

  const [content,     setContent]     = useState<EducationContent | null>(null);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState<string | null>(null);
  const [markedRead,  setMarkedRead]  = useState(false);
  const [markingRead, setMarkingRead] = useState(false);

  useEffect(() => {
    if (!id) return;
    getEducationContent(id)
      .then(setContent)
      .catch(() => setError('Content not found.'))
      .finally(() => setLoading(false));
  }, [id]);

  // Preserve all existing mark-as-read logic
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

  const markScale = useSharedValue(1);
  const markAnim  = useAnimatedStyle(() => ({ transform: [{ scale: markScale.value }] }));

  const bg      = isDark ? colors.midnight     : colors.skyMist;
  const textPri = isDark ? colors.white        : colors.navyDeep;
  const textSub = isDark ? colors.slateText    : colors.coolGray;
  const cardBg  = isDark ? colors.nightSurface : colors.white;
  const cardBdr = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)';

  if (loading) {
    return <View style={[styles.center, { backgroundColor: bg }]}><ActivityIndicator size="large" color={colors.electricBlue} /></View>;
  }
  if (error || !content) {
    return (
      <View style={[styles.center, { backgroundColor: bg }]}>
        <Text style={[styles.errorText, { color: colors.criticalRed }]}>{error ?? 'Content unavailable.'}</Text>
        <Pressable onPress={() => router.back()} style={{ marginTop: spacing[4] }} accessibilityLabel="Go back">
          <Text style={[styles.backLink, { color: colors.electricBlue }]}>← Back</Text>
        </Pressable>
      </View>
    );
  }

  const isArticle = content.content_type === 'article';
  const isVideo   = content.content_type === 'video';

  return (
    <ScrollView style={[styles.container, { backgroundColor: bg }]} contentContainerStyle={styles.content}>

      {/* Header */}
      <View style={styles.header}>
        <View style={[styles.typePill, { backgroundColor: isDark ? colors.nightElev : colors.iceBlue }]}>
          <Text style={[styles.typePillText, { color: colors.electricBlue }]}>{content.content_type.toUpperCase()}</Text>
        </View>
        <Text style={[styles.title, { color: textPri }]}>{content.title}</Text>
        {content.condition_categories.length > 0 && (
          <View style={styles.tagRow}>
            {content.condition_categories.map(cat => (
              <View key={cat} style={[styles.tag, { backgroundColor: isDark ? colors.nightElev : colors.iceBlue }]}>
                <Text style={[styles.tagText, { color: colors.electricBlue }]}>{cat.replace('_', ' ')}</Text>
              </View>
            ))}
          </View>
        )}
      </View>

      {/* AI disclosure */}
      {content.ai_disclosure && (
        <View style={[styles.disclosureBanner, { backgroundColor: colors.warningAmber + '15', borderColor: colors.warningAmber + '40' }]}>
          <Text style={[styles.disclosureText, { color: textPri }]}>
            This content was AI-assisted and has been reviewed by a qualified doctor before publication.
          </Text>
        </View>
      )}

      {/* Doctor attribution */}
      {content.reviewed_at && (
        <Text style={[styles.attribution, { color: textSub }]}>
          Reviewed & approved by Kyros clinical team · {new Date(content.reviewed_at).toLocaleDateString('en-IN')}
        </Text>
      )}

      {/* Body */}
      <View style={[styles.body, { backgroundColor: cardBg, borderColor: cardBdr }]}>
        {isArticle && content.body_md ? (
          <MarkdownView content={content.body_md} textPri={textPri} textSub={textSub} />
        ) : (isVideo || content.content_url) ? (
          <View style={styles.mediaCard}>
            <View style={[styles.mediaIconWrap, { backgroundColor: isDark ? colors.nightElev : colors.iceBlue }]}>
              <Text style={styles.mediaIcon}>{isVideo ? '▶' : '📑'}</Text>
            </View>
            <Text style={[styles.mediaLabel, { color: textSub }]}>{isVideo ? 'Video content' : 'PDF document'}</Text>
            <Pressable
              style={styles.mediaBtn}
              onPress={() => content.content_url && Linking.openURL(content.content_url)}
              accessibilityLabel={isVideo ? 'Watch video' : 'Open PDF'}
            >
              <Text style={styles.mediaBtnText}>{isVideo ? '▶ Watch video' : '📑 Open PDF'}</Text>
            </Pressable>
          </View>
        ) : (
          <Text style={[styles.noContent, { color: textSub }]}>Content not available.</Text>
        )}
      </View>

      {/* Mark as read */}
      {assignmentId && (
        <Animated.View style={markAnim}>
          <Pressable
            onPress={handleMarkRead}
            onPressIn={() => { markScale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
            onPressOut={() => { markScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
            disabled={markedRead || markingRead}
            style={[
              styles.readBtn,
              markedRead ? { backgroundColor: colors.successGreen } : { backgroundColor: colors.navyDeep },
              (markedRead || markingRead) && styles.readBtnDone,
            ]}
            accessibilityLabel="Mark as read"
          >
            <Text style={styles.readBtnText}>
              {markedRead ? '✓ Marked as read' : markingRead ? 'Saving…' : 'Mark as read'}
            </Text>
          </Pressable>
        </Animated.View>
      )}

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content:   { padding: spacing[5], paddingBottom: spacing[10], gap: spacing[4] },
  center:    { flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing[6] },
  errorText: { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center' },
  backLink:  { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontWeight: '600' },

  header: { gap: spacing[3] },
  typePill: { alignSelf: 'flex-start', borderRadius: borderRadius.full, paddingHorizontal: spacing[3], paddingVertical: spacing[1] },
  typePillText: { fontFamily: fontFamily.body, fontSize: fontSize.xs, fontWeight: '700', letterSpacing: 1 },
  title:    { fontFamily: fontFamily.display, fontSize: fontSize.h2, fontWeight: '600', lineHeight: 32 },
  tagRow:   { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[1] },
  tag:      { borderRadius: borderRadius.full, paddingHorizontal: spacing[2], paddingVertical: 2 },
  tagText:  { fontFamily: fontFamily.body, fontSize: fontSize.xs, fontWeight: '600', textTransform: 'capitalize' },

  disclosureBanner: { borderRadius: borderRadius.xl, borderWidth: 1, padding: spacing[4] },
  disclosureText:   { fontFamily: fontFamily.body, fontSize: fontSize.caption, lineHeight: 20 },
  attribution:      { fontFamily: fontFamily.body, fontSize: fontSize.caption },

  body: {
    borderRadius: borderRadius.xxl,
    padding: spacing[5],
    borderWidth: 1,
    boxShadow: '0 6px 14px rgba(0,0,0,0.07)',
  },
  noContent: { fontFamily: fontFamily.body, fontSize: fontSize.body },

  mediaCard:     { alignItems: 'center', paddingVertical: spacing[6], gap: spacing[4] },
  mediaIconWrap: { width: 64, height: 64, borderRadius: 32, alignItems: 'center', justifyContent: 'center' },
  mediaIcon:     { fontSize: 28 },
  mediaLabel:    { fontFamily: fontFamily.body, fontSize: fontSize.caption },
  mediaBtn: {
    height: 48,
    paddingHorizontal: spacing[6],
    backgroundColor: colors.navyDeep,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
  },
  mediaBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.white, fontWeight: '600' },

  readBtn: {
    height: 56,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: `0 8px 16px ${withAlpha(colors.navyDeep, 0.25)}`,
  },
  readBtnDone: { opacity: 0.70, boxShadow: '0 0 0 rgba(0,0,0,0)' },
  readBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, color: colors.white, fontWeight: '700' },
});
