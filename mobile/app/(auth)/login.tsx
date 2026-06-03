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
  View,
} from 'react-native';
import { z } from 'zod';
import { loginApi } from '../../lib/api/auth';
import { ApiError } from '../../lib/api/client';
import { useAuth } from '../../lib/auth/context';
import { colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

const schema = z.object({
  email_or_phone: z.string().min(1, 'Required'),
  password: z.string().min(1, 'Required'),
});
type FormValues = z.infer<typeof schema>;

export default function LoginScreen() {
  const router = useRouter();
  const { signIn } = useAuth();
  const [apiError, setApiError] = useState<string | null>(null);

  const { control, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email_or_phone: '', password: '' },
  });

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

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <Text style={styles.wordmark}>Kyros</Text>
        <Text style={styles.subtitle}>Doctor-first hormonal health</Text>

        <View style={styles.form}>
          <Text style={styles.label}>Email or phone</Text>
          <Controller
            control={control}
            name="email_or_phone"
            render={({ field }) => (
              <TextInput
                style={[styles.input, errors.email_or_phone && styles.inputError]}
                value={field.value}
                onChangeText={field.onChange}
                onBlur={field.onBlur}
                autoCapitalize="none"
                keyboardType="email-address"
                autoComplete="email"
                accessibilityLabel="Email or phone"
                placeholderTextColor={colors.stone}
                placeholder="you@example.com or +919876543210"
              />
            )}
          />
          {errors.email_or_phone && (
            <Text style={styles.fieldError}>{errors.email_or_phone.message}</Text>
          )}

          <Text style={[styles.label, { marginTop: spacing[4] }]}>Password</Text>
          <Controller
            control={control}
            name="password"
            render={({ field }) => (
              <TextInput
                style={[styles.input, errors.password && styles.inputError]}
                value={field.value}
                onChangeText={field.onChange}
                onBlur={field.onBlur}
                secureTextEntry
                autoComplete="password"
                accessibilityLabel="Password"
                placeholderTextColor={colors.stone}
                placeholder="••••••••"
              />
            )}
          />
          {errors.password && (
            <Text style={styles.fieldError}>{errors.password.message}</Text>
          )}

          {apiError && <Text style={styles.apiError}>{apiError}</Text>}

          <Pressable
            style={[styles.button, isSubmitting && styles.buttonDisabled]}
            onPress={handleSubmit(onSubmit)}
            disabled={isSubmitting}
            accessibilityLabel="Sign in"
          >
            {isSubmitting ? (
              <ActivityIndicator color={colors.ivory} />
            ) : (
              <Text style={styles.buttonText}>Sign in</Text>
            )}
          </Pressable>

          <Link href="/(auth)/signup" style={styles.link}>
            New to Kyros? Create an account
          </Link>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.ivory },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[16],
    paddingBottom: spacing[8],
  },
  wordmark: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.display,
    color: colors.forest,
    fontWeight: '500',
  },
  subtitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.stone,
    marginTop: spacing[1],
    marginBottom: spacing[12],
  },
  form: { gap: spacing[1] },
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
  link: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    color: colors.jade,
    textAlign: 'center',
    marginTop: spacing[4],
  },
});
