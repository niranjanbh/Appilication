import { Ionicons } from '@expo/vector-icons';
import { Tabs } from 'expo-router';
import { Platform, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { borderRadius, fontFamily, fontSize, spacing, withAlpha } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';
import { useBreakpoint } from '../../lib/hooks/useBreakpoint';
import { WebSidebar } from '../../components/web/WebSidebar';
import { GlassTabBackground, HapticTabButton } from '../../components/ui/GlassTabBar';
import { HeaderBell } from '../../components/ui/HeaderBell';
import { HeaderAvatar } from '../../components/ui/HeaderAvatar';

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

interface TabDef {
  name: string;
  title: string;
  headerTitle: string;
  active: IoniconName;
  inactive: IoniconName;
  href?: null;
}

const TABS: TabDef[] = [
  { name: 'home',          title: 'Home',       headerTitle: 'Your kyros journey',      active: 'home',                inactive: 'home-outline' },
  { name: 'consultations', title: 'Care',       headerTitle: 'Care',           active: 'heart',               inactive: 'heart-outline' },
  { name: 'reports',       title: 'Records',    headerTitle: 'Records',        active: 'folder-open',         inactive: 'folder-open-outline' },
  { name: 'reminders',     title: 'Reminders',  headerTitle: 'Reminders',      active: 'alarm',               inactive: 'alarm-outline' },
  { name: 'lifestyle',     title: 'Lifestyle',  headerTitle: 'Lifestyle',      active: 'fitness',             inactive: 'fitness-outline' },
  { name: 'notifications', title: 'Inbox',      headerTitle: 'Notifications',  active: 'notifications',       inactive: 'notifications-outline', href: null },
  { name: 'profile',       title: 'Profile',    headerTitle: 'Profile',        active: 'person',              inactive: 'person-outline',        href: null },
];

export default function TabsLayout() {
  const { isDesktop } = useBreakpoint();
  const insets = useSafeAreaInsets();
  const t = useTheme();

  const activeTint = t.primary;
  const mutedTint  = t.textSub;

  // Floating frosted dock. iOS/web get live blur via GlassTabBackground; Android
  // carries the look with a translucent solid surface (live blur is too costly
  // on low-end devices).
  const tabBarStyle = isDesktop
    ? { display: 'none' as const }
    : {
        position: 'absolute' as const,
        left: spacing[4],
        right: spacing[4],
        bottom: Math.max(insets.bottom, spacing[2]) + spacing[2],
        height: 64,
        paddingBottom: 8,
        paddingTop: 6,
        borderRadius: borderRadius.xxl + 8,
        borderTopWidth: 0,
        borderWidth: 1,
        borderColor: t.glass.border,
        backgroundColor: Platform.OS === 'android' ? t.glass.surfaceStrong : t.glass.dock,
        overflow: 'hidden' as const,
        boxShadow: `0 12px 24px ${withAlpha(t.shadow, t.isDark ? 0.45 : 0.14)}`,
      };

  const tabs = (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: activeTint,
        tabBarInactiveTintColor: mutedTint,
        tabBarStyle,
        tabBarBackground: () => <GlassTabBackground />,
        tabBarButton: (props) => <HapticTabButton {...props} />,
        tabBarLabelStyle: {
          fontFamily: fontFamily.body,
          fontSize: fontSize.xs,
          fontWeight: '500' as const,
          marginTop: 2,
        },
        headerStyle: { backgroundColor: t.background },
        headerTitleStyle: {
          fontFamily: fontFamily.body,
          fontSize: fontSize.bodyLg,
          color: t.text,
          fontWeight: '600' as const,
        },
        headerRight: () => (
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4, marginRight: spacing[3] }}>
            <HeaderBell />
            <HeaderAvatar />
          </View>
        ),
        headerShown: !isDesktop,
        headerShadowVisible: false,
        lazy: false,
        freezeOnBlur: true,
      }}
      detachInactiveScreens={false}
    >
      {TABS.map(tab => (
        <Tabs.Screen
          key={tab.name}
          name={tab.name}
          options={{
            title: tab.title,
            headerTitle: tab.headerTitle,
            href: tab.href === null ? null : undefined,
            tabBarIcon: ({ color, focused }) => (
              <Ionicons name={focused ? tab.active : tab.inactive} size={22} color={color} />
            ),
          }}
        />
      ))}
    </Tabs>
  );

  if (isDesktop) {
    return (
      <View style={{ flex: 1, flexDirection: 'row' }}>
        <WebSidebar />
        <View style={{ flex: 1 }}>{tabs}</View>
      </View>
    );
  }

  return tabs;
}
