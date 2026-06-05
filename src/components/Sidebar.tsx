import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Ticket, Package, CalendarClock, Plus, ChevronDown, ChevronRight, BellRing } from 'lucide-react';
import { cn } from '@/lib/utils';

const menuItems = [
  { to: '/', label: '仪表盘', icon: LayoutDashboard },
  { to: '/tickets', label: '升级单', icon: Ticket },
  { to: '/batches', label: '交接批次', icon: Package },
  { to: '/shifts', label: '值班排班', icon: CalendarClock },
  { to: '/reminders', label: '值班提醒', icon: BellRing },
];

export default function Sidebar() {
  const [createOpen, setCreateOpen] = useState(false);

  return (
    <aside className="flex h-screen w-64 flex-col bg-[#1e3a5f] text-white">
      <div className="flex h-16 items-center border-b border-white/10 px-6">
        <h1 className="text-lg font-bold">客服升级交接系统</h1>
      </div>

      <nav className="flex-1 space-y-1 p-4">
        {menuItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-white/20 text-white'
                    : 'text-white/70 hover:bg-white/10 hover:text-white',
                )
              }
            >
              <Icon className="h-5 w-5" />
              {item.label}
            </NavLink>
          );
        })}

        <div className="pt-4">
          <button
            onClick={() => setCreateOpen(!createOpen)}
            className="flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-sm font-medium text-white/70 hover:bg-white/10 hover:text-white"
          >
            <div className="flex items-center gap-3">
              <Plus className="h-5 w-5" />
              新建
            </div>
            {createOpen ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>

          {createOpen && (
            <div className="ml-8 mt-1 space-y-1">
              <NavLink
                to="/tickets/new"
                className={({ isActive }) =>
                  cn(
                    'block rounded-lg px-3 py-2 text-sm transition-colors',
                    isActive
                      ? 'bg-white/20 text-white'
                      : 'text-white/60 hover:bg-white/10 hover:text-white',
                  )
                }
              >
                新建升级单
              </NavLink>
              <NavLink
                to="/batches/new"
                className={({ isActive }) =>
                  cn(
                    'block rounded-lg px-3 py-2 text-sm transition-colors',
                    isActive
                      ? 'bg-white/20 text-white'
                      : 'text-white/60 hover:bg-white/10 hover:text-white',
                  )
                }
              >
                新建交接批次
              </NavLink>
            </div>
          )}
        </div>
      </nav>

      <div className="border-t border-white/10 p-4">
        <p className="text-xs text-white/50">版本 1.0.0</p>
      </div>
    </aside>
  );
}
