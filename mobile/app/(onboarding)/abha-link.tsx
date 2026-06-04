import { useRouter } from 'expo-router';
import { useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { confirmAbhaCreation, initAbhaCreation, linkAbhaNumber } from '../../lib/api/abha';
import { useAuth } from '../../lib/auth/context';
import { colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

type Tab = 'link' | 'create';
type CreateStep = 'aadhaar' | 'otp';

export default function AbhaLinkScreen() {
  const router = useRouter();
  const { markOnboardingComplete } = useAuth();

  const [tab, setTab] = useState<Tab>('link');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Link existing ABHA
  const [abhaNumber, setAbhaNumber] = useState('');

  // Create new ABHA
  const [createStep, setCreateStep] = useState<CreateStep>('aadhaar');
  const [aadhaarNumber, setAadhaarNumber] = useState('');
  const [txnId, setTxnId] = useState('');
  const [otp, setOtp] = useState('');

  const finish = async () => {
    await markOnboardingComplete();
    router.replace('/(tabs)/home');
  };

  const handleLinkExisting = async () => {
    setError(null);
    const digits = abhaNumber.replace(/-/g, '');
    if (digits.length !== 14 || !/^\d+$/.test(digits)) {
      setError('Enter a valid 14-digit ABHA number');
      return;
    }
    setLoading(true);
    try {
      const result = await linkAbhaNumber(abhaNumber);
      if (result.linked) {
        setSuccess(`ABHA linked: ${result.abha_number_masked ?? ''}`);
      } else {
        setError('ABHA number not found in ABDM registry');
      }
    } catch {
      setError('Could not verify ABHA number. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateInit = async () => {
    setError(null);
    if (!/^\d{12}$/.test(aadhaarNumber)) {
      setError('Enter a valid 12-digit Aadhaar number');
      return;
    }
    setLoading(true);
    try {
      const result = await initAbhaCreation(aadhaarNumber);
      setTxnId(result.txn_id);
      setCreateStep('otp');
    } catch {
      setError('Could not send OTP. Please check your Aadhaar number.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateConfirm = async () => {
    setError(null);
    if (!/^\d{6}$/.test(otp)) {
      setError('Enter the 6-digit OTP');
      return;
    }
    setLoading(true);
    try {
      const result = await confirmAbhaCreation(txnId, otp);
      if (result.linked) {
        setSuccess(`ABHA created: ${result.abha_number_masked ?? ''}`);
      } else {
        setError('Invalid OTP or session expired. Please start again.');
        setCreateStep('aadhaar');
      }
    } catch {
      setError('Invalid OTP. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <View style={styles.container}>
        <View style={styles.successCard}>
          <Text style={styles.successIcon}>✓</Text>
          <Text style={styles.successTitle}>ABHA linked</Text>
          <Text style={styles.successBody}>{success}</Text>
          <Text style={styles.successNote}>
            Your health records can now be securely shared with your care team.
          </Text>
        </View>
        <Pressable style={styles.button} onPress={finish} accessibilityLabel="Continue to home">
          <Text style={styles.buttonText}>Continue</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <ScrollView style={styles.flex} contentContainerStyle={styles.container}>
      <View style={styles.header}>
        <Text style={styles.step}>Step 5 of 5</Text>
        <Text style={styles.title}>Link your health record</Text>
        <Text style={styles.subtitle}>
          ABHA (Ayushman Bharat Health Account) lets you carry your health history
          securely. This step is optional.
        </Text>
      </View>

      <View style={styles.tabs}>
        <Pressable
          style={[styles.tab, tab === 'link' && styles.tabActive]}
          onPress={() => { setTab('link'); setError(null); }}
          accessibilityLabel="Link existing ABHA"
        >
          <Text style={[styles.tabText, tab === 'link' && styles.tabTextActive]}>
            I have an ABHA
          </Text>
        </Pressable>
        <Pressable
          style={[styles.tab, tab === 'create' && styles.tabActive]}
          onPress={() => { setTab('create'); setError(null); setCreateStep('aadhaar'); }}
          accessibilityLabel="Create new ABHA"
        >
          <Text style={[styles.tabText, tab === 'create' && styles.tabTextActive]}>
            Create new ABHA
          </Text>
        </Pressable>
      </View>

      {tab === 'link' && (
        <View style={styles.form}>
          <Text style={styles.label}>Your ABHA number</Text>
          <TextInput
            style={styles.input}
            placeholder="12345678901234"
            placeholderTextColor={colors.stone}
            value={abhaNumber}
            onChangeText={setAbhaNumber}
            keyboardType="number-pad"
            maxLength={17}
            accessibilityLabel="ABHA number"
          />
          <Text style={styles.hint}>14-digit number from your ABHA card or app</Text>
          <Pressable
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleLinkExisting}
            disabled={loading}
            accessibilityLabel="Verify and link ABHA"
          >
            {loading
              ? <ActivityIndicator color={colors.ivory} />
              : <Text style={styles.buttonText}>Verify and link</Text>
            }
          </Pressable>
        </View>
      )}

      {tab === 'create' && createStep === 'aadhaar' && (
        <View style={styles.form}>
          <Text style={styles.label}>Aadhaar number</Text>
          <TextInput
            style={styles.input}
            placeholder="XXXXXXXXXXXX"
            placeholderTextColor={colors.stone}
            value={aadhaarNumber}
            onChangeText={setAadhaarNumber}
            keyboardType="number-pad"
            maxLength={12}
            secureTextEntry
            accessibilityLabel="Aadhaar number"
          />
          <Text style={styles.hint}>
            An OTP will be sent to your Aadhaar-linked mobile number.
            Your Aadhaar is encrypted end-to-end and never stored by Kyros.
          </Text>
          <Pressable
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleCreateInit}
            disabled={loading}
            accessibilityLabel="Send OTP"
          >
            {loading
              ? <ActivityIndicator color={colors.ivory} />
              : <Text style={styles.buttonText}>Send OTP</Text>
            }
          </Pressable>
        </View>
      )}

      {tab === 'create' && createStep === 'otp' && (
        <View style={styles.form}>
          <Text style={styles.label}>Enter OTP</Text>
          <TextInput
            style={styles.input}
            placeholder="000000"
            placeholderTextColor={colors.stone}
            value={otp}
            onChangeText={setOtp}
            keyboardType="number-pad"
            maxLength={6}
            accessibilityLabel="OTP"
          />
          <Text style={styles.hint}>Check the mobile number linked to your Aadhaar</Text>
          <Pressable
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleCreateConfirm}
            disabled={loading}
            accessibilityLabel="Confirm OTP and create ABHA"
          >
            {loading
              ? <ActivityIndicator color={colors.ivory} />
              : <Text style={styles.buttonText}>Create ABHA</Text>
            }
          </Pressable>
          <Pressable
            style={styles.secondaryButton}
            onPress={() => { setCreateStep('aadhaar'); setOtp(''); setError(null); }}
            accessibilityLabel="Change Aadhaar number"
          >
            <Text style={styles.secondaryButtonText}>Change Aadhaar number</Text>
          </Pressable>
        </View>
      )}

      {error && <Text style={styles.errorText}>{error}</Text>}

      <Pressable
        style={styles.skipButton}
        onPress={finish}
        accessibilityLabel="Skip ABHA linking"
      >
        <Text style={styles.skipText}>Skip for now</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.ivory },
  container: {
    padding: spacing[6],
    paddingBottom: spacing[10],
    flexGrow: 1,
  },
  header: { marginBottom: spacing[6] },
  step: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    marginBottom: spacing[2],
  },
  title: {
    fontFamily: fontFamily.heading,
    fontSize: fontSize.h2,
    color: colors.ink,
    marginBottom: spacing[2],
  },
  subtitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    lineHeight: 22,
  },
  tabs: {
    flexDirection: 'row',
    borderRadius: 8,
    backgroundColor: '#F0EDE8',
    padding: 4,
    marginBottom: spacing[6],
  },
  tab: {
    flex: 1,
    paddingVertical: spacing[2],
    alignItems: 'center',
    borderRadius: 6,
  },
  tabActive: { backgroundColor: colors.ivory },
  tabText: { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.stone },
  tabTextActive: { color: colors.ink, fontFamily: fontFamily.body },
  form: { gap: spacing[3] },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
  },
  input: {
    borderWidth: 1,
    borderColor: colors.stone,
    borderRadius: 8,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    backgroundColor: colors.ivory,
  },
  hint: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.stone,
    lineHeight: 18,
  },
  button: {
    backgroundColor: colors.sage,
    borderRadius: 8,
    paddingVertical: spacing[4],
    alignItems: 'center',
    marginTop: spacing[2],
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ivory,
  },
  secondaryButton: { paddingVertical: spacing[2], alignItems: 'center' },
  secondaryButtonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.sage,
  },
  errorText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.alert,
    marginTop: spacing[3],
    textAlign: 'center',
  },
  skipButton: { marginTop: spacing[8], alignItems: 'center', paddingVertical: spacing[3] },
  skipText: { fontFamily: fontFamily.body, fontSize: fontSize.body, color: colors.stone },
  successCard: {
    backgroundColor: '#F0FAF5',
    borderRadius: 12,
    padding: spacing[6],
    alignItems: 'center',
    marginBottom: spacing[8],
    flex: 1,
    justifyContent: 'center',
  },
  successIcon: { fontSize: 48, marginBottom: spacing[4] },
  successTitle: {
    fontFamily: fontFamily.heading,
    fontSize: fontSize.h2,
    color: colors.ink,
    marginBottom: spacing[2],
  },
  successBody: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    marginBottom: spacing[2],
  },
  successNote: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    textAlign: 'center',
    lineHeight: 22,
  },
});
