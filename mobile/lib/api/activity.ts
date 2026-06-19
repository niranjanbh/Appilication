/**
 * Account activity history API client (patient-facing).
 */

import { apiFetch } from './client';

export interface ActivityItem {
  action: string;
  description: string;
  resource_type: string | null;
  allowed: boolean;
  ip_address: string | null;
  timestamp: string;
}

export interface ActivityListResponse {
  items: ActivityItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export function listActivityApi(page = 1, pageSize = 50): Promise<ActivityListResponse> {
  return apiFetch(`/v1/users/me/activity?page=${page}&page_size=${pageSize}`);
}
