/**
 * Desktop web sidebar — 240px fixed left rail.
 *
 * Replaces the bottom tab bar on screens ≥ 1024px.
 * Forest 8% right border, Ivory bg, Cormorant wordmark at top,
 * user name + sign-out at bottom.
 *
 * Platform: web only — never rendered on native.
 */

import { Pressable, StyleSheet, Text, View } from 'react-native';
import { usePathname, useRouter } from 'expo-router';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';
import { useAuth } from '../../lib/auth/context';

interface NavItem {
  label: string;
  icon: string;
  href: string;
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Home',      icon: '⌂', href: '/(tabs)/home' },
  { label: 'Care',      icon: '♡', href: '/(tabs)/consultations' },
  { label: 'Records',   icon: '⧫', href: '/(tabs)/reports' },
  { label: 'Reminders', icon: '⏰', href: '/(tabs)/reminders' },
  { label: 'Lifestyle', icon: '◎', href: '/(tabs)/lifestyle' },
];

const SECONDARY_ITEMS: NavItem[] = [
  { label: 'Notifications', icon: '🔔', href: '/(tabs)/notifications' },
  { label: 'Profile',       icon: '👤', href: '/(tabs)/profile' },
];

export function WebSidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const { state, signOut } = useAuth();
  const userName = state.status === 'authenticated' ? state.user.name.split(' ')[0] : '';

  return (
    <View style={styles.sidebar}>
      {/* Wordmark */}
      <View style={styles.wordmarkRow}>
        <Text style={styles.wordmark}>Baseline</Text>
      </View>

      {/* Primary nav */}
      <View style={styles.navItems}>
        {NAV_ITEMS.map((item) => {
          const isActive = pathname.includes(item.href.replace('/(tabs)/', ''));
          return (
            <Pressable
              key={item.href}
              style={[styles.navItem, isActive && styles.navItemActive]}
              onPress={() => router.push(item.href as Parameters<typeof router.push>[0])}
              accessibilityLabel={item.label}
              accessibilityRole="menuitem"
            >
              <Text style={styles.navIcon}>{item.icon}</Text>
              <Text style={[styles.navLabel, isActive && styles.navLabelActive]}>
                {item.label}
              </Text>
            </Pressable>
          );
        })}

        <View style={styles.divider} />

        {SECONDARY_ITEMS.map((item) => {
          const isActive = pathname.includes(item.href.replace('/(tabs)/', ''));
          return (
            <Pressable
              key={item.href}
              style={[styles.navItem, isActive && styles.navItemActive]}
              onPress={() => router.push(item.href as Parameters<typeof router.push>[0])}
              accessibilityLabel={item.label}
              accessibilityRole="menuitem"
            >
              <Text style={styles.navIcon}>{item.icon}</Text>
              <Text style={[styles.navLabel, isActive && styles.navLabelActive]}>
                {item.label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {/* User menu at bottom */}
      <View style={styles.userRow}>
        <Text style={styles.userName} numberOfLines={1}>{userName}</Text>
        <Pressable onPress={signOut} accessibilityLabel="Sign out">
          <Text style={styles.signOut}>Sign out</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  sidebar: {
    width: 240,
    height: '100%' as unknown as number,
    backgroundColor: colors.ivory,
    borderRightWidth: 1,
    borderRightColor: colors.forest + '14', // Forest at 8% opacity
    flexDirection: 'column',
    paddingTop: spacing[6],
    paddingBottom: spacing[4],
  },
  wordmarkRow: {
    paddingHorizontal: spacing[4],
    marginBottom: spacing[6],
  },
  wordmark: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h3,
    color: colors.forest,
    letterSpacing: 1,
  },
  navItems: {
    flex: 1,
  },
  divider: {
    height: 1,
    backgroundColor: colors.forest + '14',
    marginHorizontal: spacing[4],
    marginVertical: spacing[2],
  },
  navItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    paddingVertical: spacing[3],
    paddingHorizontal: spacing[4],
    borderRadius: borderRadius.md,
    marginHorizontal: spacing[2],
    marginBottom: spacing[1],
  },
  navItemActive: {
    backgroundColor: colors.forest + '14', // Forest at 8%
    borderLeftWidth: 3,
    borderLeftColor: colors.forest,
    borderRadius: 0,
    borderTopRightRadius: borderRadius.md,
    borderBottomRightRadius: borderRadius.md,
  },
  navIcon: {
    fontSize: fontSize.bodyLg,
    width: 24,
    textAlign: 'center',
  },
  navLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
  },
  navLabelActive: {
    color: colors.forest,
    fontWeight: '600',
  },
  userRow: {
    borderTopWidth: 1,
    borderTopColor: colors.stone + '20',
    paddingTop: spacing[3],
    paddingHorizontal: spacing[4],
  },
  userName: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.ink,
    marginBottom: spacing[1],
  },
  signOut: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.forest,
  },
});
