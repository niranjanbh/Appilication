import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useRouter } from 'expo-router';
import { useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  useColorScheme,
  View,
} from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { z } from 'zod';
import { loginApi } from '../../lib/api/auth';
import { ApiError } from '../../lib/api/client';
import { useAuth } from '../../lib/auth/context';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

const schema = z.object({
  email_or_phone: z.string().min(1, 'Required'),
  password: z.string().min(1, 'Required'),
});
type FormValues = z.infer<typeof schema>;

// ─── Input field ──────────────────────────────────────────────────────────────

interface FieldProps {
  label: string;
  error?: string;
  inputBg: string;
  inputBdr: string;
  textColor: string;
  children: React.ReactNode;
}

function Field({ label, error, inputBg, inputBdr, textColor, children }: FieldProps) {
  return (
    <View style={field.wrap}>
      <Text style={[field.label, { color: textColor }]}>{label}</Text>
      <View style={[field.inputWrap, { backgroundColor: inputBg, borderColor: error ? colors.criticalRed : inputBdr }]}>
        {children}
      </View>
      {error ? <Text style={field.error}>{error}</Text> : null}
    </View>
  );
}

const field = StyleSheet.create({
  wrap:     { gap: spacing[1] },
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
  error: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.criticalRed,
    marginTop: 2,
  },
});

// ─── Main screen ──────────────────────────────────────────────────────────────

export default function LoginScreen() {
  const router    = useRouter();
  const { signIn } = useAuth();
  const [apiError, setApiError] = useState<string | null>(null);
  const isDark = useColorScheme() === 'dark';

  const { control, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email_or_phone: '', password: '' },
  });

  // Preserve 100% of the existing submit logic
  const onSubmit = async (values: FormValues) => {
    setApiError(null);
    try {
      const tokens = await loginApi(values);
      await signIn(tokens);
      router.replace('/');
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setApiError('Incorrect credentials. Please try again.');
      } else if (err instanceof ApiError && err.status === 403) {
        const body = err.body as Record<string, unknown> | null;
        if (body?.detail === 'phone_not_verified') {
          const phone = (body.phone as string | undefined) ?? values.email_or_phone;
          router.push({ pathname: '/(auth)/verify-otp', params: { phone } });
          return;
        }
        setApiError('Something went wrong. Please try again.');
      } else {
        setApiError('Something went wrong. Please try again.');
      }
    }
  };

  const btnScale = useSharedValue(1);
  const btnAnim  = useAnimatedStyle(() => ({ transform: [{ scale: btnScale.value }] }));

  // Deep navy background creates premium contrast regardless of system theme
  const outerBg  = isDark ? colors.midnight    : colors.navyDeep;
  const cardBg   = isDark ? colors.nightSurface : colors.white;
  const textPri  = isDark ? colors.white        : colors.navyDeep;
  const textSub  = isDark ? colors.slateText    : colors.coolGray;
  const inputBg  = isDark ? colors.nightElev    : colors.skyMist;
  const inputBdr = isDark ? 'rgba(255,255,255,0.10)' : colors.borderLight;
  const inputTxt = isDark ? colors.white        : colors.navyDeep;

  return (
    <KeyboardAvoidingView
      style={[styles.flex, { backgroundColor: outerBg }]}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >

        {/* ── Logo area ───────────────────────────────────────────────────── */}
        <View style={styles.logoArea}>
          <Text style={styles.wordmark}>Kyros</Text>
          <Text style={styles.tagline}>Doctor-first hormonal health</Text>
        </View>

        {/* ── Form card (clay + glass effect) ─────────────────────────────── */}
        <View style={[styles.card, { backgroundColor: cardBg }]}>
          <Text style={[styles.cardTitle, { color: textPri }]}>Sign in</Text>
          <Text style={[styles.cardSub, { color: textSub }]}>
            Enter your email or phone to continue
          </Text>

          <View style={styles.fields}>
            <Field
              label="Email or phone"
              error={errors.email_or_phone?.message}
              inputBg={inputBg}
              inputBdr={inputBdr}
              textColor={textPri}
            >
              <Controller
                control={control}
                name="email_or_phone"
                render={({ field: f }) => (
                  <TextInput
                    value={f.value}
                    onChangeText={f.onChange}
                    onBlur={f.onBlur}
                    autoCapitalize="none"
                    keyboardType="email-address"
                    autoComplete="email"
                    accessibilityLabel="Email or phone"
                    placeholderTextColor={textSub}
                    placeholder="you@example.com or +91…"
                    style={[styles.textInput, { color: inputTxt }]}
                  />
                )}
              />
            </Field>

            <Field
              label="Password"
              error={errors.password?.message}
              inputBg={inputBg}
              inputBdr={inputBdr}
              textColor={textPri}
            >
              <Controller
                control={control}
                name="password"
                render={({ field: f }) => (
                  <TextInput
                    value={f.value}
                    onChangeText={f.onChange}
                    onBlur={f.onBlur}
                    secureTextEntry
                    autoComplete="password"
                    accessibilityLabel="Password"
                    placeholderTextColor={textSub}
                    placeholder="••••••••"
                    style={[styles.textInput, { color: inputTxt }]}
                  />
                )}
              />
            </Field>
          </View>

          {apiError ? (
            <Text style={styles.apiError}>{apiError}</Text>
          ) : null}

          {/* Animated submit button */}
          <Animated.View style={btnAnim}>
            <Pressable
              style={[styles.button, isSubmitting && styles.buttonBusy]}
              onPress={handleSubmit(onSubmit)}
              onPressIn={() => { btnScale.value = withSpring(0.97, { mass: 0.3, stiffness: 500 }); }}
              onPressOut={() => { btnScale.value = withSpring(1,   { mass: 0.3, stiffness: 500 }); }}
              disabled={isSubmitting}
              accessibilityLabel="Sign in"
            >
              {isSubmitting ? (
                <ActivityIndicator color={colors.white} size="small" />
              ) : (
                <Text style={styles.buttonText}>Sign in</Text>
              )}
            </Pressable>
          </Animated.View>

          <Link href="/(auth)/signup" style={[styles.signupLink, { color: textSub }]}>
            New to Kyros? Create an account
          </Link>
        </View>

      </ScrollView>
    </KeyboardAvoidingView>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flexGrow: 1,
    justifyContent: 'flex-end',
    paddingHorizontal: spacing[6],
    paddingTop: spacing[16],
    paddingBottom: spacing[8],
  },

  // Logo area — sits on the deep navy background
  logoArea: {
    alignItems: 'center',
    marginBottom: spacing[8],
    gap: spacing[2],
  },
  wordmark: {
    fontFamily: fontFamily.display,
    fontSize: 48,
    color: colors.white,
    fontWeight: '500',
    letterSpacing: -0.5,
  },
  tagline: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: 'rgba(255,255,255,0.60)',
    letterSpacing: 0.2,
  },

  // Form card (clay: large radius, soft shadow, solid surface)
  card: {
    borderRadius: borderRadius.xxl,
    padding: spacing[6],
    gap: spacing[4],
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 24 },
    shadowOpacity: 0.22,
    shadowRadius: 40,
    elevation: 16,
  },
  cardTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.h3,
    fontWeight: '700',
  },
  cardSub: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    marginTop: -spacing[2],
  },

  fields: { gap: spacing[4] },

  textInput: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    padding: 0,
  },

  apiError: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    color: colors.criticalRed,
    textAlign: 'center',
  },

  // Primary button (full-width, 56px, bold radius)
  button: {
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
    letterSpacing: 0.3,
  },

  signupLink: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    textAlign: 'center',
    paddingVertical: spacing[2],
  },
});
