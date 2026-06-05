import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Download, Eye, Filter } from 'lucide-react';
import { batchApi, exportApi } from '@/services/api';
import { useToast } from '@/hooks/useToast';
import { useAuthStore } from '@/store/useAuthStore';
import BatchStatusBadge from '@/components/BatchStatusBadge';
import { formatDateTime } from '@/utils/format';
import { batchStatusMap } from '@/types';
import type { HandoverBatch, BatchStatus } from '@/types';

export default function BatchList() {
  const [batches, setBatches] = useState<HandoverBatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<BatchStatus | ''>('');
  const navigate = useNavigate();
  const showToast = useToast((state) => state.showToast);
  const hasPermission = useAuthStore((state) => state.hasPermission);

  const fetchBatches = async () => {
    try {
      setLoading(true);
      const params = statusFilter ? { status: statusFilter } : undefined;
      const res = await batchApi.getList(params);
      if (res.success && res.data) {
        setBatches(res.data);
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '获取批次列表失败', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBatches();
  }, [statusFilter, showToast]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-[#1e3a5f]">交接批次管理</h1>
        <div className="flex gap-2">
          <button
            onClick={() => exportApi.exportBatches({ format: 'csv', status: statusFilter || undefined })}
            className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <Download className="h-4 w-4" />
            导出 CSV
          </button>
          <button
            onClick={() => exportApi.exportBatches({ format: 'json', status: statusFilter || undefined })}
            className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <Download className="h-4 w-4" />
            导出 JSON
          </button>
          {hasPermission('create_batches') && (
            <button
              onClick={() => navigate('/batches/create')}
              className="flex items-center gap-2 rounded-lg bg-[#1e3a5f] px-4 py-2 text-sm font-medium text-white hover:bg-[#2d4f7c]"
            >
              <Plus className="h-4 w-4" />
              创建批次
            </button>
          )}
        </div>
      </div>

      <div className="flex items-center gap-4 rounded-lg border border-gray-200 bg-white p-4">
        <div className="flex items-center gap-2 text-gray-500">
          <Filter className="h-4 w-4" />
          <span className="text-sm font-medium">筛选</span>
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as BatchStatus | '')}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-[#1e3a5f] focus:outline-none focus:ring-1 focus:ring-[#1e3a5f]"
        >
          <option value="">全部状态</option>
          {Object.entries(batchStatusMap).map(([key, val]) => (
            <option key={key} value={key}>
              {val.label}
            </option>
          ))}
        </select>
        {statusFilter && (
          <button
            onClick={() => setStatusFilter('')}
            className="ml-auto rounded-lg px-3 py-2 text-sm text-gray-500 hover:bg-gray-100 hover:text-gray-700"
          >
            清除筛选
          </button>
        )}
      </div>

      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="text-gray-500">加载中...</div>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">ID</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">批次名称</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">状态</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">交班人</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">接班人</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">工单数量</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">创建时间</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {batches.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-gray-500">
                    暂无批次数据
                  </td>
                </tr>
              ) : (
                  batches.map((batch) => (
                    <tr key={batch.id} className="hover:bg-gray-50">
                      <td className="whitespace-nowrap px-4 py-4 text-sm font-medium text-[#1e3a5f]">#{batch.id}</td>
                      <td className="whitespace-nowrap px-4 py-4 text-sm text-gray-900">{batch.name}</td>
                      <td className="whitespace-nowrap px-4 py-4">
                        <BatchStatusBadge status={batch.status} />
                      </td>
                      <td className="whitespace-nowrap px-4 py-4 text-sm text-gray-900">{batch.handover_person}</td>
                      <td className="whitespace-nowrap px-4 py-4 text-sm text-gray-900">
                        {batch.receiver_person || '-'}
                      </td>
                      <td className="whitespace-nowrap px-4 py-4 text-sm text-gray-900">
                        {batch.ticket_ids.length}
                      </td>
                      <td className="whitespace-nowrap px-4 py-4 text-sm text-gray-500">
                        {formatDateTime(batch.created_at)}
                      </td>
                      <td className="whitespace-nowrap px-4 py-4">
                        <button
                          onClick={() => navigate(`/batches/${batch.id}`)}
                          className="flex items-center gap-1 rounded px-2 py-1 text-sm text-[#1e3a5f] hover:bg-gray-100"
                        >
                          <Eye className="h-4 w-4" />
                          查看详情
                        </button>
                      </td>
                    </tr>
                  ))
                )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
