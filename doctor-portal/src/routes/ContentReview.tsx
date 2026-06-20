import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, FileText, X } from 'lucide-react';
import { apiFetch } from '../lib/api';

interface ContentItem {
  id: string;
  title: string;
  slug: string;
  content_type: string;
  condition_categories: string[];
  body_md: string | null;
  content_url: string | null;
  ai_disclosure: boolean;
  status: string;
  created_at: string;
  updated_at: string;
}

function formatType(s: string) {
  return s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function formatIST(iso: string) {
  return new Date(iso).toLocaleString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: true,
    timeZone: 'Asia/Kolkata',
  });
}

function ReviewCard({ item }: { item: ContentItem }) {
  const qc = useQueryClient();
  const [notes, setNotes] = useState('');
  const [expanded, setExpanded] = useState(false);

  const review = useMutation({
    mutationFn: (action: 'approved' | 'rejected') =>
      apiFetch<ContentItem>(`/v1/doctor/content/${item.id}/review`, {
        method: 'POST',
        body: JSON.stringify({ action, notes: notes.trim() || null }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['content-review-queue'] }),
  });

  return (
    <div className="bg-white rounded-card p-5 border border-stone/15">
      <div className="flex items-start gap-3 mb-2">
        <FileText size={18} className="text-forest shrink-0 mt-0.5" strokeWidth={1.75} />
        <div className="flex-1 min-w-0">
          <h2 className="font-display text-h3 text-forest font-medium">{item.title}</h2>
          <p className="font-body text-caption text-stone">
            {formatType(item.content_type)}
            {item.condition_categories.length > 0 &&
              ` · ${item.condition_categories.map(formatType).join(', ')}`}
            {item.ai_disclosure && ' · AI-assisted'}
          </p>
          <p className="font-body text-caption text-stone/60 mt-0.5">
            Submitted {formatIST(item.updated_at)}
          </p>
        </div>
      </div>

      {item.body_md && (
        <div className="mb-3">
          <button
            onClick={() => setExpanded(e => !e)}
            className="font-body text-caption font-semibold text-forest hover:underline"
          >
            {expanded ? 'Hide content' : 'Preview content'}
          </button>
          {expanded && (
            <pre className="mt-2 whitespace-pre-wrap font-body text-caption text-ink bg-ivory rounded p-3 max-h-72 overflow-auto">
              {item.body_md}
            </pre>
          )}
        </div>
      )}

      {item.content_url && (
        <a
          href={item.content_url}
          target="_blank"
          rel="noreferrer"
          className="inline-block font-body text-caption font-semibold text-forest hover:underline mb-3"
        >
          Open linked content →
        </a>
      )}

      <div className="mb-3">
        <label className="font-body text-caption text-stone block mb-1">Review notes (optional)</label>
        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          rows={2}
          placeholder="Reason for rejection, or notes for the author…"
          className="w-full font-body text-caption text-ink border border-stone/30 rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-forest/50"
        />
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => review.mutate('approved')}
          disabled={review.isPending}
          className="inline-flex items-center gap-1.5 bg-forest text-ivory font-body text-caption font-semibold px-4 py-2 rounded-md hover:bg-jade transition-colors disabled:opacity-50"
        >
          <Check size={14} /> Approve
        </button>
        <button
          onClick={() => review.mutate('rejected')}
          disabled={review.isPending}
          className="inline-flex items-center gap-1.5 font-body text-caption font-semibold text-alert border border-alert/40 px-4 py-2 rounded-md hover:bg-alert/5 transition-colors disabled:opacity-50"
        >
          <X size={14} /> Reject
        </button>
      </div>

      {review.isError && (
        <p className="font-body text-caption text-alert mt-2">Failed to submit review. Please try again.</p>
      )}
    </div>
  );
}

export function ContentReview() {
  const { data: items = [], isLoading, isError } = useQuery<ContentItem[]>({
    queryKey: ['content-review-queue'],
    queryFn: () => apiFetch<ContentItem[]>(`/v1/doctor/content`),
  });

  return (
    <div className="px-8 py-8 max-w-3xl">
      <h1 className="font-display text-h2 text-forest font-medium mb-1">Content review</h1>
      <p className="font-body text-body text-stone mb-6">
        Education content pending clinical sign-off.
      </p>

      {isLoading ? (
        <p className="font-body text-body text-stone">Loading…</p>
      ) : isError ? (
        <p className="font-body text-body text-alert">Could not load the review queue.</p>
      ) : items.length === 0 ? (
        <p className="font-body text-body text-stone">Nothing pending review.</p>
      ) : (
        <div className="space-y-4">
          {items.map(item => (
            <ReviewCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
