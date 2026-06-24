import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Dimensions, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { AmbientBackground } from '../../components/ui/AmbientBackground';
import { GlassCard } from '../../components/ui/GlassCard';
import { TAB_DOCK_CLEARANCE } from '../../components/ui/GlassTabBar';
import { HapticPressable } from '../../components/ui/HapticPressable';
import { AdaptiveHero } from '../../components/home/AdaptiveHero';
import { BiomarkerSparkStrip } from '../../components/home/BiomarkerSparkStrip';
import { CarePlanCard } from '../../components/home/CarePlanCard';
import { RequestedConsultBanner } from '../../components/home/RequestedConsultBanner';
import { useAuth } from '../../lib/auth/context';
import { listPatientNotesApi } from '../../lib/api/patient-notes';
import { listConsultations, type Consultation } from '../../lib/api/consultations';
import {
  borderRadius, colors, fontFamily, fontSize, spacing, tintSoft, withAlpha, type TintName,
} from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';

const { width: SCREEN_W } = Dimensions.get('window');
const H_PAD = spacing[6];
const GAP   = spacing[3];
const QUICK_SIZE = Math.max((SCREEN_W - H_PAD * 2 - GAP * 3) / 4, 56);

// ─── Quick actions ────────────────────────────────────────────────────────────

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

interface QuickAction {
  id: string;
  label: string;
  icon: IoniconName;
  tint: TintName;
  route: string;
}

const QUICK_ACTIONS: QuickAction[] = [
  { id: 'consult',   label: 'Consult',   icon: 'medkit-outline',        tint: 'forest',  route: '/(tabs)/consultations' },
  { id: 'reminders', label: 'Reminders', icon: 'alarm-outline',         tint: 'saffron', route: '/(tabs)/reminders' },
  { id: 'reports',   label: 'Reports',   icon: 'flask-outline',         tint: 'sage',    route: '/(tabs)/reports' },
  { id: 'notes',     label: 'My Notes',  icon: 'create-outline',        tint: 'peach',   route: '/notes' },
];

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

// ─── Upcoming-consult derivation ────────────────────────────────────────────────

/** First consult still awaiting coordinator assignment, if any. */
function findRequested(items: Consultation[]): Consultation | null {
  return items.find(c => c.status === 'requested') ?? null;
}

/** The soonest scheduled/confirmed/in-progress consult that has a slot. */
function findNextScheduled(items: Consultation[]): Consultation | null {
  const withSlot = items
    .filter(c =>
      (c.status === 'scheduled' || c.status === 'confirmed' || c.status === 'in_progress') &&
      c.scheduled_start_at != null,
    )
    .sort((a, b) =>
      new Date(a.scheduled_start_at!).getTime() - new Date(b.scheduled_start_at!).getTime(),
    );
  return withSlot[0] ?? null;
}

// ─── Quick action button ──────────────────────────────────────────────────────

function QuickBtn({
  action,
  isDark,
  onPress,
}: {
  action: QuickAction;
  isDark: boolean;
  onPress: () => void;
}) {
  const pair = tintSoft[action.tint];
  const bg   = isDark ? pair.bgDark : pair.bgLight;
  const tint = isDark ? pair.tintDark : pair.tintLight;

  return (
    <HapticPressable
      onPress={onPress}
      scaleTo={0.9}
      accessibilityLabel={action.label}
      containerStyle={{ width: QUICK_SIZE }}
      style={[styles.quickBtn, { width: QUICK_SIZE, height: QUICK_SIZE, backgroundColor: bg }]}
    >
      <Ionicons name={action.icon} size={24} color={tint} />
      <Text style={[styles.quickLabel, { color: tint }]}>{action.label}</Text>
    </HapticPressable>
  );
}

// ─── Main screen ──────────────────────────────────────────────────────────────

function formatRelativeShort(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return 'Today';
  if (days === 1) return 'Yesterday';
  return `${days}d ago`;
}

export default function HomeScreen() {
  const { state } = useAuth();
  const router    = useRouter();
  const t         = useTheme();

  const { data: notesData } = useQuery({
    queryKey: ['patient-notes'],
    queryFn: () => listPatientNotesApi(1, 3),
    staleTime: 60_000,
  });

  const { data: consultData } = useQuery({
    queryKey: ['consultations', 'upcoming'],
    queryFn: () => listConsultations({ upcoming: true }),
    staleTime: 60_000,
  });

  const recentNotes  = notesData?.items ?? [];
  const upcoming     = consultData?.items ?? [];
  const requested    = findRequested(upcoming);
  const nextScheduled = findNextScheduled(upcoming);

  const firstName = state.status === 'authenticated' ? state.user.name.split(' ')[0] : '';

  return (
    <View style={[styles.flex, { backgroundColor: t.background }]}>
      <AmbientBackground />
      <ScrollView
        style={styles.flex}
        contentContainerStyle={styles.container}
        showsVerticalScrollIndicator={false}
      >

        {/* ── Header ─────────────────────────────────────────────────────── */}
        <View style={styles.header}>
          <View>
            <Text style={[styles.greeting, { color: t.textSub }]}>{getGreeting()}</Text>
            <Text style={[styles.heroName, { color: t.text }]}>{firstName || 'Welcome'}</Text>
          </View>
        </View>

        {/* ── Coordinator "request under review" banner ──────────────────── */}
        {requested && (
          <RequestedConsultBanner onPress={() => router.push('/(tabs)/consultations')} />
        )}

        {/* ── Adaptive hero — countdown or booking CTA ───────────────────── */}
        <AdaptiveHero
          consult={nextScheduled}
          onBook={() => router.push('/consultations/book')}
          onOpenConsult={(id) => router.push(`/consultations/${id}`)}
        />

        {/* ── Biomarker spark-strip ──────────────────────────────────────── */}
        <BiomarkerSparkStrip />

        {/* ── Quick actions ───────────────────────────────────────────────── */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: t.text }]}>Quick actions</Text>
          <View style={styles.quickRow}>
            {QUICK_ACTIONS.map(a => (
              <QuickBtn
                key={a.id}
                action={a}
                isDark={t.isDark}
                onPress={() => router.push(a.route as never)}
              />
            ))}
          </View>
        </View>

        {/* ── Health notes preview ────────────────────────────────────────── */}
        <GlassCard>
          <View style={styles.notesHeader}>
            <Text style={[styles.sectionTitle, { color: t.text }]}>Health Notes</Text>
            <HapticPressable
              onPress={() => router.push('/notes' as never)}
              accessibilityLabel="View all notes"
            >
              <Text style={[styles.notesLink, { color: t.primary }]}>
                {recentNotes.length === 0 ? 'Add note' : 'See all'}
              </Text>
            </HapticPressable>
          </View>
          {recentNotes.length === 0 ? (
            <Text style={[styles.notesEmpty, { color: t.textSub }]}>
              Write down questions or reminders for your next consultation.
            </Text>
          ) : (
            <View style={styles.notesList}>
              {recentNotes.map(note => (
                <View key={note.id} style={[styles.notePreviewRow, { borderColor: t.isDark ? withAlpha(colors.white, 0.08) : withAlpha(colors.stone, 0.20) }]}>
                  <Text style={[styles.notePreviewBody, { color: t.text }]} numberOfLines={2}>
                    {note.body}
                  </Text>
                  <Text style={[styles.notePreviewTime, { color: t.textSub }]}>
                    {formatRelativeShort(note.created_at)}
                  </Text>
                </View>
              ))}
            </View>
          )}
        </GlassCard>

        {/* ── Care plan card ──────────────────────────────────────────────── */}
        <CarePlanCard />

      </ScrollView>
    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flexGrow: 1,
    paddingHorizontal: H_PAD,
    paddingTop: spacing[6],
    paddingBottom: TAB_DOCK_CLEARANCE,
    gap: spacing[6],
  },

  // Header
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  greeting: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
  },
  heroName: {
    fontFamily: fontFamily.display,
    fontSize: 28,
    fontWeight: '600',
    marginTop: 2,
  },

  // Section
  section:      { gap: spacing[4] },
  sectionTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    fontWeight: '600',
  },

  // Quick action buttons — soft pastel chips with haptic spring presses
  quickRow: { flexDirection: 'row', justifyContent: 'space-between' },
  quickBtn: {
    borderRadius: borderRadius.xl,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing[1],
    boxShadow: '0 4px 12px rgba(60,52,30,0.06)',
  },
  quickLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '600',
    textAlign: 'center',
  },

  notesHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: spacing[3] },
  notesLink: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600' },
  notesEmpty: { fontFamily: fontFamily.body, fontSize: fontSize.body, lineHeight: 20 },
  notesList: { gap: spacing[2] },
  notePreviewRow: { borderTopWidth: 1, paddingTop: spacing[2], gap: spacing[1] },
  notePreviewBody: { fontFamily: fontFamily.body, fontSize: fontSize.body, lineHeight: 20 },
  notePreviewTime: { fontFamily: fontFamily.body, fontSize: fontSize.caption },
});
