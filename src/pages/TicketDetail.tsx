import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Save, XCircle, Clock } from 'lucide-react';
import { ticketApi, historyApi } from '@/services/api';
import { useToast } from '@/hooks/useToast';
import { useAuthStore } from '@/store/useAuthStore';
import StatusBadge from '@/components/StatusBadge';
import SeverityBadge from '@/components/SeverityBadge';
import { formatDateTime } from '@/utils/format';
import { statusMap } from '@/types';
import type { Ticket, StatusHistory, TicketStatus } from '@/types';

export default function TicketDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [history, setHistory] = useState<StatusHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [progress, setProgress] = useState('');
  const [newStatus, setNewStatus] = useState<TicketStatus | ''>('');
  const showToast = useToast((state) => state.showToast);
  const hasPermission = useAuthStore((state) => state.hasPermission);
  const user = useAuthStore((state) => state.user);

  const fetchTicket = async () => {
    if (!id) return;
    try {
      setLoading(true);
      const ticketRes = await ticketApi.get(Number(id));
      if (ticketRes.success && ticketRes.data) {
        setTicket(ticketRes.data);
        setProgress(ticketRes.data.progress);
        setNewStatus(ticketRes.data.status);
      }

      const historyRes = await historyApi.getList({
        entity_type: 'ticket',
        entity_id: Number(id),
      });
      if (historyRes.success && historyRes.data) {
        setHistory(historyRes.data);
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '获取工单详情失败', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTicket();
  }, [id, showToast]);

  const handleSaveProgress = async () => {
    if (!ticket || !id) return;

    try {
      setSaving(true);
      const updateData: { progress?: string; status?: string } = {};
      if (progress !== ticket.progress) {
        updateData.progress = progress;
      }
      if (newStatus && newStatus !== ticket.status) {
        updateData.status = newStatus;
      }

      if (Object.keys(updateData).length === 0) {
        showToast('没有需要保存的更改', 'warning');
        return;
      }

      const res = await ticketApi.update(Number(id), updateData);
      if (res.success) {
        showToast('保存成功', 'success');
        fetchTicket();
      } else {
        showToast(res.error || '保存失败', 'error');
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '保存失败', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleClose = async () => {
    if (!id) return;
    if (!window.confirm('确定要关闭此工单吗？')) return;

    try {
      const res = await ticketApi.close(Number(id));
      if (res.success) {
        showToast('工单已关闭', 'success');
        fetchTicket();
      } else {
        showToast(res.error || '关闭失败', 'error');
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '关闭失败', 'error');
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  if (!ticket) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-gray-500">工单不存在</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/tickets')}
          className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <ArrowLeft className="h-4 w-4" />
          返回
        </button>
        <h1 className="text-2xl font-bold text-[#1e3a5f]">
          工单详情 #{ticket.id}
        </h1>
        <StatusBadge status={ticket.status} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">基本信息</h2>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-500">客户名称</span>
              <span className="font-medium text-gray-900">{ticket.customer_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">严重级别</span>
              <SeverityBadge severity={ticket.severity} />
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">责任人</span>
              <span className="font-medium text-gray-900">{ticket.assignee}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">创建人</span>
              <span className="font-medium text-gray-900">{ticket.created_by}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">截止时间</span>
              <span className="font-medium text-gray-900">{formatDateTime(ticket.deadline)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">创建时间</span>
              <span className="font-medium text-gray-500">{formatDateTime(ticket.created_at)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">更新时间</span>
              <span className="font-medium text-gray-500">{formatDateTime(ticket.updated_at)}</span>
            </div>
          </div>
        </div>

        <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">编辑进展</h2>
          <div>
            <label className="block text-sm font-medium text-gray-700">进展描述</label>
            <textarea
              value={progress}
              onChange={(e) => setProgress(e.target.value)}
              rows={4}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
              placeholder="请输入进展描述"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">状态更新</label>
            <select
              value={newStatus}
              onChange={(e) => setNewStatus(e.target.value as TicketStatus)}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
            >
              {Object.entries(statusMap).map(([key, val]) => (
                <option key={key} value={key}>
                  {val.label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleSaveProgress}
              disabled={saving}
              className="flex items-center gap-2 rounded-lg bg-[#1e3a5f] px-4 py-2 text-sm font-medium text-white hover:bg-[#2d4f7c] disabled:opacity-50"
            >
              <Save className="h-4 w-4" />
              {saving ? '保存中...' : '保存'}
            </button>
            {hasPermission('ticket:close') && ticket.status !== 'closed' && (
              <button
                onClick={handleClose}
                className="flex items-center gap-2 rounded-lg border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50"
              >
                <XCircle className="h-4 w-4" />
                关闭工单
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900">
          <Clock className="h-5 w-5 text-[#1e3a5f]" />
          状态历史
        </h2>
        <div className="space-y-4">
          {history.length === 0 ? (
            <p className="text-center text-gray-500">暂无历史记录</p>
          ) : (
            history.map((item) => (
              <div key={item.id} className="flex gap-4 border-b border-gray-100 pb-4 last:border-0">
                <div className="flex flex-col items-center">
                  <div className="h-2 w-2 rounded-full bg-[#1e3a5f]" />
                  <div className="h-full w-0.5 bg-gray-200" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    {item.old_status && (
                      <StatusBadge status={item.old_status as TicketStatus} />
                    )}
                    <span className="text-gray-400">→</span>
                    <StatusBadge status={item.new_status as TicketStatus} />
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-sm text-gray-500">
                    <span>操作人: {item.operator}</span>
                    <span>•</span>
                    <span>{formatDateTime(item.created_at)}</span>
                  </div>
                  {item.reason && (
                    <p className="mt-1 text-sm text-gray-600">原因: {item.reason}</p>
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
