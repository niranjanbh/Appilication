import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { z } from 'zod';
import { useThemePreference } from '../lib/theme-context';
import {
  confirmPhoneCaptureApi,
  requestPhoneCaptureApi,
} from '../lib/api/auth';
import { ApiError } from '../lib/api/client';
import { useAuth } from '../lib/auth/context';
import { AuthBackdrop } from '../components/ui/AuthBackdrop';
import { GlassCard } from '../components/ui/GlassCard';
import { HapticPressable } from '../components/ui/HapticPressable';
import { IconChip } from '../components/ui/IconChip';
import { borderRadius, colors, fontFamily, fontSize, spacing, withAlpha } from '../lib/design-tokens';

const phoneSchema = z.object({
  phone: z
    .string()
    .regex(/^\+[1-9]\d{7,14}$/, 'Enter a valid number with country code, e.g. +919876543210'),
});
type PhoneValues = z.infer<typeof phoneSchema>;

const otpSchema = z.object({
  otp: z.string().length(6, 'Enter the 6-digit code'),
});
type OtpValues = z.infer<typeof otpSchema>;

/**
 * Mandatory mobile-number capture. Reached when a signed-in patient has no
 * verified phone (Google sign-in carries none). The number is required for
 * appointment, payment, and clinical communication, so this screen has no skip
 * and no back — the only way forward is to provide a number, or sign out to use
 * a different account. When admin signup-OTP is enabled the number is verified
 * via OTP; otherwise it is saved directly.
 */
export default function AddPhoneScreen() {
  const router = useRouter();
  const { refreshUser, signOut } = useAuth();
  const isDark = useThemePreference().colorScheme === 'dark';

  const [stage, setStage] = useState<'phone' | 'otp'>('phone');
  const [phone, setPhone] = useState('');
  const [apiError, setApiError] = useState<string | null>(null);
  const [resending, setResending] = useState(false);
  const [resent, setResent] = useState(false);

  const phoneForm = useForm<PhoneValues>({
    resolver: zodResolver(phoneSchema),
    defaultValues: { phone: '+91' },
  });
  const otpForm = useForm<OtpValues>({
    resolver: zodResolver(otpSchema),
    defaultValues: { otp: '' },
  });

  const finish = async () => {
    // Refresh the cached user so the mandatory-phone gate releases, then route
    // through '/' which decides onboarding vs home.
    await refreshUser();
    router.replace('/');
  };

  const onSubmitPhone = async ({ phone: value }: PhoneValues) => {
    setApiError(null);
    try {
      const result = await requestPhoneCaptureApi(value);
      setPhone(value);
      if (result.otp_required) {
        setStage('otp');
      } else {
        await finish();
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setApiError('That number is already linked to another account.');
      } else {
        setApiError('Could not save your number. Please try again.');
      }
    }
  };

  const onSubmitOtp = async ({ otp }: OtpValues) => {
    setApiError(null);
    try {
      await confirmPhoneCaptureApi({ phone, otp });
      await finish();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setApiError('Incorrect or expired code. Please try again.');
      } else if (err instanceof ApiError && err.status === 409) {
        setApiError('That number is already linked to another account.');
      } else {
        setApiError('Something went wrong. Please try again.');
      }
    }
  };

  const handleResend = async () => {
    setResending(true);
    setApiError(null);
    try {
      await requestPhoneCaptureApi(phone);
      setResent(true);
    } catch {
      setApiError('Could not resend. Please wait a moment and try again.');
    } finally {
      setResending(false);
    }
  };

  const textPri = isDark ? colors.ivoryText : colors.ink;
  const textSub = isDark ? colors.stoneDim : colors.stone;
  const inputBg = isDark ? colors.forestSurfaceRaised : colors.ivory;
  const inputBdr = isDark ? 'rgba(255,255,255,0.10)' : colors.borderLight;

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <AuthBackdrop />
      <View style={styles.container}>
        <View style={styles.logoArea}>
          <Text style={[styles.wordmark, { color: isDark ? colors.ivoryText : colors.forest }]}>Kyros</Text>
        </View>

        <GlassCard strong unpadded style={styles.cardShadow}>
          <View style={styles.cardInner}>
            <IconChip icon="phone-portrait-outline" tint="blue" size={64} />

            {stage === 'phone' ? (
              <>
                <Text style={[styles.title, { color: textPri }]}>Add your mobile number</Text>
                <Text style={[styles.body, { color: textSub }]}>
                  We need a mobile number to reach you about appointments, payments, and
                  your care. This step is required to continue.
                </Text>

                <Controller
                  control={phoneForm.control}
                  name="phone"
                  render={({ field }) => (
                    <TextInput
                      style={[
                        styles.textInput,
                        {
                          backgroundColor: inputBg,
                          borderColor: phoneForm.formState.errors.phone ? colors.alert : inputBdr,
                          color: textPri,
                        },
                      ]}
                      value={field.value}
                      onChangeText={field.onChange}
                      onBlur={field.onBlur}
                      keyboardType="phone-pad"
                      autoFocus
                      accessibilityLabel="Mobile number with country code"
                      placeholderTextColor={textSub}
                      placeholder="+919876543210"
                      textAlign="center"
                    />
                  )}
                />
                {phoneForm.formState.errors.phone && (
                  <Text style={styles.fieldError}>{phoneForm.formState.errors.phone.message}</Text>
                )}
                {apiError && <Text style={styles.apiError}>{apiError}</Text>}

                <HapticPressable
                  haptic="medium"
                  containerStyle={styles.fullWidth}
                  style={[styles.button, phoneForm.formState.isSubmitting && styles.buttonBusy]}
                  onPress={phoneForm.handleSubmit(onSubmitPhone)}
                  disabled={phoneForm.formState.isSubmitting}
                  accessibilityLabel="Continue"
                >
                  {phoneForm.formState.isSubmitting ? (
                    <ActivityIndicator color={colors.white} size="small" />
                  ) : (
                    <Text style={styles.buttonText}>Continue</Text>
                  )}
                </HapticPressable>
              </>
            ) : (
              <>
                <Text style={[styles.title, { color: textPri }]}>Verify your number</Text>
                <Text style={[styles.body, { color: textSub }]}>
                  We sent a 6-digit code to{' '}
                  <Text style={[styles.phoneHighlight, { color: textPri }]}>{phone}</Text>
                </Text>

                <Controller
                  control={otpForm.control}
                  name="otp"
                  render={({ field }) => (
                    <TextInput
                      style={[
                        styles.otpInput,
                        {
                          backgroundColor: inputBg,
                          borderColor: otpForm.formState.errors.otp ? colors.alert : inputBdr,
                          color: textPri,
                        },
                      ]}
                      value={field.value}
                      onChangeText={field.onChange}
                      onBlur={field.onBlur}
                      keyboardType="number-pad"
                      maxLength={6}
                      autoFocus
                      accessibilityLabel="6-digit verification code"
                      placeholderTextColor={textSub}
                      placeholder="••••••"
                      textAlign="center"
                    />
                  )}
                />
                {otpForm.formState.errors.otp && (
                  <Text style={styles.fieldError}>{otpForm.formState.errors.otp.message}</Text>
                )}
                {apiError && <Text style={styles.apiError}>{apiError}</Text>}

                <HapticPressable
                  haptic="medium"
                  containerStyle={styles.fullWidth}
                  style={[styles.button, otpForm.formState.isSubmitting && styles.buttonBusy]}
                  onPress={otpForm.handleSubmit(onSubmitOtp)}
                  disabled={otpForm.formState.isSubmitting}
                  accessibilityLabel="Verify code"
                >
                  {otpForm.formState.isSubmitting ? (
                    <ActivityIndicator color={colors.white} size="small" />
                  ) : (
                    <Text style={styles.buttonText}>Verify</Text>
                  )}
                </HapticPressable>

                <Pressable
                  onPress={handleResend}
                  disabled={resending}
                  accessibilityLabel="Resend verification code"
                  style={styles.linkBtn}
                >
                  <Text style={[styles.linkText, { color: resent ? colors.jade : textSub }]}>
                    {resent ? '✓ Code sent again' : resending ? 'Sending…' : "Didn't receive it? Resend"}
                  </Text>
                </Pressable>

                <Pressable
                  onPress={() => {
                    setStage('phone');
                    setApiError(null);
                    setResent(false);
                  }}
                  accessibilityLabel="Change number"
                  style={styles.linkBtn}
                >
                  <Text style={[styles.linkText, { color: textSub }]}>Change number</Text>
                </Pressable>
              </>
            )}

            <Pressable
              onPress={() => void signOut()}
              accessibilityLabel="Use a different account"
              style={styles.linkBtn}
            >
              <Text style={[styles.linkText, { color: textSub }]}>Use a different account</Text>
            </Pressable>
          </View>
        </GlassCard>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, overflow: 'hidden' },
  container: {
    flex: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[12],
    paddingBottom: spacing[8],
    justifyContent: 'center',
    maxWidth: 480,
    alignSelf: 'center',
    width: '100%',
  },

  logoArea: { alignItems: 'center', marginBottom: spacing[6] },
  wordmark: {
    fontFamily: fontFamily.display,
    fontSize: 40,
    color: colors.ivoryText,
    fontWeight: '500',
  },

  cardShadow: { boxShadow: '0 24px 40px rgba(0,0,0,0.22)' },
  cardInner: { padding: spacing[6], gap: spacing[4], alignItems: 'center' },
  fullWidth: { width: '100%' },

  title: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.h3,
    fontWeight: '700',
    textAlign: 'center',
  },
  body: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    textAlign: 'center',
    lineHeight: 22,
  },
  phoneHighlight: { fontWeight: '600' },

  textInput: {
    width: '100%',
    borderWidth: 1,
    borderRadius: borderRadius.xl,
    paddingVertical: spacing[4],
    fontFamily: fontFamily.body,
    fontSize: 20,
    fontWeight: '600',
  },
  otpInput: {
    width: '100%',
    borderWidth: 1,
    borderRadius: borderRadius.xl,
    paddingVertical: spacing[4],
    fontFamily: fontFamily.body,
    fontSize: 28,
    fontWeight: '700',
    letterSpacing: 12,
  },

  fieldError: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.alert,
    textAlign: 'center',
  },
  apiError: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: colors.alert,
    textAlign: 'center',
  },

  button: {
    width: '100%',
    height: 56,
    backgroundColor: colors.forest,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: `0 8px 16px ${withAlpha(colors.forest, 0.30)}`,
  },
  buttonBusy: { opacity: 0.7 },
  buttonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.ivoryText,
    fontWeight: '600',
  },

  linkBtn: { paddingVertical: spacing[2] },
  linkText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    textAlign: 'center',
  },
});
