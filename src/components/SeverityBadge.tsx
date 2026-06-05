import { cn } from '@/lib/utils';
import { severityMap, type Severity } from '@/types';

interface SeverityBadgeProps {
  severity: Severity;
  className?: string;
}

export default function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  const config = severityMap[severity];
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
