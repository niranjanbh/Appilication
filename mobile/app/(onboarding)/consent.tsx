import { useRouter } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { captureConsentApi } from '../../lib/api/consent';
import { colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';
import type { ConsentType } from '../../types/auth';

const DPDP_TEXT =
  'Kyros Clinic collects and processes your personal health data under the Digital Personal ' +
  'Data Protection Act 2023 (DPDP). Your data is stored in India, is never sold, and is ' +
  'used only to provide and improve your care. You may withdraw consent, download your data, ' +
  'or request deletion at any time from Profile → My consents.';

const TELEMEDICINE_TEXT =
  'I consent to receive telemedicine consultations via the Kyros platform, delivered by ' +
  'registered medical practitioners in accordance with NMC Telemedicine Practice Guidelines ' +
  '2020 and the Indian Medical Council Act 1956. I understand that telemedicine does not ' +
  'replace in-person care for emergencies.';

interface ConsentCardProps {
  title: string;
  summary: string;
  fullText: string;
  agreed: boolean;
  onAgree: () => void;
}

function ConsentCard({ title, summary, fullText, agreed, onAgree }: ConsentCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <View style={cardStyles.card}>
      <Text style={cardStyles.title}>{title}</Text>
      <Text style={cardStyles.summary}>{summary}</Text>

      <Pressable onPress={() => setExpanded(e => !e)} accessibilityLabel="Read full consent text">
        <Text style={cardStyles.readMore}>
          {expanded ? 'Hide full text ↑' : 'Read full consent text ↓'}
        </Text>
      </Pressable>

      {expanded && <Text style={cardStyles.fullText}>{fullText}</Text>}

      <Pressable
        style={[cardStyles.agreeButton, agreed && cardStyles.agreedButton]}
        onPress={onAgree}
        disabled={agreed}
        accessibilityLabel={agreed ? `${title} agreed` : `I agree to ${title}`}
        accessibilityState={{ disabled: agreed }}
      >
        <Text style={[cardStyles.agreeText, agreed && cardStyles.agreedText]}>
          {agreed ? '✓ Agreed' : 'I agree'}
        </Text>
      </Pressable>
    </View>
  );
}

const cardStyles = StyleSheet.create({
  card: {
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: spacing[4],
    marginBottom: spacing[4],
    gap: spacing[3],
  },
  title: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.forest,
    fontWeight: '600',
  },
  summary: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    lineHeight: 22,
  },
  fullText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    lineHeight: 20,
  },
  readMore: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.jade,
  },
  agreeButton: {
    borderWidth: 1.5,
    borderColor: colors.forest,
    borderRadius: 8,
    paddingVertical: spacing[2],
    alignItems: 'center',
  },
  agreedButton: {
    borderColor: colors.sage,
    backgroundColor: '#F0F5F2',
  },
  agreeText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.forest,
    fontWeight: '600',
  },
  agreedText: { color: colors.jade },
});

export default function ConsentScreen() {
  const router = useRouter();
  const [dpdpAgreed, setDpdpAgreed] = useState(false);
  const [teleAgreed, setTeleAgreed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const bothAgreed = dpdpAgreed && teleAgreed;

  const handleAgree = async (type: ConsentType, text: string, setAgreed: (v: boolean) => void) => {
    setError(null);
    try {
      await captureConsentApi({
        consent_type: type,
        version: '1.0',
        granted: true,
        consent_text: text,
      });
      setAgreed(true);
    } catch {
      setError('Could not record your consent. Please check your connection and try again.');
    }
  };

  const handleContinue = async () => {
    setSubmitting(true);
    router.push('/(onboarding)/health-sync');
    setSubmitting(false);
  };

  return (
    <ScrollView style={styles.flex} contentContainerStyle={styles.container}>
      <View style={styles.header}>
        <Text style={styles.step}>Step 3 of 4</Text>
        <Text style={styles.title}>Your rights and permissions</Text>
        <Text style={styles.subtitle}>
          Two quick consents. Read the summary, agree, then continue.
        </Text>
      </View>

      <ConsentCard
        title="Data protection (DPDP)"
        summary="We store your health data securely in India under the DPDP Act 2023. You can withdraw, download, or delete your data at any time."
        fullText={DPDP_TEXT}
        agreed={dpdpAgreed}
        onAgree={() => handleAgree('data_processing', DPDP_TEXT, setDpdpAgreed)}
      />

      <ConsentCard
        title="Telemedicine consent"
        summary="You consent to receive medical consultations via video call from registered Kyros doctors, per NMC Telemedicine Guidelines 2020."
        fullText={TELEMEDICINE_TEXT}
        agreed={teleAgreed}
        onAgree={() => handleAgree('telemedicine', TELEMEDICINE_TEXT, setTeleAgreed)}
      />

      {error && <Text style={styles.error}>{error}</Text>}

      <Pressable
        style={[styles.button, (!bothAgreed || submitting) && styles.buttonDisabled]}
        onPress={handleContinue}
        disabled={!bothAgreed || submitting}
        accessibilityLabel="Continue"
      >
        {submitting ? (
          <ActivityIndicator color={colors.ivory} />
        ) : (
          <Text style={styles.buttonText}>Continue</Text>
        )}
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.ivory },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[12],
    paddingBottom: spacing[8],
  },
  header: { marginBottom: spacing[6], gap: spacing[2] },
  step: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    fontWeight: '500',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  title: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    color: colors.forest,
    fontWeight: '500',
  },
  subtitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    lineHeight: 22,
  },
  error: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.alert,
    textAlign: 'center',
    marginBottom: spacing[3],
  },
  button: {
    backgroundColor: colors.forest,
    borderRadius: 8,
    paddingVertical: spacing[4],
    alignItems: 'center',
    marginTop: spacing[4],
  },
  buttonDisabled: { opacity: 0.4 },
  buttonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.ivory,
    fontWeight: '600',
  },
});
