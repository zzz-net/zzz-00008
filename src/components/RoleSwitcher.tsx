import { useState, useRef, useEffect } from 'react';
import { ChevronDown, UserCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/store/useAuthStore';
import RoleBadge from './RoleBadge';
import { roleMap } from '@/types';

const demoUsers = [
  { role: 'cs' as const, username: 'cs_demo', name: '客服演示账号' },
  { role: 'handover' as const, username: 'handover_demo', name: '交班人演示账号' },
  { role: 'receiver' as const, username: 'receiver_demo', name: '接班人演示账号' },
];

export default function RoleSwitcher() {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const user = useAuthStore((state) => state.user);
  const loading = useAuthStore((state) => state.loading);
  const switchRole = useAuthStore((state) => state.switchRole);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSwitch = async (role: string, username: string) => {
    const success = await switchRole(role, username);
    if (success) {
      setOpen(false);
    }
  };

  return (
    <div ref={containerRef} className="relative">
      <button
        onClick={() => setOpen(!open)}
        disabled={loading}
        className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <UserCircle className="h-4 w-4 text-[#1e3a5f]" />
        )}
        {user ? (
          <RoleBadge role={user.role} />
        ) : (
          <span className="text-gray-500">选择角色</span>
        )}
        <ChevronDown className={cn('h-4 w-4 transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-64 rounded-lg border border-gray-200 bg-white shadow-lg">
          <div className="border-b border-gray-100 p-3">
            <p className="text-xs font-medium text-gray-500">切换演示角色</p>
          </div>
          <div className="p-1">
            {demoUsers.map((demoUser) => (
              <button
                key={demoUser.username}
                onClick={() => handleSwitch(demoUser.role, demoUser.username)}
                disabled={loading}
                className={cn(
                  'flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left text-sm transition-colors',
                  user?.username === demoUser.username
                    ? 'bg-[#1e3a5f]/10 text-[#1e3a5f]'
                    : 'text-gray-700 hover:bg-gray-50',
                  loading && 'opacity-50',
                )}
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100">
                  <UserCircle className="h-5 w-5 text-gray-500" />
                </div>
                <div className="flex-1">
                  <p className="font-medium">{demoUser.name}</p>
                  <div className="mt-0.5 flex items-center gap-2">
                    <span className="text-xs text-gray-500">{demoUser.username}</span>
                    <span
                      className={cn(
                        'rounded px-1.5 py-0.5 text-[10px] font-medium',
                        roleMap[demoUser.role].color,
                      )}
                    >
                      {roleMap[demoUser.role].label}
                    </span>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
