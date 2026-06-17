import type { Reminder } from '../../../types/wellness';

export interface ReminderListProps {
  reminders: Reminder[];
  selectedDate: Date;
  onDateChange: (date: Date) => void;
  onEdit: (reminder: Reminder) => void;
  onDelete: (reminder: Reminder) => void;
}
