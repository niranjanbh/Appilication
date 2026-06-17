import { zodResolver } from '@hookform/resolvers/zod';
import { Ionicons } from '@expo/vector-icons';
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
import { confirmPasswordResetApi } from '../../lib/api/auth';
import { ApiError } from '../../lib/api/client';
import { useThemePreference } from '../../lib/theme-context';
import { AuthBackdrop } from '../../components/ui/AuthBackdrop';
import { GlassCard } from '../../components/ui/GlassCard';
import { HapticPressable } from '../../components/ui/HapticPressable';
import { IconChip } from '../../components/ui/IconChip';
import { borderRadius, colors, fontFamily, fontSize, spacing, withAlpha } from '../../lib/design-tokens';

const schema = z.object({
  otp: z.string().length(6, 'Enter the 6-digit code'),
  new_password: z.string().min(8, 'At least 8 characters'),
});
type FormValues = z.infer<typeof schema>;

export default function ResetPasswordScreen() {
  const router = useRouter();
  const { identifier, otp_hint } = useLocalSearchParams<{ identifier: string; otp_hint?: string }>();
  const isDark = useThemePreference().colorScheme === 'dark';
  const [apiError, setApiError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  const { control, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { otp: typeof otp_hint === 'string' ? otp_hint : '', new_password: '' },
  });

  const onSubmit = async ({ otp, new_password }: FormValues) => {
    setApiError(null);
    try {
      await confirmPasswordResetApi({ identifier: identifier ?? '', otp, new_password });
      router.replace('/(auth)/login');
    } catch (err) {
      if (err instanceof ApiError && (err.status === 422 || err.status === 429)) {
        setApiError('Incorrect or expired code. Please request a new one.');
      } else {
        setApiError('Something went wrong. Please try again.');
      }
    }
  };

  const textPri = isDark ? colors.white : colors.navyDeep;
  const textSub = isDark ? colors.stoneDim : colors.coolGray;
  const inputBg = isDark ? colors.forestSurfaceRaised : colors.skyMist;
  const inputBdr = isDark ? 'rgba(255,255,255,0.10)' : colors.borderLight;

  return (
    <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
      <AuthBackdrop />
      <View style={styles.container}>
        <View style={styles.logoArea}>
          <Text style={styles.wordmark}>Kyros</Text>
        </View>

        <GlassCard strong unpadded style={styles.cardShadow}>
          <View style={styles.cardInner}>
            <IconChip icon="key-outline" tint="blue" size={64} />
            <Text style={[styles.title, { color: textPri }]}>Enter your code</Text>
            <Text style={[styles.body, { color: textSub }]}>
              We sent a 6-digit code to your registered contact. Enter it with a new password.
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
                  accessibilityLabel="6-digit reset code"
                  placeholderTextColor={textSub}
                  placeholder="••••••"
                  textAlign="center"
                />
              )}
            />
            {errors.otp && <Text style={styles.fieldError}>{errors.otp.message}</Text>}

            <View style={[styles.passwordWrap, { backgroundColor: inputBg, borderColor: errors.new_password ? colors.criticalRed : inputBdr }]}>
              <Controller
                control={control}
                name="new_password"
                render={({ field }) => (
                  <TextInput
                    style={[styles.passwordInput, { color: textPri }]}
                    value={field.value}
                    onChangeText={field.onChange}
                    onBlur={field.onBlur}
                    secureTextEntry={!showPassword}
                    autoCapitalize="none"
                    accessibilityLabel="New password"
                    placeholderTextColor={textSub}
                    placeholder="New password"
                  />
                )}
              />
              <Pressable
                onPress={() => setShowPassword((v) => !v)}
                accessibilityLabel={showPassword ? 'Hide password' : 'Show password'}
                hitSlop={8}
              >
                <Ionicons name={showPassword ? 'eye-off-outline' : 'eye-outline'} size={20} color={textSub} />
              </Pressable>
            </View>
            {errors.new_password && <Text style={styles.fieldError}>{errors.new_password.message}</Text>}
            {apiError && <Text style={styles.apiError}>{apiError}</Text>}

            <HapticPressable
              haptic="medium"
              containerStyle={styles.fullWidth}
              style={[styles.button, isSubmitting && styles.buttonBusy]}
              onPress={handleSubmit(onSubmit)}
              disabled={isSubmitting}
              accessibilityLabel="Set new password"
            >
              {isSubmitting ? (
                <ActivityIndicator color={colors.white} size="small" />
              ) : (
                <Text style={styles.buttonText}>Set new password</Text>
              )}
            </HapticPressable>
          </View>
        </GlassCard>
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
  wordmark: { fontFamily: fontFamily.display, fontSize: 40, color: colors.white, fontWeight: '500' },
  cardShadow: { boxShadow: '0 24px 40px rgba(0,0,0,0.22)' },
  cardInner: { padding: spacing[6], gap: spacing[4], alignItems: 'center' },
  fullWidth: { width: '100%' },
  title: { fontFamily: fontFamily.body, fontSize: fontSize.h3, fontWeight: '700', textAlign: 'center' },
  body: { fontFamily: fontFamily.body, fontSize: fontSize.body, textAlign: 'center', lineHeight: 22 },
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
  passwordWrap: {
    width: '100%',
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: borderRadius.xl,
    borderWidth: 1,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[4],
    gap: spacing[2],
  },
  passwordInput: { flex: 1, fontFamily: fontFamily.body, fontSize: fontSize.body, padding: 0 },
  fieldError: { fontFamily: fontFamily.body, fontSize: fontSize.caption, color: colors.criticalRed, textAlign: 'center' },
  apiError: { fontFamily: fontFamily.body, fontSize: fontSize.sm, color: colors.criticalRed, textAlign: 'center' },
  button: {
    width: '100%',
    height: 56,
    backgroundColor: colors.navyDeep,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: `0 8px 16px ${withAlpha(colors.navyDeep, 0.30)}`,
  },
  buttonBusy: { opacity: 0.7 },
  buttonText: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, color: colors.white, fontWeight: '600' },
});
