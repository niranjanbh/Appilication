import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useThemePreference } from '../../lib/theme-context';
import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import {
  listPatientEducation,
  type EducationAssignment,
  type EducationContent,
  type PatientEducationResponse,
} from '../../lib/api/education';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

const TYPE_ICON: Record<string, string> = {
  article: '📄',
  video:   '▶️',
  pdf:     '📑',
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

// ── Assignment card ───────────────────────────────────────────────────────────

function AssignmentCard({
  assignment,
  isDark,
  onPress,
}: {
  assignment: EducationAssignment;
  isDark: boolean;
  onPress: () => void;
}) {
  const scale  = useSharedValue(1);
  const anim   = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));
  const isRead = !!assignment.read_at;
  const { content } = assignment;

  const cardBg  = isDark ? colors.nightSurface : colors.white;
  const cardBdr = isDark ? colors.electricBlue + '40' : colors.electricBlue + '30';
  const textPri = isDark ? colors.white     : colors.navyDeep;
  const textSub = isDark ? colors.slateText : colors.coolGray;

  return (
    <Animated.View style={[anim, isRead && styles.readOpacity]}>
      <Pressable
        style={[styles.card, { backgroundColor: cardBg, borderColor: cardBdr, borderLeftWidth: 3 }]}
        onPress={onPress}
        onPressIn={() => { scale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
        onPressOut={() => { scale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
        accessibilityLabel={`Open ${content.title}`}
      >
        <View style={styles.cardTop}>
          <Text style={styles.typeIcon}>{TYPE_ICON[content.content_type] ?? '📄'}</Text>
          <View style={[styles.assignedBadge, { backgroundColor: colors.electricBlue + '18' }]}>
            <Text style={[styles.assignedBadgeText, { color: colors.electricBlue }]}>Doctor assigned</Text>
          </View>
          {isRead && (
            <View style={[styles.readBadge, { backgroundColor: colors.successGreen + '18' }]}>
              <Text style={[styles.readBadgeText, { color: colors.successGreen }]}>✓ Read</Text>
            </View>
          )}
        </View>
        <Text style={[styles.cardTitle, { color: textPri }]}>{content.title}</Text>
        {assignment.notes ? <Text style={[styles.cardNotes, { color: textSub }]}>"{assignment.notes}"</Text> : null}
        <Text style={[styles.cardMeta, { color: textSub }]}>Assigned {formatDate(assignment.created_at)}</Text>
        {content.ai_disclosure && (
          <Text style={[styles.aiNote, { color: colors.warningAmber }]}>AI-assisted · Doctor reviewed</Text>
        )}
      </Pressable>
    </Animated.View>
  );
}

// ── Library card ──────────────────────────────────────────────────────────────

function LibraryCard({
  content,
  isDark,
  onPress,
}: {
  content: EducationContent;
  isDark: boolean;
  onPress: () => void;
}) {
  const scale = useSharedValue(1);
  const anim  = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));

  const cardBg  = isDark ? colors.nightSurface : colors.white;
  const cardBdr = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)';
  const textPri = isDark ? colors.white     : colors.navyDeep;

  return (
    <Animated.View style={anim}>
      <Pressable
        style={[styles.card, { backgroundColor: cardBg, borderColor: cardBdr }]}
        onPress={onPress}
        onPressIn={() => { scale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
        onPressOut={() => { scale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
        accessibilityLabel={`Open ${content.title}`}
      >
        <View style={styles.cardTop}>
          <Text style={styles.typeIcon}>{TYPE_ICON[content.content_type] ?? '📄'}</Text>
        </View>
        <Text style={[styles.cardTitle, { color: textPri }]}>{content.title}</Text>
        {content.condition_categories.length > 0 && (
          <View style={styles.tagRow}>
            {content.condition_categories.slice(0, 3).map(cat => (
              <View key={cat} style={[styles.tag, { backgroundColor: isDark ? colors.nightElev : colors.iceBlue }]}>
                <Text style={[styles.tagText, { color: isDark ? colors.slateText : colors.navyDeep }]}>
                  {cat.replace('_', ' ')}
                </Text>
              </View>
            ))}
          </View>
        )}
        {content.ai_disclosure && (
          <Text style={[styles.aiNote, { color: colors.warningAmber }]}>AI-assisted · Doctor reviewed</Text>
        )}
      </Pressable>
    </Animated.View>
  );
}

// ── Screen ────────────────────────────────────────────────────────────────────

export default function EducationIndexScreen() {
  const router  = useRouter();
  const isDark  = useThemePreference().colorScheme === 'dark';
  const [data, setData]     = useState<PatientEducationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState<string | null>(null);

  useEffect(() => {
    listPatientEducation()
      .then(setData)
      .catch(() => setError('Unable to load education content.'))
      .finally(() => setLoading(false));
  }, []);

  const goToContent = (contentId: string, assignmentId?: string) => {
    const query = assignmentId ? `?assignmentId=${assignmentId}` : '';
    router.push(`/education/${contentId}${query}`);
  };

  const bg      = isDark ? colors.midnight  : colors.skyMist;
  const textPri = isDark ? colors.white     : colors.navyDeep;
  const textSub = isDark ? colors.slateText : colors.coolGray;

  if (loading) {
    return <View style={[styles.center, { backgroundColor: bg }]}><ActivityIndicator size="large" color={colors.electricBlue} /></View>;
  }
  if (error || !data) {
    return <View style={[styles.center, { backgroundColor: bg }]}><Text style={[styles.errorText, { color: colors.criticalRed }]}>{error ?? 'No content available.'}</Text></View>;
  }

  return (
    <ScrollView style={[styles.container, { backgroundColor: bg }]} contentContainerStyle={styles.content}>
      <Text style={[styles.screenTitle, { color: textPri }]}>Learn</Text>

      {data.assignments.length > 0 && (
        <>
          <Text style={[styles.sectionLabel, { color: textSub }]}>Assigned by your doctor</Text>
          {data.assignments.map(a => (
            <AssignmentCard
              key={a.id}
              assignment={a}
              isDark={isDark}
              onPress={() => goToContent(a.content_id, a.id)}
            />
          ))}
        </>
      )}

      {data.library.length > 0 && (
        <>
          <Text style={[styles.sectionLabel, { color: textSub }]}>Browse library</Text>
          {data.library.map(c => (
            <LibraryCard key={c.id} content={c} isDark={isDark} onPress={() => goToContent(c.id)} />
          ))}
        </>
      )}

      {data.assignments.length === 0 && data.library.length === 0 && (
        <View style={styles.empty}>
          <Text style={styles.emptyIcon}>📚</Text>
          <Text style={[styles.emptyTitle, { color: textPri }]}>Nothing here yet</Text>
          <Text style={[styles.emptyBody, { color: textSub }]}>
            Your doctor will assign educational content after your consultation.
          </Text>
        </View>
      )}
    </ScrollView>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1 },
  content:   { padding: spacing[6], paddingBottom: spacing[8], gap: spacing[4] },
  center:    { flex: 1, alignItems: 'center', justifyContent: 'center' },
  errorText: { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center' },

  screenTitle: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    fontWeight: '600',
    marginBottom: spacing[2],
  },
  sectionLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginTop: spacing[2],
    marginBottom: spacing[2],
  },

  card: {
    borderRadius: borderRadius.xl,
    padding: spacing[4],
    marginBottom: spacing[1],
    borderWidth: 1,
    gap: spacing[2],
    boxShadow: '0 4px 10px rgba(0,0,0,0.06)',
  },
  readOpacity: { opacity: 0.70 },
  cardTop: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  typeIcon: { fontSize: fontSize.bodyLg },
  assignedBadge: { borderRadius: borderRadius.full, paddingHorizontal: spacing[2], paddingVertical: 2 },
  assignedBadgeText: { fontFamily: fontFamily.body, fontSize: fontSize.xs, fontWeight: '700' },
  readBadge: { borderRadius: borderRadius.full, paddingHorizontal: spacing[2], paddingVertical: 2 },
  readBadgeText: { fontFamily: fontFamily.body, fontSize: fontSize.xs, fontWeight: '700' },
  cardTitle: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600' },
  cardNotes: { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontStyle: 'italic' },
  cardMeta:  { fontFamily: fontFamily.body, fontSize: fontSize.caption },
  aiNote:    { fontFamily: fontFamily.body, fontSize: fontSize.caption, fontWeight: '600' },

  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[1] },
  tag:    { borderRadius: borderRadius.full, paddingHorizontal: spacing[2], paddingVertical: 2 },
  tagText: { fontFamily: fontFamily.body, fontSize: fontSize.xs, fontWeight: '600', textTransform: 'capitalize' },

  empty:      { alignItems: 'center', paddingVertical: spacing[8], gap: spacing[3] },
  emptyIcon:  { fontSize: 48 },
  emptyTitle: { fontFamily: fontFamily.display, fontSize: fontSize.h3, fontWeight: '500', textAlign: 'center' },
  emptyBody:  { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center', maxWidth: 280, lineHeight: 22 },
});
