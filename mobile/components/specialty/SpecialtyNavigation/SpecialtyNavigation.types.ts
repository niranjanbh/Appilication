export type VerticalId =
  | 'weight'
  | 'thyroid'
  | 'pcos'
  | 'skin-hair'
  | 'intimate-health'
  | 'hormones-trt'
  | 'longevity'
  | 'conditions';

export interface DoctorCardData {
  id: string;
  name: string;
  qualification: string;
  nmcRegistration: string;
  nextAvailability: string;
}

export interface SpecialtyNavigationProps {
  selectedVertical: VerticalId;
  onSelectVertical: (vertical: VerticalId) => void;
  doctors: DoctorCardData[];
  onBookConsultation: (doctor: DoctorCardData) => void;
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
}
