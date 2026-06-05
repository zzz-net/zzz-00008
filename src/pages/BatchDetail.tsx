import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, CheckCircle, XCircle, Clock, Edit2, Send, X, Save, CheckSquare, Square, AlertCircle, Undo2, BellRing, CheckCircle2 } from 'lucide-react';
import { batchApi, historyApi, ticketApi, reminderApi } from '@/services/api';
import { useToast } from '@/hooks/useToast';
import { useAuthStore } from '@/store/useAuthStore';
import BatchStatusBadge from '@/components/BatchStatusBadge';
import SeverityBadge from '@/components/SeverityBadge';
import StatusBadge from '@/components/StatusBadge';
import { formatDateTime } from '@/utils/format';
import type { HandoverBatch, StatusHistory, Ticket, DutyReminder } from '@/types';

interface EditFormData {
  name: string;
  description: string;
  ticketIds: number[];
}

export default function BatchDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [batch, setBatch] = useState<HandoverBatch | null>(null);
  const [history, setHistory] = useState<StatusHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [showReturnReason, setShowReturnReason] = useState(false);
  const [returnReason, setReturnReason] = useState('');
  const [showRevokeReason, setShowRevokeReason] = useState(false);
  const [revokeReason, setRevokeReason] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState<EditFormData>({ name: '', description: '', ticketIds: [] });
  const [availableTickets, setAvailableTickets] = useState<Ticket[]>([]);
  const [ticketsLoading, setTicketsLoading] = useState(false);
  const [editErrors, setEditErrors] = useState<{ name?: string; ticketIds?: string }>({});
  const [shiftReminders, setShiftReminders] = useState<DutyReminder[]>([]);
  const [reminderConfirmingId, setReminderConfirmingId] = useState<number | null>(null);
  const showToast = useToast((state) => state.showToast);
  const hasPermission = useAuthStore((state) => state.hasPermission);
  const canConfirmReminder = useAuthStore((state) => state.hasPermission('confirm_reminders'));
  const user = useAuthStore((state) => state.user);

  const fetchBatch = async () => {
    if (!id) return;
    try {
      setLoading(true);
      const batchRes = await batchApi.get(Number(id));
      if (batchRes.success && batchRes.data) {
        setBatch(batchRes.data);
        setEditForm({
          name: batchRes.data.name,
          description: batchRes.data.description || '',
          ticketIds: batchRes.data.ticket_ids || [],
        });
        setShowRevokeReason(false);
        setRevokeReason('');
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

  const fetchAvailableTickets = async () => {
    try {
      setTicketsLoading(true);
      const res = await ticketApi.getOpenForHandover();
      if (res.success && res.data) {
        const currentTicketIds = batch?.ticket_ids || [];
        const currentTickets = batch?.tickets || [];
        const combinedTickets = [
          ...currentTickets,
          ...res.data.filter((t) => !currentTicketIds.includes(t.id)),
        ];
        setAvailableTickets(combinedTickets);
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '获取可交接工单失败', 'error');
    } finally {
      setTicketsLoading(false);
    }
  };

  const fetchShiftReminders = async (shiftId: number) => {
    try {
      const res = await reminderApi.getForShift(shiftId);
      if (res.success && res.data) {
        setShiftReminders(res.data);
      }
    } catch (e) {
      console.error('获取班次提醒失败', e);
    }
  };

  const handleConfirmReminder = async (reminder: DutyReminder) => {
    if (!window.confirm(`确定确认提醒「${reminder.title}」吗？`)) return;
    try {
      setReminderConfirmingId(reminder.id);
      const res = await reminderApi.confirm(reminder.id);
      if (res.success) {
        showToast('提醒已确认', 'success');
        fetchShiftReminders(reminder.shift_id!);
      } else {
        showToast(res.error || '确认失败', 'error');
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '确认失败', 'error');
    } finally {
      setReminderConfirmingId(null);
    }
  };

  useEffect(() => {
    fetchBatch();
  }, [id, showToast]);

  useEffect(() => {
    if (batch?.shift_id) {
      fetchShiftReminders(batch.shift_id);
    } else {
      setShiftReminders([]);
    }
  }, [batch?.shift_id]);

  useEffect(() => {
    if (isEditing) {
      fetchAvailableTickets();
    }
  }, [isEditing, batch?.ticket_ids]);

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

  const handleRevoke = async () => {
    if (!id || !batch) return;
    if (!revokeReason.trim()) {
      showToast('请填写撤销原因', 'warning');
      return;
    }
    if (!window.confirm('确定要撤销该交接批次吗？撤销后状态将恢复为待确认，关联工单将可继续交接。')) return;

    try {
      setActionLoading(true);
      const res = await batchApi.revoke(Number(id), {
        reason: revokeReason,
      });
      if (res.success) {
        showToast('交接已撤销', 'success');
        setShowRevokeReason(false);
        setRevokeReason('');
        fetchBatch();
      } else {
        showToast(res.error || '撤销失败', 'error');
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '撤销失败', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const canEdit = batch?.status === 'returned' && (
    (user?.username === batch.handover_person) || hasPermission('create_batches')
  );

  const canAction = batch?.status === 'pending' && (hasPermission('confirm_batches') || hasPermission('return_batches'));

  const canResubmit = batch?.status === 'returned' && (
    (user?.username === batch.handover_person) || hasPermission('create_batches')
  );

  const canRevoke = batch?.status === 'confirmed' &&
    batch.original_confirmer === user?.username &&
    hasPermission('confirm_batches');

  const validateEditForm = (): boolean => {
    const errors: { name?: string; ticketIds?: string } = {};
    if (!editForm.name.trim()) {
      errors.name = '请输入批次名称';
    }
    if (editForm.ticketIds.length === 0) {
      errors.ticketIds = '请至少选择一个工单';
    }
    setEditErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleToggleTicket = (ticketId: number) => {
    setEditForm((prev) => ({
      ...prev,
      ticketIds: prev.ticketIds.includes(ticketId)
        ? prev.ticketIds.filter((tid) => tid !== ticketId)
        : [...prev.ticketIds, ticketId],
    }));
  };

  const handleSelectAll = () => {
    if (editForm.ticketIds.length === availableTickets.length) {
      setEditForm((prev) => ({ ...prev, ticketIds: [] }));
    } else {
      setEditForm((prev) => ({ ...prev, ticketIds: availableTickets.map((t) => t.id) }));
    }
  };

  const handleEdit = () => {
    if (!batch) return;
    setEditForm({
      name: batch.name,
      description: batch.description || '',
      ticketIds: batch.ticket_ids || [],
    });
    setEditErrors({});
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditErrors({});
  };

  const handleSave = async () => {
    if (!id || !batch) return;
    if (!validateEditForm()) {
      showToast('请填写所有必填项', 'error');
      return;
    }

    try {
      setActionLoading(true);
      const res = await batchApi.update(Number(id), {
        name: editForm.name,
        description: editForm.description || undefined,
        ticket_ids: editForm.ticketIds,
      });
      if (res.success) {
        showToast('批次信息已更新', 'success');
        setIsEditing(false);
        fetchBatch();
      } else {
        showToast(res.error || '更新失败', 'error');
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '更新失败', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleResubmit = async () => {
    if (!id || !batch) return;
    if (!window.confirm('确定要重新提交该批次吗？重新提交后状态将变为待确认。')) return;

    try {
      setActionLoading(true);
      const res = await batchApi.resubmit(Number(id));
      if (res.success) {
        showToast('批次已重新提交', 'success');
        setIsEditing(false);
        fetchBatch();
      } else {
        showToast(res.error || '重新提交失败', 'error');
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '重新提交失败', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const returnHistoryItem = history.find((h) => h.new_status === 'returned');
  const revokeHistoryItem = history.find((h) => h.old_status === 'confirmed' && h.new_status === 'pending');
  const selectedTickets = availableTickets.filter((t) => editForm.ticketIds.includes(t.id));

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

      {returnHistoryItem && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-medium text-red-800">退回原因</h3>
              <p className="mt-1 text-sm text-red-700">{returnHistoryItem.reason || '无'}</p>
              <p className="mt-1 text-xs text-red-600">
                退回人: {returnHistoryItem.operator} • {formatDateTime(returnHistoryItem.created_at)}
              </p>
            </div>
          </div>
        </div>
      )}

      {shiftReminders.length > 0 && (
        <div className="rounded-lg border-2 border-amber-300 bg-amber-50 p-4 shadow-sm">
          <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold text-amber-900">
            <BellRing className="h-5 w-5" />
            关联班次的值班提醒 ({shiftReminders.length})
          </h2>
          <div className="space-y-3">
            {shiftReminders.map((r) => {
              const confirmed = r.confirmations?.some(c => c.confirmed_by === user?.name);
              const expired = new Date(r.effective_end) < new Date();
              return (
                <div key={r.id} className="rounded-lg border border-amber-200 bg-white p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="font-medium text-[#1e3a5f]">{r.title}</h3>
                        {confirmed && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                            <CheckCircle2 className="h-3 w-3" /> 已确认
                          </span>
                        )}
                        {expired && r.is_active && !confirmed && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                            已过期
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-sm text-gray-700 whitespace-pre-wrap">{r.content}</p>
                      <div className="mt-2 text-xs text-gray-500">
                        有效期: {formatDateTime(r.effective_start)} ~ {formatDateTime(r.effective_end)}
                        {r.confirmations && r.confirmations.length > 0 && (
                          <span className="ml-3">已确认: {r.confirmations.map(c => c.confirmed_by).join('、')}</span>
                        )}
                      </div>
                    </div>
                    {canConfirmReminder && r.is_active && !expired && !confirmed && (
                      <button
                        onClick={() => handleConfirmReminder(r)}
                        disabled={reminderConfirmingId === r.id}
                        className="flex flex-shrink-0 items-center gap-1 rounded-lg bg-amber-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50"
                      >
                        <CheckCircle2 className="h-4 w-4" />
                        {reminderConfirmingId === r.id ? '确认中...' : '确认提醒'}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {batch.revoked_at && (
        <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-6">
          <div className="flex items-start gap-3 mb-4">
            <Undo2 className="h-6 w-6 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-semibold text-yellow-900 text-lg">撤销复核记录</h3>
              <p className="text-sm text-yellow-700 mt-1">该批次已执行撤销操作，以下是完整的复核信息</p>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div className="rounded-lg bg-white p-4 border border-yellow-100">
              <div className="text-xs text-yellow-600 font-medium">原确认人</div>
              <div className="mt-1 text-sm font-medium text-gray-900">{batch.original_confirmer || '-'}</div>
            </div>
            <div className="rounded-lg bg-white p-4 border border-yellow-100">
              <div className="text-xs text-yellow-600 font-medium">撤销执行人</div>
              <div className="mt-1 text-sm font-medium text-gray-900">{batch.revoked_by || '-'}</div>
            </div>
            <div className="rounded-lg bg-white p-4 border border-yellow-100">
              <div className="text-xs text-yellow-600 font-medium">撤销时间</div>
              <div className="mt-1 text-sm font-medium text-gray-900">{formatDateTime(batch.revoked_at)}</div>
            </div>
            <div className="rounded-lg bg-white p-4 border border-yellow-100">
              <div className="text-xs text-yellow-600 font-medium">撤销前状态</div>
              <div className="mt-1">
                {batch.revoke_old_status && (
                  <BatchStatusBadge status={batch.revoke_old_status as 'pending' | 'confirmed' | 'returned'} />
                )}
              </div>
            </div>
            <div className="rounded-lg bg-white p-4 border border-yellow-100">
              <div className="text-xs text-yellow-600 font-medium">撤销后状态</div>
              <div className="mt-1">
                {batch.revoke_new_status && (
                  <BatchStatusBadge status={batch.revoke_new_status as 'pending' | 'confirmed' | 'returned'} />
                )}
              </div>
            </div>
            <div className="rounded-lg bg-white p-4 border border-yellow-100">
              <div className="text-xs text-yellow-600 font-medium">受影响工单数</div>
              <div className="mt-1 text-sm font-medium text-gray-900">{batch.ticket_ids.length} 个</div>
            </div>
          </div>

          <div className="mt-4 rounded-lg bg-white p-4 border border-yellow-100">
            <div className="text-xs text-yellow-600 font-medium mb-2">撤销原因</div>
            <div className="text-sm text-gray-700 whitespace-pre-wrap">{batch.revoke_reason || '未填写'}</div>
          </div>

          <div className="mt-4 rounded-lg bg-white p-4 border border-yellow-100">
            <div className="text-xs text-yellow-600 font-medium mb-3">受影响工单列表</div>
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {batch.tickets?.map((ticket) => (
                <div
                  key={ticket.id}
                  className="flex items-center justify-between rounded-lg border border-gray-200 p-3 hover:bg-gray-50 cursor-pointer"
                  onClick={() => navigate(`/tickets/${ticket.id}`)}
                >
                  <div className="flex items-center gap-3">
                    <span className="font-medium text-[#1e3a5f]">#{ticket.id}</span>
                    <span className="text-gray-900">{ticket.customer_name}</span>
                    <SeverityBadge severity={ticket.severity} />
                  </div>
                  <StatusBadge status={ticket.status} />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {isEditing ? (
          <div className="space-y-6 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-900">
              <Edit2 className="h-5 w-5 text-[#1e3a5f]" />
              编辑批次信息
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  批次名称 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={editForm.name}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  className={`mt-1 block w-full rounded-lg border px-3 py-2 text-sm ${
                    editErrors.name
                      ? 'border-red-500 focus:border-red-500 focus:ring-red-500'
                      : 'border-gray-300 focus:border-[#1e3a5f] focus:ring-[#1e3a5f]'
                  } focus:outline-none focus:ring-1`}
                  placeholder="请输入批次名称"
                />
                {editErrors.name && (
                  <p className="mt-1 text-sm text-red-500">{editErrors.name}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">描述</label>
                <input
                  type="text"
                  value={editForm.description}
                  onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
                  placeholder="请输入描述（选填）"
                />
              </div>
              <div className="flex justify-between text-sm text-gray-500">
                <span>交班人</span>
                <span className="font-medium text-gray-900">{batch.handover_person}</span>
              </div>
            </div>

            <div className="flex gap-2 pt-4 border-t border-gray-200">
              <button
                onClick={handleSave}
                disabled={actionLoading}
                className="flex items-center gap-2 rounded-lg bg-[#1e3a5f] px-4 py-2 text-sm font-medium text-white hover:bg-[#2d4f7c] disabled:opacity-50"
              >
                <Save className="h-4 w-4" />
                {actionLoading ? '保存中...' : '保存修改'}
              </button>
              <button
                onClick={handleCancelEdit}
                disabled={actionLoading}
                className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                <X className="h-4 w-4" />
                取消
              </button>
            </div>
          </div>
        ) : (
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
              {batch.shift_name && (
                <div className="flex justify-between items-center">
                  <span className="text-gray-500">关联班次</span>
                  <span className="font-medium text-[#1e3a5f]">
                    {batch.shift_name}
                    {batch.shift_duty_person && (
                    <span className="ml-2 text-sm text-gray-500">(值班人: {batch.shift_duty_person})</span>
                  )}
                  </span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-gray-500">接班人</span>
                <span className="font-medium text-gray-900">
                  {batch.receiver_person || '-'}
                </span>
              </div>
              {batch.original_confirmer && (
                <div className="flex justify-between">
                  <span className="text-gray-500">原确认人</span>
                  <span className="font-medium text-yellow-700">{batch.original_confirmer}</span>
                </div>
              )}
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
              {batch.revoked_at && (
                <>
                  <div className="flex justify-between">
                    <span className="text-gray-500">撤销时间</span>
                    <span className="font-medium text-yellow-600">{formatDateTime(batch.revoked_at)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">撤销人</span>
                    <span className="font-medium text-yellow-600">{batch.revoked_by}</span>
                  </div>
                  {batch.revoke_reason && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">撤销原因</span>
                      <span className="font-medium text-yellow-600">{batch.revoke_reason}</span>
                    </div>
                  )}
                </>
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

              {canRevoke && (
                <div className="pt-4 border-t border-gray-200 space-y-3">
                  <div className="flex gap-2">
                    <button
                      onClick={() => setShowRevokeReason(!showRevokeReason)}
                      disabled={actionLoading}
                      className="flex items-center gap-2 rounded-lg border border-yellow-500 bg-white px-4 py-2 text-sm font-medium text-yellow-700 hover:bg-yellow-50 disabled:opacity-50"
                    >
                      <Undo2 className="h-4 w-4" />
                      撤销确认
                    </button>
                  </div>
                  <p className="text-xs text-gray-500">
                    撤销后批次状态将恢复为待确认，关联工单将可继续交接。此操作只能由您作为接班人执行。
                  </p>

                  {showRevokeReason && (
                    <div className="space-y-2">
                      <label className="block text-sm font-medium text-gray-700">
                        撤销原因 <span className="text-red-500">*</span>
                      </label>
                      <textarea
                        value={revokeReason}
                        onChange={(e) => setRevokeReason(e.target.value)}
                        rows={3}
                        className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
                        placeholder="请输入撤销原因，说明交接错误的具体情况"
                      />
                      <button
                        onClick={handleRevoke}
                        disabled={actionLoading || !revokeReason.trim()}
                        className="rounded-lg bg-yellow-600 px-4 py-2 text-sm font-medium text-white hover:bg-yellow-700 disabled:opacity-50"
                      >
                        {actionLoading ? '提交中...' : '确认撤销'}
                      </button>
                    </div>
                  )}
                </div>
              )}

            {canEdit && !isEditing && (
              <div className="pt-4 border-t border-gray-200 space-y-3">
                <div className="flex gap-2">
                  <button
                    onClick={handleEdit}
                    disabled={actionLoading}
                    className="flex items-center gap-2 rounded-lg bg-[#1e3a5f] px-4 py-2 text-sm font-medium text-white hover:bg-[#2d4f7c] disabled:opacity-50"
                  >
                    <Edit2 className="h-4 w-4" />
                    编辑批次
                  </button>
                  <button
                    onClick={handleResubmit}
                    disabled={actionLoading}
                    className="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
                  >
                    <Send className="h-4 w-4" />
                    重新提交
                  </button>
                </div>
                <p className="text-xs text-gray-500">
                  编辑并调整说明和工单清单后，点击"重新提交"将批次状态改为待确认
                </p>
              </div>
            )}
          </div>
        )}

        {isEditing ? (
          <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">
                选择工单 <span className="text-red-500">*</span>
              </h2>
              <button
                type="button"
                onClick={handleSelectAll}
                className="flex items-center gap-2 text-sm text-[#1e3a5f] hover:underline"
              >
                {editForm.ticketIds.length === availableTickets.length ? '取消全选' : '全选'}
              </button>
            </div>
            {editErrors.ticketIds && (
              <p className="text-sm text-red-500">{editErrors.ticketIds}</p>
            )}

            {ticketsLoading ? (
              <div className="flex h-32 items-center justify-center">
                <div className="text-gray-500">加载中...</div>
              </div>
            ) : availableTickets.length === 0 ? (
              <div className="py-8 text-center text-gray-500">
                暂无可交接的工单
              </div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {availableTickets.map((ticket) => {
                  const isSelected = editForm.ticketIds.includes(ticket.id);
                  return (
                    <div
                      key={ticket.id}
                      onClick={() => handleToggleTicket(ticket.id)}
                      className={`flex items-center gap-4 rounded-lg border p-4 cursor-pointer transition-colors ${
                        isSelected
                          ? 'border-[#1e3a5f] bg-blue-50'
                          : 'border-gray-200 hover:bg-gray-50'
                      }`}
                    >
                      {isSelected ? (
                        <CheckSquare className="h-5 w-5 text-[#1e3a5f] flex-shrink-0" />
                      ) : (
                        <Square className="h-5 w-5 text-gray-400 flex-shrink-0" />
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-medium text-[#1e3a5f]">#{ticket.id}</span>
                          <span className="text-gray-900 truncate">{ticket.customer_name}</span>
                          <SeverityBadge severity={ticket.severity} />
                          <StatusBadge status={ticket.status} />
                        </div>
                        <div className="mt-1 flex items-center gap-4 text-sm text-gray-500 flex-wrap">
                          <span>责任人: {ticket.assignee}</span>
                          <span>截止: {formatDateTime(ticket.deadline)}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {selectedTickets.length > 0 && (
              <div className="pt-4 border-t border-gray-200">
                <h3 className="mb-3 text-sm font-medium text-gray-900">
                  已选择工单 ({selectedTickets.length})
                </h3>
                <div className="flex flex-wrap gap-2">
                  {selectedTickets.map((ticket) => (
                    <span
                      key={ticket.id}
                      className="inline-flex items-center rounded-full bg-[#1e3a5f]/10 px-3 py-1 text-sm text-[#1e3a5f]"
                    >
                      #{ticket.id} - {ticket.customer_name}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
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
        )}
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
                  <div className="flex items-center gap-2 flex-wrap">
                    {item.old_status && (
                      <BatchStatusBadge status={item.old_status as 'pending' | 'confirmed' | 'returned'} />
                    )}
                    {item.old_status && <span className="text-gray-400">→</span>}
                    <BatchStatusBadge status={item.new_status as 'pending' | 'confirmed' | 'returned'} />
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-sm text-gray-500 flex-wrap">
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
