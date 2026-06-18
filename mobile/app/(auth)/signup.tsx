import { zodResolver } from '@hookform/resolvers/zod';
import { Ionicons } from '@expo/vector-icons';
import { Link, useRouter } from 'expo-router';
import { useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useThemePreference } from '../../lib/theme-context';
import { z } from 'zod';
import { signupApi } from '../../lib/api/auth';
import { ApiError } from '../../lib/api/client';
import { AuthBackdrop } from '../../components/ui/AuthBackdrop';
import { GlassCard } from '../../components/ui/GlassCard';
import { HapticPressable } from '../../components/ui/HapticPressable';
import { borderRadius, colors, fontFamily, fontSize, spacing , withAlpha } from '../../lib/design-tokens';

const COUNTRY_CODES = [
  { code: '+91', flag: '🇮🇳', name: 'India' },
  { code: '+1',  flag: '🇺🇸', name: 'USA / Canada' },
  { code: '+44', flag: '🇬🇧', name: 'United Kingdom' },
  { code: '+971', flag: '🇦🇪', name: 'UAE' },
  { code: '+65', flag: '🇸🇬', name: 'Singapore' },
  { code: '+61', flag: '🇦🇺', name: 'Australia' },
  { code: '+49', flag: '🇩🇪', name: 'Germany' },
] as const;

const schema = z.object({
  name:        z.string().min(2, 'Name must be at least 2 characters'),
  phoneNumber: z.string().regex(/^\d{7,12}$/, 'Enter digits only, no spaces or dashes'),
  email:       z.string().email('Enter a valid email address'),
  password:    z.string().min(8, 'Password must be at least 8 characters'),
});
type FormValues = z.infer<typeof schema>;

export default function SignupScreen() {
  const router  = useRouter();
  const isDark  = useThemePreference().colorScheme === 'dark';
  const [apiError, setApiError]         = useState<string | null>(null);
  const [countryCode, setCountryCode]   = useState('+91');
  const [pickerVisible, setPickerVisible] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const { control, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', phoneNumber: '', email: '', password: '' },
  });

  const selectedCountry = COUNTRY_CODES.find(c => c.code === countryCode) ?? COUNTRY_CODES[0];

  // Preserve 100% of existing submit logic
  const onSubmit = async (values: FormValues) => {
    setApiError(null);
    const phone = `${countryCode}${values.phoneNumber}`;
    try {
      await signupApi({ name: values.name, phone, email: values.email, password: values.password });
      router.push({ pathname: '/(auth)/verify-otp', params: { phone } });
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setApiError('An account with this phone or email already exists.');
      } else if (err instanceof ApiError && err.status === 422) {
        setApiError('Please check your details and try again.');
      } else {
        setApiError('Something went wrong. Please try again.');
      }
    }
  };

  const textPri  = isDark ? colors.white        : colors.navyDeep;
  const textSub  = isDark ? colors.stoneDim    : colors.coolGray;
  const inputBg  = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.35)';
  const inputBdr = isDark ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.50)';
  const inputTxt = isDark ? colors.white        : colors.navyDeep;
  const modalBg  = isDark ? colors.forestSurface : colors.white;

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <AuthBackdrop />
      <ScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >

        {/* Logo */}
        <View style={styles.logoArea}>
          <Text style={styles.wordmark}>Kyros</Text>
          <Text style={styles.tagline}>Create your account</Text>
        </View>

        {/* Form card — frosted glass over the gradient */}
        <GlassCard strong unpadded style={styles.cardShadow}>
          <View style={styles.cardInner}>
          <View style={styles.fields}>

            {/* Name */}
            <View style={styles.field}>
              <Text style={[styles.label, { color: textPri }]}>Full name</Text>
              <Controller
                control={control}
                name="name"
                render={({ field }) => (
                  <View style={[styles.inputWrap, { backgroundColor: inputBg, borderColor: errors.name ? colors.criticalRed : inputBdr }]}>
                    <TextInput
                      style={[styles.textInput, { color: inputTxt }]}
                      value={field.value}
                      onChangeText={field.onChange}
                      onBlur={field.onBlur}
                      autoCapitalize="words"
                      autoComplete="name"
                      accessibilityLabel="Full name"
                      placeholderTextColor={textSub}
                      placeholder="Priya Sharma"
                    />
                  </View>
                )}
              />
              {errors.name && <Text style={styles.fieldError}>{errors.name.message}</Text>}
            </View>

            {/* Phone */}
            <View style={styles.field}>
              <Text style={[styles.label, { color: textPri }]}>Phone number</Text>
              <View style={styles.phoneRow}>
                <Pressable
                  style={[styles.countryBtn, { backgroundColor: inputBg, borderColor: errors.phoneNumber ? colors.criticalRed : inputBdr }]}
                  onPress={() => setPickerVisible(true)}
                  accessibilityLabel="Select country code"
                >
                  <Text style={styles.countryFlag}>{selectedCountry.flag}</Text>
                  <Text style={[styles.countryCode, { color: inputTxt }]}>{countryCode}</Text>
                  <Text style={[styles.chevron, { color: textSub }]}>▾</Text>
                </Pressable>
                <Controller
                  control={control}
                  name="phoneNumber"
                  render={({ field }) => (
                    <View style={[styles.inputWrap, styles.phoneInputWrap, { backgroundColor: inputBg, borderColor: errors.phoneNumber ? colors.criticalRed : inputBdr }]}>
                      <TextInput
                        style={[styles.textInput, { color: inputTxt }]}
                        value={field.value}
                        onChangeText={field.onChange}
                        onBlur={field.onBlur}
                        keyboardType="phone-pad"
                        autoComplete="tel-national"
                        accessibilityLabel="Phone number"
                        placeholderTextColor={textSub}
                        placeholder="9876543210"
                      />
                    </View>
                  )}
                />
              </View>
              {errors.phoneNumber && <Text style={styles.fieldError}>{errors.phoneNumber.message}</Text>}
            </View>

            {/* Email */}
            <View style={styles.field}>
              <Text style={[styles.label, { color: textPri }]}>Email address</Text>
              <Controller
                control={control}
                name="email"
                render={({ field }) => (
                  <View style={[styles.inputWrap, { backgroundColor: inputBg, borderColor: errors.email ? colors.criticalRed : inputBdr }]}>
                    <TextInput
                      style={[styles.textInput, { color: inputTxt }]}
                      value={field.value}
                      onChangeText={field.onChange}
                      onBlur={field.onBlur}
                      autoCapitalize="none"
                      keyboardType="email-address"
                      autoComplete="email"
                      accessibilityLabel="Email address"
                      placeholderTextColor={textSub}
                      placeholder="priya@example.com"
                    />
                  </View>
                )}
              />
              {errors.email && <Text style={styles.fieldError}>{errors.email.message}</Text>}
            </View>

            {/* Password */}
            <View style={styles.field}>
              <Text style={[styles.label, { color: textPri }]}>Password</Text>
              <Controller
                control={control}
                name="password"
                render={({ field }) => (
                  <View style={[styles.inputWrap, styles.inputRow, { backgroundColor: inputBg, borderColor: errors.password ? colors.criticalRed : inputBdr }]}>
                    <TextInput
                      style={[styles.textInput, styles.textInputFlex, { color: inputTxt }]}
                      value={field.value}
                      onChangeText={field.onChange}
                      onBlur={field.onBlur}
                      secureTextEntry={!showPassword}
                      autoComplete="password-new"
                      accessibilityLabel="Password"
                      placeholderTextColor={textSub}
                      placeholder="8+ characters"
                    />
                    <Pressable
                      onPress={() => setShowPassword(v => !v)}
                      accessibilityLabel={showPassword ? 'Hide password' : 'Show password'}
                      hitSlop={8}
                    >
                      <Ionicons
                        name={showPassword ? 'eye-off-outline' : 'eye-outline'}
                        size={20}
                        color={textSub}
                      />
                    </Pressable>
                  </View>
                )}
              />
              {errors.password && <Text style={styles.fieldError}>{errors.password.message}</Text>}
            </View>

          </View>

          {apiError ? <Text style={styles.apiError}>{apiError}</Text> : null}

          <HapticPressable
            haptic="medium"
            style={[styles.button, isSubmitting && styles.buttonBusy]}
            onPress={handleSubmit(onSubmit)}
            disabled={isSubmitting}
            accessibilityLabel="Create account"
          >
            {isSubmitting ? (
              <ActivityIndicator color={colors.white} size="small" />
            ) : (
              <Text style={styles.buttonText}>Create account</Text>
            )}
          </HapticPressable>

          <Link href="/(auth)/login" style={[styles.signInLink, { color: textSub }]}>
            Already have an account? Sign in
          </Link>
          </View>
        </GlassCard>

      </ScrollView>

      {/* Country code picker — modal */}
      <Modal visible={pickerVisible} transparent animationType="slide" onRequestClose={() => setPickerVisible(false)}>
        <Pressable style={styles.overlay} onPress={() => setPickerVisible(false)}>
          <View style={[styles.sheet, { backgroundColor: modalBg }]}>
            <View style={styles.sheetHandle} />
            <Text style={[styles.sheetTitle, { color: textPri }]}>Select country</Text>
            {COUNTRY_CODES.map(item => (
              <Pressable
                key={item.code}
                style={[styles.sheetRow, item.code === countryCode && { backgroundColor: isDark ? colors.forestSurfaceRaised : colors.iceBlue }]}
                onPress={() => { setCountryCode(item.code); setPickerVisible(false); }}
                accessibilityLabel={`${item.name} ${item.code}`}
              >
                <Text style={styles.sheetFlag}>{item.flag}</Text>
                <Text style={[styles.sheetName, { color: textPri }]}>{item.name}</Text>
                <Text style={[styles.sheetCode, { color: textSub }]}>{item.code}</Text>
              </Pressable>
            ))}
          </View>
        </Pressable>
      </Modal>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[12],
    paddingBottom: spacing[8],
  },

  logoArea: { alignItems: 'center', marginBottom: spacing[6], gap: spacing[1] },
  wordmark: {
    fontFamily: fontFamily.display,
    fontSize: 48,
    color: colors.white,
    fontWeight: '500',
  },
  tagline: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: 'rgba(255,255,255,0.60)',
  },

  cardShadow: {
    boxShadow: '0 24px 40px rgba(0,0,0,0.22)',
  },
  cardInner: {
    padding: spacing[6],
    gap: spacing[4],
  },

  fields: { gap: spacing[4] },
  field:  { gap: spacing[1] },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: '600',
  },
  inputWrap: {
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[4],
  },
  phoneInputWrap: { flex: 1 },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
  },
  textInput: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    padding: 0,
  },
  textInputFlex: { flex: 1 },
  fieldError: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.criticalRed,
  },
  phoneRow:   { flexDirection: 'row', gap: spacing[2] },
  countryBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[1],
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[4],
  },
  countryFlag: { fontSize: 18 },
  countryCode: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '500',
  },
  chevron: { fontSize: 11, marginLeft: 2 },

  apiError: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: colors.criticalRed,
    textAlign: 'center',
  },
  button: {
    height: 56,
    backgroundColor: colors.navyDeep,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: `0 8px 16px ${withAlpha(colors.navyDeep, 0.30)}`,
  },
  buttonBusy: { opacity: 0.70 },
  buttonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.white,
    fontWeight: '600',
  },
  signInLink: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    textAlign: 'center',
    paddingVertical: spacing[2],
  },

  // Modal sheet
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.50)', justifyContent: 'flex-end' },
  sheet: {
    borderTopLeftRadius: borderRadius.xxl,
    borderTopRightRadius: borderRadius.xxl,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[3],
    paddingBottom: spacing[10],
    gap: spacing[1],
  },
  sheetHandle: {
    width: 36,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.borderLight,
    alignSelf: 'center',
    marginBottom: spacing[4],
  },
  sheetTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    fontWeight: '700',
    marginBottom: spacing[4],
  },
  sheetRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing[3],
    paddingHorizontal: spacing[3],
    borderRadius: borderRadius.lg,
  },
  sheetFlag: { fontSize: 22, width: 38 },
  sheetName: {
    flex: 1,
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '500',
  },
  sheetCode: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
  },
});
