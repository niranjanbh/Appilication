import { Ionicons } from '@expo/vector-icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Modal,
  Platform,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Alert } from '../../lib/ui/alert';

import { AmbientBackground } from '../../components/ui/AmbientBackground';
import { EmptyState } from '../../components/ui/EmptyState';
import { NeumorphCard } from '../../components/ui/NeumorphCard';
import { NeumorphInput } from '../../components/ui/NeumorphInput';
import { TAB_DOCK_CLEARANCE } from '../../components/ui/GlassTabBar';
import { HapticPressable } from '../../components/ui/HapticPressable';
import {
  createPatientNoteApi,
  deletePatientNoteApi,
  listPatientNotesApi,
  updatePatientNoteApi,
} from '../../lib/api/patient-notes';
import {
  borderRadius,
  colors,
  fontFamily,
  fontSize,
  spacing,
  withAlpha,
} from '../../lib/design-tokens';
import { useTheme } from '../../lib/theme';
import type { PatientNote } from '../../types/clinic';

const MAX_BODY = 1000;

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'Asia/Kolkata',
  });
}

// ── Note editor modal ─────────────────────────────────────────────────────────

interface NoteEditorProps {
  visible: boolean;
  initialBody?: string;
  onSave: (body: string) => void;
  onDismiss: () => void;
  isSaving: boolean;
}

function NoteEditor({ visible, initialBody = '', onSave, onDismiss, isSaving }: NoteEditorProps) {
  const [body, setBody] = useState(initialBody);
  const t = useTheme();

  const handleSave = () => {
    const trimmed = body.trim();
    if (trimmed.length === 0) return;
    onSave(trimmed);
  };

  return (
    <Modal visible={visible} animationType="slide" presentationStyle="pageSheet" onRequestClose={onDismiss}>
      <View style={[styles.modalRoot, { backgroundColor: t.background }]}>
        <View style={styles.modalHeader}>
          <HapticPressable onPress={onDismiss} accessibilityLabel="Cancel">
            <Text style={[styles.modalAction, { color: t.textSub }]}>Cancel</Text>
          </HapticPressable>
          <Text style={[styles.modalTitle, { color: t.text }]}>
            {initialBody ? 'Edit note' : 'New note'}
          </Text>
          <HapticPressable onPress={handleSave} disabled={isSaving || body.trim().length === 0} accessibilityLabel="Save note">
            {isSaving
              ? <ActivityIndicator size="small" color={t.primary} />
              : <Text style={[styles.modalAction, { color: body.trim().length === 0 ? t.textSub : t.primary, fontWeight: '600' }]}>Save</Text>
            }
          </HapticPressable>
        </View>

        <NeumorphInput
          style={styles.textInput}
          value={body}
          onChangeText={setBody}
          placeholder="Write your question or note for the doctor…"
          multiline
          maxLength={MAX_BODY}
          autoFocus
          textAlignVertical="top"
          accessibilityLabel="Note body"
        />
        <Text style={[styles.charCount, { color: t.textSub }]}>
          {body.length}/{MAX_BODY}
        </Text>
      </View>
    </Modal>
  );
}

// ── Note card ────────────────────────────────────────────────────────────────

interface NoteCardProps {
  note: PatientNote;
  onEdit: (note: PatientNote) => void;
  onDelete: (note: PatientNote) => void;
}

function NoteCard({ note, onEdit, onDelete }: NoteCardProps) {
  const t = useTheme();

  const handleDelete = () => {
    if (Platform.OS === 'web') {
      if (window.confirm('Delete note?\n\nThis note will be permanently removed.')) {
        onDelete(note);
      }
    } else {
      Alert.alert('Delete note', 'This note will be permanently removed.', [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Delete', style: 'destructive', onPress: () => onDelete(note) },
      ]);
    }
  };

  return (
    <NeumorphCard>
      <View style={styles.noteRow}>
        <Text style={[styles.noteBody, { color: t.text }]}>{note.body}</Text>
        <View style={styles.noteActions}>
          <HapticPressable onPress={() => onEdit(note)} accessibilityLabel="Edit note" style={styles.iconBtn}>
            <Ionicons name="pencil-outline" size={16} color={t.textSub} />
          </HapticPressable>
          <HapticPressable onPress={handleDelete} accessibilityLabel="Delete note" style={styles.iconBtn}>
            <Ionicons name="trash-outline" size={16} color={colors.alert} />
          </HapticPressable>
        </View>
      </View>
      <Text style={[styles.noteTime, { color: t.textSub }]}>{formatRelative(note.created_at)}</Text>
    </NeumorphCard>
  );
}

// ── Main screen ──────────────────────────────────────────────────────────────

export default function NotesScreen() {
  const t = useTheme();
  const qc = useQueryClient();

  const [editorVisible, setEditorVisible] = useState(false);
  const [editingNote, setEditingNote] = useState<PatientNote | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['patient-notes'],
    queryFn: () => listPatientNotesApi(),
  });

  const createMutation = useMutation({
    mutationFn: (body: string) => createPatientNoteApi({ body }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['patient-notes'] });
      setEditorVisible(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: string; body: string }) =>
      updatePatientNoteApi(id, { body }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['patient-notes'] });
      setEditorVisible(false);
      setEditingNote(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deletePatientNoteApi(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['patient-notes'] });
    },
  });

  const openCreate = () => {
    setEditingNote(null);
    setEditorVisible(true);
  };

  const openEdit = (note: PatientNote) => {
    setEditingNote(note);
    setEditorVisible(true);
  };

  const handleSave = (body: string) => {
    if (editingNote) {
      updateMutation.mutate({ id: editingNote.id, body });
    } else {
      createMutation.mutate(body);
    }
  };

  const notes = data?.items ?? [];
  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <View style={[styles.flex, { backgroundColor: t.background }]}>
      <AmbientBackground />

      {isLoading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={t.primary} />
        </View>
      ) : notes.length === 0 ? (
        <EmptyState
          icon="create-outline"
          title="No notes yet"
          body="Jot down questions or things you want to tell your doctor before your next consultation."
          ctaLabel="Add first note"
          onCtaPress={openCreate}
        />
      ) : (
        <FlatList
          data={notes}
          keyExtractor={item => item.id}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => (
            <NoteCard
              note={item}
              onEdit={openEdit}
              onDelete={n => deleteMutation.mutate(n.id)}
            />
          )}
        />
      )}

      {/* Floating add button */}
      {notes.length > 0 && (
        <HapticPressable
          haptic="medium"
          onPress={openCreate}
          accessibilityLabel="Add new note"
          style={[styles.fab, { backgroundColor: t.primary }]}
        >
          <Ionicons name="add" size={28} color={colors.white} />
        </HapticPressable>
      )}

      <NoteEditor
        visible={editorVisible}
        initialBody={editingNote?.body ?? ''}
        onSave={handleSave}
        onDismiss={() => {
          setEditorVisible(false);
          setEditingNote(null);
        }}
        isSaving={isSaving}
      />
    </View>
  );
}

// ── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  flex: { flex: 1 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },

  list: {
    padding: spacing[5],
    paddingBottom: TAB_DOCK_CLEARANCE + spacing[6],
    gap: spacing[3],
  },

  noteRow: { flexDirection: 'row', gap: spacing[3] },
  noteBody: {
    flex: 1,
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    lineHeight: 22,
  },
  noteActions: { flexDirection: 'row', gap: spacing[1] },
  iconBtn: { padding: spacing[1] },
  noteTime: {
    marginTop: spacing[2],
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
  },

  fab: {
    position: 'absolute',
    right: spacing[5],
    bottom: TAB_DOCK_CLEARANCE + spacing[4],
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: `0 6px 18px ${withAlpha(colors.forest, 0.30)}`,
  },

  // Editor modal
  modalRoot: { flex: 1, padding: spacing[5] },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing[5],
  },
  modalTitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    fontWeight: '600',
  },
  modalAction: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
  },
  textInput: {
    borderRadius: borderRadius.lg,
    borderWidth: 1,
    padding: spacing[4],
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    lineHeight: 22,
    minHeight: 160,
  },
  charCount: {
    marginTop: spacing[2],
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    textAlign: 'right',
  },
});
