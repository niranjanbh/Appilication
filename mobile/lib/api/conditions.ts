import { publicFetch } from './client';

export interface Condition {
  slug: string;
  name: string;
  short_description: string;
}

/** Public catalogue of treatable conditions. Unauthenticated. */
export function listConditions(): Promise<Condition[]> {
  return publicFetch<Condition[]>('/v1/public/conditions');
}
