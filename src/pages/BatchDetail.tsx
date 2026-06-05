import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, CheckCircle, XCircle, Clock } from 'lucide-react';
import { batchApi, historyApi } from '@/services/api';
import { useToast } from '@/hooks/useToast';
import { useAuthStore } from '@/store/useAuthStore';
import BatchStatusBadge from '@/components/BatchStatusBadge';
import SeverityBadge from '@/components/SeverityBadge';
import StatusBadge from '@/components/StatusBadge';
import { formatDateTime } from '@/utils/format';
import type { HandoverBatch, StatusHistory } from '@/types';

export default function BatchDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [batch, setBatch] = useState<HandoverBatch | null>(null);
  const [history, setHistory] = useState<StatusHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [showReturnReason, setShowReturnReason] = useState(false);
  const [returnReason, setReturnReason] = useState('');
  const showToast = useToast((state) => state.showToast);
  const hasPermission = useAuthStore((state) => state.hasPermission);
  const user = useAuthStore((state) => state.user);

  const fetchBatch = async () => {
    if (!id) return;
    try {
      setLoading(true);
      const batchRes = await batchApi.get(Number(id));
      if (batchRes.success && batchRes.data) {
        setBatch(batchRes.data);
      }

      const historyRes = await historyApi.getList({
        entity_type: 'batch',
        entity_id: Number(id),
      });
      if (historyRes.success && historyRes.data) {
        setHistory(historyRes.data);
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '获取批次详情失败', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBatch();
  }, [id, showToast]);

  const handleConfirm = async () => {
    if (!id || !batch) return;
    if (!window.confirm('确定要确认交接吗？')) return;

    try {
      setActionLoading(true);
      const res = await batchApi.confirm(Number(id), {
        receiver_person: user?.username,
      });
      if (res.success) {
        showToast('交接已确认', 'success');
        setShowReturnReason(false);
        fetchBatch();
      } else {
        showToast(res.error || '确认失败', 'error');
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '确认失败', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReturn = async () => {
    if (!id || !batch) return;
    if (!returnReason.trim()) {
      showToast('请填写退回原因', 'warning');
      return;
    }
    if (!window.confirm('确定要退回交接吗？')) return;

    try {
      setActionLoading(true);
      const res = await batchApi.return(Number(id), {
        receiver_person: user?.username,
        reason: returnReason,
      });
      if (res.success) {
        showToast('交接已退回', 'success');
        setShowReturnReason(false);
        setReturnReason('');
        fetchBatch();
      } else {
        showToast(res.error || '退回失败', 'error');
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '退回失败', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const canAction = batch?.status === 'pending' && hasPermission('batch:action');

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  if (!batch) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-gray-500">批次不存在</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/batches')}
          className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <ArrowLeft className="h-4 w-4" />
          返回
        </button>
        <h1 className="text-2xl font-bold text-[#1e3a5f]">
          交接批次详情 #{batch.id}
        </h1>
        <BatchStatusBadge status={batch.status} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">批次信息</h2>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-500">批次名称</span>
              <span className="font-medium text-gray-900">{batch.name}</span>
            </div>
            {batch.description && (
              <div className="flex justify-between">
                <span className="text-gray-500">描述</span>
                <span className="font-medium text-gray-900">{batch.description}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-gray-500">交班人</span>
              <span className="font-medium text-gray-900">{batch.handover_person}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">接班人</span>
              <span className="font-medium text-gray-900">
                {batch.receiver_person || '-'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">工单数量</span>
              <span className="font-medium text-gray-900">{batch.ticket_ids.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">创建时间</span>
              <span className="font-medium text-gray-500">{formatDateTime(batch.created_at)}</span>
            </div>
            {batch.confirmed_at && (
              <div className="flex justify-between">
                <span className="text-gray-500">确认时间</span>
                <span className="font-medium text-gray-500">{formatDateTime(batch.confirmed_at)}</span>
              </div>
            )}
          </div>

          {canAction && (
            <div className="pt-4 border-t border-gray-200 space-y-3">
              <div className="flex gap-2">
                <button
                  onClick={handleConfirm}
                  disabled={actionLoading}
                  className="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
                >
                  <CheckCircle className="h-4 w-4" />
                  确认交接
                </button>
                <button
                  onClick={() => setShowReturnReason(!showReturnReason)}
                  disabled={actionLoading}
                  className="flex items-center gap-2 rounded-lg border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
                >
                  <XCircle className="h-4 w-4" />
                  退回交接
                </button>
              </div>

              {showReturnReason && (
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">
                    退回原因 <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    value={returnReason}
                    onChange={(e) => setReturnReason(e.target.value)}
                    rows={3}
                    className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
                    placeholder="请输入退回原因"
                  />
                  <button
                    onClick={handleReturn}
                    disabled={actionLoading || !returnReason.trim()}
                    className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                  >
                    {actionLoading ? '提交中...' : '提交退回'}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">
            工单列表 ({batch.tickets?.length || batch.ticket_ids.length})
          </h2>
          {!batch.tickets || batch.tickets.length === 0 ? (
            <p className="text-center text-gray-500">暂无工单数据</p>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {batch.tickets.map((ticket) => (
                <div
                  key={ticket.id}
                  className="rounded-lg border border-gray-200 p-4 hover:bg-gray-50 cursor-pointer"
                  onClick={() => navigate(`/tickets/${ticket.id}`)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-[#1e3a5f]">#{ticket.id}</span>
                      <span className="text-gray-900">{ticket.customer_name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <SeverityBadge severity={ticket.severity} />
                      <StatusBadge status={ticket.status} />
                    </div>
                  </div>
                  <div className="mt-2 flex items-center gap-4 text-sm text-gray-500">
                    <span>责任人: {ticket.assignee}</span>
                    <span>截止: {formatDateTime(ticket.deadline)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
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
                      <BatchStatusBadge status={item.old_status as 'pending' | 'confirmed' | 'returned'} />
                    )}
                    <span className="text-gray-400">→</span>
                    <BatchStatusBadge status={item.new_status as 'pending' | 'confirmed' | 'returned'} />
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
