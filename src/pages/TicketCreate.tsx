import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Save } from 'lucide-react';
import { ticketApi } from '@/services/api';
import { useToast } from '@/hooks/useToast';
import { useAuthStore } from '@/store/useAuthStore';
import { severityMap, type Severity } from '@/types';

interface FormData {
  customer_name: string;
  severity: Severity | '';
  assignee: string;
  deadline: string;
  progress: string;
}

interface FormErrors {
  customer_name?: string;
  severity?: string;
  assignee?: string;
  deadline?: string;
}

export default function TicketCreate() {
  const [formData, setFormData] = useState<FormData>({
    customer_name: '',
    severity: '',
    assignee: '',
    deadline: '',
    progress: '',
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const showToast = useToast((state) => state.showToast);
  const fetchUsers = useAuthStore((state) => state.fetchUsers);
  const users = useAuthStore((state) => state.users);
  const user = useAuthStore((state) => state.user);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const validate = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.customer_name.trim()) {
      newErrors.customer_name = '请输入客户名称';
    }
    if (!formData.severity) {
      newErrors.severity = '请选择严重级别';
    }
    if (!formData.assignee) {
      newErrors.assignee = '请选择责任人';
    }
    if (!formData.deadline) {
      newErrors.deadline = '请选择截止时间';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) {
      showToast('请填写所有必填项', 'error');
      return;
    }

    try {
      setLoading(true);
      const res = await ticketApi.create({
        customer_name: formData.customer_name,
        severity: formData.severity,
        assignee: formData.assignee,
        deadline: formData.deadline,
        progress: formData.progress || undefined,
      });

      if (res.success) {
        showToast('工单创建成功', 'success');
        navigate('/tickets');
      } else {
        showToast(res.error || '创建失败', 'error');
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '创建失败', 'error');
    } finally {
      setLoading(false);
    }
  };

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
        <h1 className="text-2xl font-bold text-[#1e3a5f]">创建工单</h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <div className="grid gap-6 md:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              客户名称 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={formData.customer_name}
              onChange={(e) => setFormData({ ...formData, customer_name: e.target.value })}
              className={`mt-1 block w-full rounded-lg border px-3 py-2 text-sm ${
                errors.customer_name ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : 'border-gray-300 focus:border-[#1e3a5f] focus:ring-[#1e3a5f]'
              } focus:outline-none focus:ring-1`}
              placeholder="请输入客户名称"
            />
            {errors.customer_name && (
              <p className="mt-1 text-sm text-red-500">{errors.customer_name}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              严重级别 <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.severity}
              onChange={(e) => setFormData({ ...formData, severity: e.target.value as Severity })}
              className={`mt-1 block w-full rounded-lg border px-3 py-2 text-sm ${
                errors.severity ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : 'border-gray-300 focus:border-[#1e3a5f] focus:ring-[#1e3a5f]'
              } focus:outline-none focus:ring-1`}
            >
              <option value="">请选择严重级别</option>
              {Object.entries(severityMap).map(([key, val]) => (
                <option key={key} value={key}>
                  {val.label}
                </option>
              ))}
            </select>
            {errors.severity && <p className="mt-1 text-sm text-red-500">{errors.severity}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              责任人 <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.assignee}
              onChange={(e) => setFormData({ ...formData, assignee: e.target.value })}
              className={`mt-1 block w-full rounded-lg border px-3 py-2 text-sm ${
                errors.assignee ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : 'border-gray-300 focus:border-[#1e3a5f] focus:ring-[#1e3a5f]'
              } focus:outline-none focus:ring-1`}
            >
              <option value="">请选择责任人</option>
              {Object.entries(users).map(([username, info]) => (
                <option key={username} value={username}>
                  {info.name} ({username})
                </option>
              ))}
            </select>
            {errors.assignee && <p className="mt-1 text-sm text-red-500">{errors.assignee}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              截止时间 <span className="text-red-500">*</span>
            </label>
            <input
              type="datetime-local"
              value={formData.deadline}
              onChange={(e) => setFormData({ ...formData, deadline: e.target.value })}
              className={`mt-1 block w-full rounded-lg border px-3 py-2 text-sm ${
                errors.deadline ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : 'border-gray-300 focus:border-[#1e3a5f] focus:ring-[#1e3a5f]'
              } focus:outline-none focus:ring-1`}
            />
            {errors.deadline && <p className="mt-1 text-sm text-red-500">{errors.deadline}</p>}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">进展描述</label>
          <textarea
            value={formData.progress}
            onChange={(e) => setFormData({ ...formData, progress: e.target.value })}
            rows={4}
            className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
            placeholder="请输入进展描述（选填）"
          />
        </div>

        <div className="flex justify-end gap-3 pt-4">
          <button
            type="button"
            onClick={() => navigate('/tickets')}
            className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            取消
          </button>
          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 rounded-lg bg-[#1e3a5f] px-4 py-2 text-sm font-medium text-white hover:bg-[#2d4f7c] disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {loading ? '提交中...' : '提交'}
          </button>
        </div>
      </form>
    </div>
  );
}
