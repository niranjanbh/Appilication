import { StyleSheet, Text, View } from 'react-native';
import { borderRadius, colors, fontFamily, fontSize, fontWeight, shadow, spacing, withAlpha } from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';

interface ChatBubbleProps {
  message: string;
  timestamp: string;
  isOutbound?: boolean;
  senderTag?: string;
  accessibilityLabel?: string;
}

export function ChatBubble({
  message,
  timestamp,
  isOutbound = false,
  senderTag,
  accessibilityLabel,
}: ChatBubbleProps) {
  const t = useTheme();

  const bubbleBg = isOutbound
    ? (t.isDark ? colors.forestSurfaceRaised : colors.forest)
    : (t.isDark ? colors.forestSurface : colors.white);

  const textColor = isOutbound
    ? (t.isDark ? colors.ivoryText : colors.ivory)
    : t.text;

  const timeColor = isOutbound
    ? (t.isDark ? colors.stoneDim : withAlpha(colors.ivory, 0.70))
    : t.textSub;

  const bubbleShadow = isOutbound
    ? (t.isDark ? shadow.darkXs : shadow.sm)
    : (t.isDark ? shadow.darkXs : shadow.xs);

  return (
    <View
      style={[styles.row, isOutbound && styles.rowOutbound]}
      accessibilityLabel={accessibilityLabel ?? `${isOutbound ? 'You' : senderTag ?? 'Coordinator'}: ${message}`}
    >
      <View style={[styles.bubble, { backgroundColor: bubbleBg, boxShadow: bubbleShadow }]}>
        {senderTag && !isOutbound && (
          <View style={styles.tagRow}>
            <Text style={[styles.tag, { color: t.isDark ? colors.jadeGlow : colors.jade }]}>
              {senderTag}
            </Text>
          </View>
        )}
        <Text style={[styles.message, { color: textColor }]}>{message}</Text>
        <Text style={[styles.time, { color: timeColor }]}>{timestamp}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    justifyContent: 'flex-start',
    paddingHorizontal: spacing[4],
    marginBottom: spacing[2],
  },
  rowOutbound: { justifyContent: 'flex-end' },
  bubble: {
    maxWidth: '78%',
    borderRadius: borderRadius.xl,
    padding: spacing[3],
    gap: spacing[1],
  },
  tagRow: { marginBottom: 2 },
  tag: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: fontWeight.semibold,
  },
  message: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
  },
  time: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    alignSelf: 'flex-end',
  },
});
