import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { AmbientBackground } from '../../components/ui/AmbientBackground';
import { GlassCard } from '../../components/ui/GlassCard';
import { NeumorphCard } from '../../components/ui/NeumorphCard';
import { SkeuToggle } from '../../components/ui/SkeuToggle';
import { TAB_DOCK_CLEARANCE } from '../../components/ui/GlassTabBar';
import { HapticPressable } from '../../components/ui/HapticPressable';
import { IconChip } from '../../components/ui/IconChip';
import { useAuth } from '../../lib/auth/context';
import { borderRadius, colors, fontFamily, fontSize, spacing, type TintName , withAlpha } from '../../lib/design-tokens';
import { useThemePreference } from '../../lib/theme-context';

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getInitials(fullName: string): string {
  return fullName
    .trim()
    .split(/\s+/)
    .map(n => n[0] ?? '')
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

// ─── MenuItem ─────────────────────────────────────────────────────────────────

interface MenuItemProps {
  icon: IoniconName;
  tint: TintName;
  label: string;
  hint?: string;
  labelColor: string;
  hintColor: string;
  onPress: () => void;
  accessibilityLabel?: string;
}

function MenuItem({ icon, tint, label, hint, labelColor, hintColor, onPress, accessibilityLabel }: MenuItemProps) {
  return (
    <HapticPressable
      haptic="selection"
      scaleTo={0.98}
      style={styles.menuRow}
      onPress={onPress}
      accessibilityLabel={accessibilityLabel ?? label}
    >
      <IconChip icon={icon} tint={tint} size={36} />
      <Text style={[styles.menuLabel, { color: labelColor }]}>{label}</Text>
      <View style={styles.menuRight}>
        {hint ? <Text style={[styles.menuHint, { color: hintColor }]}>{hint}</Text> : null}
        <Ionicons name="chevron-forward" size={16} color={hintColor} />
      </View>
    </HapticPressable>
  );
}

function Separator({ isDark }: { isDark: boolean }) {
  return (
    <View
      style={[
        styles.separator,
        { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,31,63,0.06)' },
      ]}
    />
  );
}

// ─── Main screen ──────────────────────────────────────────────────────────────

export default function ProfileScreen() {
  const router = useRouter();
  const { state, signOut } = useAuth();
  const { colorScheme, setPreference } = useThemePreference();
  const isDark = colorScheme === 'dark';

  const user     = state.status === 'authenticated' ? state.user : null;
  const initials = user ? getInitials(user.name) : 'K';

  function handleThemeToggle(val: boolean) {
    setPreference(val ? 'dark' : 'light');
  }

  const bg      = isDark ? colors.midnight     : colors.skyMist;
  const textPri = isDark ? colors.white        : colors.navyDeep;
  const textSub = isDark ? colors.slateText    : colors.coolGray;
  const cardBg  = isDark ? colors.nightSurface : colors.white;

  return (
    <View style={[styles.flex, { backgroundColor: bg }]}>
      <AmbientBackground />
      <ScrollView
        style={styles.flex}
        contentContainerStyle={styles.container}
        showsVerticalScrollIndicator={false}
      >

        {/* ── Identity card ───────────────────────────────────────────────── */}
        {user && (
          <GlassCard>
            <View style={styles.identityRow}>
              <LinearGradient colors={[colors.navyMid, colors.navyDeep]} style={styles.avatar}>
                <Text style={styles.avatarText}>{initials}</Text>
              </LinearGradient>
              <View style={styles.identityInfo}>
                <Text style={[styles.userName, { color: textPri }]}>{user.name}</Text>
                <Text style={[styles.userDetail, { color: textSub }]}>
                  {user.phone ?? user.email ?? 'Kyros patient'}
                </Text>
                <View style={[styles.planBadge, { backgroundColor: isDark ? colors.nightElev : colors.iceBlue }]}>
                  <Text style={[styles.planBadgeText, { color: colors.electricBlue }]}>
                    Free plan
                  </Text>
                </View>
              </View>
            </View>
          </GlassCard>
        )}

        {/* ── Care section ────────────────────────────────────────────────── */}
        <View style={styles.group}>
          <Text style={[styles.groupLabel, { color: textSub }]}>Care</Text>
          <NeumorphCard unpadded>
            <View style={styles.groupCard}>
              <MenuItem
                icon="medkit-outline"
                tint="blue"
                label="Health Records (ABHA)"
                hint="Linked"
                labelColor={textPri}
                hintColor={textSub}
                onPress={() => router.push('/abha-settings')}
              />
              <Separator isDark={isDark} />
              <MenuItem
                icon="stats-chart-outline"
                tint="violet"
                label="Insights & trends"
                labelColor={textPri}
                hintColor={textSub}
                onPress={() => router.push('/insights')}
              />
              <Separator isDark={isDark} />
              <MenuItem
                icon="calendar-outline"
                tint="green"
                label="Appointments"
                labelColor={textPri}
                hintColor={textSub}
                onPress={() => router.push('/(tabs)/consultations' as never)}
              />
              <Separator isDark={isDark} />
              <MenuItem
                icon="people-outline"
                tint="amber"
                label="Emergency contact"
                labelColor={textPri}
                hintColor={textSub}
                onPress={() => router.push('/emergency-contact')}
              />
            </View>
          </NeumorphCard>
        </View>

        {/* ── Preferences section ─────────────────────────────────────────── */}
        <View style={styles.group}>
          <Text style={[styles.groupLabel, { color: textSub }]}>Preferences</Text>
          <NeumorphCard unpadded>
            <View style={styles.groupCard}>

              {/* Dark theme toggle (persisted via ThemeProvider) */}
              <View style={styles.menuRow}>
                <IconChip icon={isDark ? 'moon-outline' : 'sunny-outline'} tint="amber" size={36} />
                <Text style={[styles.menuLabel, { color: textPri }]}>Dark theme</Text>
                <SkeuToggle
                  value={isDark}
                  onValueChange={handleThemeToggle}
                  accessibilityLabel="Toggle dark theme"
                />
              </View>

              <Separator isDark={isDark} />
              <MenuItem
                icon="notifications-outline"
                tint="amber"
                label="Notifications"
                labelColor={textPri}
                hintColor={textSub}
                onPress={() => router.push('/notification-preferences')}
              />
              <Separator isDark={isDark} />
              <MenuItem
                icon="lock-closed-outline"
                tint="blue"
                label="Privacy & security"
                hint="My consents"
                labelColor={textPri}
                hintColor={textSub}
                onPress={() => router.push('/privacy-security')}
              />
              <Separator isDark={isDark} />
              <MenuItem
                icon="phone-portrait-outline"
                tint="violet"
                label="Devices & sessions"
                labelColor={textPri}
                hintColor={textSub}
                onPress={() => router.push('/sessions')}
              />
            </View>
          </NeumorphCard>
        </View>

        {/* ── Account section ─────────────────────────────────────────────── */}
        <View style={styles.group}>
          <Text style={[styles.groupLabel, { color: textSub }]}>Account</Text>
          <NeumorphCard unpadded>
            <View style={styles.groupCard}>
              <MenuItem
                icon="card-outline"
                tint="green"
                label="Payments & refunds"
                labelColor={textPri}
                hintColor={textSub}
                onPress={() => router.push('/payments')}
              />
              <Separator isDark={isDark} />
              <MenuItem
                icon="download-outline"
                tint="blue"
                label="Download my data"
                labelColor={textPri}
                hintColor={textSub}
                onPress={() => router.push('/download-data')}
              />
              <Separator isDark={isDark} />
              <MenuItem
                icon="warning-outline"
                tint="amber"
                label="Delete my account"
                labelColor={colors.criticalRed}
                hintColor={colors.criticalRed}
                onPress={() => router.push('/delete-account')}
                accessibilityLabel="Delete my account"
              />
            </View>
          </NeumorphCard>
        </View>

        {/* ── Sign out ────────────────────────────────────────────────────── */}
        <HapticPressable
          scaleTo={0.97}
          style={[
            styles.signOutBtn,
            {
              backgroundColor: cardBg,
              borderColor: isDark ? 'rgba(255,255,255,0.12)' : colors.borderLight,
            },
          ]}
          onPress={signOut}
          accessibilityLabel="Sign out"
        >
          <Text style={[styles.signOutText, { color: textSub }]}>Sign out</Text>
        </HapticPressable>

      </ScrollView>
    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
    paddingBottom: TAB_DOCK_CLEARANCE,
    gap: spacing[6],
  },

  identityRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[4] },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: `0 4px 8px ${withAlpha(colors.navyDeep, 0.25)}`,
  },
  avatarText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.white,
    fontWeight: '700',
  },
  identityInfo: { flex: 1, gap: spacing[1] },
  userName: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    fontWeight: '600',
  },
  userDetail: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
  },
  planBadge: {
    alignSelf: 'flex-start',
    borderRadius: borderRadius.full,
    paddingHorizontal: spacing[2],
    paddingVertical: 3,
    marginTop: spacing[1],
  },
  planBadgeText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    letterSpacing: 0.3,
  },

  // Grouped settings
  group:    { gap: spacing[3] },
  groupLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    paddingHorizontal: spacing[2],
  },
  groupCard: {
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[2],
  },

  // Menu row
  menuRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing[3],
    gap: spacing[3],
  },
  menuLabel: {
    flex: 1,
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '500',
  },
  menuRight: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  menuHint: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
  },

  separator: {
    height: 1,
    marginLeft: 36 + spacing[3],
  },

  // Sign out button
  signOutBtn: {
    borderRadius: borderRadius.xxl,
    paddingVertical: spacing[4],
    alignItems: 'center',
    borderWidth: 1,
    boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
  },
  signOutText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '500',
  },
});
