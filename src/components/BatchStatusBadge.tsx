import { cn } from '@/lib/utils';
import { batchStatusMap, type BatchStatus } from '@/types';

interface BatchStatusBadgeProps {
  status: BatchStatus;
  className?: string;
}

export default function BatchStatusBadge({ status, className }: BatchStatusBadgeProps) {
  const config = batchStatusMap[status];
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
