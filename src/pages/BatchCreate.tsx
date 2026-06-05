import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, CheckSquare, Square, CalendarClock } from 'lucide-react';
import { batchApi, ticketApi, shiftApi } from '@/services/api';
import { useToast } from '@/hooks/useToast';
import { useAuthStore } from '@/store/useAuthStore';
import SeverityBadge from '@/components/SeverityBadge';
import StatusBadge from '@/components/StatusBadge';
import { formatDateTime } from '@/utils/format';
import type { Ticket, DutyShift } from '@/types';

interface FormData {
  name: string;
  description: string;
  ticketIds: number[];
  shiftId: number | null;
}

interface FormErrors {
  name?: string;
  ticketIds?: string;
  shiftId?: string;
}

export default function BatchCreate() {
  const [formData, setFormData] = useState<FormData>({
    name: '',
    description: '',
    ticketIds: [],
    shiftId: null,
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [shifts, setShifts] = useState<DutyShift[]>([]);
  const [loading, setLoading] = useState(true);
  const [shiftsLoading, setShiftsLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();
  const showToast = useToast((state) => state.showToast);
  const user = useAuthStore((state) => state.user);

  useEffect(() => {
    const fetchOpenTickets = async () => {
      try {
        setLoading(true);
        const res = await ticketApi.getOpenForHandover();
        if (res.success && res.data) {
          setTickets(res.data);
        }
      } catch (e) {
        showToast(e instanceof Error ? e.message : '获取可交接工单失败', 'error');
      } finally {
        setLoading(false);
      }
    };
    fetchOpenTickets();
  }, [showToast]);

  useEffect(() => {
    const fetchShifts = async () => {
      try {
        setShiftsLoading(true);
        const res = await shiftApi.getActive();
        if (res.success && res.data) {
          setShifts(res.data);
        }
      } catch (e) {
        console.error('获取班次失败:', e);
      } finally {
        setShiftsLoading(false);
      }
    };
    fetchShifts();
  }, []);

  const selectedShift = shifts.find((s) => s.id === formData.shiftId);

  const validate = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = '请输入批次名称';
    }
    if (formData.ticketIds.length === 0) {
      newErrors.ticketIds = '请至少选择一个工单';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleToggleTicket = (ticketId: number) => {
    setFormData((prev) => ({
      ...prev,
      ticketIds: prev.ticketIds.includes(ticketId)
        ? prev.ticketIds.filter((id) => id !== ticketId)
        : [...prev.ticketIds, ticketId],
    }));
  };

  const handleSelectAll = () => {
    if (formData.ticketIds.length === tickets.length) {
      setFormData((prev) => ({ ...prev, ticketIds: [] }));
    } else {
      setFormData((prev) => ({ ...prev, ticketIds: tickets.map((t) => t.id) }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) {
      showToast('请填写所有必填项', 'error');
      return;
    }

    try {
      setSubmitting(true);
      const res = await batchApi.create({
        name: formData.name,
        description: formData.description || undefined,
        ticket_ids: formData.ticketIds,
        handover_person: user?.username || '',
        shift_id: formData.shiftId ?? undefined,
      });

      if (res.success) {
        showToast('批次创建成功', 'success');
        navigate('/batches');
      } else {
        showToast(res.error || '创建失败', 'error');
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '创建失败', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const selectedTickets = tickets.filter((t) => formData.ticketIds.includes(t.id));

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
        <h1 className="text-2xl font-bold text-[#1e3a5f]">创建交接批次</h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">基本信息</h2>
          <div className="grid gap-6 md:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                批次名称 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className={`mt-1 block w-full rounded-lg border px-3 py-2 text-sm ${
                  errors.name ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : 'border-gray-300 focus:border-[#1e3a5f] focus:ring-[#1e3a5f]'
                } focus:outline-none focus:ring-1`}
                placeholder="请输入批次名称"
              />
              {errors.name && <p className="mt-1 text-sm text-red-500">{errors.name}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">描述</label>
              <input
                type="text"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
                placeholder="请输入描述（选填）"
              />
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900">
            <CalendarClock className="h-5 w-5 text-[#1e3a5f]" />
            关联值班班次
            <span className="text-sm font-normal text-gray-500">（选填，关联后接班人只能为该班次值班人）</span>
          </h2>
          <div className="grid gap-6 md:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700">选择班次</label>
              {shiftsLoading ? (
                <div className="mt-1 text-sm text-gray-500">加载中...</div>
              ) : shifts.length === 0 ? (
                <div className="mt-1 text-sm text-gray-500">当前无生效中的值班班次，可先前往「值班排班」创建</div>
              ) : (
                <select
                  value={formData.shiftId ?? ''}
                  onChange={(e) => setFormData({ ...formData, shiftId: e.target.value ? Number(e.target.value) : null })}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
                >
                  <option value="">-- 不关联班次 --</option>
                  {shifts.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} | 值班人: {s.duty_person} | {formatDateTime(s.start_time)} ~ {formatDateTime(s.end_time)}
                    </option>
                  ))}
                </select>
              )}
            </div>
            {selectedShift && (
              <div className="rounded-lg bg-blue-50 p-4 border border-blue-100">
                <div className="text-sm font-medium text-[#1e3a5f] mb-1">{selectedShift.name}</div>
                <div className="space-y-1 text-sm text-gray-600">
                  <div>值班人: <span className="font-medium text-gray-900">{selectedShift.duty_person}</span></div>
                  <div>时间: {formatDateTime(selectedShift.start_time)} ~ {formatDateTime(selectedShift.end_time)}</div>
                  <div className="flex items-center gap-1 flex-wrap">
                    可接收级别:
                    {selectedShift.allowed_severities.map((sev) => (
                      <SeverityBadge key={sev} severity={sev} />
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">
              选择工单 <span className="text-red-500">*</span>
            </h2>
            <button
              type="button"
              onClick={handleSelectAll}
              className="flex items-center gap-2 text-sm text-[#1e3a5f] hover:underline"
            >
              {formData.ticketIds.length === tickets.length ? '取消全选' : '全选'}
            </button>
          </div>
          {errors.ticketIds && <p className="mb-4 text-sm text-red-500">{errors.ticketIds}</p>}

          {loading ? (
            <div className="flex h-32 items-center justify-center">
              <div className="text-gray-500">加载中...</div>
            </div>
          ) : tickets.length === 0 ? (
            <div className="py-8 text-center text-gray-500">
              暂无可交接的工单
            </div>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {tickets.map((ticket) => {
                const isSelected = formData.ticketIds.includes(ticket.id);
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
                      <CheckSquare className="h-5 w-5 text-[#1e3a5f]" />
                    ) : (
                      <Square className="h-5 w-5 text-gray-400" />
                    )}
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-[#1e3a5f]">#{ticket.id}</span>
                        <span className="text-gray-900">{ticket.customer_name}</span>
                        <SeverityBadge severity={ticket.severity} />
                        <StatusBadge status={ticket.status} />
                      </div>
                      <div className="mt-1 flex items-center gap-4 text-sm text-gray-500">
                        <span>责任人: {ticket.assignee}</span>
                        <span>截止: {formatDateTime(ticket.deadline)}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {selectedTickets.length > 0 && (
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">
              已选择工单 ({selectedTickets.length})
            </h2>
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

        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={() => navigate('/batches')}
            className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            取消
          </button>
          <button
            type="submit"
            disabled={submitting || loading}
            className="flex items-center gap-2 rounded-lg bg-[#1e3a5f] px-4 py-2 text-sm font-medium text-white hover:bg-[#2d4f7c] disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {submitting ? '提交中...' : '提交'}
          </button>
        </div>
      </form>
    </div>
  );
}
