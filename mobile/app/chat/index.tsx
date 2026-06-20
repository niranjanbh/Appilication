import { useState } from 'react';
import { FlatList, StyleSheet, TextInput, View, Pressable } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { borderRadius, colors, fontFamily, fontSize, spacing, withAlpha } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';
import { AmbientBackground } from '../../components/ui/AmbientBackground';
import { EmptyState } from '../../components/ui/EmptyState';
import { EmergencyBanner } from '../../components/ui/EmergencyBanner';
import { ChatBubble } from '../../components/ui/ChatBubble';

interface Message {
  id: string;
  text: string;
  timestamp: string;
  isOutbound: boolean;
  senderTag?: string;
}

export default function CoordinatorChatScreen() {
  const t = useTheme();
  const [messages] = useState<Message[]>([]);
  const [draft, setDraft] = useState('');

  const isEmpty = messages.length === 0;

  return (
    <View style={[styles.container, { backgroundColor: t.background }]}>
      <AmbientBackground />

      <EmergencyBanner
        message="For medical emergencies, call 112"
        actionLabel="Call"
        onPress={() => {}}
      />

      {isEmpty ? (
        <View style={styles.emptyWrap}>
          <EmptyState
            title="No messages yet"
            body="Your care coordinator will reach out here once your plan is active."
            icon="chatbubbles-outline"
            tint="sage"
          />
        </View>
      ) : (
        <FlatList
          data={messages}
          keyExtractor={(m) => m.id}
          renderItem={({ item }) => (
            <ChatBubble
              message={item.text}
              timestamp={item.timestamp}
              isOutbound={item.isOutbound}
              senderTag={item.senderTag}
            />
          )}
          contentContainerStyle={styles.messageList}
          inverted
        />
      )}

      <View style={[styles.composer, { backgroundColor: t.surface, borderTopColor: t.border }]}>
        <TextInput
          style={[styles.input, {
            backgroundColor: t.isDark ? colors.forestSurfaceRaised : colors.white,
            borderColor: t.border,
            color: t.text,
          }]}
          placeholder="Type a message..."
          placeholderTextColor={t.textSub}
          value={draft}
          onChangeText={setDraft}
          multiline
        />
        <Pressable
          style={[styles.sendBtn, { backgroundColor: draft.trim() ? colors.forest : withAlpha(colors.forest, 0.3) }]}
          disabled={!draft.trim()}
          accessibilityLabel="Send message"
        >
          <Ionicons name="send" size={18} color={colors.ivory} />
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  emptyWrap: {
    flex: 1,
    justifyContent: 'center',
    padding: spacing[6],
  },
  messageList: {
    paddingVertical: spacing[4],
  },
  composer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: spacing[2],
    padding: spacing[3],
    borderTopWidth: 1,
  },
  input: {
    flex: 1,
    minHeight: 40,
    maxHeight: 100,
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
  },
  sendBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
