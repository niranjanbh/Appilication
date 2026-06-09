'use client';

import { useState } from 'react';

const FAQS = [
  {
    question: 'How is Kyros different from other Indian telemedicine platforms?',
    answer:
      'Most Indian telemedicine platforms connect you to any available doctor for a single visit. Kyros assigns you to one specialist who stays with you — reading your labs, adjusting your plan, and building a clinical record over time. We cover specific chronic and hormonal conditions, not general consultations.',
  },
  {
    question: 'How long does the whole process take, from filling the form to seeing a doctor?',
    answer:
      'The intake form takes 5–10 minutes. Same-day and next-day slots are typically available. Most patients see their doctor within 24–48 hours of booking.',
  },
  {
    question: 'Do I have to know which specialist I need before signing up?',
    answer:
      'No. You choose the condition closest to your concern — thyroid, PCOS, weight, hormones, and so on. If you are unsure, a care coordinator can help match you to the right vertical before your consultation.',
  },
  {
    question: 'Can my parents, partner, or child use my Kyros account?',
    answer:
      'No. Because your dashboard acts as your personal, longitudinal health record, every adult must have their own individual account to ensure clinical safety and data privacy.',
  },
  {
    question: 'Is my health data private?',
    answer:
      "Yes. Kyros operates under India's Digital Personal Data Protection Act. Your health data stays on servers in India, condition names never appear in notifications, and you can export or delete your data at any time.",
  },
];

export function HomeFAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <section className="bg-ivory py-16 px-6">
      <div className="max-w-3xl mx-auto">
        <h2 className="font-display text-h2 font-medium text-forest mb-10">
          Common questions
        </h2>
        <div>
          {FAQS.map((faq, i) => {
            const isOpen = openIndex === i;
            return (
              <div key={faq.question} className="border-t border-forest/12">
                <button
                  onClick={() => setOpenIndex(isOpen ? null : i)}
                  className="w-full flex items-start justify-between gap-6 py-6 text-left"
                  aria-expanded={isOpen}
                >
                  <span className="font-body text-body text-ink leading-snug">
                    {faq.question}
                  </span>
                  <span
                    className="flex-shrink-0 font-body text-h3 font-light text-forest leading-none mt-0.5 transition-transform duration-micro"
                    aria-hidden="true"
                  >
                    {isOpen ? '−' : '+'}
                  </span>
                </button>

                <div
                  className={`grid transition-[grid-template-rows] duration-300 ease-in-out ${
                    isOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'
                  }`}
                >
                  <div className="overflow-hidden">
                    <p className="font-body text-body text-stone leading-relaxed pb-6">
                      {faq.answer}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
          <div className="border-t border-forest/12" />
        </div>
      </div>
    </section>
  );
}
