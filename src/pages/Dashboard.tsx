import { useEffect, useState } from 'react';
import { ClipboardList, Clock, CheckCircle, AlertTriangle, Activity, Package } from 'lucide-react';
import { dashboardApi } from '@/services/api';
import { useToast } from '@/hooks/useToast';
import StatusBadge from '@/components/StatusBadge';
import SeverityBadge from '@/components/SeverityBadge';
import BatchStatusBadge from '@/components/BatchStatusBadge';
import { formatDateTime, getEntityLabel } from '@/utils/format';
import type { DashboardStats, TicketStatus, Severity, BatchStatus } from '@/types';

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
  const showToast = useToast((state) => state.showToast);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const res = await dashboardApi.getStats();
        if (res.success && res.data) {
          setStats(res.data);
        }
      } catch (e) {
        showToast(e instanceof Error ? e.message : '获取统计数据失败', 'error');
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, [showToast]);

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
