import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BookOpen, Check } from 'lucide-react';
import { apiFetch } from '../lib/api';

interface EducationContent {
  id: string;
  title: string;
  slug: string;
  content_type: string;
  condition_categories: string[];
  ai_disclosure: boolean;
  status: string;
}

function formatType(s: string) {
  return s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

interface EducationAssignPanelProps {
  consultationId: string;
}

export function EducationAssignPanel({ consultationId }: EducationAssignPanelProps) {
  const qc = useQueryClient();
  const [assignedIds, setAssignedIds] = useState<Set<string>>(new Set());

  const { data: content = [], isLoading } = useQuery<EducationContent[]>({
    queryKey: ['doctor-content'],
    queryFn: () => apiFetch<EducationContent[]>(`/v1/doctor/content`),
    staleTime: 60_000,
  });

  const assign = useMutation({
    mutationFn: (contentId: string) =>
      apiFetch<{ id: string }>(`/v1/doctor/consultations/${consultationId}/education`, {
        method: 'POST',
        body: JSON.stringify({ content_id: contentId }),
      }),
    onSuccess: (_data, contentId) => {
      setAssignedIds(prev => new Set(prev).add(contentId));
      qc.invalidateQueries({ queryKey: ['consultation-education', consultationId] });
    },
  });

  if (isLoading) {
    return <p className="font-body text-caption text-stone">Loading education content…</p>;
  }

  if (content.length === 0) {
    return <p className="font-body text-caption text-stone">No education content available.</p>;
  }

  return (
    <div>
      <h3 className="font-body text-body font-semibold text-forest mb-3">Assign education content</h3>
      <ul className="space-y-2">
        {content.map(item => {
          const isAssigned = assignedIds.has(item.id);
          const isPending = assign.isPending && assign.variables === item.id;
          return (
            <li key={item.id} className="border border-stone/15 rounded p-3 flex items-start gap-3">
              <BookOpen size={16} className="text-forest shrink-0 mt-0.5" strokeWidth={1.75} />
              <div className="flex-1 min-w-0">
                <p className="font-body text-body font-medium text-ink">{item.title}</p>
                <p className="font-body text-caption text-stone">
                  {formatType(item.content_type)}
                  {item.condition_categories.length > 0 && ` · ${item.condition_categories.map(formatType).join(', ')}`}
                </p>
                {item.ai_disclosure && (
                  <p className="font-body text-caption text-stone/60 mt-0.5">AI-assisted content</p>
                )}
              </div>
              <button
                onClick={() => assign.mutate(item.id)}
                disabled={isAssigned || isPending}
                className={`shrink-0 font-body text-caption font-semibold px-3 py-1.5 rounded-md transition-colors ${
                  isAssigned
                    ? 'bg-sage/20 text-forest cursor-default'
                    : 'bg-forest text-ivory hover:bg-jade disabled:opacity-40'
                }`}
              >
                {isAssigned ? (
                  <span className="inline-flex items-center gap-1"><Check size={12} /> Assigned</span>
                ) : isPending ? 'Assigning…' : 'Assign'}
              </button>
            </li>
          );
        })}
      </ul>
      {assign.isError && (
        <p className="font-body text-caption text-alert mt-2">Failed to assign content. Please try again.</p>
      )}
    </div>
  );
}
