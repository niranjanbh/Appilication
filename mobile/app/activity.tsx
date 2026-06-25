import { Ionicons } from '@expo/vector-icons';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { AmbientBackground } from '../components/ui/AmbientBackground';
import { GlassCard } from '../components/ui/GlassCard';
import { HapticPressable } from '../components/ui/HapticPressable';
import { useTheme } from '../lib/theme';
import { listActivityApi, type ActivityItem } from '../lib/api/activity';
import {
  borderRadius,
  colors,
  fontFamily,
  fontSize,
  spacing,
  tintSoft,
  withAlpha,
  type TintName,
} from '../lib/design-tokens';

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

// ── Category mapping ─────────────────────────────────────────────────────────

type Category = 'security' | 'health' | 'payments' | 'account';

interface ActionMeta {
  icon: IoniconName;
  tint: TintName;
  label: string;
  category: Category;
}

const ACTION_META: Record<string, ActionMeta> = {
  login:                    { icon: 'log-in-outline',        tint: 'blue',    label: 'Signed in',                  category: 'security' },
  google_login:             { icon: 'logo-google',           tint: 'blue',    label: 'Signed in with Google',      category: 'security' },
  signup:                   { icon: 'person-add-outline',    tint: 'green',   label: 'Account created',            category: 'account' },
  phone_verified:           { icon: 'checkmark-circle-outline', tint: 'green', label: 'Phone verified',            category: 'security' },
  revoke_session:           { icon: 'log-out-outline',       tint: 'amber',   label: 'Signed out a device',        category: 'security' },
  password_reset_request:   { icon: 'key-outline',           tint: 'amber',   label: 'Password reset requested',   category: 'security' },
  password_reset_confirm:   { icon: 'key-outline',           tint: 'green',   label: 'Password changed',           category: 'security' },

  capture_consent:          { icon: 'shield-checkmark-outline', tint: 'green', label: 'Consent granted',           category: 'account' },
  withdraw_consent:         { icon: 'shield-outline',        tint: 'amber',   label: 'Consent withdrawn',          category: 'account' },
  capture_recording_consent: { icon: 'mic-outline',          tint: 'green',   label: 'Recording consent given',    category: 'account' },
  request_data_export:      { icon: 'download-outline',      tint: 'blue',    label: 'Data export requested',      category: 'account' },
  request_erasure:          { icon: 'trash-outline',         tint: 'peach',   label: 'Account deletion requested', category: 'account' },
  set_emergency_contact:    { icon: 'call-outline',          tint: 'saffron', label: 'Emergency contact updated',  category: 'account' },

  book_consultation:        { icon: 'calendar-outline',      tint: 'forest',  label: 'Consultation booked',        category: 'health' },
  request_consultation:     { icon: 'chatbubble-outline',    tint: 'forest',  label: 'Consultation requested',     category: 'health' },
  cancel_consultation:      { icon: 'close-circle-outline',  tint: 'peach',   label: 'Consultation cancelled',     category: 'health' },
  reschedule_consultation:  { icon: 'swap-horizontal-outline', tint: 'saffron', label: 'Consultation rescheduled', category: 'health' },
  finalize_lab_report:      { icon: 'document-attach-outline', tint: 'sage',  label: 'Lab report uploaded',        category: 'health' },
  log_vitals:               { icon: 'pulse-outline',         tint: 'green',   label: 'Vitals logged',              category: 'health' },
  health_sync:              { icon: 'fitness-outline',       tint: 'green',   label: 'Health data synced',         category: 'health' },
  abha_link:                { icon: 'link-outline',          tint: 'blue',    label: 'ABHA number linked',         category: 'health' },
  abha_create_confirm:      { icon: 'add-circle-outline',    tint: 'blue',    label: 'ABHA number created',        category: 'health' },

  confirm_payment:          { icon: 'card-outline',          tint: 'green',   label: 'Payment confirmed',          category: 'payments' },
  create_payment_order:     { icon: 'card-outline',          tint: 'saffron', label: 'Payment started',            category: 'payments' },
};

const NOISE_ACTIONS = new Set([
  'token_refresh',
  'register_push_token',
  'send_otp',
]);

const CATEGORY_META: Record<Category, { label: string; icon: IoniconName }> = {
  security: { label: 'Security',  icon: 'shield-outline' },
  health:   { label: 'Health',    icon: 'heart-outline' },
  payments: { label: 'Payments',  icon: 'card-outline' },
  account:  { label: 'Account',   icon: 'person-outline' },
};

const ALL_CATEGORIES: Category[] = ['security', 'health', 'payments', 'account'];

function getMeta(action: string): ActionMeta {
  return ACTION_META[action] ?? {
    icon: 'ellipsis-horizontal-outline',
    tint: 'sage' as TintName,
    label: action.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    category: 'account' as Category,
  };
}

// ── Date grouping ────────────────────────────────────────────────────────────

function dateKey(iso: string): string {
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'long', year: 'numeric',
  });
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-IN', {
    hour: '2-digit', minute: '2-digit', hour12: true,
  });
}

function isToday(iso: string): boolean {
  const d = new Date(iso);
  const now = new Date();
  return d.getDate() === now.getDate() && d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
}

function isYesterday(iso: string): boolean {
  const d = new Date(iso);
  const y = new Date();
  y.setDate(y.getDate() - 1);
  return d.getDate() === y.getDate() && d.getMonth() === y.getMonth() && d.getFullYear() === y.getFullYear();
}

function friendlyDateLabel(iso: string): string {
  if (isToday(iso)) return 'Today';
  if (isYesterday(iso)) return 'Yesterday';
  return dateKey(iso);
}

interface DateGroup {
  label: string;
  items: ActivityItem[];
}

function groupByDate(items: ActivityItem[]): DateGroup[] {
  const map = new Map<string, { label: string; items: ActivityItem[] }>();
  for (const item of items) {
    const key = dateKey(item.timestamp);
    const existing = map.get(key);
    if (existing) {
      existing.items.push(item);
    } else {
      map.set(key, { label: friendlyDateLabel(item.timestamp), items: [item] });
    }
  }
  return Array.from(map.values());
}

// ── Filter chips ─────────────────────────────────────────────────────────────

function FilterChip({
  label,
  icon,
  active,
  onPress,
  tColor,
}: {
  label: string;
  icon: IoniconName;
  active: boolean;
  onPress: () => void;
  tColor: { primary: string; textSub: string; isDark: boolean };
}) {
  const bg = active
    ? withAlpha(tColor.primary, tColor.isDark ? 0.20 : 0.12)
    : 'transparent';
  const color = active ? tColor.primary : tColor.textSub;
  const border = active
    ? withAlpha(tColor.primary, 0.3)
    : withAlpha(tColor.textSub, 0.15);

  return (
    <HapticPressable
      haptic="selection"
      onPress={onPress}
      accessibilityLabel={`Filter by ${label}`}
      accessibilityState={{ selected: active }}
      style={[chip.container, { backgroundColor: bg, borderColor: border }]}
    >
      <Ionicons name={icon} size={14} color={color} />
      <Text style={[chip.label, { color }]}>{label}</Text>
    </HapticPressable>
  );
}

const chip = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[1],
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
    borderRadius: borderRadius.full,
    borderWidth: 1,
  },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '600',
  },
});

// ── Activity row ─────────────────────────────────────────────────────────────

function ActivityRow({ item }: { item: ActivityItem }) {
  const t = useTheme();
  const meta = getMeta(item.action);
  const pair = tintSoft[meta.tint];
  const chipBg = t.isDark ? pair.bgDark : pair.bgLight;
  const tint = t.isDark ? pair.tintDark : pair.tintLight;

  return (
    <View style={[row.container, { backgroundColor: t.surface }]}>
      <View style={[row.iconWrap, { backgroundColor: chipBg }]}>
        <Ionicons name={meta.icon} size={18} color={tint} />
      </View>
      <View style={row.body}>
        <Text style={[row.label, { color: t.text }]} numberOfLines={1}>
          {meta.label}
        </Text>
        <Text style={[row.time, { color: t.textSub }]}>
          {formatTime(item.timestamp)}
          {!item.allowed ? ' · Blocked' : ''}
        </Text>
      </View>
      {!item.allowed && (
        <View style={[row.blockedPill, { backgroundColor: withAlpha(colors.alert, 0.12) }]}>
          <Text style={[row.blockedText, { color: colors.alert }]}>Denied</Text>
        </View>
      )}
    </View>
  );
}

const row = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    borderRadius: borderRadius.xl,
  },
  iconWrap: {
    width: 36,
    height: 36,
    borderRadius: borderRadius.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  body: { flex: 1, gap: 2 },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
  time: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
  },
  blockedPill: {
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
    borderRadius: borderRadius.full,
  },
  blockedText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
  },
});

// ── Screen ───────────────────────────────────────────────────────────────────

export default function ActivityScreen() {
  const t = useTheme();
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<Category | null>(null);

  const fetchActivity = useCallback(async () => {
    try {
      const data = await listActivityApi(1, 100);
      setItems(data.items);
      setError(null);
    } catch {
      setError('Could not load your activity.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { void fetchActivity(); }, [fetchActivity]);

  const handleRefresh = useCallback(() => {
    setRefreshing(true);
    void fetchActivity();
  }, [fetchActivity]);

  const filtered = useMemo(() => {
    const meaningful = items.filter(it => !NOISE_ACTIONS.has(it.action));
    if (activeFilter == null) return meaningful;
    return meaningful.filter(it => getMeta(it.action).category === activeFilter);
  }, [items, activeFilter]);

  const groups = useMemo(() => groupByDate(filtered), [filtered]);

  if (loading) {
    return (
      <View style={[styles.center, { backgroundColor: t.background }]}>
        <AmbientBackground />
        <ActivityIndicator color={t.primary} />
      </View>
    );
  }

  if (error) {
    return (
      <View style={[styles.center, { backgroundColor: t.background }]}>
        <AmbientBackground />
        <Ionicons name="alert-circle-outline" size={36} color={colors.alert} />
        <Text style={[styles.errorText, { color: colors.alert }]}>{error}</Text>
        <Pressable style={styles.retryBtn} onPress={() => void fetchActivity()}>
          <Text style={[styles.retryText, { color: t.primary }]}>Try again</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={[styles.flex, { backgroundColor: t.background }]}>
      <AmbientBackground />
      <ScrollView
        style={styles.flex}
        contentContainerStyle={styles.container}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor={t.primary} />
        }
      >
        {/* Filter chips */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.filterRow}
        >
          <FilterChip
            label="All"
            icon="apps-outline"
            active={activeFilter == null}
            onPress={() => setActiveFilter(null)}
            tColor={t}
          />
          {ALL_CATEGORIES.map(cat => (
            <FilterChip
              key={cat}
              label={CATEGORY_META[cat].label}
              icon={CATEGORY_META[cat].icon}
              active={activeFilter === cat}
              onPress={() => setActiveFilter(prev => prev === cat ? null : cat)}
              tColor={t}
            />
          ))}
        </ScrollView>

        {filtered.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="shield-checkmark-outline" size={48} color={t.textSub} />
            <Text style={[styles.emptyTitle, { color: t.text }]}>
              {activeFilter ? 'No activity in this category' : 'No recent activity'}
            </Text>
            <Text style={[styles.emptySub, { color: t.textSub }]}>
              {activeFilter
                ? 'Try selecting a different filter above.'
                : 'Consultations, uploads, sign-ins, and consent changes will appear here.'}
            </Text>
          </View>
        ) : (
          groups.map(group => (
            <View key={group.label} style={styles.dateGroup}>
              <Text style={[styles.dateLabel, { color: t.textSub }]}>{group.label}</Text>
              <View style={styles.groupItems}>
                {group.items.map((it, idx) => (
                  <ActivityRow key={`${it.action}-${it.timestamp}-${idx}`} item={it} />
                ))}
              </View>
            </View>
          ))
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[4],
    paddingTop: spacing[4],
    paddingBottom: spacing[16],
    gap: spacing[5],
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing[4],
    padding: spacing[6],
  },
  errorText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    textAlign: 'center',
  },
  retryBtn: { alignItems: 'center' },
  retryText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },

  filterRow: {
    flexDirection: 'row',
    gap: spacing[2],
    paddingRight: spacing[2],
  },

  dateGroup: { gap: spacing[2] },
  dateLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
    paddingHorizontal: spacing[1],
  },
  groupItems: { gap: spacing[2] },

  emptyState: {
    paddingVertical: spacing[16],
    alignItems: 'center',
    gap: spacing[3],
  },
  emptyTitle: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h3,
    fontWeight: '500',
    textAlign: 'center',
  },
  emptySub: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    textAlign: 'center',
    lineHeight: 22,
    paddingHorizontal: spacing[4],
  },
});
