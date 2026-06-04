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
import { z } from 'zod';
import { sendOtpApi, verifyOtpApi } from '../../lib/api/auth';
import { ApiError } from '../../lib/api/client';
import { useAuth } from '../../lib/auth/context';
import { colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

const schema = z.object({
  otp: z.string().length(6, 'Enter the 6-digit code'),
});
type FormValues = z.infer<typeof schema>;

export default function VerifyOtpScreen() {
  const router = useRouter();
  const { phone } = useLocalSearchParams<{ phone: string }>();
  const { signIn } = useAuth();
  const [apiError, setApiError] = useState<string | null>(null);
  const [resending, setResending] = useState(false);
  const [resent, setResent] = useState(false);

  const { control, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { otp: '' },
  });

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

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.container}>
        <Text style={styles.title}>Verify your number</Text>
        <Text style={styles.body}>
          We sent a 6-digit code to {phone}. Enter it below.
        </Text>

        <Controller
          control={control}
          name="otp"
          render={({ field }) => (
            <TextInput
              style={[styles.otpInput, errors.otp && styles.inputError]}
              value={field.value}
              onChangeText={field.onChange}
              onBlur={field.onBlur}
              keyboardType="number-pad"
              maxLength={6}
              autoFocus
              accessibilityLabel="6-digit verification code"
              placeholderTextColor={colors.stone}
              placeholder="123456"
              textAlign="center"
            />
          )}
        />
        {errors.otp && <Text style={styles.fieldError}>{errors.otp.message}</Text>}
        {apiError && <Text style={styles.apiError}>{apiError}</Text>}

        <Pressable
          style={[styles.button, isSubmitting && styles.buttonDisabled]}
          onPress={handleSubmit(onSubmit)}
          disabled={isSubmitting}
          accessibilityLabel="Verify code"
        >
          {isSubmitting ? (
            <ActivityIndicator color={colors.ivory} />
          ) : (
            <Text style={styles.buttonText}>Verify</Text>
          )}
        </Pressable>

        <Pressable
          onPress={handleResend}
          disabled={resending}
          accessibilityLabel="Resend verification code"
          style={styles.resendContainer}
        >
          <Text style={styles.resendText}>
            {resent ? 'Code sent again' : resending ? 'Sending…' : "Didn't receive it? Resend"}
          </Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.ivory },
  container: {
    flex: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[16],
  },
  title: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    color: colors.forest,
    fontWeight: '500',
    marginBottom: spacing[3],
  },
  body: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    marginBottom: spacing[8],
    lineHeight: 22,
  },
  otpInput: {
    borderWidth: 1,
    borderColor: colors.stone,
    borderRadius: 8,
    padding: spacing[4],
    fontFamily: fontFamily.body,
    fontSize: fontSize.h2,
    color: colors.ink,
    backgroundColor: colors.white,
    letterSpacing: 8,
  },
  inputError: { borderColor: colors.alert },
  fieldError: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.alert,
    marginTop: spacing[1],
  },
  apiError: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.alert,
    marginTop: spacing[3],
    textAlign: 'center',
  },
  button: {
    backgroundColor: colors.forest,
    borderRadius: 8,
    paddingVertical: spacing[3],
    alignItems: 'center',
    marginTop: spacing[6],
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.ivory,
    fontWeight: '600',
  },
  resendContainer: { marginTop: spacing[4], alignItems: 'center' },
  resendText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.jade,
  },
});
