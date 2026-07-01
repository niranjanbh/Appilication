import { zodResolver } from '@hookform/resolvers/zod';
import { useLocalSearchParams, useRouter } from 'expo-router';
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
import { useThemePreference } from '../../lib/theme-context';
import { z } from 'zod';
import { sendOtpApi, verifyOtpApi } from '../../lib/api/auth';
import { ApiError } from '../../lib/api/client';
import { useAuth } from '../../lib/auth/context';
import { AuthBackdrop } from '../../components/ui/AuthBackdrop';
import { GlassCard } from '../../components/ui/GlassCard';
import { HapticPressable } from '../../components/ui/HapticPressable';
import { IconChip } from '../../components/ui/IconChip';
import { borderRadius, colors, fontFamily, fontSize, spacing , withAlpha } from '../../lib/design-tokens';

const schema = z.object({
  otp: z.string().length(6, 'Enter the 6-digit code'),
});
type FormValues = z.infer<typeof schema>;

export default function VerifyOtpScreen() {
  const router  = useRouter();
  const { phone } = useLocalSearchParams<{ phone: string }>();
  const { signIn }  = useAuth();
  const isDark  = useThemePreference().colorScheme === 'dark';
  const [apiError, setApiError] = useState<string | null>(null);
  const [resending, setResending] = useState(false);
  const [resent, setResent]       = useState(false);

  const { control, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { otp: '' },
  });

  // Preserve 100% of existing submit + resend logic
  const onSubmit = async ({ otp }: FormValues) => {
    setApiError(null);
    try {
      const tokens = await verifyOtpApi({ phone: phone ?? '', otp });
      await signIn(tokens);
      router.replace('/');
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setApiError('Incorrect or expired code. Please try again.');
      } else {
        setApiError('Something went wrong. Please try again.');
      }
    }
  };

  const handleResend = async () => {
    setResending(true);
    setApiError(null);
    try {
      await sendOtpApi(phone ?? '');
      setResent(true);
    } catch {
      setApiError('Could not resend. Please wait a moment and try again.');
    } finally {
      setResending(false);
    }
  };

  const textPri  = isDark ? colors.ivoryText        : colors.ink;
  const textSub  = isDark ? colors.stoneDim    : colors.stone;
  const inputBg  = isDark ? colors.forestSurfaceRaised    : colors.ivory;
  const inputBdr = isDark ? 'rgba(255,255,255,0.10)' : colors.borderLight;

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <AuthBackdrop />
      <View style={styles.container}>

        {/* Logo area */}
        <View style={styles.logoArea}>
          <Text style={[styles.wordmark, { color: isDark ? colors.ivoryText : colors.forest }]}>Baseline</Text>
        </View>

        {/* Verify card — frosted glass over the gradient */}
        <GlassCard strong unpadded style={styles.cardShadow}>
          <View style={styles.cardInner}>
          <IconChip icon="phone-portrait-outline" tint="blue" size={64} />

          <Text style={[styles.title, { color: textPri }]}>Verify your number</Text>
          <Text style={[styles.body, { color: textSub }]}>
            We sent a 6-digit code to{' '}
            <Text style={[styles.phoneHighlight, { color: textPri }]}>{phone}</Text>
          </Text>

          <Controller
            control={control}
            name="otp"
            render={({ field }) => (
              <TextInput
                style={[
                  styles.otpInput,
                  { backgroundColor: inputBg, borderColor: errors.otp ? colors.alert : inputBdr, color: textPri },
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
          {errors.otp   && <Text style={styles.fieldError}>{errors.otp.message}</Text>}
          {apiError     && <Text style={styles.apiError}>{apiError}</Text>}

          <HapticPressable
            haptic="medium"
            containerStyle={styles.fullWidth}
            style={[styles.button, isSubmitting && styles.buttonBusy]}
            onPress={handleSubmit(onSubmit)}
            disabled={isSubmitting}
            accessibilityLabel="Verify code"
          >
            {isSubmitting ? (
              <ActivityIndicator color={colors.white} size="small" />
            ) : (
              <Text style={styles.buttonText}>Verify</Text>
            )}
          </HapticPressable>

          <Pressable
            onPress={handleResend}
            disabled={resending}
            accessibilityLabel="Resend verification code"
            style={styles.resendBtn}
          >
            <Text style={[styles.resendText, { color: resent ? colors.jade : textSub }]}>
              {resent ? '✓ Code sent again' : resending ? 'Sending…' : "Didn't receive it? Resend"}
            </Text>
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

  cardShadow: {
    boxShadow: '0 24px 40px rgba(0,0,0,0.22)',
  },
  cardInner: {
    padding: spacing[6],
    gap: spacing[4],
    alignItems: 'center',
  },
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
  buttonBusy: { opacity: 0.70 },
  buttonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.ivoryText,
    fontWeight: '600',
  },

  resendBtn: { paddingVertical: spacing[2] },
  resendText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    textAlign: 'center',
  },
});
