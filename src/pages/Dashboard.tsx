import { useEffect, useState } from 'react';
import { ClipboardList, Clock, CheckCircle, AlertTriangle, Activity, Package, BellRing, CheckCircle2 } from 'lucide-react';
import { dashboardApi, reminderApi } from '@/services/api';
import { useToast } from '@/hooks/useToast';
import StatusBadge from '@/components/StatusBadge';
import SeverityBadge from '@/components/SeverityBadge';
import BatchStatusBadge from '@/components/BatchStatusBadge';
import { formatDateTime, getEntityLabel } from '@/utils/format';
import { useAuthStore } from '@/store/useAuthStore';
import type { DashboardStats, TicketStatus, Severity, BatchStatus, DutyReminder } from '@/types';

const statCardConfig: { status: TicketStatus; label: string; icon: typeof ClipboardList; color: string }[] = [
  { status: 'open', label: '待处理', icon: ClipboardList, color: 'text-blue-600' },
  { status: 'in_progress', label: '处理中', icon: Clock, color: 'text-purple-600' },
  { status: 'closed', label: '已关闭', icon: CheckCircle, color: 'text-gray-600' },
  { status: 'overdue', label: '已逾期', icon: AlertTriangle, color: 'text-red-600' },
];

const severityConfig: { severity: Severity; label: string }[] = [
  { severity: 'low', label: '低危' },
  { severity: 'medium', label: '中危' },
  { severity: 'high', label: '高危' },
  { severity: 'critical', label: '严重' },
];

const batchConfig: { status: BatchStatus; label: string }[] = [
  { status: 'pending', label: '待确认' },
  { status: 'confirmed', label: '已确认' },
  { status: 'returned', label: '已退回' },
];

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [pendingReminders, setPendingReminders] = useState<DutyReminder[]>([]);
  const [confirmingId, setConfirmingId] = useState<number | null>(null);
  const showToast = useToast((state) => state.showToast);
  const canConfirm = useAuthStore((s) => s.hasPermission('confirm_reminders'));

  const fetchStats = async () => {
    try {
      const res = await dashboardApi.getStats();
      if (res.success && res.data) {
        setStats(res.data);
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '获取统计数据失败', 'error');
    }
  };

  const fetchPendingReminders = async () => {
    try {
      const res = await reminderApi.getMyPending();
      if (res.success && res.data) {
        setPendingReminders(res.data);
      }
    } catch (e) {
      console.error('获取待确认提醒失败', e);
    }
  };

  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true);
      await Promise.all([fetchStats(), fetchPendingReminders()]);
      setLoading(false);
    };
    fetchAll();
  }, [showToast]);

  const handleConfirmReminder = async (reminder: DutyReminder) => {
    if (!window.confirm(`确定确认提醒「${reminder.title}」吗？`)) return;
    try {
      setConfirmingId(reminder.id);
      const res = await reminderApi.confirm(reminder.id);
      if (res.success) {
        showToast('提醒已确认', 'success');
        setPendingReminders((prev) => prev.filter((r) => r.id !== reminder.id));
      } else {
        showToast(res.error || '确认失败', 'error');
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '确认失败', 'error');
    } finally {
      setConfirmingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-gray-500">暂无数据</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-[#1e3a5f]">仪表盘</h1>

      {canConfirm && pendingReminders.length > 0 && (
        <div className="rounded-lg border-2 border-amber-300 bg-amber-50 p-4 shadow-sm">
          <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold text-amber-900">
            <BellRing className="h-5 w-5" />
            待确认的值班提醒 ({pendingReminders.length})
          </h2>
          <div className="space-y-3">
            {pendingReminders.map((r) => (
              <div key={r.id} className="rounded-lg border border-amber-200 bg-white p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-medium text-[#1e3a5f]">{r.title}</h3>
                      {r.shift_name && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                          {r.shift_name}
                          {r.shift_duty_person && <span>（{r.shift_duty_person}）</span>}
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-sm text-gray-700 whitespace-pre-wrap">{r.content}</p>
                    <div className="mt-2 text-xs text-gray-500">
                      有效期: {formatDateTime(r.effective_start)} ~ {formatDateTime(r.effective_end)}
                    </div>
                  </div>
                  <button
                    onClick={() => handleConfirmReminder(r)}
                    disabled={confirmingId === r.id}
                    className="flex flex-shrink-0 items-center gap-1 rounded-lg bg-amber-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    {confirmingId === r.id ? '确认中...' : '确认提醒'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-4">
        {statCardConfig.map(({ status, label, icon: Icon, color }) => (
          <div key={status} className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">{label}</p>
                <p className="mt-1 text-3xl font-bold text-gray-900">
                  {stats.tickets.by_status[status] || 0}
                </p>
              </div>
              <Icon className={`h-8 w-8 ${color}`} />
            </div>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900">
            <Activity className="h-5 w-5 text-[#1e3a5f]" />
            严重级别分布
          </h2>
          <div className="grid grid-cols-2 gap-3">
            {severityConfig.map(({ severity, label }) => (
              <div key={severity} className="rounded-lg border border-gray-100 bg-gray-50 p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">{label}</span>
                  <SeverityBadge severity={severity} />
                </div>
                <p className="mt-2 text-2xl font-bold text-gray-900">
                  {stats.tickets.by_severity[severity] || 0}
                </p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900">
            <Package className="h-5 w-5 text-[#1e3a5f]" />
            交接批次汇总
          </h2>
          <div className="grid grid-cols-3 gap-3">
            {batchConfig.map(({ status, label }) => (
              <div key={status} className="rounded-lg border border-gray-100 bg-gray-50 p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">{label}</span>
                  <BatchStatusBadge status={status} />
                </div>
                <p className="mt-2 text-2xl font-bold text-gray-900">
                  {stats.batches[status] || 0}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900">
          <Clock className="h-5 w-5 text-[#1e3a5f]" />
          最近活动
        </h2>
        <div className="space-y-4">
          {stats.recent_activity.length === 0 ? (
            <p className="text-center text-gray-500">暂无活动记录</p>
          ) : (
            stats.recent_activity.map((activity) => (
              <div key={activity.id} className="flex gap-4">
                <div className="flex flex-col items-center">
                  <div className="h-2 w-2 rounded-full bg-[#1e3a5f]" />
                  <div className="h-full w-0.5 bg-gray-200" />
                </div>
                <div className="flex-1 pb-4">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">
                      {getEntityLabel(activity.entity_type, activity.entity_id)}
                    </span>
                    {activity.old_status && (
                      activity.entity_type === 'ticket' ? (
                        <StatusBadge status={activity.old_status as TicketStatus} className="text-xs" />
                      ) : (
                        <BatchStatusBadge status={activity.old_status as BatchStatus} className="text-xs" />
                      )
                    )}
                    <span className="text-gray-400">→</span>
                    {activity.entity_type === 'ticket' ? (
                      <StatusBadge status={activity.new_status as TicketStatus} className="text-xs" />
                    ) : (
                      <BatchStatusBadge status={activity.new_status as BatchStatus} className="text-xs" />
                    )}
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-sm text-gray-500">
                    <span>操作人: {activity.operator}</span>
                    <span>•</span>
                    <span>{formatDateTime(activity.created_at)}</span>
                  </div>
                  {activity.reason && (
                    <p className="mt-1 text-sm text-gray-600">原因: {activity.reason}</p>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
