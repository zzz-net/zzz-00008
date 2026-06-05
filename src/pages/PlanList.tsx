import { useState, useEffect, useRef } from 'react';
import {
  Plus, Pencil, Ban, Play, Download, Upload, Search, X,
  CheckCircle2, XCircle, History, BookOpen, Tag
} from 'lucide-react';
import { planApi } from '@/services/api';
import { useToast } from '@/hooks/useToast';
import { useAuthStore } from '@/store/useAuthStore';
import SeverityBadge from '@/components/SeverityBadge';
import { formatDateTime } from '@/utils/format';
import type { UpgradePlan, Severity } from '@/types';
import { severityMap } from '@/types';

interface PlanFormData {
  title: string;
  applicable_severity: Severity | '';
  keywords: string[];
  steps: string;
  assignee_suggestion: string;
  is_active: boolean;
}

const defaultFormData: PlanFormData = {
  title: '',
  applicable_severity: '',
  keywords: [],
  steps: '',
  assignee_suggestion: '',
  is_active: true,
};

export default function PlanList() {
  const [plans, setPlans] = useState<UpgradePlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [activeFilter, setActiveFilter] = useState<string>('all');
  const [keywordFilter, setKeywordFilter] = useState('');
  const [titleFilter, setTitleFilter] = useState('');

  const [showModal, setShowModal] = useState(false);
  const [editingPlan, setEditingPlan] = useState<UpgradePlan | null>(null);
  const [formData, setFormData] = useState<PlanFormData>(defaultFormData);
  const [keywordInput, setKeywordInput] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const [showVersionModal, setShowVersionModal] = useState(false);
  const [versions, setVersions] = useState<UpgradePlan[]>([]);
  const [versionsLoading, setVersionsLoading] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);

  const showToast = useToast((s) => s.showToast);
  const canManage = useAuthStore((s) => s.hasPermission('manage_plans'));
  const canReference = useAuthStore((s) => s.hasPermission('reference_plans'));

  const fetchPlans = async () => {
    try {
      setLoading(true);
      const params: Record<string, any> = { only_latest: true };
      if (severityFilter !== 'all') params.severity = severityFilter;
      if (activeFilter !== 'all') params.is_active = activeFilter === 'true';
      if (keywordFilter.trim()) params.keyword = keywordFilter.trim();
      if (titleFilter.trim()) params.title = titleFilter.trim();
      const res = await planApi.getList(params);
      if (res.success && res.data) setPlans(res.data);
    } catch (e) {
      showToast(e instanceof Error ? e.message : '获取预案列表失败', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchPlans(); }, [severityFilter, activeFilter, keywordFilter, titleFilter]);

  const openCreate = () => {
    setEditingPlan(null);
    setFormData(defaultFormData);
    setKeywordInput('');
    setShowModal(true);
  };

  const openEdit = (plan: UpgradePlan) => {
    setEditingPlan(plan);
    setFormData({
      title: plan.title,
      applicable_severity: plan.applicable_severity,
      keywords: [...plan.keywords],
      steps: plan.steps,
      assignee_suggestion: plan.assignee_suggestion || '',
      is_active: plan.is_active,
    });
    setKeywordInput('');
    setShowModal(true);
  };

  const addKeyword = () => {
    const kw = keywordInput.trim();
    if (!kw) return;
    if (formData.keywords.includes(kw)) {
      showToast('关键词已存在', 'warning');
      return;
    }
    setFormData({ ...formData, keywords: [...formData.keywords, kw] });
    setKeywordInput('');
  };

  const removeKeyword = (kw: string) => {
    setFormData({ ...formData, keywords: formData.keywords.filter((k) => k !== kw) });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title.trim() || !formData.applicable_severity || formData.keywords.length === 0 || !formData.steps.trim()) {
      showToast('请填写所有必填项', 'error');
      return;
    }
    try {
      setSubmitting(true);
      const payload = {
        ...formData,
        applicable_severity: formData.applicable_severity,
        assignee_suggestion: formData.assignee_suggestion.trim() || undefined,
      };
      let res;
      if (editingPlan) {
        res = await planApi.update(editingPlan.id, payload);
      } else {
        res = await planApi.create(payload);
      }
      if (res.success) {
        showToast(editingPlan ? '预案已更新，生成新版本' : '预案创建成功', 'success');
        setShowModal(false);
        fetchPlans();
      } else {
        showToast(res.error || '操作失败', 'error');
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '操作失败', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDisable = async (plan: UpgradePlan) => {
    if (!window.confirm(`确定停用预案「${plan.title}」（v${plan.version}）吗？`)) return;
    try {
      const res = await planApi.disable(plan.id);
      if (res.success) {
        showToast('预案已停用', 'success');
        fetchPlans();
      } else {
        showToast(res.error || '停用失败', 'error');
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '停用失败', 'error');
    }
  };

  const handleEnable = async (plan: UpgradePlan) => {
    if (!window.confirm(`确定启用预案「${plan.title}」（v${plan.version}）吗？`)) return;
    try {
      const res = await planApi.enable(plan.id);
      if (res.success) {
        showToast('预案已启用', 'success');
        fetchPlans();
      } else {
        showToast(res.error || '启用失败', 'error');
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '启用失败', 'error');
    }
  };

  const showVersionHistory = async (plan: UpgradePlan) => {
    try {
      setVersionsLoading(true);
      setShowVersionModal(true);
      const res = await planApi.getVersions(plan.plan_group_id);
      if (res.success && res.data) setVersions(res.data);
    } catch (e) {
      showToast(e instanceof Error ? e.message : '获取版本历史失败', 'error');
    } finally {
      setVersionsLoading(false);
    }
  };

  const handleExport = () => {
    const params: Record<string, any> = {};
    if (severityFilter !== 'all') params.severity = severityFilter;
    if (activeFilter !== 'all') params.is_active = activeFilter === 'true';
    planApi.exportCsv(params);
  };

  const handleImportClick = () => fileInputRef.current?.click();

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      setImporting(true);
      const res = await planApi.importCsv(file);
      if (res.success && res.data) {
        const { imported, skipped, total } = res.data;
        let msg = `成功导入 ${imported}/${total} 条`;
        if (skipped && skipped.length) msg += `，跳过 ${skipped.length} 条`;
        showToast(msg, 'success');
        fetchPlans();
      } else {
        const details = (res as any).details;
        const err = res.error || '导入失败';
        showToast(details ? `${err}：${details.slice(0, 3).join('；')}` : err, 'error');
      }
    } catch (err) {
      showToast(err instanceof Error ? err.message : '导入失败', 'error');
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-[#1e3a5f]">
          <BookOpen className="mr-2 inline h-7 w-7" />
          升级预案库
        </h1>
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
                <Plus className="h-4 w-4" /> 新建预案
              </button>
            </>
          )}
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <Search className="h-4 w-4 text-gray-400" />
            <label className="text-sm text-gray-700">标题:</label>
            <input
              type="text"
              value={titleFilter}
              onChange={(e) => setTitleFilter(e.target.value)}
              placeholder="按标题搜索"
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
            />
          </div>
          <div className="flex items-center gap-2">
            <Tag className="h-4 w-4 text-gray-400" />
            <label className="text-sm text-gray-700">关键词:</label>
            <input
              type="text"
              value={keywordFilter}
              onChange={(e) => setKeywordFilter(e.target.value)}
              placeholder="按关键词搜索"
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
            />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-700">级别:</label>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
            >
              <option value="all">全部级别</option>
              {Object.entries(severityMap).map(([key, val]) => (
                <option key={key} value={key}>{val.label}</option>
              ))}
            </select>
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
          {(titleFilter || keywordFilter) && (
            <button
              onClick={() => { setTitleFilter(''); setKeywordFilter(''); }}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              清除筛选
            </button>
          )}
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
        {loading ? (
          <div className="flex h-32 items-center justify-center text-gray-500">加载中...</div>
        ) : plans.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-gray-500">暂无预案数据</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left text-gray-600">
                <tr>
                  <th className="px-4 py-3 font-medium">ID</th>
                  <th className="px-4 py-3 font-medium">预案标题</th>
                  <th className="px-4 py-3 font-medium">适用级别</th>
                  <th className="px-4 py-3 font-medium">关键词</th>
                  <th className="px-4 py-3 font-medium">版本</th>
                  <th className="px-4 py-3 font-medium">状态</th>
                  <th className="px-4 py-3 font-medium">创建人</th>
                  <th className="px-4 py-3 font-medium">更新时间</th>
                  <th className="px-4 py-3 font-medium">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {plans.map((p) => (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-500">{p.id}</td>
                    <td className="px-4 py-3 font-medium text-[#1e3a5f]">
                      <div>{p.title}</div>
                      {p.assignee_suggestion && (
                        <div className="mt-0.5 text-xs text-gray-500">建议负责人: {p.assignee_suggestion}</div>
                      )}
                    </td>
                    <td className="px-4 py-3"><SeverityBadge severity={p.applicable_severity} /></td>
                    <td className="px-4 py-3">
                      <div className="flex max-w-xs flex-wrap gap-1">
                        {p.keywords.slice(0, 4).map((kw) => (
                          <span key={kw} className="inline-flex items-center rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-700">
                            {kw}
                          </span>
                        ))}
                        {p.keywords.length > 4 && (
                          <span className="text-xs text-gray-500">+{p.keywords.length - 4}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-600">v{p.version}</td>
                    <td className="px-4 py-3">
                      {p.is_active ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">
                          <CheckCircle2 className="h-3 w-3" /> 启用
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600">
                          <XCircle className="h-3 w-3" /> 停用
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-500">{p.created_by}</td>
                    <td className="px-4 py-3 text-gray-500">{formatDateTime(p.updated_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap items-center gap-1">
                        <button
                          onClick={() => showVersionHistory(p)}
                          className="flex items-center gap-1 rounded px-2 py-1 text-sm text-purple-600 hover:bg-purple-50"
                          title="版本历史"
                        >
                          <History className="h-3.5 w-3.5" /> 历史
                        </button>
                        {canManage && (
                          <>
                            <button
                              onClick={() => openEdit(p)}
                              disabled={!p.is_latest}
                              className="flex items-center gap-1 rounded px-2 py-1 text-sm text-[#1e3a5f] hover:bg-blue-50 disabled:opacity-40"
                              title="编辑"
                            >
                              <Pencil className="h-3.5 w-3.5" /> 编辑
                            </button>
                            {p.is_active ? (
                              <button
                                onClick={() => handleDisable(p)}
                                disabled={!p.is_latest}
                                className="flex items-center gap-1 rounded px-2 py-1 text-sm text-red-600 hover:bg-red-50 disabled:opacity-40"
                                title="停用"
                              >
                                <Ban className="h-3.5 w-3.5" /> 停用
                              </button>
                            ) : (
                              <button
                                onClick={() => handleEnable(p)}
                                disabled={!p.is_latest}
                                className="flex items-center gap-1 rounded px-2 py-1 text-sm text-green-600 hover:bg-green-50 disabled:opacity-40"
                                title="启用"
                              >
                                <Play className="h-3.5 w-3.5" /> 启用
                              </button>
                            )}
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-2xl rounded-lg bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
              <h3 className="text-lg font-semibold text-gray-900">
                {editingPlan ? `编辑预案（将生成 v${editingPlan.version + 1}）` : '新建预案'}
              </h3>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4 p-6 max-h-[75vh] overflow-y-auto">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  预案标题 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="请输入预案标题"
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
                />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    适用严重级别 <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={formData.applicable_severity}
                    onChange={(e) => setFormData({ ...formData, applicable_severity: e.target.value as Severity })}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
                  >
                    <option value="">请选择严重级别</option>
                    {Object.entries(severityMap).map(([key, val]) => (
                      <option key={key} value={key}>{val.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">建议负责人（选填）</label>
                  <input
                    type="text"
                    value={formData.assignee_suggestion}
                    onChange={(e) => setFormData({ ...formData, assignee_suggestion: e.target.value })}
                    placeholder="建议由谁处理该类问题"
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  关键词 <span className="text-red-500">*</span>
                  <span className="ml-2 text-xs text-gray-500">（同一级别下启用预案的关键词不能完全重复）</span>
                </label>
                <div className="flex flex-wrap items-center gap-2">
                  <input
                    type="text"
                    value={keywordInput}
                    onChange={(e) => setKeywordInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') { e.preventDefault(); addKeyword(); }
                    }}
                    placeholder="输入关键词后回车添加"
                    className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
                  />
                  <button
                    type="button"
                    onClick={addKeyword}
                    className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                  >
                    添加
                  </button>
                </div>
                {formData.keywords.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {formData.keywords.map((kw) => (
                      <span
                        key={kw}
                        className="inline-flex items-center gap-1 rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-800"
                      >
                        {kw}
                        <button type="button" onClick={() => removeKeyword(kw)} className="text-blue-600 hover:text-blue-900">
                          <X className="h-3 w-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  处理步骤 <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={formData.steps}
                  onChange={(e) => setFormData({ ...formData, steps: e.target.value })}
                  rows={6}
                  placeholder="请详细描述处理步骤，每行一步"
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="plan_is_active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="h-4 w-4"
                />
                <label htmlFor="plan_is_active" className="text-sm text-gray-700">立即启用</label>
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
                  {submitting ? '提交中...' : (editingPlan ? '保存新版本' : '创建')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showVersionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-2xl rounded-lg bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
              <h3 className="text-lg font-semibold text-gray-900">
                <History className="mr-2 inline h-5 w-5" />
                版本历史
              </h3>
              <button onClick={() => setShowVersionModal(false)} className="text-gray-400 hover:text-gray-600">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="p-6 max-h-[65vh] overflow-y-auto">
              {versionsLoading ? (
                <div className="flex h-32 items-center justify-center text-gray-500">加载中...</div>
              ) : versions.length === 0 ? (
                <div className="flex h-32 items-center justify-center text-gray-500">暂无版本历史</div>
              ) : (
                <div className="space-y-3">
                  {versions.map((v, idx) => (
                    <div
                      key={v.id}
                      className={`rounded-lg border p-4 ${
                        v.is_latest ? 'border-[#1e3a5f] bg-blue-50' : 'border-gray-200 bg-white'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <span className="inline-flex items-center rounded-full bg-[#1e3a5f] px-2 py-0.5 font-mono text-xs text-white">
                            v{v.version}
                          </span>
                          {v.is_latest && (
                            <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                              最新版本
                            </span>
                          )}
                          {!v.is_active && (
                            <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                              已停用
                            </span>
                          )}
                        </div>
                        <span className="text-xs text-gray-500">{formatDateTime(v.created_at)}</span>
                      </div>
                      <h4 className="mt-2 font-medium text-gray-900">{v.title}</h4>
                      <div className="mt-1 flex items-center gap-2">
                        <SeverityBadge severity={v.applicable_severity} />
                        <span className="text-xs text-gray-500">创建人: {v.created_by}</span>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {v.keywords.map((kw) => (
                          <span key={kw} className="inline-flex items-center rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-700">
                            {kw}
                          </span>
                        ))}
                      </div>
                      <details className="mt-2">
                        <summary className="cursor-pointer text-xs text-gray-500 hover:text-gray-700">查看处理步骤</summary>
                        <pre className="mt-2 whitespace-pre-wrap rounded bg-gray-50 p-2 text-xs text-gray-700">{v.steps}</pre>
                      </details>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
