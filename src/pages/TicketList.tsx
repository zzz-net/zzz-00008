import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Download, Eye, Edit, ChevronLeft, ChevronRight } from 'lucide-react';
import { ticketApi, exportApi } from '@/services/api';
import { useToast } from '@/hooks/useToast';
import FilterBar from '@/components/FilterBar';
import SeverityBadge from '@/components/SeverityBadge';
import StatusBadge from '@/components/StatusBadge';
import { formatDateTime } from '@/utils/format';
import { useAuthStore } from '@/store/useAuthStore';
import type { Ticket, TicketStatus, Severity } from '@/types';

export default function TicketList() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [filters, setFilters] = useState<{ status?: TicketStatus; severity?: Severity; assignee?: string }>({});
  const navigate = useNavigate();
  const showToast = useToast((state) => state.showToast);
  const hasPermission = useAuthStore((state) => state.hasPermission);

  const fetchTickets = useCallback(async () => {
    try {
      setLoading(true);
      const res = await ticketApi.getList({
        ...filters,
        page,
        page_size: pageSize,
      });
      if (res.success && res.data) {
        setTickets(res.data.items);
        setTotal(res.data.total);
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : '获取工单列表失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [filters, page, pageSize, showToast]);

  useEffect(() => {
    fetchTickets();
  }, [fetchTickets]);

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-[#1e3a5f]">工单管理</h1>
        <div className="flex gap-2">
          <button
            onClick={() => exportApi.exportTickets({ format: 'csv', ...filters })}
            className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <Download className="h-4 w-4" />
            导出 CSV
          </button>
          <button
            onClick={() => exportApi.exportTickets({ format: 'json', ...filters })}
            className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <Download className="h-4 w-4" />
            导出 JSON
          </button>
          {hasPermission('create_tickets') && (
            <button
              onClick={() => navigate('/tickets/create')}
              className="flex items-center gap-2 rounded-lg bg-[#1e3a5f] px-4 py-2 text-sm font-medium text-white hover:bg-[#2d4f7c]"
            >
              <Plus className="h-4 w-4" />
              新建工单
            </button>
          )}
        </div>
      </div>

      <FilterBar onFilterChange={setFilters} />

      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="text-gray-500">加载中...</div>
        </div>
      ) : (
        <>
          <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">ID</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">客户</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">严重级别</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">责任人</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">截止时间</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">状态</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">创建时间</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {tickets.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-gray-500">
                      暂无工单数据
                    </td>
                  </tr>
                ) : (
                  tickets.map((ticket) => (
                    <tr key={ticket.id} className="hover:bg-gray-50">
                      <td className="whitespace-nowrap px-4 py-4 text-sm font-medium text-[#1e3a5f]">#{ticket.id}</td>
                      <td className="whitespace-nowrap px-4 py-4 text-sm text-gray-900">{ticket.customer_name}</td>
                      <td className="whitespace-nowrap px-4 py-4">
                        <SeverityBadge severity={ticket.severity} />
                      </td>
                      <td className="whitespace-nowrap px-4 py-4 text-sm text-gray-900">{ticket.assignee}</td>
                      <td className="whitespace-nowrap px-4 py-4 text-sm text-gray-900">{formatDateTime(ticket.deadline)}</td>
                      <td className="whitespace-nowrap px-4 py-4">
                        <StatusBadge status={ticket.status} />
                      </td>
                      <td className="whitespace-nowrap px-4 py-4 text-sm text-gray-500">{formatDateTime(ticket.created_at)}</td>
                      <td className="whitespace-nowrap px-4 py-4">
                        <div className="flex gap-2">
                          <button
                            onClick={() => navigate(`/tickets/${ticket.id}`)}
                            className="flex items-center gap-1 rounded px-2 py-1 text-sm text-[#1e3a5f] hover:bg-gray-100"
                          >
                            <Eye className="h-4 w-4" />
                            查看详情
                          </button>
                          {hasPermission('update_progress') && (
                            <button
                              onClick={() => navigate(`/tickets/${ticket.id}`)}
                              className="flex items-center gap-1 rounded px-2 py-1 text-sm text-[#1e3a5f] hover:bg-gray-100"
                            >
                              <Edit className="h-4 w-4" />
                              编辑进展
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-500">
                共 {total} 条，第 {page} / {totalPages} 页
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="flex items-center gap-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm disabled:opacity-50 hover:bg-gray-50"
                >
                  <ChevronLeft className="h-4 w-4" />
                  上一页
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="flex items-center gap-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm disabled:opacity-50 hover:bg-gray-50"
                >
                  下一页
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
