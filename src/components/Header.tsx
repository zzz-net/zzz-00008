import { Bell, Search, User } from 'lucide-react';
import RoleSwitcher from './RoleSwitcher';
import { useAuthStore } from '@/store/useAuthStore';

export default function Header() {
  const user = useAuthStore((state) => state.user);

  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-6">
      <div className="flex items-center gap-4">
        <h2 className="text-xl font-semibold text-gray-900">客服升级值班交接系统</h2>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="搜索..."
            className="w-64 rounded-lg border border-gray-300 bg-gray-50 py-2 pl-10 pr-4 text-sm text-gray-900 placeholder-gray-400 focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
          />
        </div>

        <button className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700">
          <Bell className="h-5 w-5" />
        </button>

        <RoleSwitcher />

        <div className="flex items-center gap-3 border-l border-gray-200 pl-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#1e3a5f] text-white">
            <User className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-900">{user?.name || '用户'}</p>
            <p className="text-xs text-gray-500">{user?.username || ''}</p>
          </div>
        </div>
      </div>
    </header>
  );
}
