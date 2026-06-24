/**
 * AdaptiveHero — the single most important call-to-action on Home.
 *
 * Resolves to one of two states from the patient's upcoming consultations:
 *   • a scheduled/confirmed consult  → a countdown card with a join affordance
 *   • nothing actionable             → "Book your first consultation" CTA
 *
 * A `requested` consult is handled by RequestedConsultBanner, not here, so the
 * hero falls back to the booking CTA in that case.
 */

import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { StyleSheet, Text, View } from 'react-native';
import { HapticPressable } from '../ui/HapticPressable';
import {
  borderRadius,
  colors,
  fontFamily,
  fontSize,
  spacing,
  withAlpha,
} from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';
import type { Consultation } from '../../lib/api/consultations';

// ── Countdown copy ──────────────────────────────────────────────────────────

/** "in 2 days", "in 3 hours", "in 20 min", "now". */
function countdownLabel(iso: string): string {
  const ms = new Date(iso).getTime() - Date.now();
  if (ms <= 0) return 'now';
  const mins = Math.round(ms / 60000);
  if (mins < 60) return `in ${mins} min`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `in ${hours} hour${hours === 1 ? '' : 's'}`;
  const days = Math.round(hours / 24);
  return `in ${days} day${days === 1 ? '' : 's'}`;
}

function whenLabel(iso: string): string {
  const d = new Date(iso);
  const date = d.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' });
  const time = d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
  return `${date} · ${time}`;
}

/** Joinable when in progress, or starting within 15 minutes. */
function isJoinable(c: Consultation): boolean {
  if (c.status === 'in_progress') return true;
  if (!c.scheduled_start_at) return false;
  const ms = new Date(c.scheduled_start_at).getTime() - Date.now();
  return ms <= 15 * 60000 && ms > -60 * 60000;
}

// ── Component ───────────────────────────────────────────────────────────────

export function AdaptiveHero({
  consult,
  onBook,
  onOpenConsult,
}: {
  /** The next scheduled/confirmed/in-progress consult with a slot, or null. */
  consult: Consultation | null;
  onBook: () => void;
  onOpenConsult: (id: string) => void;
}) {
  const t = useTheme();
  const gradientColors: readonly [string, string] = t.isDark
    ? [colors.jadeGlow, colors.forest]
    : [colors.jade, colors.forest];

  const hasSlot = consult != null && consult.scheduled_start_at != null;
  const joinable = consult != null && isJoinable(consult);

  const icon = hasSlot ? (joinable ? 'videocam' : 'calendar') : 'shield-checkmark-outline';
  const title = hasSlot
    ? joinable
      ? 'Your consultation is ready'
      : `Consultation ${countdownLabel(consult!.scheduled_start_at!)}`
    : 'Book your first consultation';
  const sub = hasSlot
    ? joinable
      ? 'Tap to join the video call'
      : whenLabel(consult!.scheduled_start_at!)
    : 'Talk to a Kyros specialist · ~2 min to book';

  const onPress = () => (consult ? onOpenConsult(consult.id) : onBook());

  return (
    <HapticPressable
      haptic="medium"
      scaleTo={0.97}
      onPress={onPress}
      accessibilityLabel={`${title}. ${sub}`}
    >
      <LinearGradient
        colors={gradientColors}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={styles.card}
      >
        {/* glass sheen along the top edge */}
        <LinearGradient
          colors={[withAlpha(colors.white, 0.14), withAlpha(colors.white, 0)]}
          style={[styles.sheen, { pointerEvents: 'none' }]}
        />
        <View style={styles.row}>
          <View style={styles.iconWrap}>
            <Ionicons name={icon} size={22} color={colors.white} />
          </View>
          <View style={styles.content}>
            <Text style={styles.title}>{title}</Text>
            <Text style={styles.sub}>{sub}</Text>
          </View>
          <Ionicons
            name={joinable ? 'arrow-forward-circle' : 'arrow-forward'}
            size={joinable ? 26 : 20}
            color={withAlpha(colors.white, joinable ? 0.92 : 0.6)}
          />
        </View>
      </LinearGradient>
    </HapticPressable>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: borderRadius.xxl,
    padding: spacing[4],
    borderWidth: 1,
    borderColor: withAlpha(colors.white, 0.1),
    overflow: 'hidden',
    boxShadow: `0 14px 24px ${withAlpha(colors.forest, 0.4)}`,
  },
  sheen: { position: 'absolute', top: 0, left: 0, right: 0, height: 56 },
  row: { flexDirection: 'row', alignItems: 'center', gap: spacing[3] },
  iconWrap: {
    width: 44,
    height: 44,
    borderRadius: borderRadius.xl,
    backgroundColor: withAlpha(colors.white, 0.12),
    alignItems: 'center',
    justifyContent: 'center',
  },
  content: { flex: 1 },
  title: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.ivoryText,
    fontWeight: '600',
  },
  sub: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: withAlpha(colors.white, 0.58),
    marginTop: 2,
  },
});
