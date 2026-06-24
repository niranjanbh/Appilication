import type { ReactElement } from 'react';
import type { RefreshControlProps } from 'react-native';
import type { DailySummary, Reminder, WeekDaySummary } from '../../../types/wellness';

export interface ReminderListProps {
  reminders: Reminder[];
  selectedDate: Date;
  onDateChange: (date: Date) => void;
  onEdit: (reminder: Reminder) => void;
  onDelete: (reminder: Reminder) => void;
  onToggle: (reminder: Reminder) => void;
  onTakeNow: (reminder: Reminder) => void;
  dailySummary?: DailySummary | null;
  weekSummary?: WeekDaySummary[] | null;
  refreshControl?: ReactElement<RefreshControlProps>;
}
