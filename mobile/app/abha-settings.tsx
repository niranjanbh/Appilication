import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useThemePreference } from '../lib/theme-context';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import {
  confirmAbhaCreation,
  getAbhaStatus,
  initAbhaCreation,
  linkAbhaNumber,
  type AbhaStatus,
} from '../lib/api/abha';
import { borderRadius, colors, fontFamily, fontSize, spacing , withAlpha } from '../lib/design-tokens';

type Tab        = 'link' | 'create';
type CreateStep = 'aadhaar' | 'otp';

export default function AbhaSettingsScreen() {
  const router  = useRouter();
  const isDark  = useThemePreference().colorScheme === 'dark';

  const [status,         setStatus]        = useState<AbhaStatus | null>(null);
  const [statusLoading,  setStatusLoading] = useState(true);
  const [tab,            setTab]           = useState<Tab>('link');
  const [loading,        setLoading]       = useState(false);
  const [error,          setError]         = useState<string | null>(null);
  const [success,        setSuccess]       = useState<string | null>(null);
  const [abhaNumber,     setAbhaNumber]    = useState('');
  const [createStep,     setCreateStep]    = useState<CreateStep>('aadhaar');
  const [aadhaarNumber,  setAadhaarNumber] = useState('');
  const [txnId,          setTxnId]         = useState('');
  const [otp,            setOtp]           = useState('');

  useEffect(() => {
    getAbhaStatus()
      .then(setStatus)
      .catch(() => setStatus(null))
      .finally(() => setStatusLoading(false));
  }, []);

  // Preserve all existing ABHA link / create logic
  const handleLinkExisting = async () => {
    setError(null);
    const digits = abhaNumber.replace(/-/g, '');
    if (digits.length !== 14 || !/^\d+$/.test(digits)) { setError('Enter a valid 14-digit ABHA number'); return; }
    setLoading(true);
    try {
      const result = await linkAbhaNumber(abhaNumber);
      if (result.linked) { setStatus(result); setSuccess(`ABHA linked: ${result.abha_number_masked ?? ''}`); }
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
      if (result.linked) { setStatus(result); setSuccess(`ABHA created: ${result.abha_number_masked ?? ''}`); }
      else { setError('Invalid OTP or session expired. Please start again.'); setCreateStep('aadhaar'); }
    } catch {
      setError('Invalid OTP. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const btnScale = useSharedValue(1);
  const btnAnim  = useAnimatedStyle(() => ({ transform: [{ scale: btnScale.value }] }));

  const bg        = isDark ? colors.midnight     : colors.skyMist;
  const textPri   = isDark ? colors.white        : colors.navyDeep;
  const textSub   = isDark ? colors.slateText    : colors.coolGray;
  const cardBg    = isDark ? colors.nightSurface : colors.white;
  const inputBg  = isDark ? colors.nightElev    : colors.skyMist;
  const inputBdr = isDark ? 'rgba(255,255,255,0.10)' : colors.borderLight;

  if (statusLoading) {
    return <View style={[styles.centered, { backgroundColor: bg }]}><ActivityIndicator color={colors.electricBlue} /></View>;
  }

  return (
    <ScrollView style={[styles.flex, { backgroundColor: bg }]} contentContainerStyle={styles.container}>

      {/* Header */}
      <Pressable onPress={() => router.back()} style={styles.backBtn} accessibilityLabel="Go back">
        <Text style={[styles.backText, { color: colors.electricBlue }]}>‹ Back</Text>
      </Pressable>
      <Text style={[styles.title, { color: textPri }]}>Health Records (ABHA)</Text>
      <Text style={[styles.subtitle, { color: textSub }]}>
        Your Ayushman Bharat Health Account lets you carry your health history securely across providers.
      </Text>

      {/* Linked state */}
      {status?.linked && (
        <View style={[styles.linkedCard, { backgroundColor: colors.successGreen + '12', borderColor: colors.successGreen + '30' }]}>
          <Text style={[styles.linkedLabel, { color: colors.successGreen }]}>✓ Linked ABHA</Text>
          <Text style={[styles.linkedNumber, { color: textPri }]}>{status.abha_number_masked}</Text>
        </View>
      )}

      {/* Success banner */}
      {success && (
        <View style={[styles.successBanner, { backgroundColor: colors.successGreen + '12', borderColor: colors.successGreen + '30' }]}>
          <Text style={[styles.successText, { color: colors.successGreen }]}>{success}</Text>
        </View>
      )}

      {/* Forms */}
      {!status?.linked && !success && (
        <>
          {/* Tab switcher */}
          <View style={[styles.tabBar, { backgroundColor: isDark ? colors.nightElev : colors.borderLight }]}>
            {(['link', 'create'] as Tab[]).map(t => (
              <Pressable
                key={t}
                style={[styles.tabItem, tab === t && [styles.tabActive, { backgroundColor: cardBg, boxShadow: `0 2px 8px ${withAlpha(isDark ? colors.midnight : colors.navyDeep, 0.08)}` }]]}
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
                  onPressIn={() => { btnScale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
                  onPressOut={() => { btnScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
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
                  onPressIn={() => { btnScale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
                  onPressOut={() => { btnScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
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
                  onPressIn={() => { btnScale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
                  onPressOut={() => { btnScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
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
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  flex:    { flex: 1 },
  centered:{ flex: 1, justifyContent: 'center', alignItems: 'center' },
  container: { padding: spacing[6], paddingBottom: spacing[10], flexGrow: 1, gap: spacing[4] },

  backBtn:  { alignSelf: 'flex-start' },
  backText: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600' },

  title: { fontFamily: fontFamily.display, fontSize: fontSize.h2, fontWeight: '600' },
  subtitle: { fontFamily: fontFamily.body, fontSize: fontSize.body, lineHeight: 22 },

  linkedCard: {
    borderRadius: borderRadius.xxl,
    padding: spacing[5],
    borderWidth: 1,
    gap: spacing[1],
  },
  linkedLabel:  { fontFamily: fontFamily.body, fontSize: fontSize.xs, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.8 },
  linkedNumber: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, fontWeight: '700' },

  successBanner: { borderRadius: borderRadius.xl, borderWidth: 1, padding: spacing[4] },
  successText:   { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600' },

  tabBar:   { flexDirection: 'row', borderRadius: borderRadius.xl, padding: 4 },
  tabItem:  { flex: 1, paddingVertical: spacing[3], alignItems: 'center', borderRadius: borderRadius.lg },
  tabActive: { },
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
  buttonText: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, color: colors.white, fontWeight: '600' },

  secondaryBtn:     { height: 48, alignItems: 'center', justifyContent: 'center' },
  secondaryBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.body, fontWeight: '600' },

  errorText: { fontFamily: fontFamily.body, fontSize: fontSize.sm, textAlign: 'center' },
});
