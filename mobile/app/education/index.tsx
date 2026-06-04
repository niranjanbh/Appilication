/**
 * Education library screen.
 *
 * Shows doctor-assigned content at the top (highlighted with a badge),
 * then the browsable published library below.
 */

import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import {
  listPatientEducation,
  type EducationAssignment,
  type EducationContent,
  type PatientEducationResponse,
} from '../../lib/api/education';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

// ── Helpers ───────────────────────────────────────────────────────────────────

const TYPE_ICON: Record<string, string> = {
  article: '📄',
  video: '▶️',
  pdf: '📑',
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  });
}

// ── Assignment card ───────────────────────────────────────────────────────────

function AssignmentCard({ assignment, onPress }: { assignment: EducationAssignment; onPress: () => void }) {
  const { content } = assignment;
  const isRead = !!assignment.read_at;
  return (
    <Pressable
      style={[styles.card, styles.assignedCard, isRead && styles.cardRead]}
      onPress={onPress}
      accessibilityLabel={`Open ${content.title}`}
    >
      <View style={styles.cardTop}>
        <Text style={styles.typeIcon}>{TYPE_ICON[content.content_type] ?? '📄'}</Text>
        <View style={styles.assignedBadge}>
          <Text style={styles.assignedBadgeText}>Assigned by doctor</Text>
        </View>
        {isRead && <Text style={styles.readBadge}>✓ Read</Text>}
      </View>
      <Text style={styles.cardTitle}>{content.title}</Text>
      {assignment.notes ? (
        <Text style={styles.cardNotes}>"{assignment.notes}"</Text>
      ) : null}
      <Text style={styles.cardMeta}>Assigned {formatDate(assignment.created_at)}</Text>
      {content.ai_disclosure && (
        <Text style={styles.aiDisclosure}>AI-assisted content · Doctor reviewed</Text>
      )}
    </Pressable>
  );
}

// ── Library card ──────────────────────────────────────────────────────────────

function LibraryCard({ content, onPress }: { content: EducationContent; onPress: () => void }) {
  return (
    <Pressable
      style={styles.card}
      onPress={onPress}
      accessibilityLabel={`Open ${content.title}`}
    >
      <View style={styles.cardTop}>
        <Text style={styles.typeIcon}>{TYPE_ICON[content.content_type] ?? '📄'}</Text>
      </View>
      <Text style={styles.cardTitle}>{content.title}</Text>
      {content.condition_categories.length > 0 && (
        <View style={styles.tagRow}>
          {content.condition_categories.slice(0, 3).map((cat) => (
            <View key={cat} style={styles.tag}>
              <Text style={styles.tagText}>{cat.replace('_', ' ')}</Text>
            </View>
          ))}
        </View>
      )}
      {content.ai_disclosure && (
        <Text style={styles.aiDisclosure}>AI-assisted · Doctor reviewed</Text>
      )}
    </Pressable>
  );
}

// ── Screen ────────────────────────────────────────────────────────────────────

export default function EducationIndexScreen() {
  const router = useRouter();
  const [data, setData] = useState<PatientEducationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.forest} />
      </View>
    );
  }

  if (error || !data) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{error ?? 'No content available.'}</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.screenTitle}>Learn</Text>

      {data.assignments.length > 0 && (
        <>
          <Text style={styles.sectionLabel}>Assigned by your doctor</Text>
          {data.assignments.map((a) => (
            <AssignmentCard
              key={a.id}
              assignment={a}
              onPress={() => goToContent(a.content_id, a.id)}
            />
          ))}
        </>
      )}

      {data.library.length > 0 && (
        <>
          <Text style={styles.sectionLabel}>Browse library</Text>
          {data.library.map((c) => (
            <LibraryCard key={c.id} content={c} onPress={() => goToContent(c.id)} />
          ))}
        </>
      )}

      {data.assignments.length === 0 && data.library.length === 0 && (
        <View style={styles.empty}>
          <Text style={styles.emptyTitle}>Nothing here yet</Text>
          <Text style={styles.emptyBody}>
            Your doctor will assign educational content after your consultation.
          </Text>
        </View>
      )}
    </ScrollView>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.ivory },
  content: { padding: spacing[4], paddingBottom: spacing[8] },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  screenTitle: { fontFamily: fontFamily.display, fontSize: fontSize.h2, color: colors.ink, marginBottom: spacing[4] },
  sectionLabel: { fontFamily: fontFamily.display, fontSize: fontSize.bodyLg, color: colors.stone, marginBottom: spacing[2], marginTop: spacing[2] },

  card: {
    backgroundColor: colors.white,
    borderRadius: borderRadius.lg,
    padding: spacing[4],
    marginBottom: spacing[3],
  },
  assignedCard: { borderLeftWidth: 3, borderLeftColor: colors.forest },
  cardRead: { opacity: 0.7 },
  cardTop: { flexDirection: 'row', alignItems: 'center', gap: spacing[2], marginBottom: spacing[2] },
  typeIcon: { fontSize: fontSize.bodyLg },
  assignedBadge: { backgroundColor: colors.forest + '20', borderRadius: borderRadius.sm, paddingHorizontal: spacing[2], paddingVertical: 2 },
  assignedBadgeText: { fontFamily: fontFamily.body, fontSize: fontSize.caption, color: colors.forest, fontWeight: '600' },
  readBadge: { fontFamily: fontFamily.body, fontSize: fontSize.caption, color: colors.stone, marginLeft: 'auto' },
  cardTitle: { fontFamily: fontFamily.display, fontSize: fontSize.body, color: colors.ink, marginBottom: spacing[1] },
  cardNotes: { fontFamily: fontFamily.body, fontSize: fontSize.caption, color: colors.stone, fontStyle: 'italic', marginBottom: spacing[1] },
  cardMeta: { fontFamily: fontFamily.body, fontSize: fontSize.caption, color: colors.stone },
  aiDisclosure: { fontFamily: fontFamily.body, fontSize: fontSize.caption, color: colors.saffron, marginTop: spacing[1] },

  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[1], marginTop: spacing[1] },
  tag: { backgroundColor: colors.sage + '30', borderRadius: borderRadius.sm, paddingHorizontal: spacing[2], paddingVertical: 2 },
  tagText: { fontFamily: fontFamily.body, fontSize: fontSize.caption, color: colors.forest, textTransform: 'capitalize' },

  empty: { alignItems: 'center', paddingVertical: spacing[8] },
  emptyTitle: { fontFamily: fontFamily.display, fontSize: fontSize.h3, color: colors.ink, marginBottom: spacing[2] },
  emptyBody: { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.stone, textAlign: 'center', maxWidth: 280 },
  errorText: { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.terracotta },
});
