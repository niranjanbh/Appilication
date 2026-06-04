/**
 * Placeholder doctor registry for seed/development articles.
 *
 * These are synthetic profiles used until real panel doctors are onboarded (P10).
 * In production, replace IDs with actual dr_doctors UUIDs and populate from the API.
 * NMC registration numbers below are fictional — do not publish live without substitution.
 */

export interface DoctorProfile {
  id: string;
  name: string;
  qualifications: string;
  specialty: string;
  nmcRegistration: string;
  bio: string;
}

export const DOCTORS: Record<string, DoctorProfile> = {
  "placeholder-dr-arun-mehta": {
    id: "placeholder-dr-arun-mehta",
    name: "Dr. Arun Mehta",
    qualifications: "MBBS, MD Endocrinology",
    specialty: "Endocrinology",
    nmcRegistration: "DEV-00000001",
    bio: "Endocrinologist with expertise in thyroid disorders, PCOS, hormonal imbalance, and diabetes.",
  },
  "placeholder-dr-priya-reddy": {
    id: "placeholder-dr-priya-reddy",
    name: "Dr. Priya Reddy",
    qualifications: "MBBS, MD Dermatology",
    specialty: "Dermatology",
    nmcRegistration: "DEV-00000002",
    bio: "Dermatologist specialising in androgenetic alopecia, adult acne, melasma, and hormonal skin conditions.",
  },
  "placeholder-dr-vikram-nair": {
    id: "placeholder-dr-vikram-nair",
    name: "Dr. Vikram Nair",
    qualifications: "MBBS, MS Urology",
    specialty: "Urology",
    nmcRegistration: "DEV-00000003",
    bio: "Urologist with clinical interest in andrology, erectile dysfunction, and men's hormonal health.",
  },
  "placeholder-dr-sunita-patel": {
    id: "placeholder-dr-sunita-patel",
    name: "Dr. Sunita Patel",
    qualifications: "MBBS, MD Internal Medicine",
    specialty: "Internal Medicine",
    nmcRegistration: "DEV-00000004",
    bio: "Internist specialising in metabolic disorders, weight management, and cardiometabolic risk.",
  },
};

export function getDoctor(id: string): DoctorProfile | undefined {
  return DOCTORS[id];
}
