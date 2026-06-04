import { Dimensions, Pressable, ScrollView, StyleSheet, Text, useColorScheme, View } from 'react-native';
import { useRouter } from 'expo-router';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { useAuth } from '../../lib/auth/context';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

const { width: SCREEN_W } = Dimensions.get('window');
const H_PAD = spacing[6];
const GAP   = spacing[3];
const QUICK_SIZE = Math.max((SCREEN_W - H_PAD * 2 - GAP * 3) / 4, 56);

// ─── Quick actions ────────────────────────────────────────────────────────────

interface QuickAction {
  id: string;
  label: string;
  icon: string;
  lightBg: string;
  darkBg: string;
  tint: string;
  route: string;
}

const QUICK_ACTIONS: QuickAction[] = [
  { id: 'consult',   label: 'Consult',   icon: '🩺', lightBg: '#EBF3FF', darkBg: '#0F1E38', tint: colors.electricBlue, route: '/(tabs)/consultations' },
  { id: 'reminders', label: 'Reminders', icon: '⏰', lightBg: '#FFF4E5', darkBg: '#2A1A05', tint: colors.warningAmber,  route: '/(tabs)/reminders' },
  { id: 'reports',   label: 'Reports',   icon: '🔬', lightBg: '#EDFAF3', darkBg: '#061E12', tint: colors.successGreen,  route: '/(tabs)/reports' },
  { id: 'profile',   label: 'Profile',   icon: '👤', lightBg: '#F3EFFF', darkBg: '#150F2B', tint: '#7C3AED',            route: '/(tabs)/profile' },
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
  const scale = useSharedValue(1);
  const anim  = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));

  return (
    <Animated.View style={[{ width: QUICK_SIZE }, anim]}>
      <Pressable
        onPress={onPress}
        onPressIn={() => { scale.value = withSpring(0.90, { mass: 0.25, stiffness: 500 }); }}
        onPressOut={() => { scale.value = withSpring(1,    { mass: 0.25, stiffness: 500 }); }}
        style={[
          styles.quickBtn,
          { width: QUICK_SIZE, height: QUICK_SIZE, backgroundColor: isDark ? action.darkBg : action.lightBg },
        ]}
        accessibilityLabel={action.label}
      >
        <Text style={styles.quickIcon}>{action.icon}</Text>
        <Text style={[styles.quickLabel, { color: action.tint }]}>{action.label}</Text>
      </Pressable>
    </Animated.View>
  );
}

// ─── Main screen ──────────────────────────────────────────────────────────────

export default function HomeScreen() {
  const { state } = useAuth();
  const router    = useRouter();
  const isDark    = useColorScheme() === 'dark';

  const firstName = state.status === 'authenticated' ? state.user.name.split(' ')[0] : '';
  const initials  = state.status === 'authenticated' ? getInitials(state.user.name) : 'K';

  const ctaScale = useSharedValue(1);
  const ctaAnim  = useAnimatedStyle(() => ({ transform: [{ scale: ctaScale.value }] }));

  const bg       = isDark ? colors.midnight     : colors.skyMist;
  const textPri  = isDark ? colors.white        : colors.navyDeep;
  const textSub  = isDark ? colors.slateText    : colors.coolGray;
  const cardBg   = isDark ? colors.nightSurface : colors.white;
  const cardBdr  = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)';

  return (
    <ScrollView
      style={[styles.flex, { backgroundColor: bg }]}
      contentContainerStyle={styles.container}
      showsVerticalScrollIndicator={false}
    >

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <View style={styles.header}>
        <View>
          <Text style={[styles.greeting, { color: textSub }]}>{getGreeting()}</Text>
          <Text style={[styles.heroName, { color: textPri }]}>{firstName || 'Welcome'}</Text>
        </View>
        <View style={[styles.avatar, { backgroundColor: colors.navyDeep }]}>
          <Text style={styles.avatarText}>{initials}</Text>
        </View>
      </View>

      {/* ── Hero CTA — dark navy card ──────────────────────────────────────── */}
      <Animated.View style={ctaAnim}>
        <Pressable
          onPress={() => router.push('/consultations/book')}
          onPressIn={() => { ctaScale.value = withSpring(0.97, { mass: 0.5, stiffness: 400 }); }}
          onPressOut={() => { ctaScale.value = withSpring(1,    { mass: 0.5, stiffness: 400 }); }}
          accessibilityLabel="Book your first consultation"
        >
          <View style={styles.heroCard}>
            {/* glass-effect inner border */}
            <View style={styles.heroRow}>
              <View style={styles.heroIconWrap}>
                <Text style={styles.heroIconEmoji}>🛡️</Text>
              </View>
              <View style={styles.heroContent}>
                <Text style={styles.heroTitle}>Complete your health profile</Text>
                <Text style={styles.heroSub}>5 quick questions · ~2 min</Text>
              </View>
              <Text style={styles.heroArrow}>→</Text>
            </View>
            {/* progress bar */}
            <View style={styles.progressTrack}>
              <View style={styles.progressFill} />
            </View>
          </View>
        </Pressable>
      </Animated.View>

      {/* ── Quick actions ─────────────────────────────────────────────────── */}
      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: textPri }]}>Quick actions</Text>
        <View style={styles.quickRow}>
          {QUICK_ACTIONS.map(a => (
            <QuickBtn
              key={a.id}
              action={a}
              isDark={isDark}
              onPress={() => router.push(a.route as never)}
            />
          ))}
        </View>
      </View>

      {/* ── Care plan card ────────────────────────────────────────────────── */}
      <View style={[styles.carePlanCard, { backgroundColor: cardBg, borderColor: cardBdr }]}>
        <Text style={[styles.eyebrow, { color: textSub }]}>YOUR CARE PLAN</Text>
        <Text style={[styles.carePlanTitle, { color: textPri }]}>
          Personalized care starts here
        </Text>
        <Text style={[styles.carePlanBody, { color: textSub }]}>
          Talk to a Kyros specialist about your hormonal health. Your care plan —
          prescriptions, reminders, and lab orders — will appear here after your
          first consultation.
        </Text>
      </View>

    </ScrollView>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flexGrow: 1,
    paddingHorizontal: H_PAD,
    paddingTop: spacing[6],
    paddingBottom: spacing[12],
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

  // Hero card (dark navy — skeuomorphic glow + glass border)
  heroCard: {
    backgroundColor: colors.navyDeep,
    borderRadius: borderRadius.xxl,
    padding: spacing[4],
    gap: spacing[4],
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.10)',
    shadowColor: colors.navyDeep,
    shadowOffset: { width: 0, height: 14 },
    shadowOpacity: 0.40,
    shadowRadius: 24,
    elevation: 10,
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
  heroIconEmoji: { fontSize: 22 },
  heroContent:   { flex: 1 },
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
  heroArrow: {
    fontFamily: fontFamily.body,
    fontSize: 20,
    color: 'rgba(255,255,255,0.60)',
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

  // Quick action buttons (claymorphism: soft rounded, inset shadow, pastel bg)
  quickRow:  { flexDirection: 'row', justifyContent: 'space-between' },
  quickBtn: {
    borderRadius: borderRadius.xl,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing[1],
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.09,
    shadowRadius: 10,
    elevation: 3,
  },
  quickIcon:  { fontSize: 24 },
  quickLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '600',
    textAlign: 'center',
  },

  // Care plan card (glassmorphism: white/dark surface, subtle border, soft shadow)
  carePlanCard: {
    borderRadius: borderRadius.xxl,
    padding: spacing[6],
    gap: spacing[2],
    borderWidth: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 14,
    elevation: 2,
  },
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
