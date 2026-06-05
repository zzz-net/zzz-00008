import { cn } from '@/lib/utils';
import { roleMap, type Role } from '@/types';

interface RoleBadgeProps {
  role: Role;
  className?: string;
}

export default function RoleBadge({ role, className }: RoleBadgeProps) {
  const config = roleMap[role];
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        config.color,
        className,
      )}
    >
      {config.label}
    </span>
  );
}
