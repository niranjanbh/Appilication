import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Alert } from '../lib/ui/alert';

import { AmbientBackground } from '../components/ui/AmbientBackground';
import { HapticPressable } from '../components/ui/HapticPressable';
import { NeumorphInput } from '../components/ui/NeumorphInput';
import {
  getEmergencyContactApi,
  setEmergencyContactApi,
  type EmergencyContactWrite,
} from '../lib/api/emergency-contact';
import { borderRadius, colors, fontFamily, fontSize, spacing, withAlpha } from '../lib/design-tokens';
import { useTheme } from '../lib/theme';

function showAlert(title: string, message: string) {
  if (Platform.OS === 'web') window.alert(`${title}\n\n${message}`);
  else Alert.alert(title, message);
}

function Field({
  label,
  value,
  onChangeText,
  placeholder,
  keyboardType,
  subColor,
}: {
  label: string;
  value: string;
  onChangeText: (v: string) => void;
  placeholder: string;
  keyboardType?: 'default' | 'phone-pad' | 'email-address';
  subColor: string;
}) {
  return (
    <View style={styles.field}>
      <Text style={[styles.label, { color: subColor }]}>{label}</Text>
      <NeumorphInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        keyboardType={keyboardType ?? 'default'}
        autoCapitalize={keyboardType === 'email-address' ? 'none' : 'words'}
      />
    </View>
  );
}

export default function EmergencyContactScreen() {
  const t = useTheme();
  const queryClient = useQueryClient();

  const [name, setName] = useState('');
  const [relationship, setRelationship] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [hydrated, setHydrated] = useState(false);

  const { isLoading } = useQuery({
    queryKey: ['emergency-contact'],
    queryFn: async () => {
      const data = await getEmergencyContactApi();
      if (!hydrated) {
        setName(data.name ?? '');
        setRelationship(data.relationship ?? '');
        setPhone(data.phone ?? '');
        setEmail(data.email ?? '');
        setHydrated(true);
      }
      return data;
    },
    staleTime: 30_000,
  });

  const mutation = useMutation({
    mutationFn: (payload: EmergencyContactWrite) => setEmergencyContactApi(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['emergency-contact'] });
      showAlert('Saved', 'Your emergency contact has been updated.');
    },
    onError: () => { showAlert('Error', 'Could not save your emergency contact. Please try again.'); },
  });

  const canSave = name.trim() && relationship.trim() && phone.trim().length >= 4;

  const handleSave = () => {
    if (!canSave) {
      showAlert('Missing details', 'Please enter a name, relationship, and phone number.');
      return;
    }
    mutation.mutate({
      name: name.trim(),
      relationship: relationship.trim(),
      phone: phone.trim(),
      email: email.trim() ? email.trim() : null,
    });
  };

  if (isLoading && !hydrated) {
    return (
      <View style={[styles.flex, styles.center, { backgroundColor: t.background }]}>
        <ActivityIndicator color={t.primary} />
      </View>
    );
  }

  return (
    <View style={[styles.flex, { backgroundColor: t.background }]}>
      <AmbientBackground />
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView style={styles.flex} contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
          <Text style={[styles.heading, { color: t.text }]}>Emergency contact</Text>
          <Text style={[styles.subtitle, { color: t.textSub }]}>
            Who should we reach in case of an emergency during your care.
          </Text>

          <Field label="Full name" value={name} onChangeText={setName} placeholder="e.g. Asha Rao" subColor={t.textSub} />
          <Field label="Relationship" value={relationship} onChangeText={setRelationship} placeholder="e.g. Sister" subColor={t.textSub} />
          <Field label="Phone number" value={phone} onChangeText={setPhone} placeholder="e.g. +91 90000 00000" keyboardType="phone-pad" subColor={t.textSub} />
          <Field label="Email (optional)" value={email} onChangeText={setEmail} placeholder="name@example.com" keyboardType="email-address" subColor={t.textSub} />

          <HapticPressable
            haptic="medium"
            scaleTo={0.97}
            style={[styles.saveBtn, (!canSave || mutation.isPending) && styles.disabled]}
            onPress={handleSave}
            disabled={mutation.isPending}
            accessibilityLabel="Save emergency contact"
          >
            <Text style={styles.saveBtnText}>{mutation.isPending ? 'Saving…' : 'Save contact'}</Text>
          </HapticPressable>
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  center: { alignItems: 'center', justifyContent: 'center' },
  container: {
    flexGrow: 1,
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
    paddingBottom: spacing[12],
    gap: spacing[4],
  },
  heading: { fontFamily: fontFamily.display, fontSize: fontSize.h2, fontWeight: '600' },
  subtitle: { fontFamily: fontFamily.body, fontSize: fontSize.body, lineHeight: 22, marginBottom: spacing[2] },
  field: { gap: spacing[2] },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: '600',
    paddingHorizontal: spacing[1],
  },
  saveBtn: {
    height: 52,
    marginTop: spacing[2],
    backgroundColor: colors.forest,
    borderRadius: borderRadius.xxl,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: `0 6px 14px ${withAlpha(colors.forest, 0.30)}`,
  },
  saveBtnText: { fontFamily: fontFamily.body, fontSize: fontSize.bodyLg, color: colors.ivoryText, fontWeight: '700' },
  disabled: { opacity: 0.5 },
});
