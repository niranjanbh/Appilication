import { zodResolver } from '@hookform/resolvers/zod';
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
import { z } from 'zod';
import { signupApi } from '../../lib/api/auth';
import { ApiError } from '../../lib/api/client';
import { colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

const COUNTRY_CODES = [
  { code: '+91', flag: '🇮🇳', name: 'India' },
  { code: '+1', flag: '🇺🇸', name: 'USA / Canada' },
  { code: '+44', flag: '🇬🇧', name: 'United Kingdom' },
  { code: '+971', flag: '🇦🇪', name: 'UAE' },
  { code: '+65', flag: '🇸🇬', name: 'Singapore' },
  { code: '+61', flag: '🇦🇺', name: 'Australia' },
  { code: '+49', flag: '🇩🇪', name: 'Germany' },
] as const;

const schema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  phoneNumber: z.string().regex(/^\d{7,12}$/, 'Enter digits only, no spaces or dashes'),
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});
type FormValues = z.infer<typeof schema>;

export default function SignupScreen() {
  const router = useRouter();
  const [apiError, setApiError] = useState<string | null>(null);
  const [countryCode, setCountryCode] = useState('+91');
  const [pickerVisible, setPickerVisible] = useState(false);

  const { control, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', phoneNumber: '', email: '', password: '' },
  });

  const selectedCountry = COUNTRY_CODES.find(c => c.code === countryCode) ?? COUNTRY_CODES[0];

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

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <Text style={styles.wordmark}>Kyros</Text>
        <Text style={styles.subtitle}>Create your account</Text>

        <View style={styles.form}>
          {/* Name */}
          <View>
            <Text style={styles.label}>Full name</Text>
            <Controller
              control={control}
              name="name"
              render={({ field }) => (
                <TextInput
                  style={[styles.input, errors.name && styles.inputError]}
                  value={field.value}
                  onChangeText={field.onChange}
                  onBlur={field.onBlur}
                  autoCapitalize="words"
                  autoComplete="name"
                  accessibilityLabel="Full name"
                  placeholderTextColor={colors.stone}
                  placeholder="Priya Sharma"
                />
              )}
            />
            {errors.name && <Text style={styles.fieldError}>{errors.name.message}</Text>}
          </View>

          {/* Phone with country code picker */}
          <View>
            <Text style={styles.label}>Phone number</Text>
            <View style={styles.phoneRow}>
              <Pressable
                style={[styles.countryButton, errors.phoneNumber && styles.inputError]}
                onPress={() => setPickerVisible(true)}
                accessibilityLabel="Select country code"
              >
                <Text style={styles.countryFlag}>{selectedCountry.flag}</Text>
                <Text style={styles.countryCode}>{countryCode}</Text>
                <Text style={styles.chevron}>▾</Text>
              </Pressable>
              <Controller
                control={control}
                name="phoneNumber"
                render={({ field }) => (
                  <TextInput
                    style={[styles.phoneInput, errors.phoneNumber && styles.inputError]}
                    value={field.value}
                    onChangeText={field.onChange}
                    onBlur={field.onBlur}
                    keyboardType="phone-pad"
                    autoComplete="tel-national"
                    accessibilityLabel="Phone number"
                    placeholderTextColor={colors.stone}
                    placeholder="9876543210"
                  />
                )}
              />
            </View>
            {errors.phoneNumber && (
              <Text style={styles.fieldError}>{errors.phoneNumber.message}</Text>
            )}
          </View>

          {/* Email */}
          <View>
            <Text style={styles.label}>Email address</Text>
            <Controller
              control={control}
              name="email"
              render={({ field }) => (
                <TextInput
                  style={[styles.input, errors.email && styles.inputError]}
                  value={field.value}
                  onChangeText={field.onChange}
                  onBlur={field.onBlur}
                  autoCapitalize="none"
                  keyboardType="email-address"
                  autoComplete="email"
                  accessibilityLabel="Email address"
                  placeholderTextColor={colors.stone}
                  placeholder="priya@example.com"
                />
              )}
            />
            {errors.email && <Text style={styles.fieldError}>{errors.email.message}</Text>}
          </View>

          {/* Password */}
          <View>
            <Text style={styles.label}>Password</Text>
            <Controller
              control={control}
              name="password"
              render={({ field }) => (
                <TextInput
                  style={[styles.input, errors.password && styles.inputError]}
                  value={field.value}
                  onChangeText={field.onChange}
                  onBlur={field.onBlur}
                  autoCapitalize="none"
                  autoComplete="password-new"
                  secureTextEntry
                  accessibilityLabel="Password"
                  placeholderTextColor={colors.stone}
                  placeholder="8+ characters"
                />
              )}
            />
            {errors.password && <Text style={styles.fieldError}>{errors.password.message}</Text>}
          </View>

          {apiError && <Text style={styles.apiError}>{apiError}</Text>}

          <Pressable
            style={[styles.button, isSubmitting && styles.buttonDisabled]}
            onPress={handleSubmit(onSubmit)}
            disabled={isSubmitting}
            accessibilityLabel="Create account"
          >
            {isSubmitting ? (
              <ActivityIndicator color={colors.ivory} />
            ) : (
              <Text style={styles.buttonText}>Create account</Text>
            )}
          </Pressable>

          <Link href="/(auth)/login" style={styles.link}>
            Already have an account? Sign in
          </Link>
        </View>
      </ScrollView>

      {/* Country code picker modal */}
      <Modal
        visible={pickerVisible}
        transparent
        animationType="slide"
        onRequestClose={() => setPickerVisible(false)}
      >
        <Pressable style={styles.modalOverlay} onPress={() => setPickerVisible(false)}>
          <View style={styles.modalSheet}>
            <Text style={styles.modalTitle}>Select country code</Text>
            {COUNTRY_CODES.map(item => (
              <Pressable
                key={item.code}
                style={[
                  styles.modalOption,
                  item.code === countryCode && styles.modalOptionSelected,
                ]}
                onPress={() => {
                  setCountryCode(item.code);
                  setPickerVisible(false);
                }}
                accessibilityLabel={`${item.name} ${item.code}`}
              >
                <Text style={styles.modalFlag}>{item.flag}</Text>
                <Text style={styles.modalOptionName}>{item.name}</Text>
                <Text style={styles.modalOptionCode}>{item.code}</Text>
              </Pressable>
            ))}
          </View>
        </Pressable>
      </Modal>
    </KeyboardAvoidingView>
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
  wordmark: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h1,
    color: colors.forest,
    fontWeight: '500',
  },
  subtitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.stone,
    marginTop: spacing[1],
    marginBottom: spacing[8],
  },
  form: { gap: spacing[3] },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    fontWeight: '500',
    marginBottom: spacing[1],
  },
  input: {
    borderWidth: 1,
    borderColor: colors.stone,
    borderRadius: 8,
    padding: spacing[3],
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    backgroundColor: colors.white,
  },
  inputError: { borderColor: colors.alert },
  fieldError: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.alert,
    marginTop: spacing[1],
  },
  phoneRow: {
    flexDirection: 'row',
    gap: spacing[2],
  },
  countryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[1],
    borderWidth: 1,
    borderColor: colors.stone,
    borderRadius: 8,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[3],
    backgroundColor: colors.white,
  },
  countryFlag: { fontSize: 18 },
  countryCode: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    fontWeight: '500',
  },
  chevron: {
    fontFamily: fontFamily.body,
    fontSize: 11,
    color: colors.stone,
    marginLeft: spacing[1],
  },
  phoneInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.stone,
    borderRadius: 8,
    padding: spacing[3],
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
    backgroundColor: colors.white,
  },
  apiError: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.alert,
    textAlign: 'center',
  },
  button: {
    backgroundColor: colors.forest,
    borderRadius: 8,
    paddingVertical: spacing[3],
    alignItems: 'center',
    marginTop: spacing[4],
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ivory,
    fontWeight: '600',
  },
  link: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.jade,
    textAlign: 'center',
    marginTop: spacing[4],
  },
  // Modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'flex-end',
  },
  modalSheet: {
    backgroundColor: colors.white,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[4],
    paddingBottom: spacing[10],
  },
  modalTitle: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.bodyLg,
    color: colors.ink,
    fontWeight: '600',
    marginBottom: spacing[4],
  },
  modalOption: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing[3],
    borderRadius: 8,
    paddingHorizontal: spacing[2],
  },
  modalOptionSelected: {
    backgroundColor: colors.ivory,
  },
  modalFlag: { fontSize: 22, width: 36 },
  modalOptionName: {
    flex: 1,
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ink,
  },
  modalOptionCode: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    fontWeight: '500',
  },
});
