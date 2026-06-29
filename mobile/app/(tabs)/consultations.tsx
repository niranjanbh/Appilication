import { useQuery } from '@tanstack/react-query';
import { Ionicons } from '@expo/vector-icons';
import {
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import { apiFetch } from '../../lib/api/client';
import { AmbientBackground } from '../../components/ui/AmbientBackground';
import { TAB_DOCK_CLEARANCE } from '../../components/ui/GlassTabBar';
import { HapticPressable } from '../../components/ui/HapticPressable';
import { GlassCard } from '../../components/ui/GlassCard';
import { SkeletonCards } from '../../components/ui/Skeleton';
import { Button } from '../../components/Button';
import { listPatientNotesApi } from '../../lib/api/patient-notes';
import {
  borderRadius,
  colors,
  fontFamily,
  fontSize,
  spacing,
  tintSoft,
  withAlpha,
  type TintName,
} from '../../lib/design-tokens';
import { useTheme, type AppPalette } from '../../lib/theme';

// ── Types ──────────────────────────────────────────────────────────────────────

type ConsultationStatus =
  | 'requested' | 'scheduled' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled' | 'no_show';

interface Consultation {
  id: string;
  doctor_id: string | null;
  doctor_name: string | null;
  doctor_specialty: string[] | null;
  condition_category: string;
  consultation_type: string;
  scheduled_start_at: string | null;
  scheduled_end_at: string | null;
  status: ConsultationStatus;
  video_room_id: string | null;
  consultation_fee_paise: number | null;
  payment_id: string | null;
  cancellation_reason: string | null;
}

interface ListResponse {
  items: Consultation[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

const UPCOMING_STATUSES: ConsultationStatus[] = ['requested', 'scheduled', 'confirmed', 'in_progress'];
function isUpcoming(c: Consultation): boolean { return UPCOMING_STATUSES.includes(c.status); }
function formatDate(iso: string) { return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }); }
function formatTime(iso: string) { return new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true }); }
function formatRupees(p: number) { return `₹${(p / 100).toFixed(0)}`; }
const CONDITION_LABEL: Record<string, string> = {
  weight: 'Weight Management',
  pcos: 'PCOS',
  thyroid: 'Thyroid',
  skin_hair: 'Skin & Hair',
  mens_intimate: 'Sexual & Intimate Health',
  hormones_trt: 'Hormones & TRT',
  longevity: 'Longevity',
};
function formatCat(cat: string): string {
  return CONDITION_LABEL[cat] ?? cat.replace(/_/g, ' ').replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}
// A requested consultation has no slot yet — show a friendly placeholder.
function formatWhen(iso: string | null) {
  return iso ? `${formatDate(iso)} · ${formatTime(iso)}` : 'Awaiting assignment';
}

// Relative time from now to an appointment slot.
function formatCountdown(iso: string): string {
  const diff = new Date(iso).getTime() - Date.now();
  if (diff <= 0) return 'Now';
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  if (days > 1) return `In ${days} days`;
  if (days === 1) return 'Tomorrow';
  if (hours > 0) return `In ${hours}h ${minutes % 60}m`;
  if (minutes < 1) return 'Starting soon';
  return `In ${minutes} min`;
}

const STATUS_LABEL: Record<ConsultationStatus, string> = {
  requested: 'Awaiting match', scheduled: 'Scheduled', confirmed: 'Confirmed',
  in_progress: 'In progress', completed: 'Completed', cancelled: 'Cancelled', no_show: 'No show',
};

const STATUS_COLOR: Record<ConsultationStatus, string> = {
  requested:   colors.saffron,
  scheduled:   colors.forest,
  confirmed:   colors.jade,
  in_progress: colors.saffron,
  completed:   colors.jade,
  cancelled:   colors.alert,
  no_show:     colors.alert,
};

// Four-step journey. `active` is the 1-based index of the highlighted step.
const TRACKER_STEPS = ['Requested', 'Assigned', 'Scheduled', 'Consult'] as const;
function activeStepFor(status: ConsultationStatus): number {
  switch (status) {
    case 'requested':   return 1;
    case 'scheduled':   return 2; // doctor assigned, awaiting payment
    case 'confirmed':   return 3; // paid / confirmed
    case 'in_progress': return 4;
    default:            return 0;
  }
}

// Condition categories shown in the rich empty state — mirrors the booking flow.
// `slug` must match the backend's accepted condition slugs so tapping a tile
// can skip the condition-picker step and go straight to the requirement step.
interface ConditionTile { label: string; emoji: string; tint: TintName; slug: string }
const CONDITION_TILES: ConditionTile[] = [
  { label: 'Weight Management', emoji: '⚖️', tint: 'forest',  slug: 'weight-management' },
  { label: 'Diabetes',          emoji: '🩸', tint: 'peach',   slug: 'diabetes' },
  { label: 'Thyroid',           emoji: '🦋', tint: 'violet',  slug: 'thyroid' },
  { label: 'PCOS',              emoji: '🌿', tint: 'green',   slug: 'pcos' },
  { label: 'Skin & Hair',       emoji: '✨', tint: 'amber',   slug: 'skin-and-hair' },
  { label: 'Sexual Health',     emoji: '🔬', tint: 'blue',    slug: 'sexual-health' },
  { label: 'Hormones & TRT',    emoji: '⚡', tint: 'saffron', slug: 'hormones-trt' },
  { label: 'Longevity',         emoji: '🌱', tint: 'sage',    slug: 'longevity' },
];

// ── Progress tracker ─────────────────────────────────────────────────────────

function ProgressTracker({ active, t }: { active: number; t: AppPalette }) {
  return (
    <View style={styles.tracker}>
      {TRACKER_STEPS.map((label, i) => {
        const stepNo = i + 1;
        const isActive = stepNo === active;
        const isDone = stepNo < active;
        const reached = isActive || isDone;
        const dotColor = reached ? colors.jade : withAlpha(t.textSub, 0.25);
        const lineColor = stepNo < active ? colors.jade : withAlpha(t.textSub, 0.25);
        return (
          <View key={label} style={styles.trackerStep}>
            <View style={styles.trackerRow}>
              {i > 0 && <View style={[styles.trackerLine, { backgroundColor: lineColor }]} />}
              <View
                style={[
                  styles.trackerDot,
                  { backgroundColor: reached ? dotColor : 'transparent', borderColor: dotColor },
                  isActive && styles.trackerDotActive,
                ]}
              >
                {isDone ? (
                  <Ionicons name="checkmark" size={11} color={colors.ivory} />
                ) : (
                  <Text style={[styles.trackerDotNum, { color: isActive ? colors.ivory : t.textSub }]}>
                    {stepNo}
                  </Text>
                )}
              </View>
              {i < TRACKER_STEPS.length - 1 && (
                <View
                  style={[
                    styles.trackerLine,
                    { backgroundColor: stepNo < active ? colors.jade : withAlpha(t.textSub, 0.25) },
                  ]}
                />
              )}
            </View>
            <Text
              style={[
                styles.trackerLabel,
                { color: reached ? t.text : withAlpha(t.textSub, 0.6) },
              ]}
              numberOfLines={1}
            >
              {label}
            </Text>
          </View>
        );
      })}
    </View>
  );
}

// ── Tappable hint row ──────────────────────────────────────────────────────────

function HintRow({
  icon,
  label,
  onPress,
  t,
}: {
  icon: React.ComponentProps<typeof Ionicons>['name'];
  label: string;
  onPress: () => void;
  t: AppPalette;
}) {
  return (
    <HapticPressable
      haptic="selection"
      onPress={onPress}
      accessibilityLabel={label}
      style={[styles.hintRow, { borderColor: withAlpha(t.textSub, 0.12) }]}
    >
      <Ionicons name={icon} size={16} color={colors.jade} />
      <Text style={[styles.hintLabel, { color: t.text }]} numberOfLines={1}>{label}</Text>
      <Ionicons name="chevron-forward" size={14} color={t.textSub} />
    </HapticPressable>
  );
}

// ── Consultation card ────────────────────────────────────────────────────────

function ConsultationCard({
  item,
  t,
  router,
}: {
  item: Consultation;
  t: AppPalette;
  router: ReturnType<typeof useRouter>;
}) {
  const sc = STATUS_COLOR[item.status];
  const active = activeStepFor(item.status);
  const slot = item.scheduled_start_at;

  return (
    <HapticPressable
      scaleTo={0.98}
      onPress={() => router.push(`/consultations/${item.id}`)}
      containerStyle={styles.cardSpacing}
      accessibilityLabel={`Consultation, ${formatCat(item.condition_category)}, ${STATUS_LABEL[item.status]}`}
    >
      <GlassCard unpadded>
        <View style={styles.card}>
          {/* Header */}
          <View style={styles.cardHeader}>
            <Text style={[styles.cardCategory, { color: t.text }]} numberOfLines={1}>
              {formatCat(item.condition_category)}
            </Text>
            <View style={[styles.statusPill, { backgroundColor: withAlpha(sc, 0.12) }]}>
              <Text style={[styles.statusText, { color: sc }]}>{STATUS_LABEL[item.status]}</Text>
            </View>
          </View>
          <Text style={[styles.cardMeta, { color: t.textSub }]}>
            {item.consultation_type === 'initial' ? 'Initial consultation' : 'Follow-up'}
            {item.consultation_fee_paise != null ? ` · ${formatRupees(item.consultation_fee_paise)}` : ''}
          </Text>

          {/* Progress tracker (not shown for terminal states) */}
          {active > 0 && <ProgressTracker active={active} t={t} />}

          {/* Status-specific body */}
          {item.status === 'requested' && (
            <View style={styles.cardBody}>
              <Text style={[styles.cardNote, { color: t.textSub }]}>Usually matched within 24 hours</Text>
              <Text style={[styles.prepLabel, { color: t.textSub }]}>Prepare for your visit</Text>
              <HintRow icon="document-attach-outline" label="Upload lab reports" t={t}
                onPress={() => router.push('/(tabs)/reports')} />
              <HintRow icon="person-outline" label="Complete your health profile" t={t}
                onPress={() => router.push('/(tabs)/profile')} />
            </View>
          )}

          {item.status === 'scheduled' && (
            <View style={styles.cardBody}>
              <View style={styles.assignRow}>
                <Ionicons name="medkit-outline" size={15} color={colors.jade} />
                <Text style={[styles.cardNote, { color: t.text }]}>
                  {item.doctor_name ? `Dr ${item.doctor_name}` : 'Doctor assigned'}
                  {item.doctor_specialty && item.doctor_specialty.length > 0
                    ? ` · ${item.doctor_specialty.map(formatCat).join(', ')}`
                    : ''}
                </Text>
              </View>
              {slot && (
                <Text style={[styles.countdown, { color: t.primary }]}>
                  {formatCountdown(slot)} · {formatWhen(slot)}
                </Text>
              )}
              <Text style={[styles.payHint, { color: colors.saffron }]}>Tap to view details and confirm</Text>
            </View>
          )}

          {item.status === 'confirmed' && (
            <View style={styles.cardBody}>
              {item.doctor_name && (
                <View style={styles.assignRow}>
                  <Ionicons name="medkit-outline" size={15} color={colors.jade} />
                  <Text style={[styles.cardNote, { color: t.text }]}>
                    Dr {item.doctor_name}
                    {item.doctor_specialty && item.doctor_specialty.length > 0
                      ? ` · ${item.doctor_specialty.map(formatCat).join(', ')}`
                      : ''}
                  </Text>
                </View>
              )}
              {slot && (
                <Text style={[styles.countdown, { color: t.primary }]}>
                  {formatCountdown(slot)} · {formatWhen(slot)}
                </Text>
              )}
              <Text style={[styles.prepLabel, { color: t.textSub }]}>Before your consultation</Text>
              <HintRow icon="document-attach-outline" label="Upload lab reports" t={t}
                onPress={() => router.push('/(tabs)/reports')} />
              <HintRow icon="person-outline" label="Review your health profile" t={t}
                onPress={() => router.push('/(tabs)/profile')} />
            </View>
          )}

          {item.status === 'in_progress' && (
            <View style={styles.cardBody}>
              <Text style={[styles.liveLabel, { color: colors.saffron }]}>Call in progress</Text>
              {item.video_room_id ? (
                <HapticPressable
                  haptic="medium"
                  onPress={() => router.push(`/consultations/join/${item.id}`)}
                  accessibilityLabel="Join video call"
                  style={styles.joinBtn}
                >
                  <Ionicons name="videocam" size={18} color={colors.ivory} />
                  <Text style={styles.joinBtnText}>Join video call</Text>
                </HapticPressable>
              ) : (
                <Text style={[styles.cardNote, { color: t.textSub }]}>Call starting soon…</Text>
              )}
            </View>
          )}

          {item.status === 'completed' && (
            <View style={styles.cardBody}>
              <View style={styles.assignRow}>
                <Ionicons name="checkmark-circle" size={16} color={colors.jade} />
                <Text style={[styles.cardNote, { color: t.text }]}>Completed</Text>
              </View>
              <HintRow icon="clipboard-outline" label="View care plan" t={t}
                onPress={() => router.push('/care-plans')} />
              <HintRow icon="add-circle-outline" label="Book follow-up" t={t}
                onPress={() => router.push(`/consultations/book?followUp=${item.id}`)} />
            </View>
          )}

          {(item.status === 'cancelled' || item.status === 'no_show') && (
            <View style={styles.cardBody}>
              {item.cancellation_reason ? (
                <Text style={[styles.cardNote, { color: t.textSub }]}>
                  {item.cancellation_reason}
                </Text>
              ) : (
                <Text style={[styles.cardNote, { color: t.textSub }]}>
                  This consultation didn’t take place.
                </Text>
              )}
              <HintRow icon="refresh-outline" label="Book again" t={t}
                onPress={() => router.push('/consultations/book')} />
            </View>
          )}
        </View>
      </GlassCard>
    </HapticPressable>
  );
}

// ── Rich empty state ───────────────────────────────────────────────────────────

function ConditionGridCard({
  tile,
  t,
  onPress,
}: {
  tile: ConditionTile;
  t: AppPalette;
  onPress: (slug: string) => void;
}) {
  const pair = tintSoft[tile.tint];
  const bg = t.isDark ? pair.bgDark : pair.bgLight;
  const tint = t.isDark ? pair.tintDark : pair.tintLight;
  return (
    <HapticPressable
      haptic="selection"
      scaleTo={0.96}
      onPress={() => onPress(tile.slug)}
      accessibilityLabel={`Consult for ${tile.label}`}
      containerStyle={styles.gridCell}
      style={[styles.conditionCard, { backgroundColor: bg, borderColor: withAlpha(tint, 0.18) }]}
    >
      <Text style={styles.conditionEmoji}>{tile.emoji}</Text>
      <Text style={[styles.conditionLabel, { color: tint }]} numberOfLines={2}>{tile.label}</Text>
    </HapticPressable>
  );
}

function RichEmptyState({
  t,
  onBook,
  onBookCondition,
}: {
  t: AppPalette;
  onBook: () => void;
  onBookCondition: (slug: string) => void;
}) {
  return (
    <View>
      {/* Trust banner */}
      <GlassCard style={styles.trustCard}>
        <View style={styles.trustRow}>
          <Ionicons name="shield-checkmark-outline" size={18} color={colors.jade} />
          <Text style={[styles.trustText, { color: t.text }]}>
            Board-certified doctors · Video consultations · Evidence-based care
          </Text>
        </View>
      </GlassCard>

      {/* Condition grid */}
      <Text style={[styles.sectionLabel, styles.gridLabel, { color: t.textSub }]}>
        What can we help with?
      </Text>
      <View style={styles.grid}>
        {CONDITION_TILES.map(tile => (
          <ConditionGridCard key={tile.label} tile={tile} t={t} onPress={onBookCondition} />
        ))}
      </View>

      {/* Hero CTA */}
      <Button
        label="Book your first consultation"
        variant="forest"
        onPress={onBook}
        accessibilityLabel="Book your first consultation"
        style={styles.heroCta}
      />
    </View>
  );
}

// ── Notes for your next visit ─────────────────────────────────────────────────

function formatRelativeShort(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return 'Today';
  if (days === 1) return 'Yesterday';
  return `${days}d ago`;
}

function NotesForVisit({ t, router }: { t: AppPalette; router: ReturnType<typeof useRouter> }) {
  const { data: notesData } = useQuery({
    queryKey: ['patient-notes', 'care-tab'],
    queryFn: () => listPatientNotesApi(1, 3),
    staleTime: 60_000,
  });

  const recentNotes = notesData?.items ?? [];

  return (
    <GlassCard style={styles.notesCard}>
      <View style={styles.notesHeader}>
        <View style={styles.notesHeaderLeft}>
          <Ionicons name="create-outline" size={16} color={t.primary} />
          <Text style={[styles.notesTitle, { color: t.text }]}>Notes for your visit</Text>
        </View>
        <HapticPressable
          onPress={() => router.push('/notes' as never)}
          accessibilityLabel={recentNotes.length === 0 ? 'Add a note' : 'View all notes'}
        >
          <Text style={[styles.notesLink, { color: t.primary }]}>
            {recentNotes.length === 0 ? 'Add note' : 'See all'}
          </Text>
        </HapticPressable>
      </View>
      {recentNotes.length === 0 ? (
        <Text style={[styles.notesEmpty, { color: t.textSub }]}>
          Jot down questions or symptoms to discuss with your doctor.
        </Text>
      ) : (
        <View style={styles.notesList}>
          {recentNotes.map(note => (
            <HapticPressable
              key={note.id}
              onPress={() => router.push('/notes' as never)}
              accessibilityLabel={`Note: ${note.body}`}
              style={[styles.noteRow, { borderColor: withAlpha(t.textSub, 0.12) }]}
            >
              <Text style={[styles.noteBody, { color: t.text }]} numberOfLines={1}>
                {note.body}
              </Text>
              <Text style={[styles.noteTime, { color: t.textSub }]}>
                {formatRelativeShort(note.created_at)}
              </Text>
            </HapticPressable>
          ))}
        </View>
      )}
    </GlassCard>
  );
}

// ── Screen ─────────────────────────────────────────────────────────────────────

export default function ConsultationsScreen() {
  const router = useRouter();
  const t = useTheme();

  const { data, isLoading, isFetching, error, refetch } = useQuery({
    queryKey: ['consultations'],
    queryFn: () => apiFetch<ListResponse>('/v1/clinic/patient/consultations?page_size=50'),
    staleTime: 60_000,
  });

  const consultations = data?.items ?? [];
  const upcoming = consultations.filter(isUpcoming);
  const past = consultations.filter(c => !isUpcoming(c));
  const isEmpty = !isLoading && consultations.length === 0;
  const goBook = () => router.push('/consultations/book');
  const goBookCondition = (slug: string) => router.push(`/consultations/book?condition=${slug}`);

  return (
    <View style={[styles.flex, { backgroundColor: t.background }]}>
      <AmbientBackground />
      <ScrollView
        style={styles.flex}
        contentContainerStyle={styles.container}
        refreshControl={
          <RefreshControl refreshing={isFetching && !isLoading} onRefresh={refetch} tintColor={t.primary} />
        }
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={[styles.title, { color: t.text }]}>Care</Text>
          {!isEmpty && (
            <Button
              label="+ Book"
              variant="forest"
              onPress={goBook}
              accessibilityLabel="Book a consultation"
              style={styles.bookBtn}
            />
          )}
        </View>

        {/* Notes for your next visit */}
        <NotesForVisit t={t} router={router} />

        {error && (
          <Text style={styles.error}>Could not load consultations. Please try again.</Text>
        )}

        {isLoading ? (
          <SkeletonCards count={3} />
        ) : isEmpty ? (
          <RichEmptyState t={t} onBook={goBook} onBookCondition={goBookCondition} />
        ) : (
          <>
            {/* Upcoming */}
            {upcoming.length > 0 && (
              <>
                <Text style={[styles.sectionLabel, { color: t.textSub }]}>Upcoming</Text>
                {upcoming.map(c => (
                  <ConsultationCard key={c.id} item={c} t={t} router={router} />
                ))}
              </>
            )}

            {/* Past */}
            {past.length > 0 && (
              <>
                <Text
                  style={[
                    styles.sectionLabel,
                    upcoming.length > 0 && styles.sectionLabelLower,
                    { color: t.textSub },
                  ]}
                >
                  Past
                </Text>
                {past.map(c => (
                  <ConsultationCard key={c.id} item={c} t={t} router={router} />
                ))}
              </>
            )}
          </>
        )}
      </ScrollView>
    </View>
  );
}

// ── Styles ─────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
    paddingBottom: TAB_DOCK_CLEARANCE,
  },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing[6],
  },
  title: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    fontWeight: '600',
  },
  bookBtn: { height: 36, paddingHorizontal: spacing[4] },

  sectionLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: spacing[3],
  },
  sectionLabelLower: { marginTop: spacing[6] },

  // Cards
  cardSpacing: { marginBottom: spacing[3] },
  card: {
    padding: spacing[4],
    gap: spacing[2],
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: spacing[2],
  },
  cardCategory: {
    flex: 1,
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    fontWeight: '700',
  },
  cardMeta: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
  },
  statusPill: {
    paddingHorizontal: spacing[2],
    paddingVertical: 3,
    borderRadius: borderRadius.full,
  },
  statusText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
  },
  cardBody: {
    gap: spacing[2],
    marginTop: spacing[1],
  },
  cardNote: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
  },
  countdown: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '700',
  },
  payHint: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: '700',
  },
  liveLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: '700',
  },
  prepLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginTop: spacing[1],
  },
  assignRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
  },

  // Progress tracker
  tracker: {
    flexDirection: 'row',
    marginTop: spacing[3],
    marginBottom: spacing[1],
  },
  trackerStep: {
    flex: 1,
    alignItems: 'center',
  },
  trackerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    width: '100%',
  },
  trackerLine: {
    flex: 1,
    height: 2,
    borderRadius: 1,
  },
  trackerDot: {
    width: 22,
    height: 22,
    borderRadius: borderRadius.full,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
  trackerDotActive: {
    transform: [{ scale: 1.08 }],
  },
  trackerDotNum: {
    fontFamily: fontFamily.body,
    fontSize: 10,
    fontWeight: '700',
  },
  trackerLabel: {
    fontFamily: fontFamily.body,
    fontSize: 10,
    fontWeight: '600',
    marginTop: spacing[1],
    textAlign: 'center',
  },

  // Hint rows
  hintRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
    paddingVertical: spacing[2],
    paddingHorizontal: spacing[3],
    borderRadius: borderRadius.lg,
    borderWidth: 1,
  },
  hintLabel: {
    flex: 1,
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: '500',
  },

  // Join call button
  joinBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing[2],
    height: 48,
    borderRadius: borderRadius.xl,
    backgroundColor: colors.forest,
  },
  joinBtnText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '700',
    color: colors.ivory,
  },

  // Rich empty state
  trustCard: { marginBottom: spacing[6] },
  trustRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
  },
  trustText: {
    flex: 1,
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: '500',
    lineHeight: 19,
  },
  gridLabel: { marginBottom: spacing[4] },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginHorizontal: -spacing[1],
  },
  gridCell: {
    width: '50%',
    paddingHorizontal: spacing[1],
    marginBottom: spacing[3],
  },
  conditionCard: {
    height: 96,
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    padding: spacing[3],
    justifyContent: 'space-between',
  },
  conditionEmoji: { fontSize: 26 },
  conditionLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '700',
  },
  heroCta: { marginTop: spacing[4] },

  // Notes for visit
  notesCard: { marginBottom: spacing[4] },
  notesHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing[3],
  },
  notesHeaderLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
  },
  notesTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
  notesLink: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    fontWeight: '600',
  },
  notesEmpty: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    lineHeight: 18,
  },
  notesList: { gap: spacing[2] },
  noteRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderTopWidth: 1,
    paddingTop: spacing[2],
    gap: spacing[3],
  },
  noteBody: {
    flex: 1,
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    lineHeight: 18,
  },
  noteTime: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
  },

  error: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: colors.alert,
    marginBottom: spacing[4],
  },
});
