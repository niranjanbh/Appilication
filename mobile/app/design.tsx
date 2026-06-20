import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useThemePreference } from '../lib/theme-context';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { PullQuote } from '../components/PullQuote';
import { Stat } from '../components/Stat';
import { Tag } from '../components/Tag';
import { borderRadius, colors, fontSize, spacing } from '../lib/design-tokens';

function SectionTitle({ children, textSub }: { children: string; textSub: string }) {
  return (
    <Text style={[styles.sectionTitle, { color: textSub }]}>{String(children).toUpperCase()}</Text>
  );
}

function Row({ children }: { children: React.ReactNode }) {
  return <View style={styles.row}>{children}</View>;
}

export default function DesignShowcase() {
  const isDark  = useThemePreference().colorScheme === 'dark';
  const bg      = isDark ? colors.forestInk      : colors.ivory;
  const textPri = isDark ? colors.ivoryText     : colors.ink;
  const textSub = isDark ? colors.stoneDim      : colors.stone;
  const cardBg  = isDark ? colors.forestSurface : colors.white;
  const cardBdr = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(15,61,46,0.06)';

  return (
    <ScrollView style={[styles.screen, { backgroundColor: bg }]} contentContainerStyle={styles.content}>

      {/* Header — forest letterhead */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Kyros Design System</Text>
        <Text style={styles.headerSub}>Warm Ivory · Light + Dark · Mobile</Text>
      </View>

      {/* Button */}
      <SectionTitle textSub={textSub}>Button</SectionTitle>
      <Row><Button variant="forest"  label="Book consultation" /></Row>
      <Row><Button variant="saffron" label="Join now" /></Row>
      <Row><Button variant="outline" label="View details" /></Row>
      <Row><Button variant="ghost"   label="Dismiss" /></Row>
      <Row><Button variant="forest"  label="Loading…" isLoading /></Row>

      {/* Card */}
      <SectionTitle textSub={textSub}>Card</SectionTitle>
      <View style={[styles.cardDemo, { backgroundColor: cardBg, borderColor: cardBdr, borderWidth: 1, borderRadius: borderRadius.xxl, padding: spacing[5] }]}>
        <Text style={[styles.cardLabel, { color: textSub }]}>Clay card — themed</Text>
        <Text style={[styles.cardText, { color: textPri }]}>Soft shadow, rounded 24 px, adapts to light and dark.</Text>
      </View>
      <Card variant="dark" style={styles.cardDemo}>
        <Text style={[styles.cardLabel, { color: 'rgba(255,255,255,0.60)' }]}>Dark card — forest hero</Text>
        <Text style={[styles.cardText, { color: colors.ivoryText }]}>Forest background with jade glass border. Used for CTAs.</Text>
      </Card>

      {/* PullQuote */}
      <SectionTitle textSub={textSub}>PullQuote</SectionTitle>
      <View style={styles.section}>
        <PullQuote accent="terracotta">"She thought she was just tired. For three years."</PullQuote>
      </View>
      <View style={styles.section}>
        <PullQuote accent="saffron">"The first honest conversation about your weight should be with someone who measures."</PullQuote>
      </View>

      {/* Stat */}
      <SectionTitle textSub={textSub}>Stat</SectionTitle>
      <Row>
        <View style={[styles.statCard, { backgroundColor: cardBg, borderColor: cardBdr, borderWidth: 1, borderRadius: borderRadius.xl }]}>
          <Stat numeral="94%" caption="reduction in symptoms" color="forest" />
        </View>
        <View style={[styles.statCard, { backgroundColor: cardBg, borderColor: cardBdr, borderWidth: 1, borderRadius: borderRadius.xl }]}>
          <Stat numeral="2,400+" caption="consultations" color="saffron" />
        </View>
      </Row>

      {/* Tag */}
      <SectionTitle textSub={textSub}>Tag</SectionTitle>
      <Row>
        <Tag variant="sage"      label="In range" />
        <Tag variant="saffron"   label="Slightly off" />
        <Tag variant="terracotta"label="Out of range" />
        <Tag variant="forest"    label="Thyroid" />
      </Row>

      {/* Typography */}
      <SectionTitle textSub={textSub}>Typography</SectionTitle>
      <View style={[styles.section, styles.typographyCard, { backgroundColor: cardBg, borderColor: cardBdr, borderWidth: 1 }]}>
        <Text style={[styles.typoH1, { color: textPri }]}>H1 — Cormorant 42px</Text>
        <Text style={[styles.typoH2, { color: textPri }]}>H2 — Cormorant 28px</Text>
        <Text style={[styles.typoH3, { color: textPri }]}>H3 — Cormorant 22px</Text>
        <Text style={[styles.typoItalic, { color: textPri }]}>"Pull-quote — Cormorant italic 22px"</Text>
        <Text style={[styles.typoBody, { color: textPri }]}>Body — DM Sans 14px. Line height 1.6 for clinical readability.</Text>
        <Text style={[styles.typoCaption, { color: textSub }]}>Caption — DM Sans 12px. Metadata, timestamps.</Text>
        <Text style={[styles.typoHindi, { color: textPri }]}>हिन्दी — Tiro Devanagari Hindi</Text>
      </View>

      {/* Color Palette */}
      <SectionTitle textSub={textSub}>{`Color Tokens (${Object.keys(colors).length})`}</SectionTitle>
      <View style={styles.paletteGrid}>
        {(Object.entries(colors) as [string, string][])
          .filter(([, hex]) => hex.startsWith('#'))
          .map(([name, hex]) => (
            <View key={name} style={styles.swatchContainer}>
              <View style={[styles.swatch, { backgroundColor: hex, borderColor: isDark ? 'rgba(255,255,255,0.10)' : 'rgba(0,0,0,0.08)' }]} />
              <Text style={[styles.swatchLabel, { color: textSub }]}>{name}</Text>
            </View>
          ))
        }
      </View>

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen:  { flex: 1 },
  content: { paddingBottom: spacing[12] },

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
    color: 'rgba(255,255,255,0.60)',
    marginTop: spacing[1],
  },

  sectionTitle: {
    fontFamily: 'DMSans-SemiBold',
    fontSize: fontSize.caption,
    letterSpacing: 1.5,
    marginHorizontal: spacing[6],
    marginTop: spacing[8],
    marginBottom: spacing[3],
    paddingBottom: spacing[2],
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0,0,0,0.06)',
  },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3], marginHorizontal: spacing[6], marginBottom: spacing[3] },
  section: { marginHorizontal: spacing[6], marginBottom: spacing[4] },

  cardDemo: { marginHorizontal: spacing[6], marginBottom: spacing[3] },
  cardLabel: { fontFamily: 'DMSans-Regular', fontSize: fontSize.caption, marginBottom: spacing[2] },
  cardText:  { fontFamily: 'DMSans-Regular', fontSize: fontSize.body, lineHeight: fontSize.body * 1.6 },

  statCard: { flex: 1, minWidth: 120, padding: spacing[4] },

  typographyCard: { borderRadius: borderRadius.xl, padding: spacing[5] },
  typoH1:     { fontFamily: 'CormorantGaramond-Medium', fontSize: fontSize.h1,  lineHeight: fontSize.h1 * 1.15, marginBottom: spacing[3] },
  typoH2:     { fontFamily: 'CormorantGaramond-Medium', fontSize: fontSize.h2,  lineHeight: fontSize.h2 * 1.25, marginBottom: spacing[3] },
  typoH3:     { fontFamily: 'CormorantGaramond-Medium', fontSize: fontSize.h3,  lineHeight: fontSize.h3 * 1.3,  marginBottom: spacing[3] },
  typoItalic: { fontFamily: 'CormorantGaramond-Italic', fontSize: fontSize.h3,  lineHeight: fontSize.h3 * 1.3,  marginBottom: spacing[4] },
  typoBody:   { fontFamily: 'DMSans-Regular',           fontSize: fontSize.body,    lineHeight: fontSize.body    * 1.6, marginBottom: spacing[3] },
  typoCaption:{ fontFamily: 'DMSans-Regular',           fontSize: fontSize.caption, lineHeight: fontSize.caption * 1.5, marginBottom: spacing[4] },
  typoHindi:  { fontFamily: 'TiroDevanagariHindi-Regular', fontSize: fontSize.h3, lineHeight: fontSize.h3 * 1.4 },

  paletteGrid:     { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[4], marginHorizontal: spacing[6], marginBottom: spacing[6] },
  swatchContainer: { alignItems: 'center', gap: spacing[2] },
  swatch:          { width: 52, height: 52, borderRadius: borderRadius.xl, borderWidth: 1 },
  swatchLabel:     { fontFamily: 'DMSans-Regular', fontSize: fontSize.xs },
});
