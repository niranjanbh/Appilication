import { Ionicons } from '@expo/vector-icons';
import { Tabs } from 'expo-router';
import { useColorScheme, View } from 'react-native';
import { colors, fontFamily, fontSize } from '../../lib/design-tokens';
import { useBreakpoint } from '../../lib/hooks/useBreakpoint';
import { WebSidebar } from '../../components/web/WebSidebar';

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

interface TabDef {
  name: string;
  title: string;
  headerTitle: string;
  active: IoniconName;
  inactive: IoniconName;
}

const TABS: TabDef[] = [
  { name: 'home',          title: 'Home',       headerTitle: 'Your plan',      active: 'home',                inactive: 'home-outline' },
  { name: 'consultations', title: 'Plan',        headerTitle: 'Consultations',  active: 'calendar',            inactive: 'calendar-outline' },
  { name: 'reports',       title: 'Reports',     headerTitle: 'Reports',        active: 'document-text',       inactive: 'document-text-outline' },
  { name: 'reminders',     title: 'Reminders',   headerTitle: 'Reminders',      active: 'alarm',               inactive: 'alarm-outline' },
  { name: 'notifications', title: 'Inbox',       headerTitle: 'Notifications',  active: 'notifications',       inactive: 'notifications-outline' },
  { name: 'profile',       title: 'Profile',     headerTitle: 'Profile',        active: 'person',              inactive: 'person-outline' },
];

export default function TabsLayout() {
  const { isDesktop } = useBreakpoint();
  const colorScheme = useColorScheme();
  const isDark = colorScheme === 'dark';

  const navBg      = isDark ? colors.nightSurface : colors.white;
  const headerBg   = isDark ? colors.midnight     : colors.skyMist;
  const activeTint = isDark ? colors.electricBlue : colors.navyDeep;
  const mutedTint  = isDark ? colors.slateText    : colors.coolGray;
  const headerText = isDark ? colors.white        : colors.navyDeep;

  const tabBarStyle = isDesktop
    ? { display: 'none' as const }
    : {
        backgroundColor: navBg,
        borderTopWidth: 0,
        height: 64,
        paddingBottom: 8,
        paddingTop: 6,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: -4 },
        shadowOpacity: isDark ? 0.28 : 0.07,
        shadowRadius: 16,
        elevation: 16,
      };

  const tabs = (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: activeTint,
        tabBarInactiveTintColor: mutedTint,
        tabBarStyle,
        tabBarLabelStyle: {
          fontFamily: fontFamily.body,
          fontSize: fontSize.xs,
          fontWeight: '500' as const,
          marginTop: 2,
        },
        headerStyle: { backgroundColor: headerBg },
        headerTitleStyle: {
          fontFamily: fontFamily.body,
          fontSize: fontSize.bodyLg,
          color: headerText,
          fontWeight: '600' as const,
        },
        headerShown: !isDesktop,
        headerShadowVisible: false,
      }}
    >
      {TABS.map(tab => (
        <Tabs.Screen
          key={tab.name}
          name={tab.name}
          options={{
            title: tab.title,
            headerTitle: tab.headerTitle,
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
