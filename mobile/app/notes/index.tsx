import { Ionicons } from '@expo/vector-icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useThemePreference } from '../../lib/theme-context';
import {
  createPatientNoteApi,
  deletePatientNoteApi,
  listPatientNotesApi,
  updatePatientNoteApi,
  type PatientNote,
} from '../../lib/api/patient-notes';
import { AmbientBackground } from '../../components/ui/AmbientBackground';
import { EmptyState } from '../../components/ui/EmptyState';
import { GlassCard } from '../../components/ui/GlassCard';
import { HapticPressable } from '../../components/ui/HapticPressable';
import { SkeletonCards } from '../../components/ui/Skeleton';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });
}

// ── Note row ─────────────────────────────────────────────────────────────────

function NoteRow({
  note,
  textPri,
  textSub,
  isDark,
  onEdit,
  onDelete,
}: {
  note: PatientNote;
  textPri: string;
  textSub: string;
  isDark: boolean;
  onEdit: (note: PatientNote) => void;
  onDelete: (note: PatientNote) => void;
}) {
  return (
    <GlassCard>
      <View style={styles.noteContent}>
        <Text style={[styles.noteBody, { color: textPri }]}>{note.body}</Text>
        <Text style={[styles.noteDate, { color: textSub }]}>{formatDate(note.updated_at)}</Text>
      </View>
      <View style={styles.noteActions}>
        <HapticPressable
          haptic="selection"
          onPress={() => onEdit(note)}
          style={[styles.actionBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,31,63,0.05)' }]}
          accessibilityLabel={`Edit note`}
        >
          <Ionicons name="pencil-outline" size={16} color={textSub} />
        </HapticPressable>
        <HapticPressable
          haptic="selection"
          onPress={() => onDelete(note)}
          style={[styles.actionBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,31,63,0.05)' }]}
          accessibilityLabel={`Delete note`}
        >
          <Ionicons name="trash-outline" size={16} color={colors.criticalRed} />
        </HapticPressable>
      </View>
    </GlassCard>
  );
}

// ── Main screen ─────────────────────────────────────────────────────────────

export default function NotesScreen() {
  const { colorScheme } = useThemePreference();
  const isDark = colorScheme === 'dark';
  const queryClient = useQueryClient();

  const [modalVisible, setModalVisible] = useState(false);
  const [editingNote, setEditingNote] = useState<PatientNote | null>(null);
  const [noteText, setNoteText] = useState('');

  const bg = isDark ? colors.forestInk : colors.skyMist;
  const textPri = isDark ? colors.white : colors.navyDeep;
  const textSub = isDark ? colors.stoneDim : colors.coolGray;

  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ['patient-notes'],
    queryFn: () => listPatientNotesApi(1, 100),
  });

  const createMutation = useMutation({
    mutationFn: (body: string) => createPatientNoteApi(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patient-notes'] });
      closeModal();
    },
    onError: () => Alert.alert('Error', 'Could not save note. Please try again.'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: string; body: string }) => updatePatientNoteApi(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patient-notes'] });
      closeModal();
    },
    onError: () => Alert.alert('Error', 'Could not update note. Please try again.'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deletePatientNoteApi(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['patient-notes'] }),
    onError: () => Alert.alert('Error', 'Could not delete note. Please try again.'),
  });

  function openCreate() {
    setEditingNote(null);
    setNoteText('');
    setModalVisible(true);
  }

  function openEdit(note: PatientNote) {
    setEditingNote(note);
    setNoteText(note.body);
    setModalVisible(true);
  }

  function closeModal() {
    setModalVisible(false);
    setEditingNote(null);
    setNoteText('');
  }

  function handleSave() {
    const trimmed = noteText.trim();
    if (!trimmed) return;
    if (editingNote) {
      updateMutation.mutate({ id: editingNote.id, body: trimmed });
    } else {
      createMutation.mutate(trimmed);
    }
  }

  function handleDelete(note: PatientNote) {
    Alert.alert('Delete note?', 'This cannot be undone.', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: () => deleteMutation.mutate(note.id) },
    ]);
  }

  const isSaving = createMutation.isPending || updateMutation.isPending;
  const notes = data?.items ?? [];

  return (
    <View style={[styles.flex, { backgroundColor: bg }]}>
      <AmbientBackground />

      {isLoading ? (
        <View style={styles.loadingContainer}>
          <SkeletonCards count={4} />
        </View>
      ) : notes.length === 0 ? (
        <View style={styles.emptyContainer}>
          <EmptyState
            icon="document-text-outline"
            title="No notes yet"
            subtitle="Add personal health notes to share context with your doctor."
          />
        </View>
      ) : (
        <FlatList
          data={notes}
          keyExtractor={n => n.id}
          renderItem={({ item }) => (
            <NoteRow
              note={item}
              textPri={textPri}
              textSub={textSub}
              isDark={isDark}
              onEdit={openEdit}
              onDelete={handleDelete}
            />
          )}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={colors.electricBlue} />
          }
        />
      )}

      {/* FAB — add note */}
      <Pressable
        style={styles.fab}
        onPress={openCreate}
        accessibilityLabel="Add new note"
      >
        <Ionicons name="add" size={28} color={colors.white} />
      </Pressable>

      {/* ── Create / Edit modal ──────────────────────────────────────────── */}
      <Modal visible={modalVisible} transparent animationType="slide" onRequestClose={closeModal}>
        <KeyboardAvoidingView
          style={styles.modalOverlay}
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        >
          <View style={[styles.modalCard, { backgroundColor: isDark ? colors.forestSurface : colors.white }]}>
            <View style={styles.modalHeader}>
              <Text style={[styles.modalTitle, { color: textPri }]}>
                {editingNote ? 'Edit note' : 'New note'}
              </Text>
              <Pressable onPress={closeModal} accessibilityLabel="Close">
                <Ionicons name="close" size={24} color={textSub} />
              </Pressable>
            </View>

            <TextInput
              style={[
                styles.modalInput,
                {
                  color: textPri,
                  borderColor: isDark ? 'rgba(255,255,255,0.15)' : colors.borderLight,
                  backgroundColor: isDark ? colors.forestInk : colors.skyMist,
                },
              ]}
              placeholder="Write your health note here…"
              placeholderTextColor={textSub}
              value={noteText}
              onChangeText={setNoteText}
              multiline
              textAlignVertical="top"
              autoFocus
              accessibilityLabel="Note content"
            />

            <View style={styles.modalButtons}>
              <Pressable
                style={[styles.modalBtn, styles.modalCancelBtn, { borderColor: isDark ? 'rgba(255,255,255,0.12)' : colors.borderLight }]}
                onPress={closeModal}
                accessibilityLabel="Cancel"
              >
                <Text style={[styles.modalBtnText, { color: textPri }]}>Cancel</Text>
              </Pressable>
              <Pressable
                style={[styles.modalBtn, styles.modalSaveBtn, !noteText.trim() && styles.modalBtnDisabled]}
                onPress={handleSave}
                disabled={!noteText.trim() || isSaving}
                accessibilityLabel="Save note"
              >
                {isSaving ? (
                  <ActivityIndicator color={colors.white} size="small" />
                ) : (
                  <Text style={[styles.modalBtnText, { color: colors.white }]}>
                    {editingNote ? 'Update' : 'Save'}
                  </Text>
                )}
              </Pressable>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </View>
  );
}

// ── Styles ─────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  flex: { flex: 1 },
  loadingContainer: { flex: 1, paddingHorizontal: spacing[6], paddingTop: spacing[6] },
  emptyContainer: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: spacing[8] },
  listContent: {
    paddingHorizontal: spacing[6],
    paddingTop: spacing[4],
    paddingBottom: spacing[20],
    gap: spacing[3],
  },

  noteContent: { gap: spacing[2] },
  noteBody: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    lineHeight: 22,
  },
  noteDate: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
  },
  noteActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: spacing[2],
    marginTop: spacing[3],
  },
  actionBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },

  fab: {
    position: 'absolute',
    right: spacing[6],
    bottom: spacing[20],
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.navyDeep,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 6,
  },

  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalCard: {
    borderTopLeftRadius: borderRadius.xxl,
    borderTopRightRadius: borderRadius.xxl,
    padding: spacing[6],
    gap: spacing[4],
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.1,
    shadowRadius: 16,
    elevation: 8,
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  modalTitle: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h3,
    fontWeight: '600',
  },
  modalInput: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    borderWidth: 1,
    borderRadius: borderRadius.lg,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    minHeight: 120,
    lineHeight: 22,
  },
  modalButtons: {
    flexDirection: 'row',
    gap: spacing[3],
  },
  modalBtn: {
    flex: 1,
    borderRadius: borderRadius.xxl,
    paddingVertical: spacing[3],
    alignItems: 'center',
    justifyContent: 'center',
  },
  modalCancelBtn: {
    borderWidth: 1,
  },
  modalSaveBtn: {
    backgroundColor: colors.navyDeep,
  },
  modalBtnDisabled: {
    opacity: 0.4,
  },
  modalBtnText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
});
