import { cn } from '@/lib/utils';
import { statusMap, type TicketStatus } from '@/types';

interface StatusBadgeProps {
  status: TicketStatus | string;
  className?: string;
}

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusMap[status as TicketStatus];
  if (!config) {
    const specialLabels: Record<string, { label: string; color: string }> = {
      plan_referenced: { label: '引用预案', color: 'bg-purple-100 text-purple-800 border-purple-300' },
    };
    const fallback = specialLabels[status] || {
      label: status,
      color: 'bg-gray-100 text-gray-800 border-gray-300',
    };
    return (
      <span
        className={cn(
          'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium',
          fallback.color,
          className,
        )}
      >
        {fallback.label}
      </span>
    );
  }
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium',
        config.color,
        className,
      )}
    >
      {config.label}
    </span>
  );
}
