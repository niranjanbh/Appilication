'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

// ── Data ──────────────────────────────────────────────────────────────────────

const CONDITIONS = [
  { slug: 'thyroid', name: 'Thyroid', sub: 'Fatigue, weight changes, hair loss, brain fog' },
  { slug: 'pcos', name: 'PCOS', sub: 'Irregular cycles, acne, hair loss, weight' },
  { slug: 'weight-management', name: 'Weight Management', sub: 'Metabolic, GLP-1, insulin resistance' },
  { slug: 'skin-and-hair', name: 'Skin & Hair', sub: 'AGA, adult acne, melasma' },
  { slug: 'mens-intimate-health', name: "Men's Intimate Health", sub: 'ED, premature ejaculation, low libido' },
  { slug: 'hormones-trt', name: 'Hormones & TRT', sub: 'Low testosterone, hormonal imbalance' },
  { slug: 'longevity', name: 'Longevity', sub: 'Preventive care, advanced biomarkers' },
] as const;

type ConditionSlug = (typeof CONDITIONS)[number]['slug'];

const INTAKE_QUESTIONS: Record<ConditionSlug, Array<{ id: string; label: string; options: string[] }>> = {
  thyroid: [
    { id: 'symptom_duration', label: 'How long have you been experiencing symptoms?', options: ['Less than 3 months', '3–6 months', '6–12 months', 'More than 1 year'] },
    { id: 'previous_diagnosis', label: 'Have you been previously diagnosed with a thyroid condition?', options: ['No diagnosis yet', 'Hypothyroidism', 'Hyperthyroidism', "Hashimoto's thyroiditis", 'Not sure'] },
    { id: 'current_medication', label: 'Are you currently on thyroid medication?', options: ['No', 'Yes, levothyroxine', 'Yes, other medication', 'Previously, not currently'] },
    { id: 'recent_labs', label: 'When did you last have a thyroid panel?', options: ['Never', 'More than 1 year ago', 'Within the last year', 'Within the last 3 months'] },
  ],
  pcos: [
    { id: 'cycle_regularity', label: 'How regular is your menstrual cycle?', options: ['Regular (24–35 days)', 'Slightly irregular', 'Very irregular', 'Absent'] },
    { id: 'primary_concern', label: 'What is your primary concern right now?', options: ['Irregular cycles', 'Acne or hair issues', 'Weight management', 'Fertility', 'General hormonal health'] },
    { id: 'previous_diagnosis', label: 'Have you been diagnosed with PCOS or PCOD before?', options: ['Yes', 'No', 'Suspected but unconfirmed'] },
    { id: 'symptom_duration', label: 'How long have you had these symptoms?', options: ['Less than 1 year', '1–3 years', 'More than 3 years'] },
  ],
  'weight-management': [
    { id: 'primary_concern', label: 'What best describes your situation?', options: ['Struggling to lose weight despite effort', 'Unexplained weight gain', 'Managing existing metabolic condition', 'Interest in GLP-1 supervision'] },
    { id: 'comorbidities', label: 'Do you have any of the following?', options: ['None', 'Pre-diabetes or diabetes', 'PCOS', 'Thyroid condition', 'High blood pressure or lipids'] },
    { id: 'previous_attempts', label: 'What have you tried?', options: ['Diet changes', 'Exercise programmes', 'Intermittent fasting', 'Weight-loss medications', 'Combination of the above'] },
    { id: 'recent_labs', label: 'Have you had metabolic blood tests in the last year?', options: ['Yes, comprehensive panel', 'Yes, basic tests only', 'No'] },
  ],
  'skin-and-hair': [
    { id: 'primary_concern', label: 'What is your primary concern?', options: ['Hair loss or thinning', 'Adult acne', 'Melasma or pigmentation', 'Multiple concerns'] },
    { id: 'duration', label: 'How long have you been experiencing this?', options: ['Less than 6 months', '6 months to 1 year', '1–3 years', 'More than 3 years'] },
    { id: 'treatments_tried', label: 'Have you tried any treatments?', options: ['No treatment yet', 'Over-the-counter products', 'Doctor-prescribed treatment', 'Clinic procedures (PRP, laser)'] },
  ],
  'mens-intimate-health': [
    { id: 'primary_concern', label: 'What is your primary concern?', options: ['Erectile dysfunction', 'Premature ejaculation', 'Reduced libido', 'Multiple concerns'] },
    { id: 'duration', label: 'How long have you been experiencing this?', options: ['Less than 6 months', '6 months to 1 year', '1–3 years', 'More than 3 years'] },
    { id: 'previous_consultation', label: 'Have you discussed this with a doctor before?', options: ['No, this is my first consultation', 'Yes, previously', 'I prefer not to say'] },
  ],
  'hormones-trt': [
    { id: 'primary_symptoms', label: 'Which symptoms concern you most?', options: ['Fatigue and low energy', 'Reduced libido', 'Mood changes', 'Reduced muscle or increased fat', 'Multiple symptoms'] },
    { id: 'duration', label: 'How long have you experienced these symptoms?', options: ['Less than 6 months', '6 months to 1 year', '1–3 years', 'More than 3 years'] },
    { id: 'previous_tests', label: 'Have you had testosterone tested?', options: ['No', 'Yes, total testosterone only', 'Yes, full hormonal panel', 'Not sure what was tested'] },
  ],
  longevity: [
    { id: 'motivation', label: 'What brings you to Kyros?', options: ['Annual preventive evaluation', 'Family history of cardiovascular disease', 'Interpreting wearable data', 'Advanced biomarker testing', 'General longevity interest'] },
    { id: 'recent_labs', label: 'When did you last have a comprehensive blood panel?', options: ['Never', 'More than 2 years ago', 'Within the last 2 years', 'Within the last 6 months'] },
    { id: 'apo_b_tested', label: 'Have you had ApoB or Lp(a) tested?', options: ['Yes, both', 'ApoB only', 'Neither', "I don't know what these are"] },
  ],
};

const COUNTRY_CODES = [
  { code: '+91', flag: '🇮🇳', name: 'India' },
  { code: '+1', flag: '🇺🇸', name: 'USA / Canada' },
  { code: '+44', flag: '🇬🇧', name: 'United Kingdom' },
  { code: '+971', flag: '🇦🇪', name: 'UAE' },
  { code: '+65', flag: '🇸🇬', name: 'Singapore' },
  { code: '+61', flag: '🇦🇺', name: 'Australia' },
] as const;

const GENDER_OPTIONS = [
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other', label: 'Prefer not to say' },
] as const;

// ── Schemas ───────────────────────────────────────────────────────────────────

const contactSchema = z.object({
  name: z.string().min(2, 'Please enter your full name'),
  gender: z.enum(['male', 'female', 'other'], { required_error: 'Please select your gender' }),
  phoneNumber: z.string().regex(/^\d{6,12}$/, 'Enter digits only — no spaces, dashes, or country code'),
  email: z.string().email('Enter a valid email address').optional().or(z.literal('')),
});

type ContactFormData = z.infer<typeof contactSchema>;

// ── Main component ────────────────────────────────────────────────────────────

type Step = 'condition' | 'intake' | 'contact' | 'success';

export function BookingFlow() {
  const [step, setStep] = useState<Step>('condition');
  const [selectedCondition, setSelectedCondition] = useState<ConditionSlug | null>(null);
  const [intakeAnswers, setIntakeAnswers] = useState<Record<string, string>>({});
  const [skippedIntake, setSkippedIntake] = useState(false);
  const [countryCode, setCountryCode] = useState('+91');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<ContactFormData>({ resolver: zodResolver(contactSchema) });

  const selectedGender = watch('gender');

  const handleSkipIntake = () => {
    setSkippedIntake(true);
    setIntakeAnswers({});
    setStep('contact');
  };

  // Step 1: condition selection
  if (step === 'condition') {
    return (
      <div>
        <h2 className="font-display text-h2 font-medium text-forest mb-2">
          What brings you in?
        </h2>
        <p className="font-body text-body text-stone mb-8">
          Choose the condition closest to your concern. You can discuss anything with your doctor.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-8">
          {CONDITIONS.map((c) => (
            <button
              key={c.slug}
              type="button"
              onClick={() => setSelectedCondition(c.slug)}
              className={[
                'text-left p-5 rounded-card border-2 transition-all duration-micro',
                selectedCondition === c.slug
                  ? 'border-forest bg-forest/5'
                  : 'border-forest/15 bg-white hover:border-forest/40',
              ].join(' ')}
            >
              <p className="font-display text-h3 font-medium text-forest">{c.name}</p>
              <p className="font-body text-caption text-stone mt-1">{c.sub}</p>
            </button>
          ))}
        </div>
        <p className="font-body text-caption text-stone mb-6">
          Not sure?{' '}
          <a href="/contact" className="text-forest underline">
            Contact us
          </a>{' '}
          and a coordinator will help you choose.
        </p>
        <button
          type="button"
          disabled={!selectedCondition}
          onClick={() => setStep('intake')}
          className="w-full md:w-auto inline-flex items-center justify-center px-8 py-3
                     rounded-button bg-forest text-ivory font-body font-medium text-body-lg
                     disabled:opacity-40 disabled:cursor-not-allowed
                     hover:bg-jade transition-colors duration-micro"
        >
          Continue
        </button>
      </div>
    );
  }

  // Step 2: intake
  if (step === 'intake' && selectedCondition) {
    const questions = INTAKE_QUESTIONS[selectedCondition];
    const conditionName = CONDITIONS.find((c) => c.slug === selectedCondition)?.name ?? '';
    const allAnswered = questions.every((q) => intakeAnswers[q.id]);

    return (
      <div>
        <button
          type="button"
          onClick={() => { setSkippedIntake(false); setStep('condition'); }}
          className="font-body text-caption text-stone hover:text-forest mb-4 flex items-center gap-1 transition-colors duration-micro"
        >
          ← Back
        </button>
        <h2 className="font-display text-h2 font-medium text-forest mb-2">
          A little about your situation
        </h2>
        <p className="font-body text-body text-stone mb-8">
          This helps your doctor prepare before your consultation — {conditionName}.
        </p>
        <div className="space-y-8 mb-8">
          {questions.map((q) => (
            <fieldset key={q.id}>
              <legend className="font-body text-body-lg font-medium text-ink mb-3">
                {q.label}
              </legend>
              <div className="flex flex-wrap gap-2">
                {q.options.map((opt) => (
                  <button
                    key={opt}
                    type="button"
                    onClick={() =>
                      setIntakeAnswers((prev) => ({ ...prev, [q.id]: opt }))
                    }
                    className={[
                      'px-4 py-2 rounded-button border font-body text-body transition-all duration-micro',
                      intakeAnswers[q.id] === opt
                        ? 'border-forest bg-forest text-ivory'
                        : 'border-forest/25 text-ink hover:border-forest/60',
                    ].join(' ')}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            </fieldset>
          ))}
        </div>

        <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
          <button
            type="button"
            disabled={!allAnswered}
            onClick={() => { setSkippedIntake(false); setStep('contact'); }}
            className="w-full sm:w-auto inline-flex items-center justify-center px-8 py-3
                       rounded-button bg-forest text-ivory font-body font-medium text-body-lg
                       disabled:opacity-40 disabled:cursor-not-allowed
                       hover:bg-jade transition-colors duration-micro"
          >
            Continue
          </button>
          <button
            type="button"
            onClick={handleSkipIntake}
            className="w-full sm:w-auto inline-flex items-center justify-center px-6 py-3
                       rounded-button border border-forest/30 text-forest font-body font-medium text-body
                       hover:border-forest hover:bg-forest/5 transition-colors duration-micro"
          >
            Skip — speak to a coordinator directly
          </button>
        </div>

        <p className="font-body text-caption text-stone mt-4">
          Skipping is fine. A care coordinator will ask you about your situation personally.
        </p>
      </div>
    );
  }

  // Step 3: contact
  if (step === 'contact') {
    const onSubmit = async (data: ContactFormData) => {
      if (!selectedCondition) return;
      setIsSubmitting(true);
      setSubmitError(null);
      const phone = `${countryCode}${data.phoneNumber}`;
      try {
        const resp = await fetch('/api/book', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: data.name,
            gender: data.gender,
            phone,
            email: data.email || undefined,
            condition_category: selectedCondition,
            intake_responses: skippedIntake ? {} : intakeAnswers,
            skipped_intake: skippedIntake,
          }),
        });
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          throw new Error(
            (err as { detail?: string }).detail ?? 'Submission failed. Please try again.'
          );
        }
        setStep('success');
      } catch (e) {
        setSubmitError(e instanceof Error ? e.message : 'Something went wrong. Please try again.');
      } finally {
        setIsSubmitting(false);
      }
    };

    return (
      <div>
        <button
          type="button"
          onClick={() => setStep('intake')}
          className="font-body text-caption text-stone hover:text-forest mb-4 flex items-center gap-1 transition-colors duration-micro"
        >
          ← Back
        </button>
        <h2 className="font-display text-h2 font-medium text-forest mb-2">
          {skippedIntake
            ? 'Just the basics — a coordinator will do the rest'
            : 'Where should we reach you?'}
        </h2>
        <p className="font-body text-body text-stone mb-8">
          {skippedIntake
            ? 'A care coordinator will call you to understand your situation and match you with the right doctor.'
            : 'A coordinator will call you within 4 hours to schedule your consultation.'}
        </p>
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5 max-w-md">

          {/* Name */}
          <div>
            <label htmlFor="name" className="block font-body text-body font-medium text-ink mb-1">
              Your name
            </label>
            <input
              id="name"
              type="text"
              autoComplete="name"
              {...register('name')}
              className="w-full border border-forest/25 rounded-input px-4 py-3 font-body text-body text-ink
                         focus:outline-none focus:border-forest focus:ring-1 focus:ring-forest
                         placeholder:text-stone"
              placeholder="Full name"
            />
            {errors.name && (
              <p className="font-body text-caption text-alert mt-1">{errors.name.message}</p>
            )}
          </div>

          {/* Gender */}
          <div>
            <p className="block font-body text-body font-medium text-ink mb-2">Gender</p>
            <div className="flex gap-2 flex-wrap">
              {GENDER_OPTIONS.map((g) => (
                <button
                  key={g.value}
                  type="button"
                  onClick={() => setValue('gender', g.value, { shouldValidate: true })}
                  className={[
                    'px-4 py-2 rounded-button border font-body text-body transition-all duration-micro',
                    selectedGender === g.value
                      ? 'border-forest bg-forest text-ivory'
                      : 'border-forest/25 text-ink hover:border-forest/60',
                  ].join(' ')}
                >
                  {g.label}
                </button>
              ))}
            </div>
            {errors.gender && (
              <p className="font-body text-caption text-alert mt-1">{errors.gender.message}</p>
            )}
          </div>

          {/* Mobile number with country code */}
          <div>
            <label htmlFor="phoneNumber" className="block font-body text-body font-medium text-ink mb-1">
              Mobile number
            </label>
            <div className="flex gap-2">
              <select
                value={countryCode}
                onChange={(e) => setCountryCode(e.target.value)}
                aria-label="Country code"
                className="border border-forest/25 rounded-input px-3 py-3 font-body text-body text-ink
                           bg-white focus:outline-none focus:border-forest focus:ring-1 focus:ring-forest
                           cursor-pointer"
              >
                {COUNTRY_CODES.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.flag} {c.code}
                  </option>
                ))}
              </select>
              <input
                id="phoneNumber"
                type="tel"
                autoComplete="tel-national"
                inputMode="numeric"
                {...register('phoneNumber')}
                className="flex-1 border border-forest/25 rounded-input px-4 py-3 font-body text-body text-ink
                           focus:outline-none focus:border-forest focus:ring-1 focus:ring-forest
                           placeholder:text-stone"
                placeholder="9876543210"
              />
            </div>
            {errors.phoneNumber && (
              <p className="font-body text-caption text-alert mt-1">{errors.phoneNumber.message}</p>
            )}
          </div>

          {/* Email (optional) */}
          <div>
            <label htmlFor="email" className="block font-body text-body font-medium text-ink mb-1">
              Email{' '}
              <span className="font-body text-caption text-stone font-normal">(optional)</span>
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              {...register('email')}
              className="w-full border border-forest/25 rounded-input px-4 py-3 font-body text-body text-ink
                         focus:outline-none focus:border-forest focus:ring-1 focus:ring-forest
                         placeholder:text-stone"
              placeholder="you@example.com"
            />
            {errors.email && (
              <p className="font-body text-caption text-alert mt-1">{errors.email.message}</p>
            )}
          </div>

          {submitError && (
            <p className="font-body text-body text-alert bg-alert/8 rounded-card px-4 py-3">
              {submitError}
            </p>
          )}

          <p className="font-body text-caption text-stone">
            By continuing, you agree to our{' '}
            <a href="/legal/privacy" className="text-forest underline">
              privacy notice
            </a>{' '}
            and{' '}
            <a href="/legal/terms" className="text-forest underline">
              terms of use
            </a>
            .
          </p>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full inline-flex items-center justify-center px-8 py-3
                       rounded-button bg-forest text-ivory font-body font-medium text-body-lg
                       disabled:opacity-60 disabled:cursor-not-allowed
                       hover:bg-jade transition-colors duration-micro"
          >
            {isSubmitting ? 'Sending…' : 'Request consultation'}
          </button>
        </form>
      </div>
    );
  }

  // Step 4: success
  return (
    <div className="max-w-md">
      <div className="w-12 h-12 rounded-full bg-sage/30 flex items-center justify-center mb-6">
        <span className="text-forest text-xl" aria-hidden="true">✓</span>
      </div>
      <h2 className="font-display text-h2 font-medium text-forest mb-3">
        We've received your request.
      </h2>
      <p className="font-body text-body-lg text-ink mb-6">
        A Kyros care coordinator will call you within 4 hours to schedule your consultation.
        Check your phone — they will call from a Bengaluru number.
      </p>
      <p className="font-body text-body text-stone">
        Questions in the meantime?{' '}
        <a href="/faq" className="text-forest underline">
          See our FAQ
        </a>{' '}
        or{' '}
        <a href="/contact" className="text-forest underline">
          contact us
        </a>
        .
      </p>
    </div>
  );
}