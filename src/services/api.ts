import axios from 'axios';
import type {
  Ticket, HandoverBatch, StatusHistory, UserInfo, RoleInfo,
  DashboardStats, TicketListResponse, ApiResponse, DutyShift, DutyReminder
} from '../types';

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  timeout: 10000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.data?.error) {
      return Promise.reject(new Error(error.response.data.error));
    }
    return Promise.reject(error);
  }
);

export const ticketApi = {
  getList: (params?: {
    status?: string;
    severity?: string;
    assignee?: string;
    page?: number;
    page_size?: number;
  }) => api.get<ApiResponse<TicketListResponse>>('/tickets', { params }).then(r => r.data),

  getOpenForHandover: () =>
    api.get<ApiResponse<Ticket[]>>('/tickets/open-for-handover').then(r => r.data),

  get: (id: number) =>
    api.get<ApiResponse<Ticket>>(`/tickets/${id}`).then(r => r.data),

  create: (data: {
    customer_name: string;
    severity: string;
    assignee: string;
    deadline: string;
    progress?: string;
  }) => api.post<ApiResponse<Ticket>>('/tickets', data).then(r => r.data),

  update: (id: number, data: {
    progress?: string;
    status?: string;
    assignee?: string;
    deadline?: string;
    reason?: string;
  }) => api.put<ApiResponse<Ticket>>(`/tickets/${id}`, data).then(r => r.data),

  close: (id: number) =>
    api.post<ApiResponse<Ticket>>(`/tickets/${id}/close`).then(r => r.data),
};

export const batchApi = {
  getList: (params?: { status?: string; is_revoked?: boolean }) =>
    api.get<ApiResponse<HandoverBatch[]>>('/batches', { params }).then(r => r.data),

  get: (id: number) =>
    api.get<ApiResponse<HandoverBatch>>(`/batches/${id}`).then(r => r.data),

  create: (data: {
    name: string;
    description?: string;
    ticket_ids: number[];
    handover_person: string;
    shift_id?: number;
  }) => api.post<ApiResponse<HandoverBatch>>('/batches', data).then(r => r.data),

  update: (id: number, data: {
    name?: string;
    description?: string;
    ticket_ids?: number[];
  }) => api.put<ApiResponse<HandoverBatch>>(`/batches/${id}`, data).then(r => r.data),

  confirm: (id: number, data?: { receiver_person?: string }) =>
    api.post<ApiResponse<HandoverBatch>>(`/batches/${id}/confirm`, data).then(r => r.data),

  return: (id: number, data?: { receiver_person?: string; reason?: string }) =>
    api.post<ApiResponse<HandoverBatch>>(`/batches/${id}/return`, data).then(r => r.data),

  resubmit: (id: number) =>
    api.post<ApiResponse<HandoverBatch>>(`/batches/${id}/resubmit`).then(r => r.data),

  revoke: (id: number, data: { reason: string }) =>
    api.post<ApiResponse<HandoverBatch>>(`/batches/${id}/revoke`, data).then(r => r.data),
};

export const historyApi = {
  getList: (params?: {
    entity_type?: string;
    entity_id?: number;
    limit?: number;
  }) => api.get<ApiResponse<StatusHistory[]>>('/history', { params }).then(r => r.data),
};

export const authApi = {
  getCurrentRole: () =>
    api.get<ApiResponse<UserInfo>>('/current-role').then(r => r.data),

  switchRole: (data: { role: string; username: string }) =>
    api.post<ApiResponse<UserInfo>>('/switch-role', data).then(r => r.data),

  getRoles: () =>
    api.get<ApiResponse<RoleInfo[]>>('/roles').then(r => r.data),

  getUsers: () =>
    api.get<ApiResponse<Record<string, { role: string; name: string }>>>('/users').then(r => r.data),
};

export const dashboardApi = {
  getStats: () =>
    api.get<ApiResponse<DashboardStats>>('/dashboard/stats').then(r => r.data),
};

export const exportApi = {
  exportTickets: (params?: { format?: string; status?: string; severity?: string }) => {
    const url = new URL('/api/export/tickets', window.location.origin);
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined) url.searchParams.append(k, v);
      });
    }
    window.open(url.toString(), '_blank');
  },

  exportBatches: (params?: { format?: string; status?: string; is_revoked?: boolean }) => {
    const url = new URL('/api/export/batches', window.location.origin);
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined) url.searchParams.append(k, String(v));
      });
    }
    window.open(url.toString(), '_blank');
  },

  exportShifts: (params?: { format?: string; date?: string }) => {
    const url = new URL('/api/shifts/export', window.location.origin);
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined) url.searchParams.append(k, String(v));
      });
    }
    window.open(url.toString(), '_blank');
  },

  exportReminders: (params?: { format?: string; date?: string }) => {
    const url = new URL('/api/reminders/export', window.location.origin);
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined) url.searchParams.append(k, String(v));
      });
    }
    window.open(url.toString(), '_blank');
  },
};

export const shiftApi = {
  getList: (params?: { date?: string; is_active?: boolean }) =>
    api.get<ApiResponse<DutyShift[]>>('/shifts', { params }).then(r => r.data),

  getActive: () =>
    api.get<ApiResponse<DutyShift[]>>('/shifts/active').then(r => r.data),

  get: (id: number) =>
    api.get<ApiResponse<DutyShift>>(`/shifts/${id}`).then(r => r.data),

  create: (data: {
    name: string;
    duty_person: string;
    start_time: string;
    end_time: string;
    allowed_severities?: string[];
    is_active?: boolean;
  }) => api.post<ApiResponse<DutyShift>>('/shifts', data).then(r => r.data),

  update: (id: number, data: {
    name?: string;
    duty_person?: string;
    start_time?: string;
    end_time?: string;
    allowed_severities?: string[];
    is_active?: boolean;
  }) => api.put<ApiResponse<DutyShift>>(`/shifts/${id}`, data).then(r => r.data),

  disable: (id: number) =>
    api.post<ApiResponse<DutyShift>>(`/shifts/${id}/disable`).then(r => r.data),

  importCsv: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post<ApiResponse<{ imported: number; skipped: string[]; total: number }>>(
      '/shifts/import', formData, { headers: { 'Content-Type': 'multipart/form-data' } }
    ).then(r => r.data);
  },
};

export const reminderApi = {
  getList: (params?: { date?: string; shift_id?: number; is_active?: boolean }) =>
    api.get<ApiResponse<DutyReminder[]>>('/reminders', { params }).then(r => r.data),

  getMyPending: () =>
    api.get<ApiResponse<DutyReminder[]>>('/reminders/my-pending').then(r => r.data),

  getForShift: (shiftId: number) =>
    api.get<ApiResponse<DutyReminder[]>>(`/reminders/for-shift/${shiftId}`).then(r => r.data),

  get: (id: number) =>
    api.get<ApiResponse<DutyReminder>>(`/reminders/${id}`).then(r => r.data),

  create: (data: {
    title: string;
    content: string;
    shift_id?: number | null;
    shift_date?: string | null;
    effective_start: string;
    effective_end: string;
    is_active?: boolean;
  }) => api.post<ApiResponse<DutyReminder>>('/reminders', data).then(r => r.data),

  update: (id: number, data: {
    title?: string;
    content?: string;
    shift_id?: number | null;
    shift_date?: string | null;
    effective_start?: string;
    effective_end?: string;
    is_active?: boolean;
  }) => api.put<ApiResponse<DutyReminder>>(`/reminders/${id}`, data).then(r => r.data),

  disable: (id: number) =>
    api.post<ApiResponse<DutyReminder>>(`/reminders/${id}/disable`).then(r => r.data),

  confirm: (id: number) =>
    api.post<ApiResponse<{ id: number; confirmed_by: string; confirmed_at: string }>>(
      `/reminders/${id}/confirm`
    ).then(r => r.data),

  importCsv: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post<ApiResponse<{ imported: number; skipped: string[]; total: number }>>(
      '/reminders/import', formData, { headers: { 'Content-Type': 'multipart/form-data' } }
    ).then(r => r.data);
  },
};

export default api;
