import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { PullQuote } from '../components/PullQuote';
import { Stat } from '../components/Stat';
import { Tag } from '../components/Tag';
import { colors, fontSize, spacing } from '../lib/design-tokens';

function SectionTitle({ children }: { children: string }) {
  return (
    <Text style={styles.sectionTitle}>{children.toUpperCase()}</Text>
  );
}

function Row({ children }: { children: React.ReactNode }) {
  return <View style={styles.row}>{children}</View>;
}

export default function DesignShowcase() {
  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Kyros Design System</Text>
        <Text style={styles.headerSub}>Mobile — Primitive Showcase</Text>
      </View>

      {/* Button */}
      <SectionTitle>Button</SectionTitle>
      <Row>
        <Button variant="forest" label="Book consultation" />
      </Row>
      <Row>
        <Button variant="saffron" label="Join now" />
      </Row>
      <Row>
        <Button variant="outline" label="View details" />
      </Row>
      <Row>
        <Button variant="ghost" label="Dismiss" />
      </Row>

      {/* Card */}
      <SectionTitle>Card</SectionTitle>
      <Card variant="white" style={styles.cardDemo}>
        <Text style={styles.cardLabel}>White on Ivory</Text>
        <Text style={styles.cardText}>
          Clinical card background. Used for lab rows, prescription detail, consultation cards.
        </Text>
      </Card>
      <View style={styles.peachMistBg}>
        <Card variant="ivory" style={styles.cardDemo}>
          <Text style={styles.cardLabel}>Ivory on Peach Mist</Text>
          <Text style={styles.cardText}>
            Warm card. Used in welcome strips and empty states.
          </Text>
        </Card>
      </View>

      {/* PullQuote */}
      <SectionTitle>PullQuote</SectionTitle>
      <View style={styles.section}>
        <PullQuote accent="terracotta">
          "She thought she was just tired. For three years."
        </PullQuote>
      </View>
      <View style={styles.section}>
        <PullQuote accent="saffron">
          "The first honest conversation about your weight should be with someone who measures."
        </PullQuote>
      </View>

      {/* Stat */}
      <SectionTitle>Stat</SectionTitle>
      <Row>
        <Card variant="white" style={styles.statCard}>
          <Stat numeral="94%" caption="reduction in symptoms" color="forest" />
        </Card>
        <Card variant="white" style={styles.statCard}>
          <Stat numeral="2,400+" caption="consultations" color="saffron" />
        </Card>
      </Row>

      {/* Tag */}
      <SectionTitle>Tag</SectionTitle>
      <Row>
        <Tag variant="sage" label="In range" />
        <Tag variant="saffron" label="Slightly off" />
        <Tag variant="terracotta" label="Out of range" />
        <Tag variant="forest" label="Thyroid" />
      </Row>

      {/* Typography */}
      <SectionTitle>Typography</SectionTitle>
      <View style={styles.section}>
        <Text style={styles.typoH1}>H1 — Cormorant 42px</Text>
        <Text style={styles.typoH2}>H2 — Cormorant 28px</Text>
        <Text style={styles.typoH3}>H3 — Cormorant 22px</Text>
        <Text style={styles.typoItalic}>"Pull-quote — Cormorant italic 22px"</Text>
        <Text style={styles.typoBody}>Body — DM Sans 14px Ink. Line height 1.6 for clinical readability.</Text>
        <Text style={styles.typoCaption}>Caption — DM Sans 12px Stone. Metadata, timestamps.</Text>
        <Text style={styles.typoHindi}>हिन्दी — Tiro Devanagari Hindi</Text>
      </View>

      {/* Color Palette */}
      <SectionTitle>Color Palette (11 tokens)</SectionTitle>
      <View style={styles.paletteGrid}>
        {(Object.entries(colors) as [string, string][]).map(([name, hex]) => (
          <View key={name} style={styles.swatchContainer}>
            <View style={[styles.swatch, { backgroundColor: hex, borderColor: colors.stone + '22' }]} />
            <Text style={styles.swatchLabel}>{name}</Text>
          </View>
        ))}
      </View>

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.ivory,
  },
  content: {
    paddingBottom: spacing[12],
  },
  header: {
    backgroundColor: colors.forest,
    paddingHorizontal: spacing[6],
    paddingVertical: spacing[8],
    marginBottom: spacing[6],
  },
  headerTitle: {
    fontFamily: 'CormorantGaramond-Medium',
    fontSize: fontSize.h2,
    color: colors.ivory,
  },
  headerSub: {
    fontFamily: 'DMSans-Regular',
    fontSize: fontSize.body,
    color: colors.ivory,
    opacity: 0.7,
    marginTop: spacing[1],
  },
  sectionTitle: {
    fontFamily: 'DMSans-SemiBold',
    fontSize: fontSize.caption,
    color: colors.stone,
    letterSpacing: 1.5,
    marginHorizontal: spacing[6],
    marginTop: spacing[8],
    marginBottom: spacing[3],
    paddingBottom: spacing[2],
    borderBottomWidth: 1,
    borderBottomColor: colors.sage + '4D',
  },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[3],
    marginHorizontal: spacing[6],
    marginBottom: spacing[3],
  },
  section: {
    marginHorizontal: spacing[6],
    marginBottom: spacing[4],
  },
  cardDemo: {
    marginHorizontal: spacing[6],
    marginBottom: spacing[3],
  },
  peachMistBg: {
    backgroundColor: colors.peachMist,
    paddingVertical: spacing[3],
  },
  cardLabel: {
    fontFamily: 'DMSans-Regular',
    fontSize: fontSize.caption,
    color: colors.stone,
    marginBottom: spacing[2],
  },
  cardText: {
    fontFamily: 'DMSans-Regular',
    fontSize: fontSize.body,
    color: colors.ink,
    lineHeight: fontSize.body * 1.6,
  },
  statCard: {
    flex: 1,
    minWidth: 120,
  },
  typoH1: {
    fontFamily: 'CormorantGaramond-Medium',
    fontSize: fontSize.h1,
    color: colors.forest,
    lineHeight: fontSize.h1 * 1.15,
    marginBottom: spacing[3],
  },
  typoH2: {
    fontFamily: 'CormorantGaramond-Medium',
    fontSize: fontSize.h2,
    color: colors.forest,
    lineHeight: fontSize.h2 * 1.25,
    marginBottom: spacing[3],
  },
  typoH3: {
    fontFamily: 'CormorantGaramond-Medium',
    fontSize: fontSize.h3,
    color: colors.forest,
    lineHeight: fontSize.h3 * 1.3,
    marginBottom: spacing[3],
  },
  typoItalic: {
    fontFamily: 'CormorantGaramond-Italic',
    fontSize: fontSize.h3,
    color: colors.forest,
    lineHeight: fontSize.h3 * 1.3,
    marginBottom: spacing[4],
  },
  typoBody: {
    fontFamily: 'DMSans-Regular',
    fontSize: fontSize.body,
    color: colors.ink,
    lineHeight: fontSize.body * 1.6,
    marginBottom: spacing[3],
  },
  typoCaption: {
    fontFamily: 'DMSans-Regular',
    fontSize: fontSize.caption,
    color: colors.stone,
    lineHeight: fontSize.caption * 1.5,
    marginBottom: spacing[4],
  },
  typoHindi: {
    fontFamily: 'TiroDevanagariHindi-Regular',
    fontSize: fontSize.h3,
    color: colors.forest,
    lineHeight: fontSize.h3 * 1.4,
  },
  paletteGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[4],
    marginHorizontal: spacing[6],
    marginBottom: spacing[6],
  },
  swatchContainer: {
    alignItems: 'center',
    gap: spacing[2],
  },
  swatch: {
    width: 56,
    height: 56,
    borderRadius: 8,
    borderWidth: 1,
  },
  swatchLabel: {
    fontFamily: 'DMSans-Regular',
    fontSize: fontSize.caption,
    color: colors.stone,
  },
});
