'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const contactSchema = z.object({
  name: z.string().min(2, 'Please enter your name'),
  email: z.string().email('Enter a valid email address'),
  subject: z.string().min(1, 'Please choose a subject'),
  message: z.string().min(10, 'Please enter a message (minimum 10 characters)').max(1000),
});

type ContactFormData = z.infer<typeof contactSchema>;

export function ContactForm() {
  const [submitted, setSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ContactFormData>({ resolver: zodResolver(contactSchema) });

  const onSubmit = async (data: ContactFormData) => {
    setSubmitError(null);
    try {
      const resp = await fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!resp.ok) throw new Error('Submission failed. Please try again.');
      setSubmitted(true);
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : 'Something went wrong.');
    }
  };

  if (submitted) {
    return (
      <div className="bg-sage/15 rounded-card p-8">
        <p className="font-display text-h3 font-medium text-forest mb-2">Message received.</p>
        <p className="font-body text-body text-ink">
          Thank you. We will reply to your email within 1 business day.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
      <div>
        <label htmlFor="contact-name" className="block font-body text-body font-medium text-ink mb-1">
          Your name
        </label>
        <input
          id="contact-name"
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

      <div>
        <label htmlFor="contact-email" className="block font-body text-body font-medium text-ink mb-1">
          Email address
        </label>
        <input
          id="contact-email"
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

      <div>
        <label htmlFor="contact-subject" className="block font-body text-body font-medium text-ink mb-1">
          Subject
        </label>
        <select
          id="contact-subject"
          {...register('subject')}
          className="w-full border border-forest/25 rounded-input px-4 py-3 font-body text-body text-ink
                     focus:outline-none focus:border-forest focus:ring-1 focus:ring-forest bg-white"
        >
          <option value="">Choose a subject</option>
          <option value="consultation-enquiry">Consultation enquiry</option>
          <option value="doctor-application">Doctor application</option>
          <option value="support">Support</option>
          <option value="data-privacy">Data and privacy</option>
          <option value="press">Press</option>
          <option value="other">Other</option>
        </select>
        {errors.subject && (
          <p className="font-body text-caption text-alert mt-1">{errors.subject.message}</p>
        )}
      </div>

      <div>
        <label htmlFor="contact-message" className="block font-body text-body font-medium text-ink mb-1">
          Message
        </label>
        <textarea
          id="contact-message"
          rows={5}
          {...register('message')}
          className="w-full border border-forest/25 rounded-input px-4 py-3 font-body text-body text-ink
                     focus:outline-none focus:border-forest focus:ring-1 focus:ring-forest
                     placeholder:text-stone resize-none"
          placeholder="Tell us what you'd like to know…"
        />
        {errors.message && (
          <p className="font-body text-caption text-alert mt-1">{errors.message.message}</p>
        )}
      </div>

      {submitError && (
        <p className="font-body text-body text-alert bg-alert/8 rounded-card px-4 py-3">
          {submitError}
        </p>
      )}

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full inline-flex items-center justify-center px-8 py-3
                   rounded-button bg-forest text-ivory font-body font-medium text-body-lg
                   disabled:opacity-60 disabled:cursor-not-allowed
                   hover:bg-jade transition-colors duration-micro"
      >
        {isSubmitting ? 'Sending…' : 'Send message'}
      </button>
    </form>
  );
}
