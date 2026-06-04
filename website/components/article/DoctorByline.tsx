import type { DoctorProfile } from "../../lib/doctors";

interface DoctorBylineProps {
  doctor: DoctorProfile;
  reviewedAt: string;
  compact?: boolean;
}

function formatReviewDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export function DoctorByline({ doctor, reviewedAt, compact = false }: DoctorBylineProps) {
  if (compact) {
    return (
      <p className="font-body text-caption text-stone">
        Reviewed by{" "}
        <span className="text-forest font-medium">{doctor.name}</span>
        {" · "}
        <span className="font-mono">{doctor.nmcRegistration}</span>
        {" · "}
        {formatReviewDate(reviewedAt)}
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
          {doctor.name.replace("Dr. ", "").charAt(0)}
        </span>
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
          <p className="font-body text-body-lg font-medium text-forest">{doctor.name}</p>
          <p className="font-body text-caption text-stone">{doctor.qualifications}</p>
        </div>
        <p className="font-body text-caption text-stone mt-0.5">
          {doctor.specialty}
          {" · NMC Reg. "}
          <span className="font-mono">{doctor.nmcRegistration}</span>
        </p>
        <p className="font-body text-caption text-stone mt-0.5">
          Medically reviewed: {formatReviewDate(reviewedAt)}
        </p>
      </div>
    </div>
  );
}
