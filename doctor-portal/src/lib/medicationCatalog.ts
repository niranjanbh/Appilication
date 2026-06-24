import { apiFetch } from './api';

export interface MedicationCatalogItem {
  id: string;
  name: string;
  generic_name: string | null;
  form: string | null;
  strength: string | null;
  has_image: boolean;
}

interface CatalogSearchResponse {
  items: MedicationCatalogItem[];
}

/** Search the admin-curated medication catalog by name (doctor-scoped). */
export function searchMedicationCatalog(query: string, limit = 10): Promise<CatalogSearchResponse> {
  const params = new URLSearchParams();
  if (query.trim()) params.set('search', query.trim());
  params.set('limit', String(limit));
  return apiFetch<CatalogSearchResponse>(`/v1/doctor/medication-catalog?${params.toString()}`);
}

/** Fetch a short-lived presigned URL for a catalog entry's image. */
export function getMedicationCatalogImageUrl(catalogId: string): Promise<{ url: string }> {
  return apiFetch<{ url: string }>(`/v1/doctor/medication-catalog/${catalogId}/image-url`);
}
