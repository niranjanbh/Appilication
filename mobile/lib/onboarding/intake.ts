/**
 * Onboarding intake — shared option definitions and helpers.
 *
 * Single source of truth for the condition chips and intake questions shown
 * across the onboarding screens, plus the mapping from onboarding condition
 * slugs to the backend's canonical `condition_category` values and a composer
 * that turns the collected answers into a consultation requirement note.
 *
 * The backend's POST /v1/clinic/patient/consultations validates
 * `condition_category` against {thyroid, weight, pcos, skin_hair, mens_intimate,
 * hormones_trt, longevity}. Onboarding used display slugs (e.g. "hormones-trt")
 * that are NOT all in the server's alias map, so we map to canonical values
 * here before submitting.
 */

export interface ConditionOption {
  slug: string; // onboarding slug
  label: string;
  icon: string;
  /** Canonical backend condition_category. */
  category: string;
}

export const CONDITION_OPTIONS: readonly ConditionOption[] = [
  { slug: 'thyroid',              label: 'Thyroid',               icon: '🦋', category: 'thyroid' },
  { slug: 'pcos',                 label: 'PCOS',                  icon: '🌿', category: 'pcos' },
  { slug: 'weight-management',    label: 'Weight management',     icon: '⚖️', category: 'weight' },
  { slug: 'skin-and-hair',        label: 'Skin & hair',           icon: '✨', category: 'skin_hair' },
  { slug: 'mens-intimate-health', label: "Men's intimate health", icon: '🛡️', category: 'mens_intimate' },
  { slug: 'hormones-trt',         label: 'Hormones & TRT',        icon: '⚡', category: 'hormones_trt' },
  { slug: 'longevity',            label: 'Longevity & energy',    icon: '🌱', category: 'longevity' },
] as const;

export interface Option { value: string; label: string }

export const GENDER_OPTIONS: readonly Option[] = [
  { value: 'male',   label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other',  label: 'Prefer not to say' },
];

export const SYMPTOM_DURATION_OPTIONS: readonly Option[] = [
  { value: 'less_than_3_months', label: 'Less than 3 months' },
  { value: '3_to_6_months',      label: '3 – 6 months' },
  { value: 'more_than_6_months', label: 'More than 6 months' },
  { value: 'more_than_2_years',  label: 'More than 2 years' },
];

export const PREVIOUS_DIAGNOSIS_OPTIONS: readonly Option[] = [
  { value: 'yes_diagnosed', label: 'Yes, I have a diagnosis' },
  { value: 'yes_suspected', label: 'Yes, it was suspected but not confirmed' },
  { value: 'no',            label: 'No previous diagnosis' },
];

export const PREVIOUS_TREATMENT_OPTIONS: readonly Option[] = [
  { value: 'yes_currently',  label: 'Yes, currently on treatment' },
  { value: 'yes_previously', label: 'Yes, previously treated' },
  { value: 'no',             label: 'No treatment yet' },
];

// ── Lookups ─────────────────────────────────────────────────────────────────

function labelFor(options: readonly Option[], value: string | null): string | null {
  if (!value) return null;
  return options.find(o => o.value === value)?.label ?? value;
}

export function conditionForSlug(slug: string): ConditionOption | undefined {
  return CONDITION_OPTIONS.find(c => c.slug === slug);
}

// ── Intake shape + request composition ──────────────────────────────────────

export interface OnboardingIntake {
  conditions: string[]; // onboarding slugs, selection order preserved
  gender: string | null;
  duration: string | null;
  diagnosis: string | null;
  treatment: string | null;
}

export const EMPTY_INTAKE: OnboardingIntake = {
  conditions: [],
  gender: null,
  duration: null,
  diagnosis: null,
  treatment: null,
};

/** The primary condition's canonical category, used as `condition_category`. */
export function primaryCategory(intake: OnboardingIntake): string | null {
  const first = intake.conditions[0];
  return first ? conditionForSlug(first)?.category ?? null : null;
}

/**
 * Compose a human-readable requirement note from the intake answers so the
 * coordinator and doctor see everything the patient told us during onboarding.
 * Returns null when there is nothing meaningful to record.
 */
export function composeRequirementNotes(intake: OnboardingIntake): string | null {
  const lines: string[] = [];

  const otherConditions = intake.conditions
    .slice(1)
    .map(slug => conditionForSlug(slug)?.label ?? slug);
  if (otherConditions.length > 0) {
    lines.push(`Also flagged: ${otherConditions.join(', ')}`);
  }

  const gender = labelFor(GENDER_OPTIONS, intake.gender);
  if (gender) lines.push(`Gender: ${gender}`);

  const duration = labelFor(SYMPTOM_DURATION_OPTIONS, intake.duration);
  if (duration) lines.push(`Symptom duration: ${duration}`);

  const diagnosis = labelFor(PREVIOUS_DIAGNOSIS_OPTIONS, intake.diagnosis);
  if (diagnosis) lines.push(`Prior diagnosis: ${diagnosis}`);

  const treatment = labelFor(PREVIOUS_TREATMENT_OPTIONS, intake.treatment);
  if (treatment) lines.push(`Prior treatment: ${treatment}`);

  if (lines.length === 0) return null;
  return lines.join('\n').slice(0, 2000); // backend caps requirement_notes at 2000
}
