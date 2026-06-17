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
import { useThemePreference } from '../../lib/theme-context';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { confirmAbhaCreation, initAbhaCreation, linkAbhaNumber } from '../../lib/api/abha';
import { useAuth } from '../../lib/auth/context';
import { borderRadius, colors, fontFamily, fontSize, spacing , withAlpha } from '../../lib/design-tokens';

type Tab        = 'link' | 'create';
type CreateStep = 'aadhaar' | 'otp';

const TOTAL_STEPS = 5;
const STEP = 5;
const SPRING = { mass: 0.3, stiffness: 500, damping: 20 };

export default function AbhaLinkScreen() {
  const router = useRouter();
  const { markOnboardingComplete } = useAuth();
  const isDark = useThemePreference().colorScheme === 'dark';

  const [tab,          setTab]          = useState<Tab>('link');
  const [loading,      setLoading]      = useState(false);
  const [error,        setError]        = useState<string | null>(null);
  const [success,      setSuccess]      = useState<string | null>(null);
  const [abhaNumber,   setAbhaNumber]   = useState('');
  const [createStep,   setCreateStep]   = useState<CreateStep>('aadhaar');
  const [aadhaarNumber,setAadhaarNumber]= useState('');
  const [txnId,        setTxnId]        = useState('');
  const [otp,          setOtp]          = useState('');

  // Preserve all existing ABHA logic
  const finish = async () => {
    await markOnboardingComplete();
    router.replace('/(tabs)/home');
  };

  const handleLinkExisting = async () => {
    setError(null);
    const digits = abhaNumber.replace(/-/g, '');
    if (digits.length !== 14 || !/^\d+$/.test(digits)) { setError('Enter a valid 14-digit ABHA number'); return; }
    setLoading(true);
    try {
      const result = await linkAbhaNumber(abhaNumber);
      if (result.linked) setSuccess(`ABHA linked: ${result.abha_number_masked ?? ''}`);
      else setError('ABHA number not found in ABDM registry');
    } catch {
      setError('Could not verify ABHA number. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateInit = async () => {
    setError(null);
    if (!/^\d{12}$/.test(aadhaarNumber)) { setError('Enter a valid 12-digit Aadhaar number'); return; }
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
    if (!/^\d{6}$/.test(otp)) { setError('Enter the 6-digit OTP'); return; }
    setLoading(true);
    try {
      const result = await confirmAbhaCreation(txnId, otp);
      if (result.linked) setSuccess(`ABHA created: ${result.abha_number_masked ?? ''}`);
      else { setError('Invalid OTP or session expired. Please start again.'); setCreateStep('aadhaar'); }
    } catch {
      setError('Invalid OTP. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const btnScale  = useSharedValue(1);
  const btnAnim   = useAnimatedStyle(() => ({ transform: [{ scale: btnScale.value }] }));
  const skipScale = useSharedValue(1);
  const skipAnim  = useAnimatedStyle(() => ({ transform: [{ scale: skipScale.value }] }));

  const bg       = isDark ? colors.forestInk     : colors.skyMist;
  const textPri  = isDark ? colors.white        : colors.navyDeep;
  const textSub  = isDark ? colors.stoneDim    : colors.coolGray;
  const cardBg   = isDark ? colors.forestSurface : colors.white;
  const inputBg  = isDark ? colors.forestSurfaceRaised    : colors.skyMist;
  const inputBdr = isDark ? 'rgba(255,255,255,0.10)' : colors.borderLight;

  // ── Success state ─────────────────────────────────────────────────────────

  if (success) {
    return (
      <View style={[styles.container, { backgroundColor: bg }]}>
        <View style={[styles.successCard, { backgroundColor: cardBg, borderColor: colors.successGreen + '30' }]}>
          <View style={[styles.successIconWrap, { backgroundColor: colors.successGreen }]}>
            <Text style={styles.successIconText}>✓</Text>
          </View>
          <Text style={[styles.successTitle, { color: textPri }]}>ABHA linked</Text>
          <Text style={[styles.successBody, { color: textSub }]}>{success}</Text>
          <Text style={[styles.successNote, { color: textSub }]}>
            Your health records can now be securely shared with your care team.
          </Text>
        </View>
        <Animated.View style={btnAnim}>
          <Pressable
            style={styles.button}
            onPress={finish}
            onPressIn={() => { btnScale.value = withSpring(0.97, SPRING); }}
            onPressOut={() => { btnScale.value = withSpring(1, SPRING); }}
            accessibilityLabel="Continue to home"
          >
            <Text style={styles.buttonText}>Continue →</Text>
          </Pressable>
        </Animated.View>
      </View>
    );
  }

  // ── Main form ─────────────────────────────────────────────────────────────

  return (
    <ScrollView style={[styles.flex, { backgroundColor: bg }]} contentContainerStyle={styles.scroll}>

      {/* Step progress */}
      <View style={styles.stepRow}>
        <View style={[styles.progressTrack, { backgroundColor: isDark ? colors.forestSurfaceRaised : colors.borderLight }]}>
          <View style={[styles.progressFill, { width: `${(STEP / TOTAL_STEPS) * 100}%` as never }]} />
        </View>
        <Text style={[styles.stepLabel, { color: textSub }]}>Step {STEP} of {TOTAL_STEPS}</Text>
      </View>

      {/* Header */}
      <View style={styles.header}>
        <Text style={[styles.title, { color: textPri }]}>Link your health record</Text>
        <Text style={[styles.subtitle, { color: textSub }]}>
          ABHA (Ayushman Bharat Health Account) lets you carry your health history securely. This step is optional.
        </Text>
      </View>

      {/* Tab switcher */}
      <View style={[styles.tabBar, { backgroundColor: isDark ? colors.forestSurfaceRaised : colors.borderLight }]}>
        {(['link', 'create'] as Tab[]).map(t => (
          <Pressable
            key={t}
            style={[styles.tabItem, tab === t && [styles.tabActive, { backgroundColor: cardBg }]]}
            onPress={() => { setTab(t); setError(null); if (t === 'create') setCreateStep('aadhaar'); }}
            accessibilityLabel={t === 'link' ? 'Link existing ABHA' : 'Create new ABHA'}
          >
            <Text style={[styles.tabText, { color: tab === t ? textPri : textSub, fontWeight: tab === t ? '700' : '400' }]}>
              {t === 'link' ? 'I have an ABHA' : 'Create new ABHA'}
            </Text>
          </Pressable>
        ))}
      </View>

      {/* Link form */}
      {tab === 'link' && (
        <View style={styles.form}>
          <View style={styles.field}>
            <Text style={[styles.fieldLabel, { color: textPri }]}>Your ABHA number</Text>
            <View style={[styles.inputWrap, { backgroundColor: inputBg, borderColor: inputBdr }]}>
              <TextInput
                style={[styles.textInput, { color: textPri }]}
                placeholder="12345678901234"
                placeholderTextColor={textSub}
                value={abhaNumber}
                onChangeText={setAbhaNumber}
                keyboardType="number-pad"
                maxLength={17}
                accessibilityLabel="ABHA number"
              />
            </View>
            <Text style={[styles.hint, { color: textSub }]}>14-digit number from your ABHA card or app</Text>
          </View>
          <Animated.View style={btnAnim}>
            <Pressable
              style={[styles.button, loading && styles.buttonBusy]}
              onPress={handleLinkExisting}
              onPressIn={() => { btnScale.value = withSpring(0.97, SPRING); }}
              onPressOut={() => { btnScale.value = withSpring(1, SPRING); }}
              disabled={loading}
              accessibilityLabel="Verify and link ABHA"
            >
              {loading ? <ActivityIndicator color={colors.white} size="small" /> : <Text style={styles.buttonText}>Verify and link</Text>}
            </Pressable>
          </Animated.View>
        </View>
      )}

      {/* Create — aadhaar step */}
      {tab === 'create' && createStep === 'aadhaar' && (
        <View style={styles.form}>
          <View style={styles.field}>
            <Text style={[styles.fieldLabel, { color: textPri }]}>Aadhaar number</Text>
            <View style={[styles.inputWrap, { backgroundColor: inputBg, borderColor: inputBdr }]}>
              <TextInput
                style={[styles.textInput, { color: textPri }]}
                placeholder="XXXXXXXXXXXX"
                placeholderTextColor={textSub}
                value={aadhaarNumber}
                onChangeText={setAadhaarNumber}
                keyboardType="number-pad"
                maxLength={12}
                secureTextEntry
                accessibilityLabel="Aadhaar number"
              />
            </View>
            <Text style={[styles.hint, { color: textSub }]}>
              An OTP will be sent to your Aadhaar-linked mobile. Your Aadhaar is encrypted end-to-end and never stored by Kyros.
            </Text>
          </View>
          <Animated.View style={btnAnim}>
            <Pressable
              style={[styles.button, loading && styles.buttonBusy]}
              onPress={handleCreateInit}
              onPressIn={() => { btnScale.value = withSpring(0.97, SPRING); }}
              onPressOut={() => { btnScale.value = withSpring(1, SPRING); }}
              disabled={loading}
              accessibilityLabel="Send OTP"
            >
              {loading ? <ActivityIndicator color={colors.white} size="small" /> : <Text style={styles.buttonText}>Send OTP</Text>}
            </Pressable>
          </Animated.View>
        </View>
      )}

      {/* Create — OTP step */}
      {tab === 'create' && createStep === 'otp' && (
        <View style={styles.form}>
          <View style={styles.field}>
            <Text style={[styles.fieldLabel, { color: textPri }]}>Enter OTP</Text>
            <View style={[styles.inputWrap, { backgroundColor: inputBg, borderColor: inputBdr }]}>
              <TextInput
                style={[styles.textInput, { color: textPri }]}
                placeholder="000000"
                placeholderTextColor={textSub}
                value={otp}
                onChangeText={setOtp}
                keyboardType="number-pad"
                maxLength={6}
                accessibilityLabel="OTP"
              />
            </View>
            <Text style={[styles.hint, { color: textSub }]}>Check the mobile number linked to your Aadhaar</Text>
          </View>
          <Animated.View style={btnAnim}>
            <Pressable
              style={[styles.button, loading && styles.buttonBusy]}
              onPress={handleCreateConfirm}
              onPressIn={() => { btnScale.value = withSpring(0.97, SPRING); }}
              onPressOut={() => { btnScale.value = withSpring(1, SPRING); }}
              disabled={loading}
              accessibilityLabel="Confirm OTP and create ABHA"
            >
              {loading ? <ActivityIndicator color={colors.white} size="small" /> : <Text style={styles.buttonText}>Create ABHA</Text>}
            </Pressable>
          </Animated.View>
          <Pressable
            style={styles.secondaryBtn}
            onPress={() => { setCreateStep('aadhaar'); setOtp(''); setError(null); }}
            accessibilityLabel="Change Aadhaar number"
          >
            <Text style={[styles.secondaryBtnText, { color: colors.electricBlue }]}>Change Aadhaar number</Text>
          </Pressable>
        </View>
      )}

      {error && <Text style={[styles.errorText, { color: colors.criticalRed }]}>{error}</Text>}

      {/* Skip */}
      <Animated.View style={skipAnim}>
        <Pressable
          style={styles.skipBtn}
          onPress={finish}
          onPressIn={() => { skipScale.value = withSpring(0.97, SPRING); }}
          onPressOut={() => { skipScale.value = withSpring(1, SPRING); }}
          accessibilityLabel="Skip ABHA linking"
        >
          <Text style={[styles.skipText, { color: textSub }]}>Skip for now</Text>
        </Pressable>
      </Animated.View>

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { flex: 1, padding: spacing[6], paddingBottom: spacing[10], justifyContent: 'space-between' },
  scroll: { padding: spacing[6], paddingBottom: spacing[10], flexGrow: 1, gap: spacing[4] },

  stepRow: { gap: spacing[2] },
  progressTrack: { height: 4, borderRadius: 2, overflow: 'hidden' },
  progressFill:  { height: 4, backgroundColor: colors.electricBlue, borderRadius: 2 },
  stepLabel: { fontFamily: fontFamily.body, fontSize: fontSize.xs, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 1 },

  header: { gap: spacing[2] },
  title:    { fontFamily: fontFamily.display, fontSize: fontSize.h2, fontWeight: '600' },
  subtitle: { fontFamily: fontFamily.body, fontSize: fontSize.body, lineHeight: 22 },

  tabBar:   { flexDirection: 'row', borderRadius: borderRadius.xl, padding: 4 },
  tabItem:  { flex: 1, paddingVertical: spacing[3], alignItems: 'center', borderRadius: borderRadius.lg },
  tabActive:{ boxShadow: '0 2px 8px rgba(0,0,0,0.07)' },
  tabText:  { fontFamily: fontFamily.body, fontSize: fontSize.body },

  form:       { gap: spacing[3] },
  field:      { gap: spacing[1] },
  fieldLabel: { fontFamily: fontFamily.body, fontSize: fontSize.sm, fontWeight: '600' },
  inputWrap:  { borderRadius: borderRadius.xl, borderWidth: 1, paddingHorizontal: spacing[4], paddingVertical: spacing[4] },
  textInput:  { fontFamily: fontFamily.body, fontSize: fontSize.body, padding: 0 },
  hint:       { fontFamily: fontFamily.body, fontSize: fontSize.caption, lineHeight: 18 },

  button: {
    height: 56,
    backgroundColor: colors.navyDeep,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: `0 8px 16px ${withAlpha(colors.navyDeep, 0.28)}`,
  },
  buttonBusy: { opacity: 0.70 },
  buttonText: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, color: colors.white, fontWeight: '700' },

  secondaryBtn:     { height: 48, alignItems: 'center', justifyContent: 'center' },
  secondaryBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600' },

  errorText: { fontFamily: fontFamily.body, fontSize: fontSize.sm, textAlign: 'center' },

  skipBtn:  { height: 52, alignItems: 'center', justifyContent: 'center', marginTop: spacing[4] },
  skipText: { fontFamily: fontFamily.body, fontSize: fontSize.body },

  // Success
  successCard: {
    borderRadius: borderRadius.xxl,
    padding: spacing[6],
    alignItems: 'center',
    gap: spacing[3],
    borderWidth: 1,
    boxShadow: '0 8px 20px rgba(0,0,0,0.08)',
    marginBottom: spacing[6],
  },
  successIconWrap: {
    width: 72,
    height: 72,
    borderRadius: 36,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: `0 8px 16px ${withAlpha(colors.successGreen, 0.35)}`,
    marginBottom: spacing[2],
  },
  successIconText: { fontSize: 36, color: colors.white },
  successTitle:    { fontFamily: fontFamily.display, fontSize: fontSize.h2, fontWeight: '600', textAlign: 'center' },
  successBody:     { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600', textAlign: 'center' },
  successNote:     { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center', lineHeight: 22 },
});
