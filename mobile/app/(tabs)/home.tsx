import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import { Dimensions, ScrollView, StyleSheet, Text, View } from 'react-native';
import { AmbientBackground } from '../../components/ui/AmbientBackground';
import { GlassCard } from '../../components/ui/GlassCard';
import { TAB_DOCK_CLEARANCE } from '../../components/ui/GlassTabBar';
import { HapticPressable } from '../../components/ui/HapticPressable';
import { useAuth } from '../../lib/auth/context';
import { listPatientNotesApi } from '../../lib/api/patient-notes';
import {
  borderRadius, colors, fontFamily, fontSize, spacing, tintSoft, withAlpha, type TintName,
} from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';
import { useQuery } from '@tanstack/react-query';

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
  { id: 'consult',   label: 'Consult',   icon: 'medkit-outline',        tint: 'blue',   route: '/(tabs)/consultations' },
  { id: 'reminders', label: 'Reminders', icon: 'alarm-outline',         tint: 'amber',  route: '/(tabs)/reminders' },
  { id: 'reports',   label: 'Reports',   icon: 'flask-outline',         tint: 'green',  route: '/(tabs)/reports' },
  { id: 'notes',     label: 'My Notes',  icon: 'create-outline',        tint: 'violet', route: '/notes' },
];

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

function getInitials(fullName: string): string {
  return fullName
    .trim()
    .split(/\s+/)
    .map(n => n[0] ?? '')
    .join('')
    .toUpperCase()
    .slice(0, 2);
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

  const recentNotes = notesData?.items ?? [];

  const firstName = state.status === 'authenticated' ? state.user.name.split(' ')[0] : '';
  const initials  = state.status === 'authenticated' ? getInitials(state.user.name) : 'K';

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
          <LinearGradient colors={[colors.navyMid, colors.navyDeep]} style={styles.avatar}>
            <Text style={styles.avatarText}>{initials}</Text>
          </LinearGradient>
        </View>

        {/* ── Hero CTA — gradient glass card ─────────────────────────────── */}
        <HapticPressable
          haptic="medium"
          scaleTo={0.97}
          onPress={() => router.push('/consultations/book')}
          accessibilityLabel="Book your first consultation"
        >
          <LinearGradient
            colors={[colors.navyMid, colors.navyDeep]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={styles.heroCard}
          >
            {/* glass sheen along the top edge */}
            <LinearGradient
              colors={[withAlpha(colors.white, 0.14), withAlpha(colors.white, 0)]}
              style={styles.heroSheen}
              pointerEvents="none"
            />
            <View style={styles.heroRow}>
              <View style={styles.heroIconWrap}>
                <Ionicons name="shield-checkmark-outline" size={22} color={colors.white} />
              </View>
              <View style={styles.heroContent}>
                <Text style={styles.heroTitle}>Complete your health profile</Text>
                <Text style={styles.heroSub}>5 quick questions · ~2 min</Text>
              </View>
              <Ionicons name="arrow-forward" size={20} color={withAlpha(colors.white, 0.6)} />
            </View>
            {/* progress bar */}
            <View style={styles.progressTrack}>
              <View style={styles.progressFill} />
            </View>
          </LinearGradient>
        </HapticPressable>

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
        <GlassCard>
          <View style={styles.carePlanInner}>
            <Text style={[styles.eyebrow, { color: t.textSub }]}>YOUR CARE PLAN</Text>
            <Text style={[styles.carePlanTitle, { color: t.text }]}>
              Personalized care starts here
            </Text>
            <Text style={[styles.carePlanBody, { color: t.textSub }]}>
              Talk to a Kyros specialist about your hormonal health. Your care plan —
              prescriptions, reminders, and lab orders — will appear here after your
              first consultation.
            </Text>
          </View>
        </GlassCard>

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
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.white,
    fontWeight: '700',
  },

  // Hero card — gradient surface with a glass sheen and soft glow
  heroCard: {
    borderRadius: borderRadius.xxl,
    padding: spacing[4],
    gap: spacing[4],
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.10)',
    overflow: 'hidden',
    boxShadow: `0 14px 24px ${withAlpha(colors.navyDeep, 0.40)}`,
  },
  heroSheen: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 56,
  },
  heroRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[3] },
  heroIconWrap: {
    width: 44,
    height: 44,
    borderRadius: borderRadius.xl,
    backgroundColor: 'rgba(255,255,255,0.12)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  heroContent: { flex: 1 },
  heroTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.white,
    fontWeight: '600',
  },
  heroSub: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: 'rgba(255,255,255,0.58)',
    marginTop: 2,
  },
  progressTrack: {
    height: 3,
    backgroundColor: 'rgba(255,255,255,0.12)',
    borderRadius: 2,
  },
  progressFill: {
    height: 3,
    width: '30%',
    backgroundColor: 'rgba(255,255,255,0.72)',
    borderRadius: 2,
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
    boxShadow: '0 4px 10px rgba(0,0,0,0.09)',
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

  carePlanInner: { gap: spacing[2] },
  eyebrow: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    letterSpacing: 1.2,
    textTransform: 'uppercase',
  },
  carePlanTitle: {
    fontFamily: fontFamily.display,
    fontSize: 22,
    fontWeight: '500',
    lineHeight: 28,
  },
  carePlanBody: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    lineHeight: 22,
  },
});
