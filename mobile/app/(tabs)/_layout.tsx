import { Tabs } from 'expo-router';
import { Text, View, type ColorValue } from 'react-native';
import { colors, fontFamily, fontSize } from '../../lib/design-tokens';
import { useBreakpoint } from '../../lib/hooks/useBreakpoint';
import { WebSidebar } from '../../components/web/WebSidebar';

export default function TabsLayout() {
  const { isDesktop } = useBreakpoint();

  // On desktop web: sidebar handles navigation; hide the native tab bar.
  const tabBarStyle = isDesktop
    ? { display: 'none' as const }
    : { backgroundColor: colors.white, borderTopColor: '#E5E0D8', borderTopWidth: 1 };

  const tabs = (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: colors.forest,
        tabBarInactiveTintColor: colors.stone,
        tabBarStyle,
        tabBarLabelStyle: {
          fontFamily: fontFamily.body,
          fontSize: fontSize.caption,
        },
        headerStyle: { backgroundColor: colors.ivory },
        headerTitleStyle: {
          fontFamily: fontFamily.body,
          fontSize: fontSize.bodyLg,
          color: colors.forest,
          fontWeight: '600',
        },
        // On desktop the sidebar provides chrome — suppress per-screen headers.
        headerShown: !isDesktop,
        headerShadowVisible: false,
      }}
    >
      <Tabs.Screen
        name="home"
        options={{
          title: 'Home',
          tabBarIcon: ({ color }) => <TabIcon label="⌂" color={color} />,
          headerTitle: 'Your plan',
        }}
      />
      <Tabs.Screen
        name="consultations"
        options={{
          title: 'Consultations',
          tabBarIcon: ({ color }) => <TabIcon label="📅" color={color} />,
          headerTitle: 'Consultations',
        }}
      />
      <Tabs.Screen
        name="reports"
        options={{
          title: 'Reports',
          tabBarIcon: ({ color }) => <TabIcon label="🔬" color={color} />,
          headerTitle: 'Reports',
        }}
      />
      <Tabs.Screen
        name="reminders"
        options={{
          title: 'Reminders',
          tabBarIcon: ({ color }) => <TabIcon label="⏰" color={color} />,
          headerTitle: 'Reminders',
        }}
      />
      <Tabs.Screen
        name="notifications"
        options={{
          title: 'Inbox',
          tabBarIcon: ({ color }) => <TabIcon label="🔔" color={color} />,
          headerTitle: 'Notifications',
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: 'Profile',
          tabBarIcon: ({ color }) => <TabIcon label="👤" color={color} />,
          headerTitle: 'Profile',
        }}
      />
    </Tabs>
  );

  if (isDesktop) {
    return (
      <View style={{ flex: 1, flexDirection: 'row' }}>
        <WebSidebar />
        <View style={{ flex: 1 }}>
          {tabs}
        </View>
      </View>
    );
  }

  return tabs;
}

function TabIcon({ label, color }: { label: string; color: ColorValue }) {
  return <Text style={{ fontSize: 20, color }}>{label}</Text>;
}
