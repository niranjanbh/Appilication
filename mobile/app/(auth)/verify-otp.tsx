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
  useColorScheme,
  View,
} from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { z } from 'zod';
import { sendOtpApi, verifyOtpApi } from '../../lib/api/auth';
import { ApiError } from '../../lib/api/client';
import { useAuth } from '../../lib/auth/context';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

const schema = z.object({
  otp: z.string().length(6, 'Enter the 6-digit code'),
});
type FormValues = z.infer<typeof schema>;

export default function VerifyOtpScreen() {
  const router  = useRouter();
  const { phone } = useLocalSearchParams<{ phone: string }>();
  const { signIn }  = useAuth();
  const isDark  = useColorScheme() === 'dark';
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

  const btnScale = useSharedValue(1);
  const btnAnim  = useAnimatedStyle(() => ({ transform: [{ scale: btnScale.value }] }));

  const outerBg  = isDark ? colors.midnight    : colors.navyDeep;
  const cardBg   = isDark ? colors.nightSurface : colors.white;
  const textPri  = isDark ? colors.white        : colors.navyDeep;
  const textSub  = isDark ? colors.slateText    : colors.coolGray;
  const inputBg  = isDark ? colors.nightElev    : colors.skyMist;
  const inputBdr = isDark ? 'rgba(255,255,255,0.10)' : colors.borderLight;

  return (
    <KeyboardAvoidingView
      style={[styles.flex, { backgroundColor: outerBg }]}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.container}>

        {/* Logo area */}
        <View style={styles.logoArea}>
          <Text style={styles.wordmark}>Kyros</Text>
        </View>

        {/* Verify card */}
        <View style={[styles.card, { backgroundColor: cardBg }]}>
          <View style={styles.iconWrap}>
            <Text style={styles.phoneIcon}>📱</Text>
          </View>

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
                  { backgroundColor: inputBg, borderColor: errors.otp ? colors.criticalRed : inputBdr, color: textPri },
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

          <Animated.View style={btnAnim}>
            <Pressable
              style={[styles.button, isSubmitting && styles.buttonBusy]}
              onPress={handleSubmit(onSubmit)}
              onPressIn={() => { btnScale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
              onPressOut={() => { btnScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
              disabled={isSubmitting}
              accessibilityLabel="Verify code"
            >
              {isSubmitting ? (
                <ActivityIndicator color={colors.white} size="small" />
              ) : (
                <Text style={styles.buttonText}>Verify</Text>
              )}
            </Pressable>
          </Animated.View>

          <Pressable
            onPress={handleResend}
            disabled={resending}
            accessibilityLabel="Resend verification code"
            style={styles.resendBtn}
          >
            <Text style={[styles.resendText, { color: resent ? colors.successGreen : textSub }]}>
              {resent ? '✓ Code sent again' : resending ? 'Sending…' : "Didn't receive it? Resend"}
            </Text>
          </Pressable>
        </View>

      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flex: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[12],
    paddingBottom: spacing[8],
    justifyContent: 'center',
  },

  logoArea: { alignItems: 'center', marginBottom: spacing[6] },
  wordmark: {
    fontFamily: fontFamily.display,
    fontSize: 40,
    color: colors.white,
    fontWeight: '500',
  },

  card: {
    borderRadius: borderRadius.xxl,
    padding: spacing[6],
    gap: spacing[4],
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 24 },
    shadowOpacity: 0.22,
    shadowRadius: 40,
    elevation: 16,
  },

  iconWrap: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: colors.iceBlue,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing[2],
  },
  phoneIcon: { fontSize: 30 },

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
    color: colors.criticalRed,
    textAlign: 'center',
  },
  apiError: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: colors.criticalRed,
    textAlign: 'center',
  },

  button: {
    width: '100%',
    height: 56,
    backgroundColor: colors.navyDeep,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: colors.navyDeep,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.30,
    shadowRadius: 16,
    elevation: 6,
  },
  buttonBusy: { opacity: 0.70 },
  buttonText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    color: colors.white,
    fontWeight: '600',
  },

  resendBtn: { paddingVertical: spacing[2] },
  resendText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    textAlign: 'center',
  },
});
