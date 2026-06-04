export interface Notification {
  id: string;
  template_name: string;
  title: string;
  body: string;
  channels: string[];
  data: Record<string, string>;
  read_at: string | null;
  sent_at: string;
  created_at: string;
}

export interface NotificationListResponse {
  items: Notification[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  unread_count: number;
}

export interface MarkAllReadResponse {
  marked_read: number;
}

export interface NotificationPreferences {
  push: boolean;
  whatsapp: boolean;
  email: boolean;
}

export interface NotificationPreferencesUpdate {
  push?: boolean;
  whatsapp?: boolean;
  email?: boolean;
}
