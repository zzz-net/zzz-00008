import { useState, useEffect, useRef } from 'react';
import { Plus, Pencil, Ban, Download, Upload, Search, X, CheckCircle2, XCircle } from 'lucide-react';
import { shiftApi, exportApi } from '@/services/api';
import { useToast } from '@/hooks/useToast';
import { useAuthStore } from '@/store/useAuthStore';
import { formatDateTime } from '@/utils/format';
import SeverityBadge from '@/components/SeverityBadge';
import type { DutyShift, Severity } from '@/types';

interface ShiftFormData {
  name: string;
  duty_person: string;
  start_time: string;
  end_time: string;
  allowed_severities: Severity[];
  is_active: boolean;
}

const SEVERITY_OPTIONS: Severity[] = ['low', 'medium', 'high', 'critical'];

function toLocalInputValue(iso: string): string {
  if (!iso) return '';
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fromLocalInputValue(v: string): string {
  if (!v) return '';
  return new Date(v).toISOString();
}

const defaultFormData: ShiftFormData = {
  name: '',
  duty_person: '',
  start_time: '',
  end_time: '',
  allowed_severities: ['low', 'medium', 'high', 'critical'],
  is_active: true,
};

export default function ShiftList() {
  const [shifts, setShifts] = useState<DutyShift[]>([]);
  const [loading, setLoading] = useState(true);
  const [dateFilter, setDateFilter] = useState('');
  const [activeFilter, setActiveFilter] = useState<string>('all');
  const [showModal, setShowModal] = useState(false);
  const [editingShift, setEditingShift] = useState<DutyShift | null>(null);
  const [formData, setFormData] = useState<ShiftFormData>(defaultFormData);
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);

  const showToast = useToast((s) => s.showToast);
  const user = useAuthStore((s) => s.user);
  const canManage = useAuthStore((s) => s.hasPermission('manage_shifts'));

  const fetchShifts = async () => {
    try {
      setLoading(true);
      const params: Record<string, any> = {};
      if (dateFilter) params.date = dateFilter;
      if (activeFilter !== 'all') params.is_active = activeFilter === 'true';
      const res = await shiftApi.getList(params);
      if (res.success && res.data) setShifts(res.data);
    } catch (e) {
      showToast(e instanceof Error ? e.message : '获取排班列表失败', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchShifts(); }, [dateFilter, activeFilter]);

  const openCreate = () => {
    setEditingShift(null);
    setFormData(defaultFormData);
    setShowModal(true);
  };

  const openEdit = (shift: DutyShift) => {
    setEditingShift(shift);
    setFormData({
      name: shift.name,
      duty_person: shift.duty_person,
      start_time: toLocalInputValue(shift.start_time),
      end_time: toLocalInputValue(shift.end_time),
      allowed_severities: [...shift.allowed_severities],
      is_active: shift.is_active,
    });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim() || !formData.duty_person.trim() || !formData.start_time || !formData.end_time) {
      showToast('请填写所有必填项', 'error');
      return;
    }
    try {
      setSubmitting(true);
      const payload = {
        ...formData,
        start_time: fromLocalInputValue(formData.start_time),
        end_time: fromLocalInputValue(formData.end_time),
      };
      let res;
      if (editingShift) {
        res = await shiftApi.update(editingShift.id, payload);
      } else {
        res = await shiftApi.create(payload);
      }
      if (res.success) {
        showToast(editingShift ? '班次更新成功' : '班次创建成功', 'success');
        setShowModal(false);
        fetchShifts();
      } else {
        showToast(res.error || '操作失败', 'error');
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '操作失败', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDisable = async (shift: DutyShift) => {
    if (!window.confirm(`确定停用班次「${shift.name}」吗？`)) return;
    try {
      const res = await shiftApi.disable(shift.id);
      if (res.success) {
        showToast('班次已停用', 'success');
        fetchShifts();
      } else {
        showToast(res.error || '停用失败', 'error');
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '停用失败', 'error');
    }
  };

  const handleExport = () => {
    const params: Record<string, any> = { format: 'csv' };
    if (dateFilter) params.date = dateFilter;
    exportApi.exportShifts(params);
  };

  const handleImportClick = () => fileInputRef.current?.click();

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      setImporting(true);
      const res = await shiftApi.importCsv(file);
      if (res.success && res.data) {
        const { imported, skipped, total } = res.data;
        let msg = `成功导入 ${imported}/${total} 条`;
        if (skipped && skipped.length) msg += `，跳过 ${skipped.length} 条`;
        showToast(msg, 'success');
        fetchShifts();
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

  const toggleSeverity = (s: Severity) => {
    setFormData((prev) => ({
      ...prev,
      allowed_severities: prev.allowed_severities.includes(s)
        ? prev.allowed_severities.filter((x) => x !== s)
        : [...prev.allowed_severities, s],
    }));
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-[#1e3a5f]">值班排班</h1>
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
                <Plus className="h-4 w-4" /> 新建班次
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
        ) : shifts.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-gray-500">暂无排班数据</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left text-gray-600">
                <tr>
                  <th className="px-4 py-3 font-medium">ID</th>
                  <th className="px-4 py-3 font-medium">班次名称</th>
                  <th className="px-4 py-3 font-medium">值班人</th>
                  <th className="px-4 py-3 font-medium">开始时间</th>
                  <th className="px-4 py-3 font-medium">结束时间</th>
                  <th className="px-4 py-3 font-medium">可接收级别</th>
                  <th className="px-4 py-3 font-medium">状态</th>
                  <th className="px-4 py-3 font-medium">创建人</th>
                  {canManage && <th className="px-4 py-3 font-medium">操作</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {shifts.map((s) => (
                  <tr key={s.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-500">{s.id}</td>
                    <td className="px-4 py-3 font-medium text-[#1e3a5f]">{s.name}</td>
                    <td className="px-4 py-3">{s.duty_person}</td>
                    <td className="px-4 py-3 text-gray-600">{formatDateTime(s.start_time)}</td>
                    <td className="px-4 py-3 text-gray-600">{formatDateTime(s.end_time)}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {s.allowed_severities.map((sev) => (
                          <SeverityBadge key={sev} severity={sev} />
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {s.is_active ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">
                          <CheckCircle2 className="h-3 w-3" /> 启用
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600">
                          <XCircle className="h-3 w-3" /> 停用
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-500">{s.created_by}</td>
                    {canManage && (
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => openEdit(s)}
                            className="flex items-center gap-1 rounded px-2 py-1 text-sm text-[#1e3a5f] hover:bg-blue-50"
                          >
                            <Pencil className="h-3.5 w-3.5" /> 编辑
                          </button>
                          {s.is_active && (
                            <button
                              onClick={() => handleDisable(s)}
                              className="flex items-center gap-1 rounded px-2 py-1 text-sm text-red-600 hover:bg-red-50"
                            >
                              <Ban className="h-3.5 w-3.5" /> 停用
                            </button>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-lg bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
              <h3 className="text-lg font-semibold text-gray-900">
                {editingShift ? '编辑班次' : '新建班次'}
              </h3>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4 p-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    班次名称 <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="如：2026-06-05 白班"
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    值班人 <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.duty_person}
                    onChange={(e) => setFormData({ ...formData, duty_person: e.target.value })}
                    placeholder="值班人姓名"
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
                  />
                </div>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    开始时间 <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="datetime-local"
                    value={formData.start_time}
                    onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    结束时间 <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="datetime-local"
                    value={formData.end_time}
                    onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">可接收严重级别</label>
                <div className="flex flex-wrap gap-2">
                  {SEVERITY_OPTIONS.map((s) => {
                    const checked = formData.allowed_severities.includes(s);
                    return (
                      <label
                        key={s}
                        className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-1.5 text-sm transition-colors ${
                          checked ? 'border-[#1e3a5f] bg-blue-50 text-[#1e3a5f]' : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleSeverity(s)}
                          className="h-3.5 w-3.5"
                        />
                        <SeverityBadge severity={s} />
                      </label>
                    );
                  })}
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
                  {submitting ? '提交中...' : (editingShift ? '保存修改' : '创建')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
