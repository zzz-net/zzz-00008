import { useState, useEffect } from 'react';
import { X, BookOpen, Search, Tag } from 'lucide-react';
import { planApi } from '@/services/api';
import { useToast } from '@/hooks/useToast';
import SeverityBadge from '@/components/SeverityBadge';
import type { UpgradePlan, Severity } from '@/types';
import { severityMap } from '@/types';

interface PlanReferenceModalProps {
  open: boolean;
  onClose: () => void;
  ticketId?: number;
  customerName?: string;
  severity?: Severity | '';
  progress?: string;
  onApply: (plan: UpgradePlan) => void;
  mode?: 'create' | 'detail';
}

export default function PlanReferenceModal({
  open, onClose, ticketId, customerName, severity, progress, onApply, mode }: PlanReferenceModalProps) {
  const [plans, setPlans] = useState<UpgradePlan[]>([]);
  const [loading, setLoading] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [keywordFilter, setKeywordFilter] = useState('');
  const [referencing, setReferencing] = useState<number | null>(null);

  const showToast = useToast((s) => s.showToast);

  const fetchPlans = async () => {
    try {
      setLoading(true);
      const hasMatch = customerName || severity || progress;
      let res;
      if (hasMatch && mode === 'create') {
        res = await planApi.getMatch({
          customer_name: customerName, severity: severity || undefined, progress });
      } else {
        const params: Record<string, any> = { is_active: true, only_latest: true };
        if (severityFilter !== 'all') params.severity = severityFilter;
        if (keywordFilter.trim()) params.keyword = keywordFilter.trim();
        res = await planApi.getList(params);
      }
      if (res.success && res.data) setPlans(res.data);
    } catch (e) {
      showToast(e instanceof Error ? e.message : '获取预案列表失败', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchPlans();
    }
  }, [open, severityFilter, keywordFilter]);

  const handleReference = async (plan: UpgradePlan) => {
    if (mode === 'detail' && ticketId) {
      try {
        setReferencing(plan.id);
        const res = await planApi.reference(plan.id, ticketId);
        if (res.success) {
          showToast(`已引用预案「${plan.title}」（v${plan.version}）`, 'success');
          onApply(plan);
          onClose();
        } else {
          showToast(res.error || '引用失败', 'error');
        }
      } catch (e) {
        showToast(e instanceof Error ? e.message : '引用失败', 'error');
      } finally {
        setReferencing(null);
      }
    } else {
      onApply(plan);
      onClose();
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-3xl rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h3 className="flex items-center gap-2 text-lg font-semibold text-gray-900">
            <BookOpen className="h-5 w-5 text-[#1e3a5f]" />
            引用升级预案
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="border-b border-gray-100 px-6 py-3">
          <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-700">级别:</label>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
            >
              <option value="all">全部</option>
              {Object.entries(severityMap).map(([key, val]) => (
                <option key={key} value={key}>{val.label}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <Search className="h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={keywordFilter}
              onChange={(e) => setKeywordFilter(e.target.value)}
              placeholder="按关键词搜索"
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
            />
          </div>
          {(customerName || severity) && mode === 'create' && (
            <span className="text-xs text-gray-500">根据当前表单智能匹配</span>
          )}
        </div>
        </div>

        <div className="max-h-[60vh] overflow-y-auto p-6">
          {loading ? (
            <div className="flex h-32 items-center justify-center text-gray-500">加载中...</div>
          ) : plans.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-gray-500">暂无可用的启用预案</div>
          ) : (
            <div className="space-y-3">
              {plans.map((plan) => (
                <div
                  key={plan.id} className="rounded-lg border border-gray-200 bg-white p-4 hover:border-[#1e3a5f] hover:shadow-sm transition-shadow">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium text-gray-900">{plan.title}</h4>
                        <SeverityBadge severity={plan.applicable_severity} />
                        <span className="font-mono text-xs text-gray-500">v{plan.version}</span>
                        {plan.match_score !== undefined && plan.match_score > 0 && (
                          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                            匹配度 {plan.match_score}
                          </span>
                        )}
                      </div>
                      {plan.assignee_suggestion && (
                        <div className="mt-1 text-xs text-gray-500">建议负责人: {plan.assignee_suggestion}</div>
                      )}
                      <div className="mt-2 flex flex-wrap gap-1">
                        {plan.keywords.map((kw) => (
                          <span
                            key={kw}
                            className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs ${
                              plan.matched_keywords?.includes(kw)
                                ? 'bg-green-100 text-green-800'
                                : 'bg-gray-100 text-gray-700'
                            }`}
                          >
                            <Tag className="h-3 w-3" />
                            {kw}
                          </span>
                        ))}
                      </div>
                      <details className="mt-2">
                        <summary className="cursor-pointer text-xs text-gray-500 hover:text-gray-700">
                          查看处理步骤
                        </summary>
                        <pre className="mt-2 whitespace-pre-wrap rounded bg-gray-50 p-2 text-xs text-gray-700">
                          {plan.steps}
                        </pre>
                      </details>
                    </div>
                    <button
                      onClick={() => handleReference(plan)}
                      disabled={referencing === plan.id}
                      className="ml-4 flex-shrink-0 rounded-lg bg-[#1e3a5f] px-3 py-1.5 text-xs font-medium text-white hover:bg-[#2d4f7c] disabled:opacity-50"
                    >
                      {referencing === plan.id ? '引用中...' : (mode === 'detail' ? '引用' : '套用')}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
