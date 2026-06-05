import { useState, useEffect, useRef } from 'react';
import { Plus, Pencil, Ban, Download, Upload, Search, X, CheckCircle2, XCircle, BellRing, CheckCircle } from 'lucide-react';
import { reminderApi, shiftApi, exportApi } from '@/services/api';
import { useToast } from '@/hooks/useToast';
import { useAuthStore } from '@/store/useAuthStore';
import { formatDateTime, toLocalInputValue, fromLocalInputValue } from '@/utils/format';
import type { DutyReminder, DutyShift } from '@/types';

interface ReminderFormData {
  title: string;
  content: string;
  shift_id: number | null;
  shift_date: string;
  effective_start: string;
  effective_end: string;
  is_active: boolean;
}

const defaultFormData: ReminderFormData = {
  title: '',
  content: '',
  shift_id: null,
  shift_date: '',
  effective_start: '',
  effective_end: '',
  is_active: true,
};

export default function ReminderList() {
  const [reminders, setReminders] = useState<DutyReminder[]>([]);
  const [shifts, setShifts] = useState<DutyShift[]>([]);
  const [loading, setLoading] = useState(true);
  const [dateFilter, setDateFilter] = useState('');
  const [activeFilter, setActiveFilter] = useState<string>('all');
  const [showModal, setShowModal] = useState(false);
  const [editingReminder, setEditingReminder] = useState<DutyReminder | null>(null);
  const [formData, setFormData] = useState<ReminderFormData>(defaultFormData);
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);
  const [confirmingId, setConfirmingId] = useState<number | null>(null);

  const showToast = useToast((s) => s.showToast);
  const user = useAuthStore((s) => s.user);
  const canManage = useAuthStore((s) => s.hasPermission('manage_reminders'));
  const canConfirm = useAuthStore((s) => s.hasPermission('confirm_reminders'));

  const fetchReminders = async () => {
    try {
      setLoading(true);
      const params: Record<string, any> = {};
      if (dateFilter) params.date = dateFilter;
      if (activeFilter !== 'all') params.is_active = activeFilter === 'true';
      const res = await reminderApi.getList(params);
      if (res.success && res.data) setReminders(res.data);
    } catch (e) {
      showToast(e instanceof Error ? e.message : '获取提醒列表失败', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchShifts = async () => {
    try {
      const res = await shiftApi.getList({ is_active: true });
      if (res.success && res.data) setShifts(res.data);
    } catch (e) {
      console.error('获取班次列表失败', e);
    }
  };

  useEffect(() => { fetchReminders(); }, [dateFilter, activeFilter]);
  useEffect(() => { fetchShifts(); }, []);

  const openCreate = () => {
    setEditingReminder(null);
    setFormData(defaultFormData);
    setShowModal(true);
  };

  const openEdit = (reminder: DutyReminder) => {
    setEditingReminder(reminder);
    setFormData({
      title: reminder.title,
      content: reminder.content,
      shift_id: reminder.shift_id,
      shift_date: reminder.shift_date ? toLocalInputValue(reminder.shift_date).slice(0, 10) : '',
      effective_start: toLocalInputValue(reminder.effective_start),
      effective_end: toLocalInputValue(reminder.effective_end),
      is_active: reminder.is_active,
    });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title.trim() || !formData.content.trim() || !formData.effective_start || !formData.effective_end) {
      showToast('请填写所有必填项', 'error');
      return;
    }
    try {
      setSubmitting(true);
      const payload = {
        ...formData,
        effective_start: fromLocalInputValue(formData.effective_start),
        effective_end: fromLocalInputValue(formData.effective_end),
        shift_date: formData.shift_date ? fromLocalInputValue(formData.shift_date + 'T00:00') : null,
        shift_id: formData.shift_id && formData.shift_id > 0 ? formData.shift_id : null,
      };
      let res;
      if (editingReminder) {
        res = await reminderApi.update(editingReminder.id, payload);
      } else {
        res = await reminderApi.create(payload);
      }
      if (res.success) {
        showToast(editingReminder ? '提醒更新成功' : '提醒创建成功', 'success');
        setShowModal(false);
        fetchReminders();
      } else {
        showToast(res.error || '操作失败', 'error');
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '操作失败', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDisable = async (reminder: DutyReminder) => {
    if (!window.confirm(`确定停用提醒「${reminder.title}」吗？`)) return;
    try {
      const res = await reminderApi.disable(reminder.id);
      if (res.success) {
        showToast('提醒已停用', 'success');
        fetchReminders();
      } else {
        showToast(res.error || '停用失败', 'error');
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '停用失败', 'error');
    }
  };

  const handleConfirm = async (reminder: DutyReminder) => {
    if (!window.confirm(`确定确认提醒「${reminder.title}」吗？`)) return;
    try {
      setConfirmingId(reminder.id);
      const res = await reminderApi.confirm(reminder.id);
      if (res.success) {
        showToast('提醒已确认', 'success');
        fetchReminders();
      } else {
        showToast(res.error || '确认失败', 'error');
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '确认失败', 'error');
    } finally {
      setConfirmingId(null);
    }
  };

  const handleExport = () => {
    const params: Record<string, any> = { format: 'csv' };
    if (dateFilter) params.date = dateFilter;
    exportApi.exportReminders(params);
  };

  const handleImportClick = () => fileInputRef.current?.click();

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      setImporting(true);
      const res = await reminderApi.importCsv(file);
      if (res.success && res.data) {
        const { imported, skipped, total } = res.data;
        let msg = `成功导入 ${imported}/${total} 条`;
        if (skipped && skipped.length) msg += `，跳过 ${skipped.length} 条`;
        showToast(msg, 'success');
        fetchReminders();
      } else {
        const details = (res as any).details;
        const err = res.error || '导入失败';
        showToast(details ? `${err}: ${details.slice(0, 3).join('; ')}` : err, 'error');
      }
    } catch (err) {
      showToast(err instanceof Error ? err.message : '导入失败', 'error');
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const isConfirmedByMe = (r: DutyReminder) => {
    if (!user) return false;
    return r.confirmations?.some(c => c.confirmed_by === user.name);
  };

  const isExpired = (r: DutyReminder) => {
    return new Date(r.effective_end) < new Date();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-[#1e3a5f]">值班提醒</h1>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleExport}
            className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <Download className="h-4 w-4" /> 导出CSV
          </button>
          {canManage && (
            <>
              <button
                onClick={handleImportClick}
                disabled={importing}
                className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                <Upload className="h-4 w-4" /> {importing ? '导入中...' : '导入CSV'}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                onChange={handleImportFile}
                className="hidden"
              />
              <button
                onClick={openCreate}
                className="flex items-center gap-2 rounded-lg bg-[#1e3a5f] px-3 py-2 text-sm font-medium text-white hover:bg-[#2d4f7c]"
              >
                <Plus className="h-4 w-4" /> 新建提醒
              </button>
            </>
          )}
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <Search className="h-4 w-4 text-gray-400" />
            <label className="text-sm text-gray-700">日期:</label>
            <input
              type="date"
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
            />
            {dateFilter && (
              <button onClick={() => setDateFilter('')} className="text-sm text-gray-500 hover:text-gray-700">清除</button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-700">状态:</label>
            <select
              value={activeFilter}
              onChange={(e) => setActiveFilter(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
            >
              <option value="all">全部</option>
              <option value="true">启用中</option>
              <option value="false">已停用</option>
            </select>
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
        {loading ? (
          <div className="flex h-32 items-center justify-center text-gray-500">加载中...</div>
        ) : reminders.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-gray-500">暂无提醒数据</div>
        ) : (
          <div className="divide-y divide-gray-100">
            {reminders.map((r) => {
              const confirmed = isConfirmedByMe(r);
              const expired = isExpired(r);
              return (
                <div key={r.id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="font-medium text-[#1e3a5f">{r.title}</h3>
                        {r.is_active ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                            <CheckCircle2 className="h-3 w-3" /> 启用
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                            <XCircle className="h-3 w-3" /> 停用
                          </span>
                        )}
                        {expired && r.is_active && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-800">
                            已过期
                          </span>
                        )}
                        {confirmed && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                            <CheckCircle className="h-3 w-3" /> 已确认
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-sm text-gray-700 whitespace-pre-wrap">{r.content}</p>
                      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500">
                        {r.shift_name && (
                          <span className="flex items-center gap-1">
                            <BellRing className="h-3 w-3" /> {r.shift_name}
                            {r.shift_duty_person && <span>（值班人: {r.shift_duty_person}）</span>}
                          </span>
                        )}
                        <span>有效期: {formatDateTime(r.effective_start)} ~ {formatDateTime(r.effective_end)}</span>
                        <span>创建人: {r.created_by}</span>
                        {r.confirmations && r.confirmations.length > 0 && (
                          <span>已确认: {r.confirmations.map(c => c.confirmed_by).join('、')}</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {canConfirm && r.is_active && !expired && !confirmed && (
                        <button
                          onClick={() => handleConfirm(r)}
                          disabled={confirmingId === r.id}
                          className="flex items-center gap-1 rounded bg-blue-600 px-2 py-1 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                        >
                          <CheckCircle className="h-3.5 w-3.5" /> {confirmingId === r.id ? '确认中...' : '确认提醒'}
                        </button>
                      )}
                      {canManage && (
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => openEdit(r)}
                            className="flex items-center gap-1 rounded px-2 py-1 text-xs text-[#1e3a5f] hover:bg-blue-50"
                          >
                            <Pencil className="h-3.5 w-3.5" /> 编辑
                          </button>
                          {r.is_active && (
                            <button
                              onClick={() => handleDisable(r)}
                              className="flex items-center gap-1 rounded px-2 py-1 text-xs text-red-600 hover:bg-red-50"
                            >
                              <Ban className="h-3.5 w-3.5" /> 停用
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-lg bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
              <h3 className="text-lg font-semibold text-gray-900">
                {editingReminder ? '编辑提醒' : '新建提醒'}
              </h3>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4 p-6">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  提醒标题 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="请输入提醒标题"
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  提醒内容 <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={formData.content}
                  onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                  rows={3}
                  placeholder="请输入提醒内容"
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
                />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700">关联班次</label>
                  <select
                    value={formData.shift_id || ''}
                    onChange={(e) => setFormData({ ...formData, shift_id: e.target.value ? Number(e.target.value) : null })}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
                  >
                    <option value="">不关联班次</option>
                    {shifts.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}（{s.duty_person}）
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">班次日期</label>
                  <input
                    type="date"
                    value={formData.shift_date}
                    onChange={(e) => setFormData({ ...formData, shift_date: e.target.value })}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
                  />
                </div>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    生效开始时间 <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="datetime-local"
                    value={formData.effective_start}
                    onChange={(e) => setFormData({ ...formData, effective_start: e.target.value })}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    生效结束时间 <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="datetime-local"
                    value={formData.effective_end}
                    onChange={(e) => setFormData({ ...formData, effective_end: e.target.value })}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="h-4 w-4"
                />
                <label htmlFor="is_active" className="text-sm text-gray-700">立即启用</label>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="rounded-lg bg-[#1e3a5f] px-4 py-2 text-sm font-medium text-white hover:bg-[#2d4f7c] disabled:opacity-50"
                >
                  {submitting ? '提交中...' : (editingReminder ? '保存修改' : '创建')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
