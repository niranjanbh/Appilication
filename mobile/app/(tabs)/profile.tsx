import { Appearance, Pressable, ScrollView, StyleSheet, Switch, Text, useColorScheme, View } from 'react-native';
import { useRouter } from 'expo-router';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { useAuth } from '../../lib/auth/context';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

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
  icon: string;
  iconBg: string;
  label: string;
  hint?: string;
  labelColor: string;
  hintColor: string;
  onPress: () => void;
  accessibilityLabel?: string;
}

function MenuItem({ icon, iconBg, label, hint, labelColor, hintColor, onPress, accessibilityLabel }: MenuItemProps) {
  const scale = useSharedValue(1);
  const anim  = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));

  return (
    <Animated.View style={anim}>
      <Pressable
        style={styles.menuRow}
        onPress={onPress}
        onPressIn={() => { scale.value = withSpring(0.98, { mass: 0.3, stiffness: 500 }); }}
        onPressOut={() => { scale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
        accessibilityLabel={accessibilityLabel ?? label}
      >
        <View style={[styles.menuIconWrap, { backgroundColor: iconBg }]}>
          <Text style={styles.menuIcon}>{icon}</Text>
        </View>
        <Text style={[styles.menuLabel, { color: labelColor }]}>{label}</Text>
        <View style={styles.menuRight}>
          {hint ? <Text style={[styles.menuHint, { color: hintColor }]}>{hint}</Text> : null}
          <Text style={[styles.chevron, { color: hintColor }]}>›</Text>
        </View>
      </Pressable>
    </Animated.View>
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
  const isDark = useColorScheme() === 'dark';

  const user     = state.status === 'authenticated' ? state.user : null;
  const initials = user ? getInitials(user.name) : 'K';

  function handleThemeToggle(val: boolean) {
    Appearance.setColorScheme(val ? 'dark' : 'light');
  }

  const signScale = useSharedValue(1);
  const signAnim  = useAnimatedStyle(() => ({ transform: [{ scale: signScale.value }] }));

  const bg        = isDark ? colors.midnight     : colors.skyMist;
  const textPri   = isDark ? colors.white        : colors.navyDeep;
  const textSub   = isDark ? colors.slateText    : colors.coolGray;
  const cardBg    = isDark ? colors.nightSurface : colors.white;
  const cardBdr   = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,31,63,0.06)';
  const iconBlue  = isDark ? '#0F1E38' : '#EBF3FF';
  const iconAmb   = isDark ? '#2A1A05' : '#FFF4E5';
  const iconGreen = isDark ? '#061E12' : '#EDFAF3';
  const iconPurp  = isDark ? '#150F2B' : '#F3EFFF';
  const iconRed   = isDark ? '#2A0505' : '#FFF0F0';

  return (
    <ScrollView
      style={[styles.flex, { backgroundColor: bg }]}
      contentContainerStyle={styles.container}
      showsVerticalScrollIndicator={false}
    >

      {/* ── Identity card ─────────────────────────────────────────────────── */}
      {user && (
        <View style={[styles.identityCard, { backgroundColor: cardBg, borderColor: cardBdr }]}>
          <View style={styles.identityRow}>
            <View style={[styles.avatar, { backgroundColor: colors.navyDeep }]}>
              <Text style={styles.avatarText}>{initials}</Text>
            </View>
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
        </View>
      )}

      {/* ── Care section ──────────────────────────────────────────────────── */}
      <View style={styles.group}>
        <Text style={[styles.groupLabel, { color: textSub }]}>Care</Text>
        <View style={[styles.groupCard, { backgroundColor: cardBg, borderColor: cardBdr }]}>
          <MenuItem
            icon="🏥"
            iconBg={iconBlue}
            label="Health Records (ABHA)"
            hint="Linked"
            labelColor={textPri}
            hintColor={textSub}
            onPress={() => router.push('/abha-settings')}
          />
          <Separator isDark={isDark} />
          <MenuItem
            icon="📊"
            iconBg={iconPurp}
            label="Insights & trends"
            labelColor={textPri}
            hintColor={textSub}
            onPress={() => {}}
          />
          <Separator isDark={isDark} />
          <MenuItem
            icon="📅"
            iconBg={iconGreen}
            label="Appointments"
            labelColor={textPri}
            hintColor={textSub}
            onPress={() => router.push('/(tabs)/consultations' as never)}
          />
        </View>
      </View>

      {/* ── Preferences section ───────────────────────────────────────────── */}
      <View style={styles.group}>
        <Text style={[styles.groupLabel, { color: textSub }]}>Preferences</Text>
        <View style={[styles.groupCard, { backgroundColor: cardBg, borderColor: cardBdr }]}>

          {/* Dark theme toggle (pure UI — Appearance API) */}
          <View style={styles.menuRow}>
            <View style={[styles.menuIconWrap, { backgroundColor: iconAmb }]}>
              <Text style={styles.menuIcon}>☀️</Text>
            </View>
            <Text style={[styles.menuLabel, { color: textPri }]}>Dark theme</Text>
            <Switch
              value={isDark}
              onValueChange={handleThemeToggle}
              trackColor={{
                false: colors.borderLight,
                true:  colors.electricBlue + '80',
              }}
              thumbColor={isDark ? colors.electricBlue : colors.white}
              ios_backgroundColor={colors.borderLight}
              accessibilityLabel="Toggle dark theme"
            />
          </View>

          <Separator isDark={isDark} />
          <MenuItem
            icon="🔔"
            iconBg={iconAmb}
            label="Notifications"
            labelColor={textPri}
            hintColor={textSub}
            onPress={() => router.push('/notification-preferences')}
          />
          <Separator isDark={isDark} />
          <MenuItem
            icon="🔒"
            iconBg={iconBlue}
            label="Privacy & security"
            hint="My consents"
            labelColor={textPri}
            hintColor={textSub}
            onPress={() => {}}
          />
        </View>
      </View>

      {/* ── Account section ───────────────────────────────────────────────── */}
      <View style={styles.group}>
        <Text style={[styles.groupLabel, { color: textSub }]}>Account</Text>
        <View style={[styles.groupCard, { backgroundColor: cardBg, borderColor: cardBdr }]}>
          <MenuItem
            icon="📥"
            iconBg={iconBlue}
            label="Download my data"
            labelColor={textPri}
            hintColor={textSub}
            onPress={() => {}}
          />
          <Separator isDark={isDark} />
          <MenuItem
            icon="⚠️"
            iconBg={iconRed}
            label="Delete my account"
            labelColor={colors.criticalRed}
            hintColor={colors.criticalRed}
            onPress={() => {}}
            accessibilityLabel="Delete my account"
          />
        </View>
      </View>

      {/* ── Sign out ──────────────────────────────────────────────────────── */}
      <Animated.View style={signAnim}>
        <Pressable
          style={[
            styles.signOutBtn,
            {
              backgroundColor: cardBg,
              borderColor: isDark ? 'rgba(255,255,255,0.12)' : colors.borderLight,
            },
          ]}
          onPress={signOut}
          onPressIn={() => { signScale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
          onPressOut={() => { signScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
          accessibilityLabel="Sign out"
        >
          <Text style={[styles.signOutText, { color: textSub }]}>Sign out</Text>
        </Pressable>
      </Animated.View>

    </ScrollView>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
    paddingBottom: spacing[12],
    gap: spacing[6],
  },

  // Identity card (clay — elevated, soft shadow)
  identityCard: {
    borderRadius: borderRadius.xxl,
    padding: spacing[5],
    borderWidth: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.07,
    shadowRadius: 16,
    elevation: 3,
  },
  identityRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[4] },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: colors.navyDeep,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    elevation: 4,
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

  // Grouped settings (clay cards)
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
    borderRadius: borderRadius.xxl,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[2],
    borderWidth: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 12,
    elevation: 2,
  },

  // Menu row
  menuRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing[3],
    gap: spacing[3],
  },
  menuIconWrap: {
    width: 36,
    height: 36,
    borderRadius: borderRadius.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  menuIcon:  { fontSize: 18 },
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
  chevron: {
    fontFamily: fontFamily.body,
    fontSize: 20,
    lineHeight: 22,
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
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.04,
    shadowRadius: 8,
    elevation: 1,
  },
  signOutText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '500',
  },
});
