import { cn } from '@/lib/utils';
import { statusMap, type TicketStatus } from '@/types';

interface StatusBadgeProps {
  status: TicketStatus;
  className?: string;
}

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusMap[status];
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
