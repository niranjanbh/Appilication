interface Step {
  number: number;
  title: string;
  body: string;
}

interface ProcessStepsProps {
  steps: Step[];
  heading?: string;
}

export function ProcessSteps({ steps, heading }: ProcessStepsProps) {
  return (
    <section className="bg-ivory py-16 px-6">
      <div className="max-w-4xl mx-auto">
        {heading && (
          <h2 className="font-display text-h2 font-medium text-forest mb-12 text-center">
            {heading}
          </h2>
        )}
        <ol className="space-y-10" role="list">
          {steps.map((step) => (
            <li key={step.number} className="flex gap-6">
              <div
                className="flex-shrink-0 w-10 h-10 rounded-full bg-saffron flex items-center justify-center"
                aria-hidden="true"
              >
                <span className="font-display text-h3 font-medium text-forest">
                  {step.number}
                </span>
              </div>
              <div className="pt-1">
                <h3 className="font-display text-h3 font-medium text-forest mb-2">
                  {step.title}
                </h3>
                <p className="font-body text-body text-ink leading-relaxed">{step.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
