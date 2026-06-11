import type { ArticleReviewer } from "../../lib/mdx";

interface DoctorBylineProps {
  reviewer?: ArticleReviewer;
  reviewedAt: string;
  compact?: boolean;
}

function formatReviewDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-IN", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

const PLACEHOLDER_NAME = "TO BE ADDED AT PUBLISH";

function isNamed(reviewer?: ArticleReviewer): boolean {
  return Boolean(reviewer?.name) && reviewer!.name !== PLACEHOLDER_NAME;
}

export function DoctorByline({ reviewer, reviewedAt, compact = false }: DoctorBylineProps) {
  const named = isNamed(reviewer);
  const reviewedDate = formatReviewDate(reviewedAt);
  const specialty = reviewer?.specialty;

  if (compact) {
    return (
      <p className="font-body text-caption text-stone">
        {named ? (
          <>
            Reviewed by <span className="text-forest font-medium">{reviewer!.name}</span>
            {reviewer!.nmcRegNo ? (
              <>
                {" · "}
                <span className="font-mono">NMC Reg. {reviewer!.nmcRegNo}</span>
              </>
            ) : null}
          </>
        ) : (
          <>
            Reviewed by a Kyros{specialty ? ` ${specialty}` : ""} specialist
          </>
        )}
        {reviewedDate ? <>{" · "}{reviewedDate}</> : null}
      </p>
    );
  }

  return (
    <div className="flex items-start gap-4 py-5 border-t border-b border-forest/10">
      {/* Avatar placeholder */}
      <div
        className="w-12 h-12 rounded-full bg-sage/20 flex-shrink-0 flex items-center justify-center"
        aria-hidden="true"
      >
        <span className="font-display text-h3 font-medium text-forest">
          {named ? reviewer!.name.replace("Dr. ", "").charAt(0) : "K"}
        </span>
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
          <p className="font-body text-body-lg font-medium text-forest">
            {named ? reviewer!.name : "Reviewed by a Kyros specialist"}
          </p>
          {named && reviewer!.credentials ? (
            <p className="font-body text-caption text-stone">{reviewer!.credentials}</p>
          ) : null}
        </div>
        {specialty ? (
          <p className="font-body text-caption text-stone mt-0.5">
            {specialty}
            {named && reviewer!.nmcRegNo ? (
              <>
                {" · NMC Reg. "}
                <span className="font-mono">{reviewer!.nmcRegNo}</span>
              </>
            ) : null}
          </p>
        ) : null}
        {reviewedDate ? (
          <p className="font-body text-caption text-stone mt-0.5">
            Medically reviewed: {reviewedDate}
          </p>
        ) : null}
      </div>
    </div>
  );
}
