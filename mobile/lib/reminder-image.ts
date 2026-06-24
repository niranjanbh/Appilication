import { Ionicons } from '@expo/vector-icons';
import type { TintName } from './design-tokens';
import type { Reminder, ReminderType } from '../types/wellness';

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

/**
 * Resolved visual for a reminder.
 *
 * - `kind: 'photo'` — a real image (patient-uploaded custom photo, or a
 *   doctor/admin medication-catalog image). The `uri` is a short-lived
 *   presigned S3 URL fetched separately (Phase 5); not present yet.
 * - `kind: 'default'` — a built-in category illustration (icon + tint). Shown
 *   for every reminder that has no photo, including all patient reminders by
 *   default.
 */
export interface ReminderImage {
  kind: 'photo' | 'default';
  uri?: string;
  icon: IoniconName;
  tint: TintName;
}

// Default category illustrations. Medication can be refined by `metadata.form`
// (tablet / capsule / injection / syrup) once that field is captured.
const TYPE_DEFAULT: Record<ReminderType, { icon: IoniconName; tint: TintName }> = {
  water:      { icon: 'water',         tint: 'blue' },
  supplement: { icon: 'leaf',          tint: 'green' },
  medication: { icon: 'medkit',        tint: 'violet' },
  gym:        { icon: 'barbell',       tint: 'amber' },
  custom:     { icon: 'notifications', tint: 'blue' },
};

const FORM_DEFAULT: Record<string, { icon: IoniconName; tint: TintName }> = {
  tablet:    { icon: 'medical',  tint: 'violet' },
  capsule:   { icon: 'medical',  tint: 'violet' },
  injection: { icon: 'eyedrop',  tint: 'violet' },
  syrup:     { icon: 'flask',    tint: 'violet' },
};

/**
 * Resolve the image to show for a reminder.
 *
 * Resolution order:
 *   1. Patient-uploaded custom photo (`metadata.image_url`, presigned) — Phase 5.
 *   2. Doctor/admin catalog photo (`metadata.catalog_image_url`, presigned) — Phase 5.
 *   3. Built-in default illustration by medication form, then by type.
 */
export function resolveReminderImage(reminder: Reminder): ReminderImage {
  const meta = reminder.metadata ?? {};
  const photoUri = (meta.image_url ?? meta.catalog_image_url) as string | undefined;
  if (typeof photoUri === 'string' && photoUri.length > 0) {
    const fallback = TYPE_DEFAULT[reminder.type] ?? TYPE_DEFAULT.custom;
    return { kind: 'photo', uri: photoUri, icon: fallback.icon, tint: fallback.tint };
  }

  const form = typeof meta.form === 'string' ? meta.form.toLowerCase() : '';
  if (reminder.type === 'medication' && FORM_DEFAULT[form]) {
    return { kind: 'default', ...FORM_DEFAULT[form] };
  }
  return { kind: 'default', ...(TYPE_DEFAULT[reminder.type] ?? TYPE_DEFAULT.custom) };
}
