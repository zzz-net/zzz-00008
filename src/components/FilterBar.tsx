import { useState, useEffect } from 'react';
import { Filter, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/store/useAuthStore';
import { statusMap, severityMap, type TicketStatus, type Severity } from '@/types';

interface FilterBarProps {
  onFilterChange: (filters: {
    status?: TicketStatus;
    severity?: Severity;
    assignee?: string;
  }) => void;
  className?: string;
}

export default function FilterBar({ onFilterChange, className }: FilterBarProps) {
  const [status, setStatus] = useState<TicketStatus | ''>('');
  const [severity, setSeverity] = useState<Severity | ''>('');
  const [assignee, setAssignee] = useState('');
  const fetchUsers = useAuthStore((state) => state.fetchUsers);
  const users = useAuthStore((state) => state.users);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  useEffect(() => {
    onFilterChange({
      ...(status ? { status } : {}),
      ...(severity ? { severity } : {}),
      ...(assignee ? { assignee } : {}),
    });
  }, [status, severity, assignee, onFilterChange]);

  const handleClear = () => {
    setStatus('');
    setSeverity('');
    setAssignee('');
  };

  const hasFilters = status || severity || assignee;

  return (
    <div
      className={cn(
        'flex flex-wrap items-center gap-4 rounded-lg border border-gray-200 bg-white p-4',
        className,
      )}
    >
      <div className="flex items-center gap-2 text-gray-500">
        <Filter className="h-4 w-4" />
        <span className="text-sm font-medium">筛选</span>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value as TicketStatus | '')}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
        >
          <option value="">全部状态</option>
          {Object.entries(statusMap).map(([key, val]) => (
            <option key={key} value={key}>
              {val.label}
            </option>
          ))}
        </select>

        <select
          value={severity}
          onChange={(e) => setSeverity(e.target.value as Severity | '')}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
        >
          <option value="">全部优先级</option>
          {Object.entries(severityMap).map(([key, val]) => (
            <option key={key} value={key}>
              {val.label}
            </option>
          ))}
        </select>

        <select
          value={assignee}
          onChange={(e) => setAssignee(e.target.value)}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
        >
          <option value="">全部负责人</option>
          {Object.entries(users).map(([username, info]) => (
            <option key={username} value={username}>
              {info.name} ({username})
            </option>
          ))}
        </select>
      </div>

      {hasFilters && (
        <button
          onClick={handleClear}
          className="ml-auto flex items-center gap-1 rounded-lg px-3 py-2 text-sm text-gray-500 hover:bg-gray-100 hover:text-gray-700"
        >
          <X className="h-4 w-4" />
          清除筛选
        </button>
      )}
    </div>
  );
}
