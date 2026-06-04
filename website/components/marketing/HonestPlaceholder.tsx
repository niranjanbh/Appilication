interface HonestPlaceholderProps {
  type: 'doctor' | 'advisor' | 'testimonial';
  count?: number;
}

const COPY: Record<
  HonestPlaceholderProps['type'],
  { heading: string; body: string; card: string }
> = {
  doctor: {
    heading: 'Our doctors are being introduced carefully.',
    body:
      'Kyros doctors are verified by NMC registration and specialty. We are onboarding our first panel now — only doctors we have vetted in person and whose clinical approach we stand behind. We will introduce each doctor by name and credentials as they come on board.',
    card: 'Doctor joining soon',
  },
  advisor: {
    heading: 'Our advisory board is being formed with care.',
    body:
      'We will name advisors here only once they have confirmed their role in writing. Aspirational names are not on this page. Every advisor listed has reviewed the platform and agreed to contribute.',
    card: 'Advisor joining soon',
  },
  testimonial: {
    heading: 'Patient stories will appear here once our clinic is live.',
    body:
      'We do not publish testimonials we have not independently verified. As patients complete consultations and consent to sharing their experience, their stories will appear here with their permission.',
    card: 'Patient story coming soon',
  },
};

export function HonestPlaceholder({ type, count = 3 }: HonestPlaceholderProps) {
  const copy = COPY[type];
  return (
    <section className="bg-ivory py-16 px-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-10">
          <h2 className="font-display text-h2 font-medium text-forest mb-3">{copy.heading}</h2>
          <p className="font-body text-body text-stone max-w-2xl">{copy.body}</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {Array.from({ length: count }).map((_, i) => (
            <div
              key={i}
              className="bg-white rounded-card p-8 border border-forest/8 flex flex-col items-center justify-center min-h-48"
            >
              <div className="w-16 h-16 rounded-full bg-sage/20 mb-4" aria-hidden="true" />
              <p className="font-body text-caption text-stone text-center">{copy.card}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
