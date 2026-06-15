import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { z } from 'zod';
import { requestPasswordResetApi } from '../../lib/api/auth';
import { useThemePreference } from '../../lib/theme-context';
import { AuthBackdrop } from '../../components/ui/AuthBackdrop';
import { GlassCard } from '../../components/ui/GlassCard';
import { HapticPressable } from '../../components/ui/HapticPressable';
import { IconChip } from '../../components/ui/IconChip';
import { borderRadius, colors, fontFamily, fontSize, spacing, withAlpha } from '../../lib/design-tokens';

const schema = z.object({
  identifier: z.string().min(1, 'Enter your email or phone'),
});
type FormValues = z.infer<typeof schema>;

export default function ForgotPasswordScreen() {
  const router = useRouter();
  const isDark = useThemePreference().colorScheme === 'dark';
  const [apiError, setApiError] = useState<string | null>(null);

  const { control, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { identifier: '' },
  });

  const onSubmit = async ({ identifier }: FormValues) => {
    setApiError(null);
    try {
      const result = await requestPasswordResetApi(identifier.trim());
      // Response is deliberately generic (no account enumeration); always advance.
      router.push({
        pathname: '/(auth)/reset-password',
        params: { identifier: identifier.trim(), otp_hint: result.otp_hint ?? '' },
      });
    } catch {
      setApiError('Something went wrong. Please try again.');
    }
  };

  const textPri = isDark ? colors.white : colors.navyDeep;
  const textSub = isDark ? colors.slateText : colors.coolGray;
  const inputBg = isDark ? colors.nightElev : colors.skyMist;
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
            <IconChip icon="lock-closed-outline" tint="blue" size={64} />
            <Text style={[styles.title, { color: textPri }]}>Reset your password</Text>
            <Text style={[styles.body, { color: textSub }]}>
              Enter your email or phone. If an account exists, we'll send a verification code.
            </Text>

            <Controller
              control={control}
              name="identifier"
              render={({ field }) => (
                <TextInput
                  style={[
                    styles.input,
                    { backgroundColor: inputBg, borderColor: errors.identifier ? colors.criticalRed : inputBdr, color: textPri },
                  ]}
                  value={field.value}
                  onChangeText={field.onChange}
                  onBlur={field.onBlur}
                  autoCapitalize="none"
                  keyboardType="email-address"
                  accessibilityLabel="Email or phone"
                  placeholderTextColor={textSub}
                  placeholder="you@example.com or +91…"
                />
              )}
            />
            {errors.identifier && <Text style={styles.fieldError}>{errors.identifier.message}</Text>}
            {apiError && <Text style={styles.apiError}>{apiError}</Text>}

            <HapticPressable
              haptic="medium"
              containerStyle={styles.fullWidth}
              style={[styles.button, isSubmitting && styles.buttonBusy]}
              onPress={handleSubmit(onSubmit)}
              disabled={isSubmitting}
              accessibilityLabel="Send reset code"
            >
              {isSubmitting ? (
                <ActivityIndicator color={colors.white} size="small" />
              ) : (
                <Text style={styles.buttonText}>Send code</Text>
              )}
            </HapticPressable>

            <HapticPressable
              haptic="light"
              containerStyle={styles.fullWidth}
              style={styles.backBtn}
              onPress={() => router.back()}
              accessibilityLabel="Back to sign in"
            >
              <Text style={[styles.backText, { color: textSub }]}>Back to sign in</Text>
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
  input: {
    width: '100%',
    borderWidth: 1,
    borderRadius: borderRadius.xl,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[4],
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
  },
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
  backBtn: { paddingVertical: spacing[2] },
  backText: { fontFamily: fontFamily.body, fontSize: fontSize.sm, textAlign: 'center' },
});
